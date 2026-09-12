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


class _DogvParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[str] = []
        self.forms: list[dict[str, str]] = []
        self.scripts: list[str] = []

    def handle_starttag(self, tag, attrs):
        datos = dict(attrs)
        if tag == "a" and datos.get("href"):
            self.links.append(datos["href"])
        elif tag == "form":
            self.forms.append({
                "action": datos.get("action", ""),
                "method": datos.get("method", "get"),
            })
        elif tag == "script" and datos.get("src"):
            self.scripts.append(datos["src"])


def _diagnostico_dogv() -> None:
    objetivos = [
        "https://dogv.gva.es/",
        "https://dogv.gva.es/datos/2026/09/11/PortalCAS.html",
    ]
    resultado: dict = {"marca": "DIAGNOSTICO_ESTRUCTURA_DOGV", "paginas": []}
    for url in objetivos:
        entrada: dict = {"url": url}
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "Mozilla/5.0 NetReto-Diagnostico/1.0"},
            )
            with urllib.request.urlopen(req, timeout=12) as r:
                html = r.read(300000).decode("utf-8", errors="replace")
                entrada["status"] = r.status
                entrada["final_url"] = r.geturl()
                entrada["bytes"] = len(html.encode("utf-8"))
                parser = _DogvParser()
                parser.feed(html)
                entrada["forms"] = parser.forms[:20]
                entrada["links_interes"] = [
                    urllib.parse.urljoin(r.geturl(), x)
                    for x in parser.links
                    if any(k in x.lower() for k in (
                        "busc", "search", "consulta", "datos/", "pdf/", "xml", "rss", "json", "portal"
                    ))
                ][:80]
                entrada["scripts"] = [urllib.parse.urljoin(r.geturl(), x) for x in parser.scripts][:40]
                patrones = sorted(set(re.findall(
                    r'https?://[^\"\'<> ]+|/[A-Za-z0-9_./?=&%-]*(?:busc|search|consulta|rss|xml|json)[A-Za-z0-9_./?=&%-]*',
                    html,
                    flags=re.I,
                )))
                entrada["patrones_interes"] = patrones[:80]
        except Exception as exc:
            entrada["error"] = f"{type(exc).__name__}: {exc}"
        resultado["paginas"].append(entrada)
    logging.error(json.dumps(resultado, ensure_ascii=False))


threading.Thread(target=_diagnostico_dogv, daemon=True).start()


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
