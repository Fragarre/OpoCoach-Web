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
