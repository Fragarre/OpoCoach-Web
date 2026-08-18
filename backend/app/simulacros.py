from __future__ import annotations

import random
from datetime import datetime, timedelta
from uuid import UUID

from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from app.database import conectar_contenidos
from app.postgres import conectar_postgres

ORIGENES_VALIDOS = {"A1", "A2", "C1", "C2"}
FUENTES_VALIDAS = {"REAL", "IA"}
RESPUESTAS_VALIDAS = {"A", "B", "C", "D"}
SEGURIDADES_VALIDAS = {"MUY_SEGURO", "BASTANTE_SEGURO", "POCO_SEGURO"}
DIAS_SIN_REPETICION = 3


def _normalizar_origenes(origenes: list[str]) -> list[str]:
    resultado = sorted({str(x).strip().upper() for x in origenes if str(x).strip()})
    if not resultado:
        raise ValueError("Debe seleccionar al menos un origen de preguntas.")
    if set(resultado) - ORIGENES_VALIDOS:
        raise ValueError("Existe algún origen de preguntas no válido.")
    return resultado


def _normalizar_fuentes(fuentes: list[str] | None) -> set[str]:
    resultado = {
        str(x).strip().upper()
        for x in (fuentes or ["REAL", "IA"])
        if str(x).strip()
    }
    if not resultado or resultado - FUENTES_VALIDAS:
        raise ValueError("Debe seleccionar al menos una fuente válida: REAL y/o IA.")
    return resultado


def _condicion_fuente(fuentes: set[str]) -> str:
    if fuentes == {"IA"}:
        return "LOWER(TRIM(lp.tipo_fuente)) = 'ia_generada'"
    if fuentes == {"REAL"}:
        return "LOWER(TRIM(lp.tipo_fuente)) <> 'ia_generada'"
    return "1 = 1"


def _serializar_fila(fila) -> dict:
    resultado = dict(fila)
    for clave, valor in list(resultado.items()):
        if isinstance(valor, datetime):
            resultado[clave] = valor.isoformat()
        elif isinstance(valor, UUID):
            resultado[clave] = str(valor)
    return resultado


def obtener_disponibilidad(
    convocatoria_id: int,
    origenes: list[str],
    fuentes: list[str] | None,
) -> list[dict]:
    origenes_n = _normalizar_origenes(origenes)
    fuentes_n = _normalizar_fuentes(fuentes)
    marcas = ", ".join("?" for _ in origenes_n)
    condicion = _condicion_fuente(fuentes_n)

    with conectar_contenidos() as con:
        filas = con.execute(
            f"""
            SELECT cp.id AS parte_id, cp.nombre AS parte, cp.orden AS parte_orden,
                   cp.numero_preguntas AS necesarias,
                   COUNT(DISTINCT CASE WHEN lp.id IS NOT NULL THEN bp.id END) AS disponibles
            FROM convocatoria_partes cp
            LEFT JOIN banco_preguntas bp
              ON bp.convocatoria_parte_id = cp.id
             AND bp.convocatoria_id = cp.convocatoria_id
             AND bp.estado = 'INCLUIDA'
            LEFT JOIN lote_preguntas lp
              ON lp.id = bp.pregunta_id
             AND (
                    lp.origen_oposicion IS NULL
                    OR TRIM(lp.origen_oposicion) = ''
                    OR UPPER(TRIM(lp.origen_oposicion)) IN ({marcas})
                 )
             AND ({condicion})
            WHERE cp.convocatoria_id = ?
            GROUP BY cp.id, cp.nombre, cp.orden, cp.numero_preguntas
            ORDER BY cp.orden
            """,
            (*origenes_n, convocatoria_id),
        ).fetchall()

    return [dict(x) for x in filas]


