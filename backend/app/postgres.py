from __future__ import annotations

import json
import logging
import os
import threading
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


def _diagnostico_temporal_datos_abiertos_gva() -> None:
    """Diagnóstico temporal y de solo lectura del catálogo CKAN de GVA."""
    base = "https://dadesobertes.gva.es/es/api/3/action/package_search"
    consultas = [
        "oposiciones",
        "procesos selectivos",
        "empleo publico",
        "funcion publica",
        "seleccion personal",
        "ocupacio publica",
        "id_emp",
    ]
    salida: dict[str, object] = {
        "marca": "DIAGNOSTICO_CKAN_GVA_FRANKFURT",
        "consultas": [],
    }
    for consulta in consultas:
        url = f"{base}?rows=10&q={urllib.parse.quote_plus(consulta)}"
        entrada: dict[str, object] = {"q": consulta, "url": url}
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "NetReto-Empleo/0.1 (diagnostico)"},
            )
            with urllib.request.urlopen(req, timeout=12) as respuesta:
                datos = json.loads(respuesta.read().decode("utf-8", errors="replace"))
            resultado = datos.get("result") or {}
            paquetes = resultado.get("results") or []
            entrada["ok"] = bool(datos.get("success"))
            entrada["count"] = resultado.get("count")
            entrada["resultados"] = [
                {
                    "name": p.get("name"),
                    "title": p.get("title"),
                    "notes": str(p.get("notes") or "")[:220],
                    "tags": [t.get("name") for t in (p.get("tags") or [])[:8]],
                    "resources": [
                        {
                            "name": r.get("name"),
                            "format": r.get("format"),
                            "url": r.get("url"),
                            "datastore_active": r.get("datastore_active"),
                        }
                        for r in (p.get("resources") or [])[:5]
                    ],
                }
                for p in paquetes[:10]
            ]
        except Exception as exc:
            entrada["ok"] = False
            entrada["error"] = f"{type(exc).__name__}: {exc}"
        salida["consultas"].append(entrada)
    logging.getLogger("uvicorn.error").error(json.dumps(salida, ensure_ascii=False))


_diagnostico_temporal_datos_abiertos_gva()


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
