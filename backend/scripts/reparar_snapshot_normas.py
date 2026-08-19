from __future__ import annotations

from psycopg.rows import dict_row

from app.database import (
    ORIGEN_CONTENIDOS_POSTGRES,
    conectar_contenidos_postgres,
    conectar_contenidos_sqlite,
    obtener_origen_contenidos,
)
from app.postgres import conectar_postgres


def cargar_nombres_canonicos() -> dict[int, str]:
    origen = obtener_origen_contenidos()

    if origen == ORIGEN_CONTENIDOS_POSTGRES:
        with conectar_contenidos_postgres() as con:
            with con.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, nombre_canonico
                    FROM contenidos.normas
                    WHERE nombre_canonico IS NOT NULL
                      AND TRIM(nombre_canonico) <> ''
                    """
                )
                filas = cur.fetchall()
    else:
        with conectar_contenidos_sqlite() as con:
            filas = con.execute(
                """
                SELECT id, nombre_canonico
                FROM normas
                WHERE nombre_canonico IS NOT NULL
                  AND TRIM(nombre_canonico) <> ''
                """
            ).fetchall()

    return {
        int(fila["id"]): str(fila["nombre_canonico"]).strip()
        for fila in filas
    }


def main() -> None:
    canonicos = cargar_nombres_canonicos()

    if not canonicos:
        raise RuntimeError("La tabla normas no contiene nombres canónicos utilizables.")

    with conectar_postgres() as con:
        with con.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT
                    norma_id_normalizada,
                    nombre_norma_normalizado,
                    COUNT(*) AS total
                FROM public.simulacro_snapshot
                WHERE norma_id_normalizada IS NOT NULL
                GROUP BY norma_id_normalizada, nombre_norma_normalizado
                ORDER BY norma_id_normalizada, nombre_norma_normalizado
                """
            )
            antes = cur.fetchall()

        cambios_previstos = []
        sin_catalogo = []

        for fila in antes:
            norma_id = int(fila["norma_id_normalizada"])
            actual = fila["nombre_norma_normalizado"]
            canonico = canonicos.get(norma_id)

            if canonico is None:
                sin_catalogo.append(
                    {
                        "norma_id": norma_id,
                        "actual": actual,
                        "total": int(fila["total"]),
                    }
                )
                continue

            if actual != canonico:
                cambios_previstos.append(
                    {
                        "norma_id": norma_id,
                        "actual": actual,
                        "canonico": canonico,
                        "total": int(fila["total"]),
                    }
                )

        print("=" * 78)
        print("REPARACIÓN DE NOMBRES NORMALIZADOS EN SIMULACRO_SNAPSHOT")
        print("=" * 78)
        print(f"Grupos a corregir: {len(cambios_previstos)}")
        print(f"Grupos sin norma canónica local: {len(sin_catalogo)}")

        for item in cambios_previstos:
            print(
                f"ID {item['norma_id']}: "
                f"{item['actual']!r} -> {item['canonico']!r} "
                f"({item['total']} filas)"
            )

        if sin_catalogo:
            print("\nSIN CATÁLOGO:")
            for item in sin_catalogo:
                print(
                    f"ID {item['norma_id']}: {item['actual']!r} "
                    f"({item['total']} filas)"
                )
            raise RuntimeError(
                "Hay norma_id_normalizada sin nombre canónico local. "
                "No se ha modificado PostgreSQL."
            )

        if not cambios_previstos:
            print("\nNo hay cambios que aplicar.")
            return

        total_actualizadas = 0
        with con.cursor() as cur:
            for norma_id, canonico in canonicos.items():
                cur.execute(
                    """
                    UPDATE public.simulacro_snapshot
                    SET nombre_norma_normalizado = %s
                    WHERE norma_id_normalizada = %s
                      AND nombre_norma_normalizado IS DISTINCT FROM %s
                    """,
                    (canonico, norma_id, canonico),
                )
                total_actualizadas += cur.rowcount

        con.commit()

    print(f"\nFilas actualizadas: {total_actualizadas}")
    print("Reparación completada.")


if __name__ == "__main__":
    main()