def _ultima_aparicion(
    convocatoria_id: int,
    user_id: UUID,
) -> dict[int, datetime]:
    with conectar_postgres() as con:
        with con.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT sp.pregunta_id, MAX(s.fecha_generacion) AS ultima_fecha
                FROM public.simulacros s
                JOIN public.simulacro_preguntas sp ON sp.simulacro_id = s.id
                WHERE s.user_id = %s
                  AND s.convocatoria_id = %s
                  AND s.estado <> 'ANULADO'
                  AND sp.pregunta_id IS NOT NULL
                GROUP BY sp.pregunta_id
                """,
                (user_id, convocatoria_id),
            )
            filas = cur.fetchall()

    return {
        int(fila["pregunta_id"]): fila["ultima_fecha"]
        for fila in filas
        if fila["ultima_fecha"] is not None
    }


def _seleccionar(
    candidatas: list,
    cantidad: int,
    ultima: dict[int, datetime],
) -> list:
    limite = datetime.now().astimezone() - timedelta(days=DIAS_SIN_REPETICION)
    no_recientes, recientes = [], []

    for pregunta in candidatas:
        fecha = ultima.get(int(pregunta["pregunta_id"]))
        if fecha is not None and fecha.tzinfo is None:
            fecha = fecha.astimezone()
        (
            no_recientes
            if fecha is None or fecha <= limite
            else recientes
        ).append(pregunta)

    if len(no_recientes) >= cantidad:
        return random.sample(no_recientes, cantidad)

    random.shuffle(no_recientes)
    random.shuffle(recientes)
    recientes.sort(key=lambda p: ultima[int(p["pregunta_id"])])
    return no_recientes + recientes[: cantidad - len(no_recientes)]


def crear_simulacro(
    convocatoria_id: int,
    origenes: list[str],
    fuentes: list[str] | None,
    user_id: UUID,
) -> int:
    origenes_n = _normalizar_origenes(origenes)
    fuentes_n = _normalizar_fuentes(fuentes)
    marcas = ", ".join("?" for _ in origenes_n)
    condicion = _condicion_fuente(fuentes_n)

    with conectar_contenidos() as con:
        convocatoria = con.execute(
            """
            SELECT id, puesto, numero, anio, codigo, numero_preguntas,
                   valoracion_test_acierto, valoracion_test_fallo,
                   valoracion_test_no_contesta, formula_nota, factor_escala_nota
            FROM convocatorias
            WHERE id = ?
            """,
            (convocatoria_id,),
        ).fetchone()

        if convocatoria is None:
            raise ValueError("La convocatoria no existe.")

        partes = con.execute(
            """
            SELECT id, nombre, numero_preguntas, orden
            FROM convocatoria_partes
            WHERE convocatoria_id = ?
            ORDER BY orden
            """,
            (convocatoria_id,),
        ).fetchall()

        if not partes:
            raise ValueError("La convocatoria no tiene partes configuradas.")

        if sum(p["numero_preguntas"] for p in partes) != convocatoria["numero_preguntas"]:
            raise ValueError(
                "La suma de preguntas de las partes no coincide con el total configurado."
            )

        candidatas = con.execute(
            f"""
            SELECT DISTINCT
                bp.id AS banco_pregunta_id,
                bp.pregunta_id,
                bp.convocatoria_parte_id,
                lp.enunciado,
                lp.opcion_a,
                lp.opcion_b,
                lp.opcion_c,
                lp.opcion_d,
                lp.respuesta_correcta,
                lp.tipo_clasificacion,
                lp.tipo_norma,
                lp.nombre_norma,
                lp.articulo,
                lp.tema_no_juridico,
                lp.origen_oposicion,
                lp.tipo_fuente,
                lp.importacion_fichero_id,
                lp.pagina_origen,
                lp.norma_id_normalizada,
                lp.articulo_normalizado,
                lp.teorica_practica,
                lp.tipo_norma_normalizado,
                lp.nombre_norma_normalizado,
                bp.tipo_vinculacion,
                bp.estado AS banco_estado,
                bp.metodo_vinculacion,
                bp.motivo_revision,
                tt.id AS tema_id,
                tt.parte AS tema_parte,
                tt.numero_tema,
                tt.titulo AS tema_titulo,
                tt.tipo_contenido AS tema_tipo_contenido
            FROM banco_preguntas bp
            JOIN convocatoria_partes cp
              ON cp.id = bp.convocatoria_parte_id
             AND cp.convocatoria_id = bp.convocatoria_id
            JOIN lote_preguntas lp
              ON lp.id = bp.pregunta_id
            JOIN banco_preguntas_temas bpt
              ON bpt.banco_pregunta_id = bp.id
             AND bpt.es_principal = 1
            JOIN temario_temas tt
              ON tt.id = bpt.tema_id
            WHERE bp.convocatoria_id = ?
              AND bp.estado = 'INCLUIDA'
              AND (
                    lp.origen_oposicion IS NULL
                    OR TRIM(lp.origen_oposicion) = ''
                    OR UPPER(TRIM(lp.origen_oposicion)) IN ({marcas})
                  )
              AND ({condicion})
            """,
            (convocatoria_id, *origenes_n),
        ).fetchall()

    ultima = _ultima_aparicion(convocatoria_id, user_id)
    seleccionadas = []
    usadas = set()

    for parte in partes:
        disponibles = [
            pregunta
            for pregunta in candidatas
            if pregunta["convocatoria_parte_id"] == parte["id"]
            and pregunta["pregunta_id"] not in usadas
        ]
        cantidad = parte["numero_preguntas"]

        if len(disponibles) < cantidad:
            raise ValueError(
                f'No hay suficientes preguntas para {parte["nombre"]}. '
                f"Se necesitan {cantidad} y solo hay {len(disponibles)}."
            )

        for pregunta in _seleccionar(disponibles, cantidad, ultima):
            usadas.add(pregunta["pregunta_id"])
            seleccionadas.append((parte, pregunta))

    with conectar_postgres() as con:
        with con.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT COALESCE(MAX(numero), 0) + 1 AS siguiente
                FROM public.simulacros
                WHERE user_id = %s
                  AND convocatoria_id = %s
                  AND tipo_prueba = 'SIMULACRO'
                """,
                (user_id, convocatoria_id),
            )
            numero = int(cur.fetchone()["siguiente"])

            cur.execute(
                """
                INSERT INTO public.simulacros (
                    user_id,
                    convocatoria_id,
                    numero,
                    total_preguntas,
                    tipo_prueba,
                    convocatoria_codigo,
                    convocatoria_puesto,
                    convocatoria_numero,
                    convocatoria_anio,
                    convocatoria_numero_preguntas,
                    valoracion_test_acierto,
                    valoracion_test_fallo,
                    valoracion_test_no_contesta,
                    formula_nota,
                    factor_escala_nota
                )
                VALUES (
                    %s, %s, %s, %s, 'SIMULACRO',
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
                RETURNING id
                """,
                (
                    user_id,
                    convocatoria_id,
                    numero,
                    convocatoria["numero_preguntas"],
                    convocatoria["codigo"],
                    convocatoria["puesto"],
                    convocatoria["numero"],
                    convocatoria["anio"],
                    convocatoria["numero_preguntas"],
                    convocatoria["valoracion_test_acierto"],
                    convocatoria["valoracion_test_fallo"],
                    convocatoria["valoracion_test_no_contesta"],
                    convocatoria["formula_nota"],
                    convocatoria["factor_escala_nota"],
                ),
            )
            simulacro_id = int(cur.fetchone()["id"])

            for orden, (parte, pregunta) in enumerate(seleccionadas, 1):
                cur.execute(
                    """
                    INSERT INTO public.simulacro_preguntas (
                        simulacro_id,
                        orden,
                        pregunta_id,
                        banco_pregunta_id,
                        parte_id,
                        parte_nombre,
                        parte_orden
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (
                        simulacro_id,
                        orden,
                        pregunta["pregunta_id"],
                        pregunta["banco_pregunta_id"],
                        parte["id"],
                        parte["nombre"],
                        parte["orden"],
                    ),
                )
                simulacro_pregunta_id = int(cur.fetchone()["id"])

                tema = {
                    "tema_id_original": pregunta["tema_id"],
                    "parte": pregunta["tema_parte"],
                    "numero_tema": pregunta["numero_tema"],
                    "titulo": pregunta["tema_titulo"],
                    "tipo_contenido": pregunta["tema_tipo_contenido"],
                    "es_principal": 1,
                }

                cur.execute(
                    """
                    INSERT INTO public.simulacro_snapshot (
                        simulacro_pregunta_id,
                        enunciado,
                        opcion_a,
                        opcion_b,
                        opcion_c,
                        opcion_d,
                        respuesta_correcta,
                        tipo_clasificacion,
                        tipo_norma,
                        nombre_norma,
                        articulo,
                        tema_no_juridico,
                        origen_oposicion,
                        tipo_fuente,
                        importacion_fichero_id,
                        pagina_origen,
                        norma_id_normalizada,
                        articulo_normalizado,
                        teorica_practica,
                        tipo_norma_normalizado,
                        nombre_norma_normalizado,
                        banco_tipo_vinculacion,
                        banco_estado,
                        banco_metodo_vinculacion,
                        banco_motivo_revision,
                        temas_json,
                        comentario_solucion
                    )
                    VALUES (
                        %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, NULL
                    )
                    """,
                    (
                        simulacro_pregunta_id,
                        pregunta["enunciado"],
                        pregunta["opcion_a"],
                        pregunta["opcion_b"],
                        pregunta["opcion_c"],
                        pregunta["opcion_d"],
                        pregunta["respuesta_correcta"],
                        pregunta["tipo_clasificacion"],
                        pregunta["tipo_norma"],
                        pregunta["nombre_norma"],
                        pregunta["articulo"],
                        pregunta["tema_no_juridico"],
                        pregunta["origen_oposicion"],
                        pregunta["tipo_fuente"],
                        pregunta["importacion_fichero_id"],
                        pregunta["pagina_origen"],
                        pregunta["norma_id_normalizada"],
                        pregunta["articulo_normalizado"],
                        pregunta["teorica_practica"],
                        pregunta["tipo_norma_normalizado"],
                        pregunta["nombre_norma_normalizado"],
                        pregunta["tipo_vinculacion"],
                        pregunta["banco_estado"],
                        pregunta["metodo_vinculacion"],
                        pregunta["motivo_revision"],
                        Jsonb(tema),
                    ),
                )

        con.commit()

    return simulacro_id


def obtener_simulacro(simulacro_id: int, user_id: UUID) -> dict | None:

    with conectar_postgres() as con:
        with con.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT
                    id,
                    convocatoria_id,
                    numero,
                    fecha_generacion,
                    total_preguntas,
                    estado,
                    tipo_prueba,
                    convocatoria_codigo,
                    convocatoria_puesto,
                    convocatoria_numero,
                    convocatoria_anio
                FROM public.simulacros
                WHERE id = %s
                  AND user_id = %s
                """,
                (simulacro_id, user_id),
            )
            fila = cur.fetchone()

    return _serializar_fila(fila) if fila else None


