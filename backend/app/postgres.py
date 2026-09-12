from __future__ import annotations

import json
import logging
import os
import threading
import urllib.error
import urllib.parse
import urllib.request
from contextlib import contextmanager
from typing import Iterator

import psycopg
from dotenv import load_dotenv
from psycopg_pool import ConnectionPool

load_dotenv()

_pool: ConnectionPool | None = None
_pool_lock = threading.Lock()


def _json_get(url: str):
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 NetReto-Diagnostico/1.0",
        "Accept": "application/json, text/plain, */*",
    })
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return {"ok": True, "status": r.status, "data": json.loads(r.read(1200000).decode("utf-8", errors="replace"))}
    except urllib.error.HTTPError as exc:
        try:
            detalle = exc.read(4000).decode("utf-8", errors="replace")
        except Exception:
            detalle = ""
        return {"ok": False, "status": exc.code, "error": str(exc), "detalle": detalle}
    except Exception as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}


def _compactar(d: dict) -> dict:
    claves = (
        "id", "codigoInsercion", "cve", "titulo", "organismo", "numeroDogv",
        "fechaPublicacion", "fechaPublicacionSumario", "fechaDisposicion",
        "tipoDocumento", "seccion", "estado", "urlPdf", "texto"
    )
    out = {k: d.get(k) for k in claves if k in d}
    if isinstance(out.get("texto"), str):
        out["texto"] = out["texto"][:1200]
    return out


def _diagnostico_identidad_dogv() -> None:
    base = "https://dogv.gva.es/dogv-portal"
    out: dict = {"marca": "DIAGNOSTICO_IDENTIDAD_DOGV"}
    fecha = _json_get(f"{base}/dogv?date=2026-07-08&lang=es_es")
    if not fecha.get("ok"):
        out["fecha_error"] = fecha
        logging.error(json.dumps(out, ensure_ascii=False))
        return

    disposiciones = fecha["data"].get("disposiciones", [])
    candidatos = []
    for d in disposiciones:
        texto = " ".join(str(d.get(k) or "") for k in ("titulo", "organismo", "codigoInsercion"))
        bajo = texto.lower()
        if "a1-01" in bajo or "administración" in bajo and "pruebas selectivas" in bajo:
            candidatos.append(_compactar(d))
    out["dogv_2026_07_08_total"] = len(disposiciones)
    out["candidatos"] = candidatos

    detalles = []
    for c in candidatos:
        ident = c.get("id")
        if not ident:
            continue
        r = _json_get(f"{base}/disposicion/{ident}?lang=es_es")
        if r.get("ok") and isinstance(r.get("data"), dict):
            detalles.append({"id": ident, "detalle": _compactar(r["data"]), "claves": list(r["data"].keys())[:80]})
        else:
            detalles.append({"id": ident, "error": r})
    out["detalles"] = detalles

    logging.error(json.dumps(out, ensure_ascii=False))


threading.Thread(target=_diagnostico_identidad_dogv, daemon=True).start()


def obtener_database_url() -> str:
    url = os.getenv("DATABASE_URL", "").strip()
    if not url:
        raise RuntimeError(
            "DATABASE_URL no está configurada. Copia backend/.env.example a "
            "backend/.env y completa la cadena de conexión de Supabase."
        )
    # Supabase puede mostrar postgres://; psycopg acepta ambos, pero normalizamos.
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    return url


def _obtener_pool() -> ConnectionPool:
    global _pool

    if _pool is None:
        with _pool_lock:
            if _pool is None:
                _pool = ConnectionPool(
                    conninfo=obtener_database_url(),
                    min_size=2,
                    max_size=10,
                    timeout=10.0,
                    kwargs={"connect_timeout": 10},
                    open=True,
                    name="opocoach-postgres",
                )

    return _pool


@contextmanager
def conectar_postgres() -> Iterator[psycopg.Connection]:
    with _obtener_pool().connection() as con:
        yield con


def cerrar_pool_postgres() -> None:
    global _pool

    with _pool_lock:
        if _pool is not None:
            _pool.close()
            _pool = None


def comprobar_postgres() -> dict[str, str]:
    with conectar_postgres() as con:
        with con.cursor() as cur:
            cur.execute("SELECT current_database(), current_setting('server_version')")
            database, version = cur.fetchone()
    return {
        "estado": "ok",
        "database": str(database),
        "postgres_version": str(version),
    }
