from __future__ import annotations

import os

from app.database import (
    conectar_contenidos_sqlite,
    conectar_contenidos_postgres,
)
from app.explicaciones_soluciones import _obtener_texto_articulo


def _casos_representativos() -> list[tuple[str, str]]:
    casos: list[tuple[str, str]] = []

    with conectar_contenidos_sqlite() as con:
        filas = con.execute(
            """
            SELECT DISTINCT
                CAST(tr.norma_id AS TEXT) AS norma_id,
                tr.articulo_solicitado
            FROM temario_referencias tr
            JOIN articulos_fuente af
              ON af.id = tr.articulo_fuente_id
            WHERE tr.norma_id IS NOT NULL
              AND tr.articulo_solicitado IS NOT NULL
              AND TRIM(tr.articulo_solicitado) <> ''
              AND af.texto IS NOT NULL
              AND TRIM(af.texto) <> ''
            ORDER BY tr.norma_id, tr.articulo_solicitado
            LIMIT 40
            """
        ).fetchall()

    for fila in filas:
        casos.append((str(fila["norma_id"]), str(fila["articulo_solicitado"])))

    if not casos:
        raise RuntimeError("No se han encontrado casos jurídicos representativos.")

    return casos


def main() -> int:
    original = os.environ.get("OPOCOACH_CONTENT_SOURCE")

    try:
        print("=" * 78)
        print("PRUEBA EXPLICACIONES/SOLUCIONES SQLITE ↔ POSTGRES")
        print("=" * 78)
        print("Modo: SOLO LECTURA. No se llama a OpenAI ni se modifican datos.")
        print()

        casos = _casos_representativos()
        errores = 0

        for norma_id, articulo in casos:
            os.environ["OPOCOACH_CONTENT_SOURCE"] = "sqlite"
            sqlite = _obtener_texto_articulo(norma_id, articulo)

            os.environ["OPOCOACH_CONTENT_SOURCE"] = "postgres"
            postgres = _obtener_texto_articulo(norma_id, articulo)

            if sqlite != postgres:
                errores += 1
                print(
                    f"ERROR | norma_id={norma_id} | articulo={articulo!r} | "
                    f"sqlite={'sí' if sqlite else 'no'} | "
                    f"postgres={'sí' if postgres else 'no'}"
                )

        # Casos vacíos / inválidos deben comportarse igual.
        for norma_id, articulo in (
            (None, None),
            ("", ""),
            ("999999999", "999999999"),
        ):
            os.environ["OPOCOACH_CONTENT_SOURCE"] = "sqlite"
            sqlite = _obtener_texto_articulo(norma_id, articulo)
            os.environ["OPOCOACH_CONTENT_SOURCE"] = "postgres"
            postgres = _obtener_texto_articulo(norma_id, articulo)
            if sqlite != postgres:
                errores += 1
                print(
                    f"ERROR caso borde | norma_id={norma_id!r} | "
                    f"articulo={articulo!r}"
                )

        if errores:
            print()
            print("=" * 78)
            print("RESULTADO FINAL: ERROR")
            print("=" * 78)
            print(f"Diferencias detectadas: {errores}")
            return 1

        print(f"Casos jurídicos comparados....................... {len(casos)}")
        print()
        print("=" * 78)
        print("RESULTADO FINAL: CORRECTO")
        print("=" * 78)
        print(
            "La recuperación del texto jurídico usada para generar explicaciones "
            "es equivalente en SQLite y PostgreSQL/Supabase."
        )
        print("No se ha llamado a OpenAI ni se ha modificado ningún dato.")
        return 0

    finally:
        if original is None:
            os.environ.pop("OPOCOACH_CONTENT_SOURCE", None)
        else:
            os.environ["OPOCOACH_CONTENT_SOURCE"] = original


if __name__ == "__main__":
    raise SystemExit(main())
