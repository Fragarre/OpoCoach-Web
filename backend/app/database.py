from __future__ import annotations

import os
import sqlite3
from pathlib import Path

import psycopg
from psycopg.rows import dict_row

from app.postgres import obtener_database_url


BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = BASE_DIR / "data" / "oposiciones.sqlite3"
DEFAULT_USER_DB_PATH = BASE_DIR / "data" / "usuario_pruebas.sqlite3"

ORIGEN_CONTENIDOS_SQLITE = "sqlite"
ORIGEN_CONTENIDOS_POSTGRES = "postgres"
ORIGENES_CONTENIDOS_VALIDOS = {
    ORIGEN_CONTENIDOS_SQLITE,
    ORIGEN_CONTENIDOS_POSTGRES,
}


def obtener_db_path() -> Path:
    valor = os.getenv("OPOCOACH_DB_PATH", "").strip()
    return Path(valor) if valor else DEFAULT_DB_PATH


def obtener_user_db_path() -> Path:
    valor = os.getenv("OPOCOACH_USER_DB_PATH", "").strip()
    return Path(valor) if valor else DEFAULT_USER_DB_PATH


def obtener_origen_contenidos() -> str:
    """
    Devuelve el origen configurado para los contenidos de OpoCoach-Web.

    Por seguridad, el valor predeterminado sigue siendo SQLite.
    """
    valor = (
        os.getenv("OPOCOACH_CONTENT_SOURCE", ORIGEN_CONTENIDOS_SQLITE)
        .strip()
        .lower()
    )

    if valor not in ORIGENES_CONTENIDOS_VALIDOS:
        permitidos = ", ".join(sorted(ORIGENES_CONTENIDOS_VALIDOS))
        raise RuntimeError(
            "OPOCOACH_CONTENT_SOURCE no es válido. "
            f"Valor recibido: {valor!r}. Valores permitidos: {permitidos}."
        )

    return valor


def conectar_contenidos_sqlite() -> sqlite3.Connection:
    """Abre la base local de contenidos SQLite en modo estrictamente lectura."""
    db_path = obtener_db_path().resolve()
    if not db_path.exists():
        raise FileNotFoundError(f"No existe la base de contenidos: {db_path}")

    uri = f"file:{db_path.as_posix()}?mode=ro"
    con = sqlite3.connect(uri, uri=True, check_same_thread=False)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    con.execute("PRAGMA query_only = ON")
    return con


def conectar_contenidos_postgres() -> psycopg.Connection:
    """
    Abre PostgreSQL/Supabase para consultas de contenidos.

    Esta función sólo crea la conexión. Los módulos que la utilicen deben
    consultar explícitamente el esquema `contenidos`.
    """
    return psycopg.connect(
        obtener_database_url(),
        row_factory=dict_row,
    )


def conectar_contenidos() -> sqlite3.Connection:
    """
    Conexión de contenidos usada actualmente por OpoCoach-Web.

    IMPORTANTE:
    Durante la migración esta función continúa apuntando deliberadamente
    a SQLite, aunque OPOCOACH_CONTENT_SOURCE esté configurado como postgres.

    Los módulos se migrarán y validarán uno a uno antes de cambiar este
    comportamiento.
    """
    return conectar_contenidos_sqlite()


def conectar_usuario_pruebas() -> sqlite3.Connection:
    """Base temporal de pruebas para validar persistencia durante la migración."""
    db_path = obtener_user_db_path().resolve()
    if not db_path.exists():
        raise FileNotFoundError(
            f"No existe la base de usuario de pruebas: {db_path}"
        )
    con = sqlite3.connect(db_path, check_same_thread=False)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con
