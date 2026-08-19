from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from psycopg.rows import dict_row

from app.postgres import conectar_postgres


BACKEND_DIR = Path(__file__).resolve().parents[1]
SQLITE_PATH = BACKEND_DIR / "data" / "oposiciones.sqlite3"


def conectar_sqlite() -> sqlite3.Connection:
    if not SQLITE_PATH.is_file():
        raise RuntimeError(f"No existe la SQLite local: {SQLITE_PATH}")
    uri = SQLITE_PATH.resolve().as_uri() + "?mode=ro"
    con = sqlite3.connect(uri, uri=True)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA query_only = ON")
    return con


def normalizar(valor: Any) -> Any:
    if isinstance(valor, sqlite3.Row):
        return {k: normalizar(valor[k]) for k in valor.keys()}
    if isinstance(valor, dict):
        return {str(k): normalizar(v) for k, v in valor.items()}
    if isinstance(valor, (list, tuple)):
        return [normalizar(v) for v in valor]
    return valor


def _clave_canonica(valor: Any) -> str:
    return json.dumps(
        normalizar(valor),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )


def comparar(
    nombre: str,
    sqlite_valor: Any,
    pg_valor: Any,
    *,
    ignorar_orden: bool = False,
) -> None:
    a = normalizar(sqlite_valor)
    b = normalizar(pg_valor)

    if ignorar_orden:
        if not isinstance(a, list) or not isinstance(b, list):
            raise TypeError("ignorar_orden sólo puede usarse con listas.")
        a_cmp = sorted((_clave_canonica(x) for x in a))
        b_cmp = sorted((_clave_canonica(x) for x in b))
    else:
        a_cmp = a
        b_cmp = b

    if a_cmp == b_cmp:
        sufijo = ""
        if isinstance(a, list):
            sufijo = f" ({len(a)} filas)"
        print(f"{nombre:<48} OK{sufijo}")
        return

    print(f"\nERROR EN {nombre}")
    if isinstance(a, list) and isinstance(b, list):
        print(f"Filas SQLite:  {len(a)}")
        print(f"Filas Supabase:{len(b)}")

        if ignorar_orden:
            set_a = set(a_cmp)
            set_b = set(b_cmp)
            solo_a = sorted(set_a - set_b)
            solo_b = sorted(set_b - set_a)

            print(f"Sólo en SQLite:   {len(solo_a)}")
            print(f"Sólo en Supabase: {len(solo_b)}")

            if solo_a:
                print("\nEjemplos sólo en SQLite:")
                for item in solo_a[:3]:
                    print(item)
            if solo_b:
                print("\nEjemplos sólo en Supabase:")
                for item in solo_b[:3]:
                    print(item)
        else:
            limite = min(len(a), len(b))
            indice = next((i for i in range(limite) if a[i] != b[i]), None)
            if indice is None and len(a) != len(b):
                indice = limite
            print(f"Primera diferencia en posición: {indice}")
            if indice is not None and indice < len(a):
                print("SQLite:", _clave_canonica(a[indice]))
            if indice is not None and indice < len(b):
                print("Supabase:", _clave_canonica(b[indice]))
    else:
        print("SQLite:", _clave_canonica(a))
        print("Supabase:", _clave_canonica(b))

    raise RuntimeError(f"No coincide: {nombre}")


def consultar_sqlite(con: sqlite3.Connection, query: str, params=()):
    return [dict(r) for r in con.execute(query, params).fetchall()]


def consultar_pg(query: str, params=()):
    with conectar_postgres() as con:
        with con.cursor(row_factory=dict_row) as cur:
            cur.execute(query, params)
            return [dict(r) for r in cur.fetchall()]