def obtener_preguntas_para_realizar(
    simulacro_id: int,
    user_id: UUID,
) -> list[dict]:
    """No expone respuesta_correcta: endpoint apto para el futuro frontend."""

    with conectar_postgres() as con:
        with con.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT
                    sp.id AS simulacro_pregunta_id,
                    sp.orden,
                    sp.parte_nombre,
                    sp.respuesta_usuario,
                    sp.seguridad_usuario,
                    ss.enunciado,
                    ss.opcion_a,
                    ss.opcion_b,
                    ss.opcion_c,
                    ss.opcion_d
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
            filas = cur.fetchall()

    return [_serializar_fila(fila) for fila in filas]


def guardar_respuestas(
    simulacro_id: int,
    respuestas: list[dict],
    user_id: UUID,
) -> None:

    with conectar_postgres() as con:
        with con.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT id, estado
                FROM public.simulacros
                WHERE id = %s
                  AND user_id = %s
                FOR UPDATE
                """,
                (simulacro_id, user_id),
            )
            simulacro = cur.fetchone()

            if simulacro is None:
                raise ValueError("El simulacro no existe.")

            if simulacro["estado"] == "FINALIZADO":
                raise ValueError(
                    "El simulacro ya está finalizado y no admite cambios."
                )

            cur.execute(
                """
                SELECT id
                FROM public.simulacro_preguntas
                WHERE simulacro_id = %s
                """,
                (simulacro_id,),
            )
            ids_validos = {int(fila["id"]) for fila in cur.fetchall()}

            vistos: set[int] = set()

            for item in respuestas:
                simulacro_pregunta_id = int(item["simulacro_pregunta_id"])

                if simulacro_pregunta_id in vistos:
                    raise ValueError(
                        f"La pregunta {simulacro_pregunta_id} aparece repetida en el envío."
                    )
                vistos.add(simulacro_pregunta_id)

                if simulacro_pregunta_id not in ids_validos:
                    raise ValueError(
                        f"La pregunta {simulacro_pregunta_id} no pertenece al simulacro."
                    )

                respuesta = item.get("respuesta")
                if respuesta is not None:
                    respuesta = str(respuesta).strip().upper() or None

                if respuesta is not None and respuesta not in RESPUESTAS_VALIDAS:
                    raise ValueError("La respuesta debe ser A, B, C, D o null.")

                seguridad = item.get("seguridad")
                if seguridad is not None:
                    seguridad = (
                        str(seguridad).strip().upper().replace(" ", "_") or None
                    )

                if seguridad is not None and seguridad not in SEGURIDADES_VALIDAS:
                    raise ValueError("Seguridad no válida.")

                if respuesta is None:
                    seguridad = None

                cur.execute(
                    """
                    UPDATE public.simulacro_preguntas
                    SET respuesta_usuario = %s,
                        seguridad_usuario = %s,
                        updated_at = now()
                    WHERE id = %s
                      AND simulacro_id = %s
                    """,
                    (
                        respuesta,
                        seguridad,
                        simulacro_pregunta_id,
                        simulacro_id,
                    ),
                )

            cur.execute(
                """
                UPDATE public.simulacros
                SET updated_at = now()
                WHERE id = %s
                  AND user_id = %s
                """,
                (simulacro_id, user_id),
            )

        con.commit()


def finalizar_simulacro(simulacro_id: int, user_id: UUID) -> dict:
    """Cierra y califica usando la configuración congelada del simulacro."""

    with conectar_postgres() as con:
        with con.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT
                    id,
                    estado,
                    tipo_prueba,
                    total_preguntas,
                    convocatoria_numero_preguntas,
                    valoracion_test_acierto,
                    valoracion_test_fallo,
                    valoracion_test_no_contesta,
                    factor_escala_nota
                FROM public.simulacros
                WHERE id = %s
                  AND user_id = %s
                FOR UPDATE
                """,
                (simulacro_id, user_id),
            )
            simulacro = cur.fetchone()

            if simulacro is None:
                raise ValueError("El simulacro no existe.")

            cur.execute(
                """
                SELECT sp.respuesta_usuario, ss.respuesta_correcta
                FROM public.simulacro_preguntas sp
                JOIN public.simulacro_snapshot ss
                  ON ss.simulacro_pregunta_id = sp.id
                WHERE sp.simulacro_id = %s
                """,
                (simulacro_id,),
            )
            filas = cur.fetchall()

            if not filas:
                raise ValueError("El simulacro no contiene preguntas.")

            aciertos = 0
            fallos = 0
            no_contestadas = 0

            for fila in filas:
                respuesta = (fila["respuesta_usuario"] or "").strip().upper()
                correcta = (fila["respuesta_correcta"] or "").strip().upper()

                if not respuesta:
                    no_contestadas += 1
                elif respuesta == correcta:
                    aciertos += 1
                else:
                    fallos += 1

            valor_acierto = float(
                simulacro["valoracion_test_acierto"]
                if simulacro["valoracion_test_acierto"] is not None
                else 1.0
            )
            valor_fallo = float(
                simulacro["valoracion_test_fallo"]
                if simulacro["valoracion_test_fallo"] is not None
                else 0.0
            )
            valor_no_contesta = float(
                simulacro["valoracion_test_no_contesta"]
                if simulacro["valoracion_test_no_contesta"] is not None
                else 0.0
            )
            escala = float(
                simulacro["factor_escala_nota"]
                if simulacro["factor_escala_nota"] is not None
                else 10.0
            )
            denominador = int(
                simulacro["total_preguntas"]
                if simulacro["tipo_prueba"] == "TEST"
                else (
                    simulacro["convocatoria_numero_preguntas"]
                    or simulacro["total_preguntas"]
                    or len(filas)
                )
            )

            puntos = (
                aciertos * valor_acierto
                + fallos * valor_fallo
                + no_contestadas * valor_no_contesta
            )
            nota = (puntos / denominador) * escala if denominador else 0.0

            cur.execute(
                """
                UPDATE public.simulacros
                SET estado = 'FINALIZADO',
                    finalizado_at = COALESCE(finalizado_at, now()),
                    updated_at = now()
                WHERE id = %s
                  AND user_id = %s
                """,
                (simulacro_id, user_id),
            )

        con.commit()

    return {
        "simulacro_id": simulacro_id,
        "total": len(filas),
        "contestadas": aciertos + fallos,
        "aciertos": aciertos,
        "fallos": fallos,
        "no_contestadas": no_contestadas,
        "puntos": round(puntos, 4),
        "nota": round(nota, 2),
    }


