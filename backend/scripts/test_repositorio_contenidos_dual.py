from __future__ import annotations

import os

from app.repositorio_contenidos import (
    comprobar_base,
    obtener_convocatorias,
    obtener_resumen_convocatoria,
)


def ejecutar(origen: str) -> dict:
    os.environ["OPOCOACH_CONTENT_SOURCE"] = origen

    convocatorias = obtener_convocatorias()
    resumenes = [
        obtener_resumen_convocatoria(int(convocatoria["id"]))
        for convocatoria in convocatorias
    ]
    estado = comprobar_base()

    return {
        "convocatorias": convocatorias,
        "resumenes": resumenes,
        "estado": estado,
    }


def main() -> int:
    original = os.environ.get("OPOCOACH_CONTENT_SOURCE")

    try:
        sqlite = ejecutar("sqlite")
        postgres = ejecutar("postgres")

        print("=" * 78)
        print("PRUEBA REPOSITORIO DE CONTENIDOS SQLITE ↔ POSTGRES")
        print("=" * 78)

        errores = []

        if sqlite["convocatorias"] != postgres["convocatorias"]:
            errores.append("Listado de convocatorias distinto.")
        else:
            print("Listado de convocatorias........................ OK")

        if sqlite["resumenes"] != postgres["resumenes"]:
            errores.append("Resúmenes de convocatorias distintos.")
        else:
            print("Resúmenes de convocatorias..................... OK")

        if (
            sqlite["estado"]["convocatorias"]
            != postgres["estado"]["convocatorias"]
        ):
            errores.append("Total de convocatorias distinto.")
        else:
            print("Total de convocatorias.......................... OK")

        if sqlite["estado"]["preguntas"] != postgres["estado"]["preguntas"]:
            errores.append("Total de preguntas distinto.")
        else:
            print("Total de preguntas.............................. OK")

        if sqlite["estado"]["integridad"] != "ok":
            errores.append(
                f"SQLite integrity_check: {sqlite['estado']['integridad']!r}"
            )
        else:
            print("SQLite integrity_check.......................... OK")

        if postgres["estado"]["integridad"] != "ok":
            errores.append(
                f"Estado PostgreSQL: {postgres['estado']['integridad']!r}"
            )
        else:
            print("Consulta esencial PostgreSQL.................... OK")

        if errores:
            print()
            print("RESULTADO FINAL: ERROR")
            for error in errores:
                print(f"- {error}")
            return 1

        print()
        print("=" * 78)
        print("RESULTADO FINAL: CORRECTO")
        print("=" * 78)
        print("repositorio_contenidos.py devuelve datos equivalentes")
        print("con OPOCOACH_CONTENT_SOURCE=sqlite y postgres.")
        print("No se ha modificado ningún dato.")
        return 0

    finally:
        if original is None:
            os.environ.pop("OPOCOACH_CONTENT_SOURCE", None)
        else:
            os.environ["OPOCOACH_CONTENT_SOURCE"] = original


if __name__ == "__main__":
    raise SystemExit(main())
