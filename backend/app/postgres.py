from __future__ import annotations

import json
import logging
import os
import re
import threading
import urllib.request
from contextlib import contextmanager
from typing import Iterator

import psycopg
from dotenv import load_dotenv
from psycopg_pool import ConnectionPool

load_dotenv()

_pool: ConnectionPool | None = None
_pool_lock = threading.Lock()


def _diagnostico_endpoints_dogv() -> None:
    url = "https://dogv.gva.es/dogv-portal-frontend/main.4430d940a79e5c6fddac.js"
    resultado: dict = {"marca": "DIAGNOSTICO_ENDPOINTS_DOGV", "url": url}
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 NetReto-Diagnostico/1.0"})
        with urllib.request.urlopen(req, timeout=15) as r:
            js = r.read(2000000).decode("utf-8", errors="replace")
        resultado["chars"] = len(js)
        urls = sorted(set(re.findall(r'https?://[^\"\'`\\\s<>]+', js)))
        resultado["urls"] = [u for u in urls if any(k in u.lower() for k in ("dogv", "gva", "api", "document", "diari", "busc", "search"))][:200]
        rutas = sorted(set(re.findall(r'[\"\'`](/[^\"\'`]{2,180})[\"\'`]', js)))
        resultado["rutas"] = [p for p in rutas if any(k in p.lower() for k in ("api", "document", "diari", "sumari", "busc", "search", "portal"))][:250]
        claves = ["http", "api", "documento", "document", "diario", "diari", "sumario", "sumari", "buscar", "busc", "cve"]
        fragmentos = []
        bajo = js.lower()
        for clave in claves:
            inicio = 0
            n = 0
            while n < 30:
                pos = bajo.find(clave, inicio)
                if pos < 0:
                    break
                fragmentos.append(js[max(0, pos-180):min(len(js), pos+320)])
                inicio = pos + len(clave)
                n += 1
        resultado["fragmentos"] = fragmentos[:220]
    except Exception as exc:
        resultado["error"] = f"{type(exc).__name__}: {exc}"
    logging.error(json.dumps(resultado, ensure_ascii=False))

threading.Thread(target=_diagnostico_endpoints_dogv, daemon=True).start()


def obtener_database_url() -> str:
    url = os.getenv("DATABASE_URL", "").strip()
    if not url:
        raise RuntimeError(
            "DATABASE_URL no está configurada. Copia backend/.env.example a "
            "backend/.env y completa la cadena de conexión de Supabase."
        )
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    return url


def _obtener_pool() -> ConnectionPool:
    global _pool
    if _pool is None:
        with _pool_lock:
            if _pool is None:
                _pool = ConnectionPool(
                    conninfo=obtener_database_url(), min_size=2, max_size=10,
                    timeout=10.0, kwargs={"connect_timeout": 10}, open=True,
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
            _pool.close(); _pool = None

def comprobar_postgres() -> dict[str, str]:
    with conectar_postgres() as con:
        with con.cursor() as cur:
            cur.execute("SELECT current_database(), current_setting('server_version')")
            database, version = cur.fetchone()
    return {"estado": "ok", "database": str(database), "postgres_version": str(version)}
