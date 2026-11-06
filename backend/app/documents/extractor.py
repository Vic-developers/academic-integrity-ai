import json
import math
import re
import sys
from importlib.metadata import version
from pathlib import Path
from app.config import settings
from app.documents.normalization import NORMALIZER, fragment
from app.documents.validation import DocumentError, validate_docx


def extract_txt(path: Path) -> dict:
    text = path.read_bytes().decode("utf-8-sig")
    if len(text) > settings().max_document_chars:
        raise DocumentError("text_limit")
    parts = []
    page = 1
    base = 0
    for page_text in text.split("\f"):
        for match in re.finditer(r"[^\r\n]+(?:\r?\n(?!\s*\r?\n)[^\r\n]+)*", page_text):
            if match.group().strip():
                parts.append(
                    fragment(
                        match.group(),
                        len(parts) + 1,
                        page=page,
                        locations=[
                            {
                                "kind": "txt",
                                "page_start": match.start(),
                                "page_end": match.end(),
                                "file_start": base + match.start(),
                                "file_end": base + match.end(),
                            }
                        ],
                    )
                )
        base += len(page_text) + 1
        page += 1
    return {
        "fragments": parts,
        "pages": page - 1,
        "metadata": {"encoding": "UTF-8"},
        "warnings": ["txt_pages_are_form_feed_sections"],
        "extractor": "txt-utf8-v1/" + NORMALIZER,
    }


def extract_docx(path: Path) -> dict:
    validate_docx(path)
    from docx import Document
    from docx.table import Table
    from docx.text.paragraph import Paragraph

    document = Document(path)
    fragments = []
    section = None
    chars = 0

    def paragraph(p: Paragraph, location: dict) -> None:
        nonlocal section, chars
        if not p.text.strip():
            return
        chars += len(p.text)
        if chars > settings().max_document_chars:
            raise DocumentError("text_limit")
        if p.style and p.style.name.startswith(("Heading", "Título")):
            section = p.text[:250]
        locations = []
        offset = 0
        for number, run in enumerate(p.runs):
            if run.text:
                locations.append(
                    {
                        **location,
                        "run": number,
                        "start": offset,
                        "end": offset + len(run.text),
                        "explicit_hidden": run.font.hidden is True,
                        "explicit_white": str(run.font.color.rgb or "") == "FFFFFF",
                        "font_size_pt": run.font.size.pt if run.font.size is not None else None,
                    }
                )
                offset += len(run.text)
        if offset != len(p.text):
            locations = [{**location, "start": 0, "end": len(p.text), "runs_reliable": False}]
        fragments.append(fragment(p.text, len(fragments) + 1, section=section, locations=locations))

    def blocks(container, part: str) -> None:
        for index, element in enumerate(container.iter_inner_content()):
            if isinstance(element, Paragraph):
                paragraph(element, {"kind": "docx", "part": part, "block": index})
            elif isinstance(element, Table):
                seen = set()
                for row_number, row in enumerate(element.rows):
                    for cell_number, cell in enumerate(row.cells):
                        # Merged cells have the same underlying XML object.
                        if cell._tc in seen:
                            continue
                        seen.add(cell._tc)
                        blocks(cell, f"{part}/table:{index}/row:{row_number}/cell:{cell_number}")

    blocks(document, "word/document.xml")
    seen_parts = set()
    for item in document.sections:
        for container in [item.header, item.footer]:
            part = str(container.part.partname)
            if part not in seen_parts:
                seen_parts.add(part)
                section = None
                blocks(container, part)
    props = document.core_properties
    metadata = {
        name: str(getattr(props, name) or "")[:1000]
        for name in ["author", "title", "subject", "last_modified_by", "revision", "created", "modified"]
    }
    from zipfile import ZipFile
    from defusedxml.ElementTree import fromstring

    with ZipFile(path) as archive:
        if "docProps/app.xml" in archive.namelist() and archive.getinfo("docProps/app.xml").file_size <= 65536:
            root = fromstring(archive.read("docProps/app.xml"))
            namespace = "{http://schemas.openxmlformats.org/officeDocument/2006/extended-properties}"
            for field in ["Application", "AppVersion"]:
                value = root.find(namespace + field)
                if value is not None and value.text:
                    metadata[field] = value.text[:1000]
    return {
        "fragments": fragments,
        "pages": None,
        "metadata": metadata,
        "warnings": [
            "docx_structured_view_not_word_pagination",
            "format_observations_explicit_only_not_rendered_visibility",
        ],
        "extractor": "python-docx/" + version("python-docx") + "/forensic-v1/" + NORMALIZER,
    }


