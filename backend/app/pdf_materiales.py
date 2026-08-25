from __future__ import annotations

import re
from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
)


def _limpiar(texto) -> str:
    valor = str(texto or "").replace("\x00", "").strip()
    return escape(valor).replace("\n", "<br/>")


def _nombre_archivo(texto: str) -> str:
    valor = re.sub(r"[^A-Za-z0-9._-]+", "_", texto.strip())
    return re.sub(r"_+", "_", valor).strip("_") or "material"


def generar_pdf_material(
    *,
    convocatoria_codigo: str,
    convocatoria_puesto: str,
    norma_nombre: str,
    tipo_material: str,
    articulos: list[dict],
    sufijo: str,
) -> tuple[str, bytes]:
    if not articulos:
        raise ValueError(
            "No hay artículos disponibles para generar el PDF."
        )

    buffer = BytesIO()
    izquierdo = 18 * mm
    derecho = 18 * mm
    superior = 20 * mm
    inferior = 18 * mm

    documento = BaseDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=izquierdo,
        rightMargin=derecho,
        topMargin=superior,
        bottomMargin=inferior,
        title=f"OpoCoach - {norma_nombre}",
        author="OpoCoach",
        subject=tipo_material,
    )

    ancho, alto = A4
    marco = Frame(
        izquierdo,
        inferior,
        ancho - izquierdo - derecho,
        alto - superior - inferior,
        id="principal",
    )

    def pie(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.drawString(
            izquierdo,
            9 * mm,
            f"OpoCoach · {convocatoria_codigo}",
        )
        canvas.drawRightString(
            ancho - derecho,
            9 * mm,
            f"Página {doc.page}",
        )
        canvas.restoreState()

    documento.addPageTemplates(
        [PageTemplate(id="material", frames=[marco], onPage=pie)]
    )

    estilos = getSampleStyleSheet()
    titulo = ParagraphStyle(
        "TituloMaterial",
        parent=estilos["Title"],
        fontName="Helvetica-Bold",
        fontSize=16,
        leading=19,
        alignment=TA_CENTER,
        spaceAfter=4 * mm,
    )
    subtitulo = ParagraphStyle(
        "SubtituloMaterial",
        parent=estilos["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=14,
        alignment=TA_CENTER,
        spaceAfter=3 * mm,
    )
    articulo_titulo = ParagraphStyle(
        "ArticuloTitulo",
        parent=estilos["Heading3"],
        fontName="Helvetica-Bold",
        fontSize=10.5,
        leading=13,
        spaceBefore=4 * mm,
        spaceAfter=1.5 * mm,
    )
    cuerpo = ParagraphStyle(
        "CuerpoMaterial",
        parent=estilos["BodyText"],
        fontName="Helvetica",
        fontSize=9.5,
        leading=13,
        spaceAfter=2.5 * mm,
    )

    contenido = [
        Paragraph("OPOCOACH", titulo),
        Paragraph(_limpiar(convocatoria_codigo), subtitulo),
        Paragraph(_limpiar(convocatoria_puesto), subtitulo),
        Spacer(1, 3 * mm),
        Paragraph(_limpiar(norma_nombre), titulo),
        Paragraph(_limpiar(tipo_material), subtitulo),
        PageBreak(),
    ]

    for articulo in articulos:
        rubrica = (
            articulo.get("titulo_bloque")
            or (
                f"Artículo {articulo.get('articulo_boe')}"
                if articulo.get("articulo_boe")
                else articulo.get("id_bloque")
            )
            or "Contenido normativo"
        )
        contenido.append(
            Paragraph(_limpiar(rubrica), articulo_titulo)
        )
        contenido.append(
            Paragraph(_limpiar(articulo.get("texto")), cuerpo)
        )

    documento.build(contenido)
    pdf = buffer.getvalue()
    buffer.close()

    filename = (
        f"{_nombre_archivo(convocatoria_codigo)}_"
        f"{_nombre_archivo(norma_nombre)}_{sufijo}.pdf"
    )
    return filename, pdf
