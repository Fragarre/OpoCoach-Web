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


def _resumir_json(data):
    if isinstance(data, dict):
        resumen = {"tipo": "dict", "claves": list(data.keys())[:40]}
        for clave in ("content", "results", "resultado", "disposiciones"):
            valor = data.get(clave)
            if isinstance(valor, list):
                resumen[clave + "_n"] = len(valor)
                resumen[clave + "_muestra"] = [
                    {k: item.get(k) for k in (
                        "id", "codigoInsercion", "cve", "titulo", "organismo",
                        "numeroDogv", "fechaPublicacion", "fechaPublicacionSumario",
                        "fechaDisposicion", "tipoDocumento", "seccion", "estado"
                    ) if k in item}
                    for item in valor[:5] if isinstance(item, dict)
                ]
        for clave in ("totalElements", "totalPages", "number", "size", "fechaSumario", "urlPdf"):
            if clave in data:
                resumen[clave] = data[clave]
        return resumen
    if isinstance(data, list):
        return {"tipo": "list", "n": len(data), "muestra": data[:3]}
    return {"tipo": type(data).__name__, "valor": str(data)[:500]}


def _llamar(url: str, *, body=None):
    headers = {
        "User-Agent": "Mozilla/5.0 NetReto-Diagnostico/1.0",
        "Accept": "application/json, text/plain, */*",
    }
    data = None
    metodo = "GET"
    if body is not None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
        metodo = "POST"
    req = urllib.request.Request(url, data=data, headers=headers, method=metodo)
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            bruto = r.read(1000000)
            texto = bruto.decode("utf-8", errors="replace")
            entrada = {
                "ok": True,
                "status": r.status,
                "final_url": r.geturl(),
                "content_type": r.headers.get("Content-Type"),
                "bytes": len(bruto),
            }
            try:
                entrada["json"] = _resumir_json(json.loads(texto))
            except Exception:
                entrada["texto"] = texto[:1500]
            return entrada
    except urllib.error.HTTPError as exc:
        try:
            detalle = exc.read(5000).decode("utf-8", errors="replace")
        except Exception:
            detalle = ""
        return {"ok": False, "status": exc.code, "error": f"HTTPError: {exc}", "detalle": detalle[:3000]}
    except Exception as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}


def _diagnostico_api_dogv() -> None:
    base = "https://dogv.gva.es/dogv-portal"
    out = {"marca": "DIAGNOSTICO_API_DOGV", "pruebas": []}

    pruebas = [
        ("latest", f"{base}/dogv/latest?lang=es_es", None),
        ("fecha_2026_07_08", f"{base}/dogv?date=2026-07-08&lang=es_es", None),
    ]
    for nombre, url, body in pruebas:
        out["pruebas"].append({"nombre": nombre, "url": url, "resultado": _llamar(url, body=body)})

    for texto in ("A1-01", "1/26", "58/26"):
        qs = urllib.parse.urlencode({
            "lang": "es_es", "page": 0, "size": 10, "sort": "fechaPublicacion,desc"
        })
        url = f"{base}/dogv/search?{qs}"
        body = {
            "texto": texto,
            "textoFijo": False,
            "soloTitulo": False,
            "soloVigentes": False,
            "soloConsolidadas": False,
        }
        out["pruebas"].append({
            "nombre": f"search_{texto}",
            "url": url,
            "body": body,
            "resultado": _llamar(url, body=body),
        })

    logging.error(json.dumps(out, ensure_ascii=False))


threading.Thread(target=_diagnostico_api_dogv, daemon=True).start()


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
