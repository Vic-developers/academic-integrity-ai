"""Create labelled synthetic, valid documents for browser tests."""

import sys
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
print("Cuatro documentos sintéticos de prueba generados")
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
