from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass
from uuid import UUID

from fastapi import Header, HTTPException
from psycopg.rows import dict_row

from app.postgres import conectar_postgres


@dataclass(frozen=True)
class AgenteAutenticado:
    id: UUID
    nombre: str


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def exigir_agente(
    authorization: str | None = Header(default=None),
) -> AgenteAutenticado:
    if not authorization:
        raise HTTPException(status_code=401, detail="Se requiere autenticación de agente.")

    esquema, separador, token = authorization.partition(" ")
    if separador != " " or esquema.lower() != "bearer" or not token.strip():
        raise HTTPException(status_code=401, detail="Credencial de agente no válida.")

    token_hash = _hash_token(token.strip())

    with conectar_postgres() as con, con.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            SELECT id, nombre, token_hash
            FROM public.admin_agents
            WHERE activo = true
              AND token_hash IS NOT NULL
            """
        )
        agentes = cur.fetchall()

    # compare_digest evita comparar directamente secretos derivados.
    for agente in agentes:
        if hmac.compare_digest(str(agente["token_hash"]), token_hash):
            return AgenteAutenticado(id=agente["id"], nombre=agente["nombre"])

    raise HTTPException(status_code=401, detail="Credencial de agente no válida.")
