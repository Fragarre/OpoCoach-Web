from __future__ import annotations

import os
import threading
from contextlib import contextmanager
from typing import Iterator

import psycopg
from dotenv import load_dotenv
from psycopg_pool import ConnectionPool

load_dotenv()

_pool: ConnectionPool | None = None
_pool_lock = threading.Lock()


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


# Diagnóstico temporal y aislado: compara la conectividad de Frankfurt con GVA.
# No modifica BD ni comportamiento de la API; solo escribe una línea en logs.
def _diagnostico_temporal_gva() -> None:
    import json
    import socket
    import ssl
    import urllib.request

    host = "sede.gva.es"
    resultado: dict[str, object] = {
        "marca": "DIAGNOSTICO_GVA_FRANKFURT",
        "host": host,
    }

    try:
        info = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
        resultado["dns"] = sorted({item[4][0] for item in info})
    except Exception as exc:
        resultado["dns_error"] = f"{type(exc).__name__}: {exc}"

    try:
        with socket.create_connection((host, 443), timeout=8.0) as sock:
            resultado["tcp_443"] = "ok"
            contexto = ssl.create_default_context()
            with contexto.wrap_socket(sock, server_hostname=host) as tls:
                resultado["tls"] = {
                    "ok": True,
                    "version": tls.version(),
                    "cipher": tls.cipher()[0] if tls.cipher() else None,
                }
    except Exception as exc:
        resultado["tcp_tls_error"] = f"{type(exc).__name__}: {exc}"

    try:
        req = urllib.request.Request(
            "https://sede.gva.es/es/cercador-ocupacio-publica?tipoOrganismo=1",
            headers={
                "User-Agent": "NetReto-Empleo/0.1 (https://netexamenes.com)",
                "Accept-Language": "es-ES,es;q=0.9",
            },
        )
        with urllib.request.urlopen(req, timeout=12.0) as respuesta:
            muestra = respuesta.read(256)
            resultado["http"] = {
                "ok": True,
                "status": getattr(respuesta, "status", None),
                "url_final": respuesta.geturl(),
                "bytes_muestra": len(muestra),
            }
    except Exception as exc:
        resultado["http_error"] = f"{type(exc).__name__}: {exc}"

    print(json.dumps(resultado, ensure_ascii=False), flush=True)


threading.Thread(target=_diagnostico_temporal_gva, daemon=True).start()
