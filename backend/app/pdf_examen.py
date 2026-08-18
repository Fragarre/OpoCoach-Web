from __future__ import annotations

from io import BytesIO
import re
from xml.sax.saxutils import escape

from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
)

from app.simulacros import (
    obtener_preguntas_para_realizar,
    obtener_simulacro,
)


def _texto(valor: object | None) -> str:
    if valor is None:
        return ""

    texto = str(valor)
    reemplazos = {
        "\ufb00": "ff",
        "\ufb01": "fi",
        "\ufb02": "fl",
        "\ufb03": "ffi",
        "\ufb04": "ffl",
        "\ufb05": "ft",
        "\ufb06": "st",
    }

    for origen, destino in reemplazos.items():
        texto = texto.replace(origen, destino)

    return escape(texto)


def _nombre_archivo(simulacro: dict) -> str:
    tipo = str(simulacro.get("tipo_prueba") or "SIMULACRO").upper()
    codigo = str(simulacro.get("convocatoria_codigo") or "OPOCOACH")
    numero = int(simulacro.get("numero") or 0)

    prefijo = "TEST" if tipo == "TEST" else "SIMULACRO"
    codigo_seguro = re.sub(r"[^A-Za-z0-9_-]+", "_", codigo).strip("_")

    return f"{prefijo}_{numero:04d}_{codigo_seguro}_PREGUNTAS.pdf"


def generar_pdf_preguntas(
    simulacro_id: int,
    user_id,
    incluir_seguridad: bool = True,
) -> tuple[str, bytes]:
    """
    Genera en memoria el PDF de preguntas de una prueba ya guardada.

    La fuente de verdad son los snapshots PostgreSQL asociados a la prueba.
    No modifica ninguna base de datos ni escribe archivos en disco.
    """
    simulacro = obtener_simulacro(simulacro_id, user_id)
    if simulacro is None:
        raise ValueError("El simulacro no existe.")

    preguntas = obtener_preguntas_para_realizar(simulacro_id, user_id)
    if not preguntas:
        raise ValueError("La prueba no contiene preguntas.")

    tipo = str(simulacro.get("tipo_prueba") or "SIMULACRO").upper()
    codigo = str(simulacro.get("convocatoria_codigo") or "")
    puesto = str(simulacro.get("convocatoria_puesto") or "")
    numero = int(simulacro.get("numero") or 0)

    estilos = getSampleStyleSheet()

    estilo_titulo = ParagraphStyle(
        "TituloOpoCoach",
        parent=estilos["Title"],
        fontName="Helvetica-Bold",
        fontSize=14,
        leading=17,
        alignment=TA_CENTER,
        spaceAfter=4,
    )
    estilo_subtitulo = ParagraphStyle(
        "SubtituloOpoCoach",
        parent=estilos["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=13,
        alignment=TA_CENTER,
        spaceAfter=10,
    )
    estilo_pregunta = ParagraphStyle(
        "PreguntaOpoCoach",
        parent=estilos["BodyText"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        spaceAfter=4,
    )
    estilo_opcion = ParagraphStyle(
        "OpcionOpoCoach",
        parent=estilos["BodyText"],
        fontName="Helvetica",
        fontSize=9.5,
        leading=13,
        leftIndent=0.55 * cm,
        spaceAfter=2,
    )
    estilo_seguridad = ParagraphStyle(
        "SeguridadOpoCoach",
        parent=estilos["BodyText"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=11,
        leftIndent=0.55 * cm,
        spaceBefore=3,
        spaceAfter=8,
    )

    salida = BytesIO()

    doc = SimpleDocTemplate(
        salida,
        pagesize=A4,
        leftMargin=1.8 * cm,
        rightMargin=1.8 * cm,
        topMargin=1.7 * cm,
        bottomMargin=1.7 * cm,
        title=f"OpoCoach - {tipo.title()} {numero}",
        author="OpoCoach",
    )

    story = [
        Paragraph("OPOCOACH", estilo_titulo),
        Paragraph(
            _texto(
                f"{'TEST' if tipo == 'TEST' else 'SIMULACRO DE EXAMEN'}"
                + (f" - {codigo}" if codigo else "")
            ),
            estilo_subtitulo,
        ),
    ]

    if puesto:
        story.append(Paragraph(_texto(puesto), estilo_subtitulo))

    story.append(Spacer(1, 0.2 * cm))

    for pregunta in preguntas:
        numero_pregunta = int(pregunta["orden"])
        bloque = [
            Paragraph(
                f"<b>{numero_pregunta}.</b> {_texto(pregunta['enunciado'])}",
                estilo_pregunta,
            ),
            Paragraph(
                f"<b>A)</b> {_texto(pregunta['opcion_a'])}",
                estilo_opcion,
            ),
            Paragraph(
                f"<b>B)</b> {_texto(pregunta['opcion_b'])}",
                estilo_opcion,
            ),
            Paragraph(
                f"<b>C)</b> {_texto(pregunta['opcion_c'])}",
                estilo_opcion,
            ),
            Paragraph(
                f"<b>D)</b> {_texto(pregunta['opcion_d'])}",
                estilo_opcion,
            ),
        ]

        if incluir_seguridad:
            bloque.append(
                Paragraph(
                    "Seguridad en la respuesta: "
                    "( ) Seguro&nbsp;&nbsp;&nbsp;&nbsp;( ) Menos seguro",
                    estilo_seguridad,
                )
            )
        else:
            bloque.append(Spacer(1, 0.18 * cm))

        story.append(KeepTogether(bloque))

    def pie_pagina(canvas, _doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.drawString(
            1.8 * cm,
            0.9 * cm,
            f"OpoCoach - {codigo or tipo}",
        )
        canvas.drawRightString(
            A4[0] - 1.8 * cm,
            0.9 * cm,
            f"Página {canvas.getPageNumber()}",
        )
        canvas.restoreState()

    doc.build(
        story,
        onFirstPage=pie_pagina,
        onLaterPages=pie_pagina,
    )

    return _nombre_archivo(simulacro), salida.getvalue()
