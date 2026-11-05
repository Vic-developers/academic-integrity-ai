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
(root / 'visor-rotado-fuente.pdf').write_bytes((root / 'visor-rotado.pdf').read_bytes())
