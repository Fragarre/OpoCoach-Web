from __future__ import annotations

from app.database import conectar_contenidos


def obtener_convocatorias() -> list[dict]:
    with conectar_contenidos() as con:
        filas = con.execute(
            """
            SELECT id, puesto, numero, anio, codigo
            FROM convocatorias
            ORDER BY anio DESC, numero, puesto
            """
        ).fetchall()
    return [dict(fila) for fila in filas]


def obtener_resumen_convocatoria(convocatoria_id: int) -> dict | None:
    with conectar_contenidos() as con:
        fila = con.execute(
            """
            SELECT
                c.id,
                c.codigo,
                c.puesto,
                c.numero,
                c.anio,
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
            """,
            (convocatoria_id,),
        ).fetchone()
    return dict(fila) if fila is not None else None


def comprobar_base() -> dict:
    with conectar_contenidos() as con:
        integridad = con.execute("PRAGMA integrity_check").fetchone()[0]
        total_convocatorias = con.execute("SELECT COUNT(*) FROM convocatorias").fetchone()[0]
        total_preguntas = con.execute("SELECT COUNT(*) FROM lote_preguntas").fetchone()[0]
    return {
        "integridad": integridad,
        "convocatorias": total_convocatorias,
        "preguntas": total_preguntas,
    }
