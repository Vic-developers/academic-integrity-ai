import hashlib
import unicodedata
import zipfile
from pathlib import PurePosixPath
from fastapi import HTTPException
from defusedxml import ElementTree
from app.config import settings


class DocumentError(Exception):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


ERRORS = {
    "sandbox_unavailable": "El aislamiento del parser no está disponible; se bloqueó la extracción por seguridad.",
    "integrity_error": "El original almacenado no coincide con su hash; se detuvo la extracción.",
    "invalid_pdf": "El PDF está corrupto o no se puede interpretar.",
    "encrypted_pdf": "El PDF está cifrado; proporciona una copia autorizada sin contraseña.",
    "invalid_docx": "El DOCX está corrupto o no contiene una estructura Word válida.",
    "unsafe_docx": "El DOCX contiene entradas o relaciones no admitidas.",
    "invalid_utf8": "El TXT debe estar codificado como UTF-8 y contener texto válido.",
    "empty_document": "El documento no contiene texto utilizable.",
    "page_limit": "El PDF supera el límite de páginas permitido.",
    "text_limit": "El texto extraído supera el límite de procesamiento.",
    "extraction_timeout": "La extracción excedió el tiempo o los recursos permitidos.",
    "extraction_failed": "No se pudo extraer el archivo bajo los límites de seguridad.",
    "storage_unavailable": "El original no está disponible en el almacenamiento privado.",
    "worker_retries_exhausted": "La extracción se interrumpió repetidamente; requiere revisión.",
}


def safe_name(name: str) -> str:
    if not name or len(name) > 160 or "/" in name or "\\" in name or any(ord(c) < 32 for c in name):
        raise HTTPException(422, "El nombre de archivo no es válido")
    return name


def validate_docx(source) -> None:
    cfg = settings()
    try:
        with zipfile.ZipFile(source) as archive:
            info = archive.infolist()
            names = [entry.filename for entry in info]
            if len(info) > cfg.max_zip_entries or sum(e.file_size for e in info) > cfg.max_zip_bytes:
                raise DocumentError("unsafe_docx")
            if len(names) != len(set(names)):
                raise DocumentError("unsafe_docx")
            for entry in info:
                path = PurePosixPath(entry.filename)
                if path.is_absolute() or ".." in path.parts or "\\" in entry.filename or entry.flag_bits & 1:
                    raise DocumentError("unsafe_docx")
                if entry.file_size > cfg.max_zip_bytes or (
                    entry.file_size > 1024 * 1024 and entry.file_size > max(entry.compress_size, 1) * 200
                ):
                    raise DocumentError("unsafe_docx")
            required = {"[Content_Types].xml", "_rels/.rels", "word/document.xml"}
            if not required.issubset(names) or any(n.lower().endswith("vbaproject.bin") for n in names):
                raise DocumentError("invalid_docx")
            for entry in info:
                if entry.filename.endswith((".xml", ".rels")):
                    root = ElementTree.fromstring(archive.read(entry))
                    # Hyperlinks are retained as data; no external document/template/image is fetched.
                    for element in root.iter():
                        if element.attrib.get("TargetMode") == "External" and not element.attrib.get(
                            "Type", ""
                        ).endswith("/hyperlink"):
                            raise DocumentError("unsafe_docx")
            types = archive.read("[Content_Types].xml")
            if b"wordprocessingml.document.main+xml" not in types:
                raise DocumentError("invalid_docx")
            if archive.testzip() is not None:
                raise DocumentError("invalid_docx")
    except DocumentError:
        raise
    except Exception as exc:
        raise DocumentError("invalid_docx") from exc


def inspect(source, filename: str) -> tuple[str, int, str]:
    suffix = filename.rsplit(".", 1)[-1].lower()
    if suffix not in {"pdf", "docx", "txt"}:
        raise HTTPException(415, "Solo se admiten PDF, DOCX y TXT")
    source.seek(0)
    size, sha = 0, hashlib.sha256()
    while chunk := source.read(65536):
        size += len(chunk)
        if size > settings().max_file_bytes:
            raise HTTPException(413, "El archivo supera el límite configurado")
        sha.update(chunk)
    if size == 0:
        raise HTTPException(422, "El archivo está vacío")
    source.seek(0)
    head = source.read(8)
    if suffix == "pdf" and not head.startswith(b"%PDF-"):
        raise HTTPException(415, "El contenido no corresponde a un PDF")
    if suffix == "docx" and not head.startswith(b"PK\x03\x04"):
        raise HTTPException(415, "El contenido no corresponde a un DOCX")
    if suffix == "txt":
        source.seek(0)
        try:
            text = source.read().decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise HTTPException(422, ERRORS["invalid_utf8"]) from exc
        if not text.strip() or any(unicodedata.category(c) == "Cc" and c not in "\n\r\t\f" for c in text):
            raise HTTPException(422, ERRORS["invalid_utf8"])
        if text.lstrip().startswith(("%PDF-", "PK\x03\x04")):
            raise HTTPException(415, "El contenido no corresponde a TXT")
    source.seek(0)
    return suffix, size, sha.hexdigest()
