from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from app.database import conectar_contenidos_postgres


BACKEND_DIR = Path(__file__).resolve().parent.parent
RESUMENES_DIR = BACKEND_DIR / "materiales" / "resumenes"


def _clave_articulo(valor: str | None) -> tuple:
    texto = str(valor or "").strip()
    m = re.match(r"^\s*(\d+)\s*(.*)$", texto, flags=re.IGNORECASE)
    if not m:
        return (1, 10**9, texto.casefold())
    return (0, int(m.group(1)), m.group(2).strip().casefold())


def _fuente_principal_desde_temario(
    cur,
    convocatoria_id: int,
    norma_id: int,
) -> dict[str, Any] | None:
    """
    Resuelve la fuente del corpus sin depender de norma_fuentes, tabla que no
    forma parte del conjunto publicable actual de Supabase.

    1. Localiza las fuentes id_boe realmente enlazadas desde el temario.
    2. Cuenta cuántos artículos/bloques existen en articulos_fuente para cada
       fuente.
    3. Elige la fuente con mayor corpus disponible.
    """
    cur.execute(
        """
        WITH fuentes_temario AS (
            SELECT DISTINCT af.id_boe
            FROM contenidos.temarios t
            JOIN contenidos.temario_temas tt
                ON tt.temario_id = t.id
            JOIN contenidos.temario_referencias tr
                ON tr.tema_id = tt.id
            JOIN contenidos.articulos_fuente af
                ON af.id = tr.articulo_fuente_id
            WHERE t.convocatoria_id = %s
              AND tr.norma_id = %s
              AND af.id_boe IS NOT NULL
        ),
        recuento AS (
            SELECT
                ft.id_boe,
                COUNT(af.id) AS articulos_corpus
            FROM fuentes_temario ft
            JOIN contenidos.articulos_fuente af
                ON af.id_boe = ft.id_boe
            GROUP BY ft.id_boe
        )
        SELECT id_boe AS id_fuente, articulos_corpus
        FROM recuento
        ORDER BY articulos_corpus DESC, id_boe
        LIMIT 1
        """,
        (convocatoria_id, norma_id),
    )
    fila = cur.fetchone()
    return dict(fila) if fila else None


def obtener_convocatoria_materiales(
    convocatoria_id: int,
) -> dict[str, Any] | None:
    with conectar_contenidos_postgres() as con:
        with con.cursor() as cur:
            cur.execute(
                """
                SELECT id, codigo, puesto, activa
                FROM contenidos.convocatorias
                WHERE id = %s
                """,
                (convocatoria_id,),
            )
            fila = cur.fetchone()
    return dict(fila) if fila else None


def listar_normas_materiales(
    convocatoria_id: int,
) -> list[dict[str, Any]]:
    with conectar_contenidos_postgres() as con:
        with con.cursor() as cur:
            cur.execute(
                """
                SELECT
                    n.id AS norma_id,
                    n.nombre_canonico
                FROM contenidos.temarios t
                JOIN contenidos.temario_temas tt
                    ON tt.temario_id = t.id
                JOIN contenidos.temario_referencias tr
                    ON tr.tema_id = tt.id
                JOIN contenidos.normas n
                    ON n.id = tr.norma_id
                WHERE t.convocatoria_id = %s
                  AND tr.norma_id IS NOT NULL
                GROUP BY n.id, n.nombre_canonico
                ORDER BY UPPER(n.nombre_canonico), n.id
                """,
                (convocatoria_id,),
            )
            filas = [dict(f) for f in cur.fetchall()]

            salida: list[dict[str, Any]] = []
            for item in filas:
                fuente = _fuente_principal_desde_temario(
                    cur,
                    convocatoria_id,
                    int(item["norma_id"]),
                )
                if fuente is None:
                    continue
                item.update(fuente)
                salida.append(item)

    return salida


def _comprobar_norma_convocatoria(
    cur,
    convocatoria_id: int,
    norma_id: int,
) -> dict[str, Any]:
    cur.execute(
        """
        SELECT DISTINCT
            n.id AS norma_id,
            n.nombre_canonico
        FROM contenidos.temarios t
        JOIN contenidos.temario_temas tt
            ON tt.temario_id = t.id
        JOIN contenidos.temario_referencias tr
            ON tr.tema_id = tt.id
        JOIN contenidos.normas n
            ON n.id = tr.norma_id
        WHERE t.convocatoria_id = %s
          AND n.id = %s
        LIMIT 1
        """,
        (convocatoria_id, norma_id),
    )
    fila = cur.fetchone()
    if fila is None:
        raise ValueError(
            "La norma no pertenece al temario de esta convocatoria."
        )
    return dict(fila)