def obtener_correccion(simulacro_id: int, user_id: UUID) -> list[dict]:
    """Expone la solución solo si el simulacro del usuario está finalizado."""

    with conectar_postgres() as con:
        with con.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT id, estado
                FROM public.simulacros
                WHERE id = %s
                  AND user_id = %s
                """,
                (simulacro_id, user_id),
            )
            simulacro = cur.fetchone()

            if simulacro is None:
                raise ValueError("El simulacro no existe.")

            if simulacro["estado"] != "FINALIZADO":
                raise ValueError(
                    "Debe finalizar el simulacro antes de consultar la corrección."
                )

            cur.execute(
                """
                SELECT
                    sp.id AS simulacro_pregunta_id,
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
                    CASE
                        WHEN sp.respuesta_usuario IS NULL
                             OR btrim(sp.respuesta_usuario) = ''
                            THEN 'NO_CONTESTADA'
                        WHEN upper(btrim(sp.respuesta_usuario))
                             = upper(btrim(ss.respuesta_correcta))
                            THEN 'ACIERTO'
                        ELSE 'FALLO'
                    END AS resultado
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
            filas = cur.fetchall()

    return [_serializar_fila(fila) for fila in filas]



def listar_simulacros(
    user_id: UUID,
    convocatoria_id: int | None = None,
    tipo_prueba: str = "SIMULACRO",
) -> list[dict]:
    tipo = str(tipo_prueba).strip().upper()
    if tipo not in {"SIMULACRO", "TEST"}:
        raise ValueError("tipo_prueba debe ser SIMULACRO o TEST.")

    parametros: list[object] = [user_id, tipo]
    filtro_convocatoria = ""

    if convocatoria_id is not None:
        filtro_convocatoria = "AND s.convocatoria_id = %s"
        parametros.append(convocatoria_id)

    with conectar_postgres() as con:
        with con.cursor(row_factory=dict_row) as cur:
            cur.execute(
                f"""
                SELECT
                    s.id,
                    s.convocatoria_id,
                    s.numero,
                    s.fecha_generacion,
                    s.total_preguntas,
                    s.estado,
                    s.tipo_prueba,
                    s.convocatoria_codigo,
                    COUNT(sp.id) FILTER (
                        WHERE sp.respuesta_usuario IS NOT NULL
                    )::int AS contestadas
                FROM public.simulacros s
                LEFT JOIN public.simulacro_preguntas sp
                  ON sp.simulacro_id = s.id
                WHERE s.user_id = %s
                  AND s.tipo_prueba = %s
                  AND s.estado <> 'ANULADO'
                  {filtro_convocatoria}
                GROUP BY s.id
                ORDER BY s.fecha_generacion DESC, s.id DESC
                """,
                tuple(parametros),
            )
            filas = cur.fetchall()

    return [_serializar_fila(fila) for fila in filas]


