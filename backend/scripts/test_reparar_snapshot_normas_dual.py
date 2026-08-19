from __future__ import annotations

import os

from scripts.reparar_snapshot_normas import cargar_nombres_canonicos


def main() -> int:
    original = os.environ.get("OPOCOACH_CONTENT_SOURCE")

    try:
        print("=" * 78)
        print("PRUEBA CATÁLOGO DE NORMAS SQLITE ↔ POSTGRES")
        print("=" * 78)
        print("Modo: SOLO LECTURA. No se modifica simulacro_snapshot.")
        print()

        os.environ["OPOCOACH_CONTENT_SOURCE"] = "sqlite"
        sqlite = cargar_nombres_canonicos()

        os.environ["OPOCOACH_CONTENT_SOURCE"] = "postgres"
        postgres = cargar_nombres_canonicos()

        if sqlite != postgres:
            ids_sqlite = set(sqlite)
            ids_postgres = set(postgres)
            solo_sqlite = sorted(ids_sqlite - ids_postgres)
            solo_postgres = sorted(ids_postgres - ids_sqlite)
            distintos = sorted(
                i for i in ids_sqlite & ids_postgres
                if sqlite[i] != postgres[i]
            )

            print("RESULTADO FINAL: ERROR")
            print(f"Entradas SQLite:    {len(sqlite)}")
            print(f"Entradas PostgreSQL:{len(postgres)}")
            print(f"Solo SQLite:        {solo_sqlite[:20]}")
            print(f"Solo PostgreSQL:    {solo_postgres[:20]}")
            print(f"Nombres distintos:  {distintos[:20]}")
            return 1

        print(f"Nombres canónicos comparados.................... {len(sqlite)}")
        print()
        print("=" * 78)
        print("RESULTADO FINAL: CORRECTO")
        print("=" * 78)
        print("El catálogo canónico de normas es equivalente en SQLite y Supabase.")
        print("No se ha modificado ningún dato.")
        return 0

    finally:
        if original is None:
            os.environ.pop("OPOCOACH_CONTENT_SOURCE", None)
        else:
            os.environ["OPOCOACH_CONTENT_SOURCE"] = original


if __name__ == "__main__":
    raise SystemExit(main())