def obtener_articulos_extracto(
    convocatoria_id: int,
    norma_id: int,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    with conectar_contenidos_postgres() as con:
        with con.cursor() as cur:
            meta = _comprobar_norma_convocatoria(
                cur,
                convocatoria_id,
                norma_id,
            )

            cur.execute(
                """
                SELECT DISTINCT
                    af.id,
                    af.id_boe,
                    af.id_bloque,
                    af.articulo_boe,
                    af.titulo_bloque,
                    af.texto
                FROM contenidos.temarios t
                JOIN contenidos.temario_temas tt
                    ON tt.temario_id = t.id
                JOIN contenidos.temario_referencias tr
                    ON tr.tema_id = tt.id
                JOIN contenidos.articulos_fuente af
                    ON af.id = tr.articulo_fuente_id
                WHERE t.convocatoria_id = %s
                  AND tr.norma_id = %s
                  AND BTRIM(COALESCE(af.texto, '')) <> ''
                """,
                (convocatoria_id, norma_id),
            )
            articulos = [dict(f) for f in cur.fetchall()]

    articulos.sort(
        key=lambda x: (
            _clave_articulo(x.get("articulo_boe")),
            str(x.get("id_bloque") or "").casefold(),
            int(x["id"]),
        )
    )
    return meta, articulos


def obtener_articulos_texto_completo(
    convocatoria_id: int,
    norma_id: int,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    with conectar_contenidos_postgres() as con:
        with con.cursor() as cur:
            meta = _comprobar_norma_convocatoria(
                cur,
                convocatoria_id,
                norma_id,
            )

            fuente = _fuente_principal_desde_temario(
                cur,
                convocatoria_id,
                norma_id,
            )
            if fuente is None:
                raise ValueError(
                    "La norma no tiene texto disponible en el corpus."
                )

            cur.execute(
                """
                SELECT
                    id,
                    id_boe,
                    id_bloque,
                    articulo_boe,
                    titulo_bloque,
                    texto
                FROM contenidos.articulos_fuente
                WHERE id_boe = %s
                  AND BTRIM(COALESCE(texto, '')) <> ''
                """,
                (fuente["id_fuente"],),
            )
            articulos = [dict(f) for f in cur.fetchall()]

    articulos.sort(
        key=lambda x: (
            _clave_articulo(x.get("articulo_boe")),
            str(x.get("id_bloque") or "").casefold(),
            int(x["id"]),
        )
    )

    meta.update(fuente)
    return meta, articulos


def obtener_resumen_preparado(
    convocatoria_id: int,
    norma_id: int,
) -> tuple[str, bytes]:
    """
    El catálogo y los PDF son artefactos previamente validados.
    Antes de servirlos se comprueba en Supabase que la norma pertenece a la
    convocatoria solicitada.
    """
    with conectar_contenidos_postgres() as con:
        with con.cursor() as cur:
            _comprobar_norma_convocatoria(
                cur,
                convocatoria_id,
                norma_id,
            )

    catalogo_path = RESUMENES_DIR / "catalogo_resumenes.json"
    if not catalogo_path.is_file():
        raise RuntimeError(
            "No está instalado el catálogo de resúmenes de estudio."
        )

    import json

    datos = json.loads(catalogo_path.read_text(encoding="utf-8"))
    item = next(
        (
            x for x in datos
            if int(x.get("norma_id", -1)) == int(norma_id)
        ),
        None,
    )
    if item is None:
        raise ValueError(
            "No existe resumen preparado para la norma seleccionada."
        )

    nombre = str(item.get("archivo") or "").strip()
    if not nombre:
        raise RuntimeError(
            "El catálogo del resumen no contiene nombre de archivo."
        )

    ruta = RESUMENES_DIR / nombre
    if not ruta.is_file():
        raise RuntimeError(
            f"No se encuentra el resumen preparado: {nombre}"
        )

    return nombre, ruta.read_bytes()
