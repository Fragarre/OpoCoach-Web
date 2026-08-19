from __future__ import annotations

import json
import re
from typing import Any, Iterable
from uuid import UUID

from psycopg.rows import dict_row

from app.database import (
    ORIGEN_CONTENIDOS_POSTGRES,
    conectar_contenidos_postgres,
    conectar_contenidos_sqlite,
    obtener_origen_contenidos,
)
from app.openai_api import seleccionar_fragmento_json
from app.postgres import conectar_postgres


TAMANO_LOTE = 16
MODELO_PREDETERMINADO = "gpt-5.4-mini"
OPERACION_IA = "comentarios_pdf_soluciones"


INSTRUCCIONES = """
Eres preparador de oposiciones.

La respuesta correcta de cada pregunta ya está determinada. No debes resolver
la pregunta de nuevo ni cuestionar la respuesta indicada.

Recibirás preguntas de dos tipos: JURIDICA e INFORMATICA. Redacta un comentario
claro que explique por qué la opción indicada es correcta.

REGLAS PARA PREGUNTAS JURIDICAS:
- Utiliza exclusivamente la norma, el artículo y el texto de la fuente aportada.
- Comienza identificando expresamente la norma y el artículo aplicables.
- Usa una fórmula natural, por ejemplo:
  "Según el artículo 96 de la Ley 39/2015, ..."
- Explica la regla concreta del precepto que permite reconocer la respuesta.
- Señala el elemento decisivo: plazo, órgano competente, requisito, excepción,
  efecto jurídico, definición o procedimiento.
- Cuando aporte valor, indica brevemente por qué las restantes opciones no
  encajan con la regla del artículo, sin analizarlas una por una.
- No uses conocimiento jurídico externo ni completes información ausente.

REGLAS PARA PREGUNTAS INFORMATICAS:
- Utiliza el enunciado, las opciones y la respuesta correcta proporcionada.
- Explica el concepto, función, comando, herramienta o comportamiento técnico
  que hace correcta esa opción.
- Puedes usar conocimiento técnico general y estable de informática, sistemas
  operativos, seguridad, redes y aplicaciones ofimáticas.
- No inventes versiones, rutas, nombres de menús o detalles que no sean seguros.
- Cuando una respuesta dependa de una versión concreta y esta no figure en la
  pregunta, limita la explicación al principio técnico que pueda afirmarse con
  seguridad.
- Cuando aporte valor, señala brevemente el error conceptual de las alternativas,
  sin analizarlas una por una.

REGLAS COMUNES:
- No te limites a afirmar que la opción es correcta: explica la razón.
- No repitas el enunciado ni reproduzcas las opciones completas.
- No escribas "Respuesta A", "Respuesta B", "Respuesta C" o "Respuesta D",
  porque esa indicación ya se añade automáticamente en el PDF.
- No añadas encabezados, listas, conclusiones ni Markdown.
- Un único párrafo por pregunta.
- Entre 40 y 100 palabras, salvo que no sea posible alcanzar esa extensión sin
  repetir o inventar información.
- Texto directamente imprimible en el PDF de soluciones.

Devuelve exclusivamente un JSON con esta forma:
[
  {
    "orden": 1,
    "comentario": "Explicación de la respuesta correcta."
  }
]

Debes devolver exactamente un objeto por cada pregunta recibida y conservar su
valor de "orden".
""".strip()


def _limpiar_texto(valor: Any | None) -> str:
    if valor is None:
        return ""
    return " ".join(str(valor).split()).strip()


def _normalizar_articulo(valor: Any | None) -> str:
    texto = _limpiar_texto(valor).lower()
    if not texto:
        return ""
    texto = texto.replace("artículo", "")
    texto = texto.replace("articulo", "")
    texto = re.sub(r"\bart\.?\b", "", texto)
    texto = re.sub(r"\s+", "", texto)
    return texto.rstrip(".")


def _dividir_lotes(
    elementos: list[dict[str, Any]],
    tamano: int,
) -> Iterable[list[dict[str, Any]]]:
    for inicio in range(0, len(elementos), tamano):
        yield elementos[inicio:inicio + tamano]


