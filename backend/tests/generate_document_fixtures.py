"""Create labelled synthetic, valid documents for browser tests."""

import sys
from docx import Document as Docx
import io
from reportlab.pdfgen import canvas
from pathlib import Path
from document_fixtures import pdf_bytes, docx_bytes

root = Path(sys.argv[1])
root.mkdir(parents=True, exist_ok=True)
(root / "evidencia.txt").write_text(
    "Árbol, ß y ﬁ. Evidencia documental verificable.\n\nSegundo párrafo.", encoding="utf-8"
)
(root / "evidencia.pdf").write_bytes(pdf_bytes())
(root / "evidencia.docx").write_bytes(docx_bytes())
(root / "escaneado.pdf").write_bytes(pdf_bytes(scanned=True))
phrase = "La investigación académica exige evidencia verificable y revisión humana responsable."
(root / "literal-principal.txt").write_text(
    "Introducción singular propia. " + phrase + " Conclusión particular distinta.", encoding="utf-8"
)
(root / "literal-fuente.txt").write_text(
    "Referencia institucional anterior. " + phrase + " Cierre separado ajeno.", encoding="utf-8"
)
(root / "literal-distinto.txt").write_text(
    "La pedagogía colaborativa considera múltiples perspectivas sobre el aprendizaje. Este contenido emplea palabras diferentes y no reproduce secuencias largas del documento principal.",
    encoding="utf-8",
)
# Phase 4: original Unicode, multiple paragraphs, overlapping sources and PDF page navigation.

unicode_phrase = "Árbol ß ﬁ uno dos tres cuatro cinco seis siete ocho"
(root / "visor-unicode.txt").write_text(
    "🧭 Preámbulo propio. " + unicode_phrase + "\n\nNueve diez once doce trece catorce quince dieciséis. Final propio.",
    encoding="utf-8",
)
(root / "visor-unicode-fuente.txt").write_text(
    "árbol ss fi uno dos tres cuatro cinco seis siete ocho nueve diez once doce trece catorce quince dieciséis",
    encoding="utf-8",
)
doc = Docx()
doc.add_paragraph("Encabezamiento particular. " + unicode_phrase)
doc.add_paragraph("Nueve diez once doce trece catorce quince dieciséis. Final de otra fuente.")
doc.save(root / "visor-unicode.docx")
for rotated in [False, True]:
    out = io.BytesIO()
    pdf = canvas.Canvas(out)
    if rotated:
        pdf.setPageRotation(90)
    pdf.drawString(40, 750, "prefix La evidencia verificable exige una revision humana responsable ahora")
    pdf.showPage()
    pdf.drawString(40, 750, "con palabras finales que permiten comparar tambien la segunda pagina suffix")
    pdf.save()
    (root / ("visor-rotado.pdf" if rotated else "visor.pdf")).write_bytes(out.getvalue())
(root / "visor-pdf-fuente.txt").write_text(
    "La evidencia verificable exige una revision humana responsable ahora con palabras finales que permiten comparar tambien la segunda pagina",
    encoding="utf-8",
)

print("Documentos sintéticos de prueba generados")
(root / "visor-rotado-fuente.pdf").write_bytes((root / "visor-rotado.pdf").read_bytes())


def geometry_pdf(rotation, crop=False, offset=False, user_unit=1):
    out = io.BytesIO()
    pdf = canvas.Canvas(out, pagesize=(600, 800), pageCompression=0)
    pdf.drawString(100, 600, "La evidencia verificable exige una revision humana responsable ahora")
    pdf.save()
    data = out.getvalue().decode("latin1")
    # reportlab writes a plain page dictionary; rebuild xref offsets after changing it.
    import re

    data = data.replace("/Rotate 0", f"/Rotate {rotation}")
    if offset:
        data = data.replace("/MediaBox [ 0 0 600 800 ]", "/MediaBox [ 20 30 620 830 ]")
    if crop:
        data = data.replace("/Rotate ", "/CropBox [ 60 100 550 740 ] /Rotate ", 1)
    if user_unit != 1:
        data = data.replace("/Rotate ", f"/UserUnit {user_unit} /Rotate ", 1)
    # Rebuild the classic xref because substituted dictionary lengths change object positions.
    starts = {int(m.group(1)): m.start() for m in re.finditer(r"(?m)^(\d+) 0 obj\b", data)}
    xref = data.index("xref\n")
    trailer = data[data.index("trailer\n", xref) : data.index("startxref\n", xref)]
    data = (
        data[:xref]
        + "xref\n0 "
        + str(max(starts) + 1)
        + "\n0000000000 65535 f \n"
        + "".join(f"{starts[i]:010d} 00000 n \n" for i in range(1, max(starts) + 1))
        + trailer
        + "startxref\n"
        + str(xref)
        + "\n%%EOF\n"
    )
    return data.encode("latin1")


for rotation in [0, 90, 180, 270]:
    for crop in [False, True]:
        name = f"geometria-{rotation}-{'crop' if crop else 'media'}.pdf"
        data = geometry_pdf(rotation, crop, offset=crop, user_unit=2 if rotation == 270 and crop else 1)
        (root / name).write_bytes(data)
        (root / name.replace(".pdf", "-fuente.pdf")).write_bytes(data)
