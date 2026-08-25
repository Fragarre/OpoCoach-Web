from __future__ import annotations

import json
from pathlib import Path

from app.database import conectar_contenidos_postgres


BACKEND_DIR = Path(__file__).resolve().parents[1]
CATALOGO = (
    BACKEND_DIR
    / "materiales"
    / "resumenes"
    / "catalogo_resumenes.json"
)


def main() -> int:
    if not CATALOGO.is_file():
        raise RuntimeError(f"No existe el catálogo: {CATALOGO}")

    catalogo = json.loads(CATALOGO.read_text(encoding="utf-8"))
    ids = sorted({int(x["norma_id"]) for x in catalogo})

    with conectar_contenidos_postgres() as con:
        with con.cursor() as cur:
            cur.execute(
                """
                SELECT id, nombre_canonico
                FROM contenidos.normas
                WHERE id = ANY(%s)
                ORDER BY id
                """,
                (ids,),
            )
            presentes = {int(x["id"]): str(x["nombre_canonico"]) for x in cur.fetchall()}

            cur.execute(
                """
                SELECT DISTINCT tr.norma_id
                FROM contenidos.temarios t
                JOIN contenidos.convocatorias c
                    ON c.id = t.convocatoria_id
                JOIN contenidos.temario_temas tt
                    ON tt.temario_id = t.id
                JOIN contenidos.temario_referencias tr
                    ON tr.tema_id = tt.id
                WHERE c.activa = TRUE
                  AND tr.norma_id IS NOT NULL
                """
            )
            activas = {int(x["norma_id"]) for x in cur.fetchall()}

    faltantes_supabase = [x for x in ids if x not in presentes]
    faltantes_catalogo = sorted(activas - set(ids))

    print("=" * 78)
    print("VERIFICACIÓN MATERIALES DE ESTUDIO / SUPABASE")
    print("=" * 78)
    print(f"Resúmenes en catálogo:                 {len(ids)}")
    print(f"Normas del catálogo presentes Supabase:{len(ids) - len(faltantes_supabase)}")
    print(f"Normas activas sin resumen:            {len(faltantes_catalogo)}")

    if faltantes_supabase:
        print("\nFALTAN EN SUPABASE:")
        for norma_id in faltantes_supabase:
            print(f"  {norma_id}")

    if faltantes_catalogo:
        print("\nACTIVAS SIN RESUMEN:")
        for norma_id in faltantes_catalogo:
            print(f"  {norma_id}")

    if faltantes_supabase or faltantes_catalogo:
        print("\nRESULTADO: REVISAR")
        return 1

    print("\nRESULTADO: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
