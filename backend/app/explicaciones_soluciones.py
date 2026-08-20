from __future__ import annotations

import json
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable, Iterable
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


TAMANO_LOTE = 24
MAX_TRABAJADORES_IA = 3
MODELO_PREDETERMINADO = "gpt-5.4-nano"
OPERACION_IA = "comentarios_pdf_soluciones"


INSTRUCCIONES = """
Eres preparador de oposiciones.

La respuesta correcta de cada pregunta ya está determinada. No debes resolver
la pregunta de nuevo ni cuestionar la respuesta indicada.

Recibirás preguntas JURIDICAS y NO JURIDICAS. Las no jurídicas suelen ser
de INFORMATICA. Redacta un comentario claro que explique por qué la opción
indicada es correcta.

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

REGLAS PARA PREGUNTAS NO JURIDICAS, INCLUIDAS LAS INFORMATICAS:
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
    """Convierte cualquier valor en texto limpio de una sola línea."""
    if valor is None:
        return ""
    return " ".join(str(valor).split()).strip()


def _normalizar_articulo(valor: Any | None) -> str:
    """Extrae la referencia numérica principal del artículo."""
    texto = _limpiar_texto(valor).lower()
    if not texto:
        return ""

    texto = texto.replace(",", ".")
    coincidencia = re.search(r"\b\d+(?:\.\d+)*\b", texto)
    if coincidencia is None:
        return ""
    return coincidencia.group(0)


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
                    ss.tema_no_juridico,
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


def _cargar_fuentes_juridicas(
    preguntas: list[dict[str, Any]],
) -> dict[tuple[str, str], str]:
    """
    Carga en una sola consulta los textos jurídicos necesarios para el conjunto
    de preguntas.

    En OpoCoach Streamlit la consulta individual por pregunta es barata porque
    los contenidos están en SQLite local. En Web, repetir esa misma estrategia
    contra PostgreSQL/Supabase introduce una latencia de red por pregunta.
    Esta función evita el patrón N+1 de consultas remotas y carga en bloque
    todas las referencias de las normas necesarias. La selección exacta o
    por artículo padre se realiza después en memoria.
    """
    normas_necesarias: set[str] = set()

    for pregunta in preguntas:
        tipo = _limpiar_texto(pregunta.get("tipo_clasificacion")).upper()
        if tipo != "JURIDICA":
            continue

        norma_id = _limpiar_texto(pregunta.get("norma_id_normalizada"))
        articulo = _normalizar_articulo(pregunta.get("articulo_normalizado"))
        if not norma_id or not articulo:
            continue

        normas_necesarias.add(norma_id)

    if not normas_necesarias:
        return {}

    normas_ordenadas = sorted(normas_necesarias)
    origen = obtener_origen_contenidos()

    if origen == ORIGEN_CONTENIDOS_POSTGRES:
        marcadores = ", ".join(["%s"] * len(normas_ordenadas))
        with conectar_contenidos_postgres() as con:
            with con.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    f"""
                    SELECT
                        CAST(tr.norma_id AS TEXT) AS norma_id,
                        tr.articulo_solicitado,
                        af.texto
                    FROM contenidos.temario_referencias tr
                    JOIN contenidos.articulos_fuente af
                      ON af.id = tr.articulo_fuente_id
                    WHERE CAST(tr.norma_id AS TEXT) IN ({marcadores})
                      AND af.texto IS NOT NULL
                      AND TRIM(af.texto) <> ''
                    """,
                    tuple(normas_ordenadas),
                )
                filas = cur.fetchall()
    else:
        marcadores = ", ".join(["?"] * len(normas_ordenadas))
        with conectar_contenidos_sqlite() as con:
            filas = con.execute(
                f"""
                SELECT
                    CAST(tr.norma_id AS TEXT) AS norma_id,
                    tr.articulo_solicitado,
                    af.texto
                FROM temario_referencias tr
                JOIN articulos_fuente af
                  ON af.id = tr.articulo_fuente_id
                WHERE CAST(tr.norma_id AS TEXT) IN ({marcadores})
                  AND af.texto IS NOT NULL
                  AND TRIM(af.texto) <> ''
                """,
                tuple(normas_ordenadas),
            ).fetchall()

    fuentes: dict[tuple[str, str], str] = {}
    for fila in filas:
        norma_id = _limpiar_texto(fila["norma_id"])
        articulo = _normalizar_articulo(fila["articulo_solicitado"])
        clave = (norma_id, articulo)

        if not norma_id or not articulo or clave in fuentes:
            continue

        texto = _limpiar_texto(fila["texto"])
        if texto:
            fuentes[clave] = texto

    return fuentes


def _preparar_preguntas(
    preguntas: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[int], list[dict[str, Any]]]:
    preparadas: list[dict[str, Any]] = []
    sin_fuente: list[int] = []
    detalle_sin_fuente: list[dict[str, Any]] = []

    fuentes_juridicas = _cargar_fuentes_juridicas(preguntas)

    for pregunta in preguntas:
        orden = int(pregunta["orden"])
        tipo_clasificacion = _limpiar_texto(
            pregunta.get("tipo_clasificacion")
        ).upper()

        # Paridad funcional con OpoCoach Streamlit:
        # sólo JURIDICA exige fuente normativa. El resto es no jurídico.
        es_juridica = tipo_clasificacion == "JURIDICA"
        texto_fuente: str | None = None

        if es_juridica:
            norma_id = _limpiar_texto(
                pregunta.get("norma_id_normalizada")
            )
            articulo_normalizado = _normalizar_articulo(
                pregunta.get("articulo_normalizado")
            )
            # Paridad con OpoCoach Streamlit validado:
            # primero referencia exacta y, si no existe, apartados/artículo padre.
            # Ej.: 34.1.b (normalizado 34.1) -> 34.1 -> 34.
            referencias_busqueda = [articulo_normalizado]
            partes = articulo_normalizado.split(".")

            while len(partes) > 1:
                partes = partes[:-1]
                referencias_busqueda.append(".".join(partes))

            for referencia in referencias_busqueda:
                texto_fuente = fuentes_juridicas.get(
                    (norma_id, referencia)
                )
                if texto_fuente:
                    break

            if not texto_fuente:
                sin_fuente.append(orden)
                detalle_sin_fuente.append(
                    {
                        "orden": orden,
                        "tipo_clasificacion": tipo_clasificacion,
                        "tema_no_juridico": _limpiar_texto(
                            pregunta.get("tema_no_juridico")
                        ),
                        "nombre_norma": _limpiar_texto(
                            pregunta.get("nombre_norma")
                        ),
                        "norma_id_normalizada": pregunta.get(
                            "norma_id_normalizada"
                        ),
                        "articulo": _limpiar_texto(
                            pregunta.get("articulo")
                        ),
                        "articulo_normalizado": _limpiar_texto(
                            pregunta.get("articulo_normalizado")
                        ),
                        "articulo_clave": articulo_normalizado,
                        "enunciado": _limpiar_texto(
                            pregunta.get("enunciado")
                        ),
                    }
                )
                continue

        preparadas.append(
            {
                "simulacro_pregunta_id": int(
                    pregunta["simulacro_pregunta_id"]
                ),
                "orden": orden,
                "tipo_clasificacion": (
                    "JURIDICA" if es_juridica else "NO_JURIDICA"
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
                    _limpiar_texto(pregunta.get("nombre_norma"))
                    if es_juridica
                    else ""
                ),
                "articulo": (
                    _limpiar_texto(pregunta.get("articulo"))
                    if es_juridica
                    else ""
                ),
                "texto_fuente": texto_fuente or "",
            }
        )

    return preparadas, sin_fuente, detalle_sin_fuente

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


def _limitar_comentario_palabras(
    comentario: str,
    max_palabras: int = 100,
) -> str:
    """
    Garantiza de forma determinista el máximo de palabras del comentario.

    Si la IA excede el límite, se conserva el comienzo hasta max_palabras.
    No se repite todo el lote por un exceso puramente formal.
    """
    palabras = comentario.split()

    if len(palabras) <= max_palabras:
        return comentario

    return " ".join(palabras[:max_palabras]).strip()


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

        comentario = _limitar_comentario_palabras(
            comentario,
            max_palabras=100,
        )

        comentarios[orden] = comentario

    if set(comentarios) != esperados:
        faltan = sorted(esperados - set(comentarios))
        raise ValueError(
            "La IA no devolvió todos los comentarios. Faltan: "
            + ", ".join(str(valor) for valor in faltan)
        )

    return comentarios


def _guardar_comentarios(
    lote: list[dict[str, Any]],
    comentarios: dict[int, str],
    user_id: UUID,
) -> int:
    """Guarda todos los comentarios del lote con un único UPDATE PostgreSQL."""
    ids_por_orden = {
        int(p["orden"]): int(p["simulacro_pregunta_id"])
        for p in lote
    }
    pares = [
        (ids_por_orden[int(orden)], comentario)
        for orden, comentario in comentarios.items()
    ]

    if not pares:
        return 0

    valores_sql = ", ".join(["(%s, %s)"] * len(pares))
    parametros: list[Any] = []
    for simulacro_pregunta_id, comentario in pares:
        parametros.extend((simulacro_pregunta_id, comentario))
    parametros.append(user_id)

    sql = f"""
        UPDATE public.simulacro_snapshot AS ss
        SET comentario_solucion = datos.comentario
        FROM (VALUES {valores_sql})
             AS datos(simulacro_pregunta_id, comentario)
        WHERE ss.simulacro_pregunta_id = datos.simulacro_pregunta_id
          AND (
                ss.comentario_solucion IS NULL
                OR BTRIM(ss.comentario_solucion) = ''
              )
          AND EXISTS (
                SELECT 1
                FROM public.simulacro_preguntas sp
                JOIN public.simulacros s
                  ON s.id = sp.simulacro_id
                WHERE sp.id = ss.simulacro_pregunta_id
                  AND s.user_id = %s
              )
    """

    with conectar_postgres() as con:
        with con.cursor() as cur:
            cur.execute(sql, tuple(parametros))
            actualizados = cur.rowcount
        con.commit()

    return int(actualizados)


def _procesar_lote_ia(
    numero_lote: int,
    lote: list[dict[str, Any]],
    modelo: str,
) -> dict[str, Any]:
    """Ejecuta la llamada IA de un lote y valida la respuesta; no escribe BD."""
    prompt = _crear_prompt(lote)
    respuesta: Any | None = None
    errores_intentos: list[str] = []
    tiempo_ia = 0.0
    llamadas_ia = 0

    for intento in (1, 2):
        try:
            inicio_ia = time.perf_counter()
            try:
                respuesta = seleccionar_fragmento_json(
                    prompt=prompt,
                    modelo=modelo,
                    operacion=OPERACION_IA,
                )
            finally:
                tiempo_ia += time.perf_counter() - inicio_ia
                llamadas_ia += 1

            comentarios = _validar_respuesta(respuesta, lote)
            return {
                "numero_lote": numero_lote,
                "lote": lote,
                "comentarios": comentarios,
                "error": None,
                "tiempo_ia": tiempo_ia,
                "llamadas_ia": llamadas_ia,
                "intentos_fallidos": intento - 1,
            }
        except Exception as exc:
            errores_intentos.append(
                f"Intento {intento}: {type(exc).__name__}: {exc}"
            )

    return {
        "numero_lote": numero_lote,
        "lote": lote,
        "comentarios": None,
        "error": "\n".join(errores_intentos),
        "tiempo_ia": tiempo_ia,
        "llamadas_ia": llamadas_ia,
        "intentos_fallidos": 2,
    }


def generar_comentarios_soluciones(
    simulacro_id: int,
    user_id: UUID,
    modelo: str = MODELO_PREDETERMINADO,
    tamano_lote: int = TAMANO_LOTE,
    progreso: Callable[[int, int, int], None] | None = None,
    max_trabajadores_ia: int = MAX_TRABAJADORES_IA,
) -> dict[str, Any]:
    """
    Genera sólo comentarios pendientes y los persiste de forma idempotente.

    Mantiene la seguridad multiusuario de OpoCoach-Web. Las llamadas IA se
    ejecutan en paralelo, como en OpoCoach Streamlit, y las escrituras se hacen
    después de forma secuencial y por lote.
    """
    inicio_total = time.perf_counter()

    tiempo_lectura_postgres = 0.0
    tiempo_preparacion = 0.0
    tiempo_ia_acumulado = 0.0
    tiempo_ia_pared = 0.0
    tiempo_guardado_postgres = 0.0
    llamadas_ia = 0
    intentos_fallidos = 0
    total_lotes = 0

    resumen: dict[str, Any] = {
        "simulacro_id": simulacro_id,
        "pendientes_iniciales": 0,
        "con_fuente": 0,
        "sin_fuente": [],
        "detalle_sin_fuente": [],
        "actualizadas": 0,
        "errores": [],
        "lotes_procesados": 0,
    }

    try:
        if simulacro_id <= 0:
            raise ValueError("simulacro_id debe ser mayor que cero.")
        if tamano_lote <= 0:
            raise ValueError("tamano_lote debe ser mayor que cero.")
        if max_trabajadores_ia <= 0:
            raise ValueError("max_trabajadores_ia debe ser mayor que cero.")

        inicio = time.perf_counter()
        pendientes = _obtener_preguntas_pendientes(simulacro_id, user_id)
        tiempo_lectura_postgres += time.perf_counter() - inicio

        inicio = time.perf_counter()
        preparadas, sin_fuente, detalle_sin_fuente = _preparar_preguntas(
            pendientes
        )
        tiempo_preparacion += time.perf_counter() - inicio

        resumen.update(
            {
                "pendientes_iniciales": len(pendientes),
                "con_fuente": len(preparadas),
                "sin_fuente": sin_fuente,
                "detalle_sin_fuente": detalle_sin_fuente,
            }
        )

        if not preparadas:
            if progreso is not None:
                progreso(0, 0, 0)
            return resumen

        lotes = list(_dividir_lotes(preparadas, tamano_lote))
        total_lotes = len(lotes)
        resultados: dict[int, dict[str, Any]] = {}

        inicio_ia_pared = time.perf_counter()
        with ThreadPoolExecutor(
            max_workers=min(max_trabajadores_ia, total_lotes)
        ) as executor:
            futuros = {
                executor.submit(
                    _procesar_lote_ia,
                    numero_lote,
                    lote,
                    modelo,
                ): numero_lote
                for numero_lote, lote in enumerate(lotes, start=1)
            }

            for futuro in as_completed(futuros):
                resultado = futuro.result()
                numero_lote = int(resultado["numero_lote"])
                resultados[numero_lote] = resultado
                tiempo_ia_acumulado += float(resultado["tiempo_ia"])
                llamadas_ia += int(resultado["llamadas_ia"])
                intentos_fallidos += int(resultado["intentos_fallidos"])

        tiempo_ia_pared = time.perf_counter() - inicio_ia_pared

        for numero_lote in range(1, total_lotes + 1):
            resultado = resultados[numero_lote]
            lote = resultado["lote"]
            error = resultado["error"]

            if error is None:
                inicio = time.perf_counter()
                actualizadas = _guardar_comentarios(
                    lote,
                    resultado["comentarios"],
                    user_id,
                )
                tiempo_guardado_postgres += time.perf_counter() - inicio

                resumen["actualizadas"] += actualizadas
                resumen["lotes_procesados"] += 1
            else:
                resumen["errores"].append(
                    {
                        "lote": numero_lote,
                        "ordenes": [int(p["orden"]) for p in lote],
                        "error": error,
                    }
                )

            if progreso is not None:
                progreso(
                    numero_lote,
                    total_lotes,
                    resumen["actualizadas"],
                )

        return resumen

    finally:
        tiempo_total = time.perf_counter() - inicio_total
        print(
            "TIEMPOS comentarios soluciones WEB"
            f" | total={tiempo_total:.2f}s"
            f" | lectura_postgres={tiempo_lectura_postgres:.2f}s"
            f" | preparacion_fuentes={tiempo_preparacion:.2f}s"
            f" | ia_pared={tiempo_ia_pared:.2f}s"
            f" | ia_acumulada={tiempo_ia_acumulado:.2f}s"
            f" | guardado_postgres={tiempo_guardado_postgres:.2f}s"
            f" | lotes={total_lotes}"
            f" | llamadas_ia={llamadas_ia}"
            f" | intentos_fallidos={intentos_fallidos}"
            f" | tamano_lote={tamano_lote}"
            f" | trabajadores_ia={max_trabajadores_ia}"
            f" | pendientes={resumen['pendientes_iniciales']}"
            f" | preparadas={resumen['con_fuente']}"
            f" | sin_fuente_juridica={len(resumen['sin_fuente'])}"
            f" | actualizadas={resumen['actualizadas']}"
            f" | lotes_error={len(resumen['errores'])}",
            flush=True,
        )

        if resumen["sin_fuente"]:
            print(
                "PREGUNTAS JURIDICAS SIN FUENTE PARA COMENTARIO: "
                + ", ".join(str(orden) for orden in resumen["sin_fuente"]),
                flush=True,
            )
            for detalle in resumen["detalle_sin_fuente"]:
                print(
                    "  SIN FUENTE"
                    f" | orden={detalle['orden']}"
                    f" | norma_id={detalle['norma_id_normalizada']}"
                    f" | norma={detalle['nombre_norma']}"
                    f" | articulo={detalle['articulo']}"
                    f" | articulo_normalizado={detalle['articulo_normalizado']}"
                    f" | articulo_clave={detalle['articulo_clave']}",
                    flush=True,
                )

        if resumen["errores"]:
            for error_lote in resumen["errores"]:
                print(
                    "ERROR COMENTARIOS LOTE "
                    f'{error_lote["lote"]}: {error_lote["error"]}',
                    flush=True,
                )