def main() -> int:
    print("=" * 78)
    print("COMPARACIÓN DE CONTENIDOS SQLITE ↔ SUPABASE")
    print("=" * 78)
    print(f"SQLite:  {SQLITE_PATH}")
    print("Supabase: esquema contenidos")
    print("Modo: SOLO LECTURA")
    print()

    sqlite_con = conectar_sqlite()
    try:
        # 1. Convocatorias
        q_sqlite = """
            SELECT id, puesto, numero, anio, codigo
            FROM convocatorias
            ORDER BY anio DESC, numero, puesto
        """
        q_pg = """
            SELECT id, puesto, numero, anio, codigo
            FROM contenidos.convocatorias
            ORDER BY anio DESC, numero, puesto
        """
        convocatorias_sqlite = consultar_sqlite(sqlite_con, q_sqlite)
        convocatorias_pg = consultar_pg(q_pg)
        comparar("Listado de convocatorias", convocatorias_sqlite, convocatorias_pg)

        ids = [int(x["id"]) for x in convocatorias_sqlite]
        if not ids:
            raise RuntimeError("No existen convocatorias en SQLite.")

        for convocatoria_id in ids:
            # 2. Resumen de convocatoria
            q_sqlite = """
                SELECT
                    c.id, c.codigo, c.puesto, c.numero, c.anio,
                    c.numero_preguntas,
                    t.id AS temario_id,
                    t.nombre AS temario_nombre,
                    (
                        SELECT COUNT(*)
                        FROM temario_temas tt
                        WHERE tt.temario_id = t.id
                    ) AS total_temas,
                    (
                        SELECT COUNT(*)
                        FROM banco_preguntas bp
                        JOIN lote_preguntas lp ON lp.id = bp.pregunta_id
                        WHERE bp.convocatoria_id = c.id
                          AND bp.estado = 'INCLUIDA'
                    ) AS total_banco
                FROM convocatorias c
                LEFT JOIN temarios t ON t.convocatoria_id = c.id
                WHERE c.id = ?
            """
            q_pg = """
                SELECT
                    c.id, c.codigo, c.puesto, c.numero, c.anio,
                    c.numero_preguntas,
                    t.id AS temario_id,
                    t.nombre AS temario_nombre,
                    (
                        SELECT COUNT(*)
                        FROM contenidos.temario_temas tt
                        WHERE tt.temario_id = t.id
                    ) AS total_temas,
                    (
                        SELECT COUNT(*)
                        FROM contenidos.banco_preguntas bp
                        JOIN contenidos.lote_preguntas lp ON lp.id = bp.pregunta_id
                        WHERE bp.convocatoria_id = c.id
                          AND bp.estado = 'INCLUIDA'
                    ) AS total_banco
                FROM contenidos.convocatorias c
                LEFT JOIN contenidos.temarios t ON t.convocatoria_id = c.id
                WHERE c.id = %s
            """
            s = consultar_sqlite(sqlite_con, q_sqlite, (convocatoria_id,))
            p = consultar_pg(q_pg, (convocatoria_id,))
            comparar(f"Resumen convocatoria {convocatoria_id}", s, p)

            # 3. Partes
            s = consultar_sqlite(
                sqlite_con,
                """
                SELECT id, nombre, numero_preguntas, orden
                FROM convocatoria_partes
                WHERE convocatoria_id = ?
                ORDER BY orden
                """,
                (convocatoria_id,),
            )
            p = consultar_pg(
                """
                SELECT id, nombre, numero_preguntas, orden
                FROM contenidos.convocatoria_partes
                WHERE convocatoria_id = %s
                ORDER BY orden
                """,
                (convocatoria_id,),
            )
            comparar(f"Partes convocatoria {convocatoria_id}", s, p)

            # 4. Temas
            s = consultar_sqlite(
                sqlite_con,
                """
                SELECT tt.id, tt.parte, tt.numero_tema, tt.titulo, tt.tipo_contenido
                FROM temarios t
                JOIN temario_temas tt ON tt.temario_id = t.id
                WHERE t.convocatoria_id = ?
                ORDER BY tt.parte, tt.numero_tema, tt.id
                """,
                (convocatoria_id,),
            )
            p = consultar_pg(
                """
                SELECT tt.id, tt.parte, tt.numero_tema, tt.titulo, tt.tipo_contenido
                FROM contenidos.temarios t
                JOIN contenidos.temario_temas tt ON tt.temario_id = t.id
                WHERE t.convocatoria_id = %s
                ORDER BY tt.parte, tt.numero_tema, tt.id
                """,
                (convocatoria_id,),
            )
            comparar(f"Temario convocatoria {convocatoria_id}", s, p)

            # 5. Modelo de examen
            s = consultar_sqlite(
                sqlite_con,
                """
                SELECT
                    cmb.id, cmb.convocatoria_parte_id, cmb.orden,
                    cmb.tipo_bloque, cmb.norma_id, cmb.cantidad,
                    n.nombre_canonico AS norma
                FROM convocatoria_modelo_bloques cmb
                LEFT JOIN normas n ON n.id = cmb.norma_id
                JOIN convocatoria_partes cp ON cp.id = cmb.convocatoria_parte_id
                WHERE cp.convocatoria_id = ?
                ORDER BY cp.orden, cmb.orden, cmb.id
                """,
                (convocatoria_id,),
            )
            p = consultar_pg(
                """
                SELECT
                    cmb.id, cmb.convocatoria_parte_id, cmb.orden,
                    cmb.tipo_bloque, cmb.norma_id, cmb.cantidad,
                    n.nombre_canonico AS norma
                FROM contenidos.convocatoria_modelo_bloques cmb
                LEFT JOIN contenidos.normas n ON n.id = cmb.norma_id
                JOIN contenidos.convocatoria_partes cp
                  ON cp.id = cmb.convocatoria_parte_id
                WHERE cp.convocatoria_id = %s
                ORDER BY cp.orden, cmb.orden, cmb.id
                """,
                (convocatoria_id,),
            )
            comparar(f"Modelo examen convocatoria {convocatoria_id}", s, p)

            # 6. Corpus real usado por chat
            s = consultar_sqlite(
                sqlite_con,
                """
                SELECT DISTINCT
                    af.id AS articulo_fuente_id,
                    tt.id AS tema_id,
                    tt.parte,
                    tt.numero_tema,
                    tt.titulo AS titulo_tema,
                    tr.nombre_norma_csv,
                    tr.nombre_norma_normalizada,
                    tr.articulo_solicitado,
                    af.articulo_boe,
                    af.titulo_bloque,
                    af.texto
                FROM temarios t
                JOIN temario_temas tt ON tt.temario_id = t.id
                JOIN temario_referencias tr ON tr.tema_id = tt.id
                JOIN articulos_fuente af ON af.id = tr.articulo_fuente_id
                WHERE t.convocatoria_id = ?
                  AND tr.estado = 'COMPLETADO'
                  AND af.texto IS NOT NULL
                  AND TRIM(af.texto) <> ''
                ORDER BY
                    tt.parte,
                    tt.numero_tema,
                    tr.nombre_norma_csv,
                    tr.articulo_solicitado
                """,
                (convocatoria_id,),
            )
            p = consultar_pg(
                """
                SELECT DISTINCT
                    af.id AS articulo_fuente_id,
                    tt.id AS tema_id,
                    tt.parte,
                    tt.numero_tema,
                    tt.titulo AS titulo_tema,
                    tr.nombre_norma_csv,
                    tr.nombre_norma_normalizada,
                    tr.articulo_solicitado,
                    af.articulo_boe,
                    af.titulo_bloque,
                    af.texto
                FROM contenidos.temarios t
                JOIN contenidos.temario_temas tt ON tt.temario_id = t.id
                JOIN contenidos.temario_referencias tr ON tr.tema_id = tt.id
                JOIN contenidos.articulos_fuente af ON af.id = tr.articulo_fuente_id
                WHERE t.convocatoria_id = %s
                  AND tr.estado = 'COMPLETADO'
                  AND af.texto IS NOT NULL
                  AND TRIM(af.texto) <> ''
                ORDER BY
                    tt.parte,
                    tt.numero_tema,
                    tr.nombre_norma_csv,
                    tr.articulo_solicitado
                """,
                (convocatoria_id,),
            )
            comparar(
                f"Corpus chat convocatoria {convocatoria_id}",
                s,
                p,
                ignorar_orden=True,
            )

            # 7. Banco: comparación de identificadores y atributos esenciales.
            s = consultar_sqlite(
                sqlite_con,
                """
                SELECT
                    bp.id AS banco_pregunta_id,
                    bp.pregunta_id,
                    bp.convocatoria_parte_id,
                    bp.tipo_vinculacion,
                    bp.estado,
                    lp.tipo_clasificacion,
                    lp.tipo_fuente,
                    lp.origen_oposicion,
                    lp.norma_id_normalizada,
                    lp.teorica_practica
                FROM banco_preguntas bp
                JOIN lote_preguntas lp ON lp.id = bp.pregunta_id
                WHERE bp.convocatoria_id = ?
                ORDER BY bp.id
                """,
                (convocatoria_id,),
            )
            p = consultar_pg(
                """
                SELECT
                    bp.id AS banco_pregunta_id,
                    bp.pregunta_id,
                    bp.convocatoria_parte_id,
                    bp.tipo_vinculacion,
                    bp.estado,
                    lp.tipo_clasificacion,
                    lp.tipo_fuente,
                    lp.origen_oposicion,
                    lp.norma_id_normalizada,
                    lp.teorica_practica
                FROM contenidos.banco_preguntas bp
                JOIN contenidos.lote_preguntas lp ON lp.id = bp.pregunta_id
                WHERE bp.convocatoria_id = %s
                ORDER BY bp.id
                """,
                (convocatoria_id,),
            )
            comparar(
                f"Banco convocatoria {convocatoria_id}",
                s,
                p,
                ignorar_orden=True,
            )

        print()
        print("=" * 78)
        print("RESULTADO FINAL: CORRECTO")
        print("=" * 78)
        print("Las consultas básicas de contenidos devuelven los mismos datos")
        print("en SQLite local y en contenidos.* de Supabase.")
        print("No se ha modificado ningún dato.")
        return 0

    finally:
        sqlite_con.close()


if __name__ == "__main__":
    raise SystemExit(main())
