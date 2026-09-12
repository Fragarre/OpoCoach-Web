from __future__ import annotations

import json
import os
import socket
import ssl
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


def _diagnostico_hosts_gva() -> None:
    objetivos = [
        ("sede", "https://sede.gva.es/"),
        ("datos_abiertos", "https://dadesobertes.gva.es/es/api/3/action/package_search?q=oposiciones"),
        ("dogv", "https://dogv.gva.es/"),
        ("hisenda", "https://hisenda.gva.es/"),
    ]
    resultado = {"marca": "DIAGNOSTICO_HOSTS_GVA_FRANKFURT", "objetivos": []}
    for nombre, url in objetivos:
        host = urllib.request.urlparse(url).hostname if hasattr(urllib.request, "urlparse") else None
        if host is None:
            from urllib.parse import urlparse
            host = urlparse(url).hostname
        item = {"nombre": nombre, "url": url, "host": host}
        try:
            info = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
            item["dns"] = sorted({x[4][0] for x in info})
        except Exception as exc:
            item["dns_error"] = f"{type(exc).__name__}: {exc}"
        try:
            raw = socket.create_connection((host, 443), timeout=8)
            try:
                ctx = ssl.create_default_context()
                tls = ctx.wrap_socket(raw, server_hostname=host)
                item["tcp_tls"] = "ok"
                tls.close()
            finally:
                try:
                    raw.close()
                except Exception:
                    pass
        except Exception as exc:
            item["tcp_tls_error"] = f"{type(exc).__name__}: {exc}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "NetReto-Empleo/0.1 (https://netexamenes.com)"})
            with urllib.request.urlopen(req, timeout=12) as resp:
                item["http"] = {"status": getattr(resp, "status", None), "final_url": resp.geturl(), "bytes_leidos": len(resp.read(2048))}
        except Exception as exc:
            item["http_error"] = f"{type(exc).__name__}: {exc}"
        resultado["objetivos"].append(item)
    print(json.dumps(resultado, ensure_ascii=False), flush=True)


try:
    _diagnostico_hosts_gva()
except Exception as exc:
    print(json.dumps({"marca": "DIAGNOSTICO_HOSTS_GVA_FRANKFURT", "error": f"{type(exc).__name__}: {exc}"}), flush=True)


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
