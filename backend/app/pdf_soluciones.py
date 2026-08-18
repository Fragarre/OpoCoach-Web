from __future__ import annotations

from io import BytesIO
import re
from xml.sax.saxutils import escape

from psycopg.rows import dict_row
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.postgres import conectar_postgres
from app.explicaciones_soluciones import generar_comentarios_soluciones
from app.simulacros import obtener_simulacro


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

    return f"{prefijo}_{numero:04d}_{codigo_seguro}_SOLUCIONES.pdf"


def _cargar_soluciones(simulacro_id: int, user_id) -> list[dict]:
    with conectar_postgres() as con:
        with con.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT
                    sp.orden,
                    sp.parte_nombre,
                    sp.respuesta_usuario,
                    sp.seguridad_usuario,
                    ss.enunciado,
                    ss.opcion_a,
                    ss.opcion_b,
                    ss.opcion_c,
                    ss.opcion_d,
                    ss.respuesta_correcta,
                    ss.tipo_clasificacion,
                    ss.nombre_norma_normalizado,
                    ss.articulo_normalizado,
                    ss.tema_no_juridico,
                    ss.comentario_solucion
                FROM public.simulacro_preguntas sp
                JOIN public.simulacro_snapshot ss
                  ON ss.simulacro_pregunta_id = sp.id
                JOIN public.simulacros s
                  ON s.id = sp.simulacro_id
                WHERE sp.simulacro_id = %s
                  AND s.user_id = %s
                ORDER BY sp.orden
                """,
                (simulacro_id, user_id),
            )
            return [dict(fila) for fila in cur.fetchall()]


def _texto_opcion_correcta(solucion: dict) -> str:
    letra = str(solucion.get("respuesta_correcta") or "").strip().upper()
    mapa = {
        "A": solucion.get("opcion_a"),
        "B": solucion.get("opcion_b"),
        "C": solucion.get("opcion_c"),
        "D": solucion.get("opcion_d"),
    }
    return str(mapa.get(letra) or "")


def _referencia(solucion: dict) -> str:
    tipo = str(solucion.get("tipo_clasificacion") or "").upper()

    if tipo == "INFORMATICA":
        tema = str(solucion.get("tema_no_juridico") or "").strip()
        return tema or "Informática"

    norma = str(solucion.get("nombre_norma_normalizado") or "").strip()
    articulo = str(solucion.get("articulo_normalizado") or "").strip()

    if norma and articulo:
        return f"{norma} · artículo {articulo}"
    if norma:
        return norma
    if articulo:
        return f"Artículo {articulo}"
    return ""


def generar_pdf_soluciones(
    simulacro_id: int,
    user_id,
) -> tuple[str, bytes]:
    """
    Genera en memoria el PDF de soluciones de cualquier prueba guardada.

    No exige que la prueba esté finalizada. Esto permite imprimir preguntas y
    soluciones para trabajar fuera de la aplicación y corregirse posteriormente.
    """
    simulacro = obtener_simulacro(simulacro_id, user_id)
    if simulacro is None:
        raise ValueError("El simulacro no existe.")

    # Igual que en Streamlit: generar sólo comentarios pendientes antes de
    # construir el PDF y volver a leer después los snapshots actualizados.
    generar_comentarios_soluciones(
        simulacro_id=simulacro_id,
        user_id=user_id,
    )

    soluciones = _cargar_soluciones(simulacro_id, user_id)
    if not soluciones:
        raise ValueError("La prueba no contiene preguntas.")

    tipo = str(simulacro.get("tipo_prueba") or "SIMULACRO").upper()
    codigo = str(simulacro.get("convocatoria_codigo") or "")
    puesto = str(simulacro.get("convocatoria_puesto") or "")
    numero = int(simulacro.get("numero") or 0)

    estilos = getSampleStyleSheet()

    titulo = ParagraphStyle(
        "Titulo",
        parent=estilos["Title"],
        fontName="Helvetica-Bold",
        fontSize=14,
        leading=17,
        alignment=TA_CENTER,
        spaceAfter=4,
    )
    subtitulo = ParagraphStyle(
        "Subtitulo",
        parent=estilos["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=13,
        alignment=TA_CENTER,
        spaceAfter=8,
    )
    normal = ParagraphStyle(
        "NormalSol",
        parent=estilos["BodyText"],
        fontName="Helvetica",
        fontSize=9.5,
        leading=13,
        spaceAfter=4,
    )
    pregunta_estilo = ParagraphStyle(
        "PreguntaSol",
        parent=estilos["BodyText"],
        fontName="Helvetica-Bold",
        fontSize=10,
        leading=14,
        spaceAfter=5,
    )
    referencia_estilo = ParagraphStyle(
        "ReferenciaSol",
        parent=estilos["BodyText"],
        fontName="Helvetica-Oblique",
        fontSize=8.7,
        leading=12,
        spaceAfter=4,
    )
    comentario_estilo = ParagraphStyle(
        "ComentarioSol",
        parent=estilos["BodyText"],
        fontName="Helvetica",
        fontSize=9.2,
        leading=13,
        leftIndent=0.35 * cm,
        rightIndent=0.35 * cm,
        spaceAfter=10,
    )

    salida = BytesIO()
    doc = SimpleDocTemplate(
        salida,
        pagesize=A4,
        leftMargin=1.8 * cm,
        rightMargin=1.8 * cm,
        topMargin=1.7 * cm,
        bottomMargin=1.7 * cm,
        title=f"OpoCoach - Soluciones {tipo.title()} {numero}",
        author="OpoCoach",
    )

    story = [
        Paragraph("OPOCOACH", titulo),
        Paragraph(
            _texto(
                f"{'TEST' if tipo == 'TEST' else 'SIMULACRO'} {numero}"
                + (f" - {codigo}" if codigo else "")
            ),
            subtitulo,
        ),
        Paragraph("SOLUCIONES", titulo),
    ]

    if puesto:
        story.append(Paragraph(_texto(puesto), subtitulo))

    story.append(Spacer(1, 0.25 * cm))

    respuestas = [
        (
            int(sol["orden"]),
            str(sol.get("respuesta_correcta") or "").strip().upper(),
        )
        for sol in soluciones
    ]

    filas_por_columna = (len(respuestas) + 3) // 4
    columnas = [
        respuestas[i * filas_por_columna:(i + 1) * filas_por_columna]
        for i in range(4)
    ]

    filas = []
    for indice in range(filas_por_columna):
        fila = []
        for columna in columnas:
            if indice < len(columna):
                n, letra = columna[indice]
                fila.append(Paragraph(f"<b>{n}.</b>&nbsp;&nbsp;{_texto(letra)}", normal))
            else:
                fila.append("")
        filas.append(fila)

    tabla = Table(filas, colWidths=[4.1 * cm] * 4, hAlign="CENTER")
    tabla.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                ("BOX", (0, 0), (-1, -1), 0.35, colors.grey),
                ("INNERGRID", (0, 0), (-1, -1), 0.2, colors.lightgrey),
            ]
        )
    )
    story.append(tabla)
    story.append(PageBreak())

    for solucion in soluciones:
        orden = int(solucion["orden"])
        correcta = str(solucion.get("respuesta_correcta") or "").strip().upper()
        opcion_correcta = _texto_opcion_correcta(solucion)
        referencia = _referencia(solucion)
        comentario = str(solucion.get("comentario_solucion") or "").strip()

        story.append(
            Paragraph(
                f"{orden}. {_texto(solucion.get('enunciado'))}",
                pregunta_estilo,
            )
        )
        story.append(
            Paragraph(
                f"<b>Respuesta correcta: { _texto(correcta) })</b> "
                f"{_texto(opcion_correcta)}",
                normal,
            )
        )

        if referencia:
            story.append(
                Paragraph(
                    f"<b>Referencia:</b> {_texto(referencia)}",
                    referencia_estilo,
                )
            )

        if comentario:
            story.append(
                Paragraph(
                    f"<b>Comentario:</b> {_texto(comentario)}",
                    comentario_estilo,
                )
            )
        else:
            story.append(Spacer(1, 0.18 * cm))

    def pie_pagina(canvas, _doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.drawString(
            1.8 * cm,
            0.9 * cm,
            f"OpoCoach - Soluciones - {codigo or tipo}",
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
