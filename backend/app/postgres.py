from __future__ import annotations

import json
import logging
import os
import re
import threading
import urllib.parse
import urllib.request
from contextlib import contextmanager
from html.parser import HTMLParser
from typing import Iterator

import psycopg
from dotenv import load_dotenv
from psycopg_pool import ConnectionPool

load_dotenv()

_pool: ConnectionPool | None = None
_pool_lock = threading.Lock()


class _Parser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[str] = []
        self.scripts: list[str] = []
    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        if tag == "a" and d.get("href"):
            self.links.append(d["href"])
        if tag == "script" and d.get("src"):
            self.scripts.append(d["src"])


def _leer(url: str, limite: int = 500000) -> tuple[str, str, int]:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 NetReto-Diagnostico/1.0"})
    with urllib.request.urlopen(req, timeout=15) as r:
        return r.read(limite).decode("utf-8", errors="replace"), r.geturl(), r.status


def _diagnostico_dogv_frontend() -> None:
    resultado: dict = {"marca": "DIAGNOSTICO_FRONTEND_DOGV", "paginas": [], "scripts": []}
    for url in [
        "https://dogv.gva.es/dogv-portal-frontend/va",
        "https://dogv.gva.es/va/portal",
        "https://dogv.gva.es/es/portal",
    ]:
        e: dict = {"url": url}
        try:
            html, final, status = _leer(url)
            e.update({"status": status, "final_url": final, "chars": len(html)})
            p = _Parser(); p.feed(html)
            e["links"] = [urllib.parse.urljoin(final, x) for x in p.links][:100]
            e["scripts"] = [urllib.parse.urljoin(final, x) for x in p.scripts][:100]
            e["fragmentos_api"] = sorted(set(re.findall(
                r'[^\"\'\s<>]{0,100}(?:api|buscar|buscador|search|consulta|sumario|documento|diario|dogv)[^\"\'\s<>]{0,120}',
                html, flags=re.I
            )))[:120]
            for src in e["scripts"][:30]:
                if src in [x.get("url") for x in resultado["scripts"]]:
                    continue
                se = {"url": src}
                try:
                    js, jsfinal, jsstatus = _leer(src, 800000)
                    se.update({"status": jsstatus, "final_url": jsfinal, "chars": len(js)})
                    se["fragmentos"] = sorted(set(re.findall(
                        r'[^\"\'\s<>]{0,120}(?:/api/|api/|search|buscar|consulta|sumario|documento|dogv)[^\"\'\s<>]{0,160}',
                        js, flags=re.I
                    )))[:160]
                except Exception as exc:
                    se["error"] = f"{type(exc).__name__}: {exc}"
                resultado["scripts"].append(se)
        except Exception as exc:
            e["error"] = f"{type(exc).__name__}: {exc}"
        resultado["paginas"].append(e)
    logging.error(json.dumps(resultado, ensure_ascii=False))

threading.Thread(target=_diagnostico_dogv_frontend, daemon=True).start()


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