def _obtener_preguntas_pendientes(
    simulacro_id: int,
    user_id: UUID,
) -> list[dict[str, Any]]:
    """Lee sólo snapshots vacíos pertenecientes al usuario autenticado."""
    with conectar_postgres() as con:
        with con.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT
                    sp.id AS simulacro_pregunta_id,
                    sp.orden,
                    ss.enunciado,
                    ss.opcion_a,
                    ss.opcion_b,
                    ss.opcion_c,
                    ss.opcion_d,
                    ss.respuesta_correcta,
                    ss.tipo_clasificacion,
                    ss.nombre_norma,
                    ss.articulo,
                    ss.norma_id_normalizada,
                    ss.articulo_normalizado,
                    ss.comentario_solucion
                FROM public.simulacro_preguntas sp
                JOIN public.simulacro_snapshot ss
                  ON ss.simulacro_pregunta_id = sp.id
                JOIN public.simulacros s
                  ON s.id = sp.simulacro_id
                WHERE sp.simulacro_id = %s
                  AND s.user_id = %s
                  AND (
                        ss.comentario_solucion IS NULL
                        OR BTRIM(ss.comentario_solucion) = ''
                      )
                ORDER BY sp.orden
                """,
                (simulacro_id, user_id),
            )
            return [dict(fila) for fila in cur.fetchall()]


def _obtener_texto_articulo(
    norma_id_normalizada: Any | None,
    articulo_normalizado: Any | None,
) -> str | None:
    """Recupera el texto jurídico desde el origen de contenidos configurado."""
    norma_id = _limpiar_texto(norma_id_normalizada)
    articulo_buscado = _normalizar_articulo(articulo_normalizado)

    if not norma_id or not articulo_buscado:
        return None

    origen = obtener_origen_contenidos()

    if origen == ORIGEN_CONTENIDOS_POSTGRES:
        with conectar_contenidos_postgres() as con:
            with con.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                        tr.articulo_solicitado,
                        af.texto
                    FROM contenidos.temario_referencias tr
                    JOIN contenidos.articulos_fuente af
                      ON af.id = tr.articulo_fuente_id
                    WHERE CAST(tr.norma_id AS TEXT) = %s
                      AND af.texto IS NOT NULL
                      AND TRIM(af.texto) <> ''
                    """,
                    (norma_id,),
                )
                filas = cur.fetchall()
    else:
        with conectar_contenidos_sqlite() as con:
            filas = con.execute(
                """
                SELECT
                    tr.articulo_solicitado,
                    af.texto
                FROM temario_referencias tr
                JOIN articulos_fuente af
                  ON af.id = tr.articulo_fuente_id
                WHERE CAST(tr.norma_id AS TEXT) = ?
                  AND af.texto IS NOT NULL
                  AND TRIM(af.texto) <> ''
                """,
                (norma_id,),
            ).fetchall()

    for fila in filas:
        articulo_candidato = _normalizar_articulo(
            fila["articulo_solicitado"]
        )
        if articulo_candidato == articulo_buscado:
            texto = _limpiar_texto(fila["texto"])
            return texto or None

    return None


def _preparar_preguntas(
    preguntas: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[int]]:
    preparadas: list[dict[str, Any]] = []
    sin_fuente: list[int] = []

    for pregunta in preguntas:
        orden = int(pregunta["orden"])
        tipo_clasificacion = _limpiar_texto(
            pregunta.get("tipo_clasificacion")
        ).upper()
        es_informatica = tipo_clasificacion == "INFORMATICA"
        texto_fuente: str | None = None

        if not es_informatica:
            texto_fuente = _obtener_texto_articulo(
                pregunta.get("norma_id_normalizada"),
                pregunta.get("articulo_normalizado"),
            )
            if not texto_fuente:
                sin_fuente.append(orden)
                continue

        preparadas.append(
            {
                "simulacro_pregunta_id": int(
                    pregunta["simulacro_pregunta_id"]
                ),
                "orden": orden,
                "tipo_clasificacion": (
                    "INFORMATICA" if es_informatica else "JURIDICA"
                ),
                "enunciado": _limpiar_texto(pregunta.get("enunciado")),
                "opciones": {
                    "A": _limpiar_texto(pregunta.get("opcion_a")),
                    "B": _limpiar_texto(pregunta.get("opcion_b")),
                    "C": _limpiar_texto(pregunta.get("opcion_c")),
                    "D": _limpiar_texto(pregunta.get("opcion_d")),
                },
                "respuesta_correcta": _limpiar_texto(
                    pregunta.get("respuesta_correcta")
                ).upper(),
                "norma": (
                    "" if es_informatica else _limpiar_texto(
                        pregunta.get("nombre_norma")
                    )
                ),
                "articulo": (
                    "" if es_informatica else _limpiar_texto(
                        pregunta.get("articulo")
                    )
                ),
                "texto_fuente": texto_fuente or "",
            }
        )

    return preparadas, sin_fuente


def _crear_prompt(lote: list[dict[str, Any]]) -> str:
    datos_ia = [
        {
            "orden": pregunta["orden"],
            "tipo_clasificacion": pregunta["tipo_clasificacion"],
            "enunciado": pregunta["enunciado"],
            "opciones": pregunta["opciones"],
            "respuesta_correcta": pregunta["respuesta_correcta"],
            "norma": pregunta["norma"],
            "articulo": pregunta["articulo"],
            "texto_fuente": pregunta["texto_fuente"],
        }
        for pregunta in lote
    ]
    return (
        INSTRUCCIONES
        + "\n\nPREGUNTAS:\n"
        + json.dumps(datos_ia, ensure_ascii=False, indent=2)
    )


