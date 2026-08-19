from __future__ import annotations

import os

from app.chat_convocatoria import _obtener_corpus_convocatoria


def canon(filas: list[dict]) -> list[tuple]:
    return sorted(
        (
            int(f["articulo_fuente_id"]),
            int(f["tema_id"]),
            str(f["parte"]),
            int(f["numero_tema"]),
            str(f["titulo_tema"]),
            str(f["nombre_norma_csv"] or ""),
            str(f["nombre_norma_normalizada"] or ""),
            str(f["articulo_solicitado"] or ""),
            str(f["articulo_boe"] or ""),
            str(f["titulo_bloque"] or ""),
            str(f["texto"] or ""),
        )
        for f in filas
    )


def cargar(origen: str, convocatoria_id: int) -> list[dict]:
    os.environ["OPOCOACH_CONTENT_SOURCE"] = origen
    return _obtener_corpus_convocatoria(convocatoria_id)


def main() -> int:
    original = os.environ.get("OPOCOACH_CONTENT_SOURCE")

    try:
        print("=" * 78)
        print("PRUEBA CORPUS CHAT SQLITE ↔ POSTGRES")
        print("=" * 78)

        for convocatoria_id in (1, 2):
            sqlite = cargar("sqlite", convocatoria_id)
            postgres = cargar("postgres", convocatoria_id)

            if canon(sqlite) != canon(postgres):
                print(
                    f"Convocatoria {convocatoria_id}: ERROR "
                    f"(SQLite={len(sqlite)}, PostgreSQL={len(postgres)})"
                )
                return 1

            print(
                f"Convocatoria {convocatoria_id}: "
                f"OK ({len(sqlite)} fragmentos)"
            )

        print()
        print("=" * 78)
        print("RESULTADO FINAL: CORRECTO")
        print("=" * 78)
        print("El corpus recuperado por chat_convocatoria.py es equivalente")
        print("con SQLite y PostgreSQL/Supabase.")
        print("No se ha llamado a OpenAI ni se ha modificado ningún dato.")
        return 0

    finally:
        if original is None:
            os.environ.pop("OPOCOACH_CONTENT_SOURCE", None)
        else:
            os.environ["OPOCOACH_CONTENT_SOURCE"] = original


if __name__ == "__main__":
    raise SystemExit(main())
