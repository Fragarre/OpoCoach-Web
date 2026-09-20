from __future__ import annotations

import json
import os

from app.simulacros import _condicion_fuente, _normalizar_fuentes
from app.tests_opocoach import (
    _cargar_datos_creacion_test,
    obtener_normas_test,
    obtener_puntos_temario_test,
)


def _canon(valor) -> str:
    return json.dumps(
        valor,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )


def _canon_lista(filas: list[dict]) -> list[str]:
    return sorted(_canon(dict(fila)) for fila in filas)


def _ejecutar_listados(
    origen: str,
    convocatoria_id: int,
    fuentes: list[str] | None,
):
    os.environ["OPOCOACH_CONTENT_SOURCE"] = origen
    return (
        obtener_puntos_temario_test(convocatoria_id, fuentes),
        obtener_normas_test(convocatoria_id, fuentes),
    )


def _ejecutar_candidatas(
    origen: str,
    convocatoria_id: int,
    modo: str,
    seleccion,
    fuentes: list[str] | None,
):
    os.environ["OPOCOACH_CONTENT_SOURCE"] = origen
    condicion = _condicion_fuente(_normalizar_fuentes(fuentes))

    if modo == "TEMA":
        return _cargar_datos_creacion_test(
            convocatoria_id=convocatoria_id,
            temas_ids=[int(seleccion)],
            normas_claves=[],
            modo="TEMA",
            condicion=condicion,
        )

    return _cargar_datos_creacion_test(
        convocatoria_id=convocatoria_id,
        temas_ids=[],
        normas_claves=[str(seleccion)],
        modo="NORMA",
        condicion=condicion,
    )


def main() -> int:
    original = os.environ.get("OPOCOACH_CONTENT_SOURCE")
    combinaciones_fuentes = (
        None,
        ["REAL"],
        ["IA"],
        ["REAL", "IA"],
    )

    try:
        print("=" * 78)
        print("PRUEBA TESTS OPOCOACH SQLITE ↔ POSTGRES")
        print("=" * 78)

        for convocatoria_id in (1, 2):
            for fuentes in combinaciones_fuentes:
                etiqueta = "REAL+IA" if fuentes is None else "+".join(fuentes)

                temas_sqlite, normas_sqlite = _ejecutar_listados(
                    "sqlite", convocatoria_id, fuentes
                )
                temas_pg, normas_pg = _ejecutar_listados(
                    "postgres", convocatoria_id, fuentes
                )

                if _canon_lista(temas_sqlite) != _canon_lista(temas_pg):
                    raise RuntimeError(
                        f"Temas distintos: convocatoria={convocatoria_id}, "
                        f"fuentes={etiqueta}"
                    )

                if _canon_lista(normas_sqlite) != _canon_lista(normas_pg):
                    raise RuntimeError(
                        f"Normas distintas: convocatoria={convocatoria_id}, "
                        f"fuentes={etiqueta}"
                    )

                print(
                    f"Conv {convocatoria_id} | {etiqueta:<7} | "
                    f"temas={len(temas_sqlite):>2} | "
                    f"normas={len(normas_sqlite):>3} ........ OK"
                )

            # Comparamos además las consultas que utiliza crear_test para
            # construir el conjunto de candidatas, sin escribir ningún test.
            temas, normas = _ejecutar_listados(
                "sqlite", convocatoria_id, ["REAL", "IA"]
            )

            if temas:
                tema_id = int(temas[0]["id"])
                s = _ejecutar_candidatas(
                    "sqlite", convocatoria_id, "TEMA", tema_id, ["REAL", "IA"]
                )
                p = _ejecutar_candidatas(
                    "postgres", convocatoria_id, "TEMA", tema_id, ["REAL", "IA"]
                )
                if _canon(s[0]) != _canon(p[0]):
                    raise RuntimeError(
                        f"Convocatoria distinta en selección por tema {tema_id}"
                    )
                if _canon_lista(s[1]) != _canon_lista(p[1]):
                    raise RuntimeError(
                        f"Elementos distintos en selección por tema {tema_id}"
                    )
                if _canon_lista(s[2]) != _canon_lista(p[2]):
                    raise RuntimeError(
                        f"Candidatas distintas en selección por tema {tema_id}"
                    )
                if s[3] != p[3]:
                    raise RuntimeError(
                        f"Claves distintas en selección por tema {tema_id}"
                    )
                print(
                    f"Conv {convocatoria_id} | selección TEMA "
                    f"{tema_id} | candidatas={len(s[2])} ........ OK"
                )

            if normas:
                norma = str(normas[0]["norma_clave"])
                s = _ejecutar_candidatas(
                    "sqlite", convocatoria_id, "NORMA", norma, ["REAL", "IA"]
                )
                p = _ejecutar_candidatas(
                    "postgres", convocatoria_id, "NORMA", norma, ["REAL", "IA"]
                )
                if _canon(s[0]) != _canon(p[0]):
                    raise RuntimeError(
                        f"Convocatoria distinta en selección por norma {norma}"
                    )
                if _canon_lista(s[1]) != _canon_lista(p[1]):
                    raise RuntimeError(
                        f"Elementos distintos en selección por norma {norma}"
                    )
                if _canon_lista(s[2]) != _canon_lista(p[2]):
                    raise RuntimeError(
                        f"Candidatas distintas en selección por norma {norma}"
                    )
                if s[3] != p[3]:
                    raise RuntimeError(
                        f"Claves distintas en selección por norma {norma}"
                    )
                print(
                    f"Conv {convocatoria_id} | selección NORMA "
                    f"{norma} | candidatas={len(s[2])} ........ OK"
                )

        print()
        print("=" * 78)
        print("RESULTADO FINAL: CORRECTO")
        print("=" * 78)
        print("Los listados de temas/normas y las consultas de candidatas")
        print("devuelven contenido equivalente en SQLite y PostgreSQL/Supabase.")
        print("No se ha creado ningún test ni se ha modificado ningún dato.")
        return 0

    except Exception as exc:
        print()
        print("RESULTADO FINAL: ERROR")
        print(exc)
        return 1

    finally:
        if original is None:
            os.environ.pop("OPOCOACH_CONTENT_SOURCE", None)
        else:
            os.environ["OPOCOACH_CONTENT_SOURCE"] = original


if __name__ == "__main__":
    raise SystemExit(main())