def _validar_respuesta(
    respuesta: Any,
    lote: list[dict[str, Any]],
) -> dict[int, str]:
    if not isinstance(respuesta, list):
        raise ValueError("La respuesta de la IA no es una lista JSON.")

    esperados = {int(p["orden"]) for p in lote}
    comentarios: dict[int, str] = {}

    for elemento in respuesta:
        if not isinstance(elemento, dict):
            raise ValueError(
                "La respuesta contiene un elemento que no es un objeto."
            )
        try:
            orden = int(elemento["orden"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(
                "Un comentario no contiene un orden válido."
            ) from exc

        comentario = _limpiar_texto(elemento.get("comentario"))
        if orden not in esperados:
            raise ValueError(
                f"La IA devolvió un orden inesperado: {orden}."
            )
        if orden in comentarios:
            raise ValueError(
                f"La IA devolvió dos veces el orden {orden}."
            )
        if not comentario:
            raise ValueError(
                f"El comentario del orden {orden} está vacío."
            )
        comentarios[orden] = comentario

    if set(comentarios) != esperados:
        faltan = sorted(esperados - set(comentarios))
        raise ValueError(
            f"La IA no devolvió todos los comentarios. Faltan: {faltan}."
        )

    return comentarios


def _guardar_comentarios(
    lote: list[dict[str, Any]],
    comentarios: dict[int, str],
    user_id: UUID,
) -> int:
    ids_por_orden = {
        int(p["orden"]): int(p["simulacro_pregunta_id"])
        for p in lote
    }
    actualizados = 0

    with conectar_postgres() as con:
        with con.cursor() as cur:
            for orden, comentario in comentarios.items():
                cur.execute(
                    """
                    UPDATE public.simulacro_snapshot ss
                    SET comentario_solucion = %s
                    FROM public.simulacro_preguntas sp,
                         public.simulacros s
                    WHERE ss.simulacro_pregunta_id = %s
                      AND sp.id = ss.simulacro_pregunta_id
                      AND s.id = sp.simulacro_id
                      AND s.user_id = %s
                      AND (
                            ss.comentario_solucion IS NULL
                            OR BTRIM(ss.comentario_solucion) = ''
                          )
                    """,
                    (
                        comentario,
                        ids_por_orden[orden],
                        user_id,
                    ),
                )
                actualizados += cur.rowcount
        con.commit()

    return actualizados


def generar_comentarios_soluciones(
    simulacro_id: int,
    user_id: UUID,
    modelo: str = MODELO_PREDETERMINADO,
    tamano_lote: int = TAMANO_LOTE,
) -> dict[str, Any]:
    """Genera sólo comentarios pendientes y los persiste de forma idempotente."""
    if simulacro_id <= 0:
        raise ValueError("simulacro_id debe ser mayor que cero.")
    if tamano_lote <= 0:
        raise ValueError("tamano_lote debe ser mayor que cero.")

    pendientes = _obtener_preguntas_pendientes(simulacro_id, user_id)
    preparadas, sin_fuente = _preparar_preguntas(pendientes)

    resumen: dict[str, Any] = {
        "simulacro_id": simulacro_id,
        "pendientes_iniciales": len(pendientes),
        "con_fuente": len(preparadas),
        "sin_fuente": sin_fuente,
        "actualizadas": 0,
        "errores": [],
        "lotes_procesados": 0,
    }

    if not preparadas:
        return resumen

    for numero_lote, lote in enumerate(
        _dividir_lotes(preparadas, tamano_lote),
        start=1,
    ):
        prompt = _crear_prompt(lote)
        errores_intentos: list[str] = []
        lote_completado = False

        for intento in (1, 2):
            try:
                respuesta = seleccionar_fragmento_json(
                    prompt=prompt,
                    modelo=modelo,
                    operacion=OPERACION_IA,
                )
                comentarios = _validar_respuesta(respuesta, lote)
                resumen["actualizadas"] += _guardar_comentarios(
                    lote,
                    comentarios,
                    user_id,
                )
                resumen["lotes_procesados"] += 1
                lote_completado = True
                break
            except Exception as exc:
                errores_intentos.append(
                    f"Intento {intento}: {type(exc).__name__}: {exc}"
                )

        if not lote_completado:
            resumen["errores"].append(
                {
                    "lote": numero_lote,
                    "ordenes": [int(p["orden"]) for p in lote],
                    "error": "\n".join(errores_intentos),
                }
            )

    return resumen
