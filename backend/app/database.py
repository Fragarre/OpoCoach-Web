from __future__ import annotations

import os
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = BASE_DIR / "data" / "oposiciones.sqlite3"
DEFAULT_USER_DB_PATH = BASE_DIR / "data" / "usuario_pruebas.sqlite3"


def obtener_db_path() -> Path:
    valor = os.getenv("OPOCOACH_DB_PATH", "").strip()
    return Path(valor) if valor else DEFAULT_DB_PATH


def obtener_user_db_path() -> Path:
    valor = os.getenv("OPOCOACH_USER_DB_PATH", "").strip()
    return Path(valor) if valor else DEFAULT_USER_DB_PATH


def conectar_contenidos() -> sqlite3.Connection:
    """Abre la base maestra de contenidos en modo estrictamente lectura."""
    db_path = obtener_db_path().resolve()
    if not db_path.exists():
        raise FileNotFoundError(f"No existe la base de contenidos: {db_path}")

    uri = f"file:{db_path.as_posix()}?mode=ro"
    con = sqlite3.connect(uri, uri=True, check_same_thread=False)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    con.execute("PRAGMA query_only = ON")
    return con


def conectar_usuario_pruebas() -> sqlite3.Connection:
    """Base temporal de pruebas para validar persistencia durante la migración."""
    db_path = obtener_user_db_path().resolve()
    if not db_path.exists():
        raise FileNotFoundError(f"No existe la base de usuario de pruebas: {db_path}")
    con = sqlite3.connect(db_path, check_same_thread=False)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con