def extract_pdf(path: Path) -> dict:
    import pdfplumber
    from pdfminer.pdfdocument import PDFPasswordIncorrect

    try:
        with pdfplumber.open(path) as document:
            if document.doc.encryption:
                raise DocumentError("encrypted_pdf")
            if len(document.pages) > settings().max_pdf_pages:
                raise DocumentError("page_limit")
            fragments, pages, warnings = [], [], []
            total = 0
            for page in document.pages:
                pages.append(
                    {
                        "number": page.page_number,
                        "width": page.width,
                        "height": page.height,
                        "rotation": page.rotation,
                        "bbox": list(page.bbox),
                        "coordinates": "pdfplumber-top-left-points",
                    }
                )
                words = page.extract_words(return_chars=True, expand_ligatures=False)
                if not words:
                    warnings.append(f"page_{page.page_number}_no_text_ocr_unavailable")
                    continue
                # Build deterministic line paragraphs; complex reading order remains an explicit limitation.
                lines: list[list[dict]] = []
                for word in words:
                    if not lines or abs(word["top"] - lines[-1][0]["top"]) > 3:
                        lines.append([])
                    lines[-1].append(word)
                for line in lines:
                    text_parts, locations, offset = [], [], 0
                    for word in line:
                        if text_parts:
                            offset += 1
                        value = word["text"]
                        text_parts.append(value)
                        locations.append(
                            {
                                "kind": "pdf_word",
                                "char_mapping_reliable": word["text"] == "".join(c["text"] for c in word["chars"]),
                                "font_size_min_pt": min(
                                    (
                                        float(c["size"])
                                        for c in word["chars"]
                                        if isinstance(c.get("size"), (int, float)) and math.isfinite(c["size"])
                                    ),
                                    default=None,
                                ),
                                "all_characters_white": bool(word["chars"])
                                and all(
                                    c.get("non_stroking_color") in (1, (1, 1, 1), [1, 1, 1]) for c in word["chars"]
                                ),
                                "start": offset,
                                "end": offset + len(value),
                                "bbox": [word["x0"], word["top"], word["x1"], word["bottom"]],
                                "chars": [
                                    {"text": c["text"], "bbox": [c["x0"], c["top"], c["x1"], c["bottom"]]}
                                    for c in word["chars"]
                                ],
                            }
                        )
                        offset += len(value)
                    original = " ".join(text_parts)
                    total += len(original)
                    if total > settings().max_document_chars:
                        raise DocumentError("text_limit")
                    fragments.append(fragment(original, len(fragments) + 1, page=page.page_number, locations=locations))
                page.close()
            metadata = {str(k): str(v)[:1000] for k, v in (document.metadata or {}).items()}
            metadata["pages"] = pages
            warnings.append("pdf_reading_order_and_line_paragraphs_require_review")
            return {
                "fragments": fragments,
                "pages": len(document.pages),
                "metadata": metadata,
                "warnings": warnings,
                "extractor": "pdfplumber/" + version("pdfplumber") + "/forensic-v1/" + NORMALIZER,
            }
    except PDFPasswordIncorrect as exc:
        raise DocumentError("encrypted_pdf") from exc
    except DocumentError:
        raise
    except Exception as exc:
        if isinstance(exc.__context__, PDFPasswordIncorrect) or any(
            isinstance(a, PDFPasswordIncorrect) for a in exc.args
        ):
            raise DocumentError("encrypted_pdf") from exc
        raise DocumentError("invalid_pdf") from exc


def extract(path: Path, format: str) -> dict:
    try:
        result = {"txt": extract_txt, "pdf": extract_pdf, "docx": extract_docx}[format](path)
        if not any(f["normalized"] for f in result["fragments"]) and format != "pdf":
            raise DocumentError("empty_document")
        result["partial"] = any("no_text_ocr_unavailable" in w for w in result["warnings"])
        return result
    except UnicodeError as exc:
        raise DocumentError("invalid_utf8") from exc


if __name__ == "__main__":
    from app.documents.sandbox import restrict

    try:
        try:
            restrict()
        except (OSError, RuntimeError):
            raise DocumentError("sandbox_unavailable") from None
        result = extract(Path(sys.argv[1]), sys.argv[2])
        print(json.dumps({"ok": True, **result}, ensure_ascii=False))
    except DocumentError as exc:
        print(json.dumps({"ok": False, "error": exc.code}))
    except BaseException:
        print(json.dumps({"ok": False, "error": "extraction_failed"}))
