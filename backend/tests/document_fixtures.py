import io
from docx import Document as Docx
from PIL import Image
from reportlab.pdfgen import canvas


def pdf_bytes(*, scanned=False, encrypt=None, pages=2):
    output = io.BytesIO()
    pdf = canvas.Canvas(output, encrypt=encrypt)
    pdf.setAuthor("Autora de prueba")
    for page in range(pages):
        if scanned:
            pdf.drawInlineImage(Image.new("RGB", (20, 20), "white"), 40, 600)
        else:
            pdf.drawString(40, 750, f"Evidence on page {page + 1}. Academic document.")
        pdf.showPage()
    pdf.save()
    return output.getvalue()


def docx_bytes():
    document = Docx()
    document.add_heading("Introducción", 1)
    p = document.add_paragraph()
    p.add_run("Una prueba ")
    p.add_run("académica con acentos y ß.")
    document.add_table(rows=1, cols=1).cell(0, 0).text = "Contenido de tabla"
    document.sections[0].header.paragraphs[0].text = "Encabezado autorizado"
    out = io.BytesIO()
    document.save(out)
    return out.getvalue()
