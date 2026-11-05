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