def eliminar_simulacro(simulacro_id: int, user_id: UUID) -> bool:
    with conectar_postgres() as con:
        with con.cursor() as cur:
            cur.execute(
                """
                DELETE FROM public.simulacros
                WHERE id = %s
                  AND user_id = %s
                """,
                (simulacro_id, user_id),
            )
            eliminado = cur.rowcount == 1
        con.commit()

    return eliminado


def obtener_resultado_guardado(
    simulacro_id: int,
    user_id: UUID,
) -> dict:
    with conectar_postgres() as con:
        with con.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT
                    id,
                    estado,
                    tipo_prueba,
                    total_preguntas,
                    convocatoria_numero_preguntas,
                    valoracion_test_acierto,
                    valoracion_test_fallo,
                    valoracion_test_no_contesta,
                    factor_escala_nota
                FROM public.simulacros
                WHERE id = %s
                  AND user_id = %s
                """,
                (simulacro_id, user_id),
            )
            simulacro = cur.fetchone()

            if simulacro is None:
                raise ValueError("El simulacro no existe.")

            if simulacro["estado"] != "FINALIZADO":
                raise ValueError("El simulacro todavía no está finalizado.")

            cur.execute(
                """
                SELECT sp.respuesta_usuario, ss.respuesta_correcta
                FROM public.simulacro_preguntas sp
                JOIN public.simulacro_snapshot ss
                  ON ss.simulacro_pregunta_id = sp.id
                WHERE sp.simulacro_id = %s
                """,
                (simulacro_id,),
            )
            filas = cur.fetchall()

    aciertos = 0
    fallos = 0
    no_contestadas = 0

    for fila in filas:
        respuesta = (fila["respuesta_usuario"] or "").strip().upper()
        correcta = (fila["respuesta_correcta"] or "").strip().upper()

        if not respuesta:
            no_contestadas += 1
        elif respuesta == correcta:
            aciertos += 1
        else:
            fallos += 1

    valor_acierto = float(
        simulacro["valoracion_test_acierto"]
        if simulacro["valoracion_test_acierto"] is not None
        else 1.0
    )
    valor_fallo = float(
        simulacro["valoracion_test_fallo"]
        if simulacro["valoracion_test_fallo"] is not None
        else 0.0
    )
    valor_no_contesta = float(
        simulacro["valoracion_test_no_contesta"]
        if simulacro["valoracion_test_no_contesta"] is not None
        else 0.0
    )
    escala = float(
        simulacro["factor_escala_nota"]
        if simulacro["factor_escala_nota"] is not None
        else 10.0
    )
    denominador = int(
        simulacro["total_preguntas"]
        if simulacro["tipo_prueba"] == "TEST"
        else (
            simulacro["convocatoria_numero_preguntas"]
            or simulacro["total_preguntas"]
            or len(filas)
        )
    )

    puntos = (
        aciertos * valor_acierto
        + fallos * valor_fallo
        + no_contestadas * valor_no_contesta
    )
    nota = (puntos / denominador) * escala if denominador else 0.0

    return {
        "simulacro_id": simulacro_id,
        "total": len(filas),
        "contestadas": aciertos + fallos,
        "aciertos": aciertos,
        "fallos": fallos,
        "no_contestadas": no_contestadas,
        "puntos": round(puntos, 4),
        "nota": round(nota, 2),
    }
