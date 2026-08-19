from __future__ import annotations

import os

from app.simulacros import (
    _cargar_bloques_modelo_parte,
    _conectar_contenidos_dual,
    _tabla_modelo_examen_existe,
    obtener_disponibilidad,
)


def canon(filas):
    return sorted(
        [tuple(sorted(dict(f).items())) for f in filas],
        key=repr,
    )


def leer(origen: str) -> dict:
    os.environ["OPOCOACH_CONTENT_SOURCE"] = origen

    with _conectar_contenidos_dual() as con:
        convocatorias = [
            dict(f)
            for f in con.execute(
                """
                SELECT id, codigo, puesto, numero, anio, numero_preguntas
                FROM convocatorias
                ORDER BY id
                """
            ).fetchall()
        ]
        existe_modelo = _tabla_modelo_examen_existe(con)

        partes = {}
        bloques = {}
        for convocatoria in convocatorias:
            cid = int(convocatoria["id"])
            filas_partes = [
                dict(f)
                for f in con.execute(
                    """
                    SELECT id, nombre, numero_preguntas, orden
                    FROM convocatoria_partes
                    WHERE convocatoria_id = ?
                    ORDER BY orden
                    """,
                    (cid,),
                ).fetchall()
            ]
            partes[cid] = filas_partes
            for parte in filas_partes:
                pid = int(parte["id"])
                bloques[pid] = [
                    dict(f) for f in _cargar_bloques_modelo_parte(con, pid)
                ]

    disponibilidad = {}
    for convocatoria in convocatorias:
        cid = int(convocatoria["id"])
        for fuentes in (["REAL", "IA"], ["REAL"], ["IA"]):
            clave = (cid, tuple(fuentes))
            disponibilidad[clave] = obtener_disponibilidad(
                cid, ["A1", "A2", "C1", "C2"], fuentes
            )

    return {
        "convocatorias": convocatorias,
        "existe_modelo": existe_modelo,
        "partes": partes,
        "bloques": bloques,
        "disponibilidad": disponibilidad,
    }


def main() -> int:
    original = os.environ.get("OPOCOACH_CONTENT_SOURCE")
    try:
        print("=" * 78)
        print("PRUEBA SIMULACROS: CONTENIDOS SQLITE ↔ POSTGRES")
        print("=" * 78)
        print("Modo: SOLO LECTURA. No se crea ningún simulacro.")
        print()

        sqlite = leer("sqlite")
        postgres = leer("postgres")

        errores = []

        if sqlite["convocatorias"] != postgres["convocatorias"]:
            errores.append("Convocatorias distintas.")
        else:
            print("Convocatorias.................................... OK")

        if sqlite["existe_modelo"] != postgres["existe_modelo"]:
            errores.append("Detección de convocatoria_modelo_bloques distinta.")
        else:
            print("Detección tabla modelo........................... OK")

        if sqlite["partes"] != postgres["partes"]:
            errores.append("Partes de convocatoria distintas.")
        else:
            print("Partes de convocatoria.......................... OK")

        for pid in sorted(sqlite["bloques"]):
            if canon(sqlite["bloques"][pid]) != canon(postgres["bloques"].get(pid, [])):
                errores.append(f"Bloques de modelo distintos para parte {pid}.")
        if not any(e.startswith("Bloques") for e in errores):
            print("Bloques de modelo............................... OK")

        for clave, valor_sqlite in sqlite["disponibilidad"].items():
            valor_pg = postgres["disponibilidad"].get(clave)
            if canon(valor_sqlite) != canon(valor_pg or []):
                errores.append(
                    f"Disponibilidad distinta: convocatoria={clave[0]}, fuentes={clave[1]}."
                )
        if not any(e.startswith("Disponibilidad") for e in errores):
            print("Disponibilidad REAL/IA........................... OK")

        if errores:
            print("\nRESULTADO FINAL: ERROR")
            for error in errores:
                print(f"- {error}")
            return 1

        print("\n" + "=" * 78)
        print("RESULTADO FINAL: CORRECTO")
        print("=" * 78)
        print("Las lecturas de contenidos usadas por simulacros son equivalentes")
        print("con SQLite y PostgreSQL/Supabase.")
        print("No se ha creado, modificado ni eliminado ningún simulacro.")
        return 0
    finally:
        if original is None:
            os.environ.pop("OPOCOACH_CONTENT_SOURCE", None)
        else:
            os.environ["OPOCOACH_CONTENT_SOURCE"] = original


if __name__ == "__main__":
    raise SystemExit(main())
