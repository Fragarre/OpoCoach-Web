from __future__ import annotations

import os
from dataclasses import dataclass
from uuid import UUID

import httpx
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from psycopg.rows import dict_row

from app.postgres import conectar_postgres

bearer = HTTPBearer(auto_error=False)

_supabase_http = httpx.Client(
    timeout=10.0,
    limits=httpx.Limits(
        max_connections=20,
        max_keepalive_connections=10,
        keepalive_expiry=30.0,
    ),
)


@dataclass(frozen=True)
class UsuarioAutenticado:
    id: UUID
    email: str


def obtener_supabase_url() -> str:
    valor = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
    if not valor:
        raise RuntimeError("SUPABASE_URL no está configurado en backend/.env.")
    return valor


def obtener_supabase_public_key() -> str:
    """
    Acepta el nombre moderno SUPABASE_PUBLISHABLE_KEY y, por compatibilidad,
    SUPABASE_ANON_KEY.
    """
    valor = (
        os.getenv("SUPABASE_PUBLISHABLE_KEY", "").strip()
        or os.getenv("SUPABASE_ANON_KEY", "").strip()
    )
    if not valor:
        raise RuntimeError(
            "SUPABASE_PUBLISHABLE_KEY no está configurado en backend/.env."
        )
    return valor


def validar_access_token(token: str) -> UsuarioAutenticado:
    """
    Valida el access token contra Supabase Auth y comprueba además que el
    perfil local de OpoCoach existe y está activo.
    """
    try:
        respuesta = _supabase_http.get(
            f"{obtener_supabase_url()}/auth/v1/user",
            headers={
                "Authorization": f"Bearer {token}",
                "apikey": obtener_supabase_public_key(),
            },
        )
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=503,
            detail="No se ha podido validar la sesión con Supabase Auth.",
        ) from exc

    if respuesta.status_code != 200:
        raise HTTPException(
            status_code=401,
            detail="Sesión no válida o caducada.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    datos = respuesta.json()
    try:
        user_id = UUID(datos["id"])
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=401, detail="Token de usuario no válido.") from exc

    email = str(datos.get("email") or "").strip()
    if not email:
        raise HTTPException(status_code=401, detail="El usuario autenticado no tiene email.")

    with conectar_postgres() as con:
        with con.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT id, email, activo
                FROM public.profiles
                WHERE id = %s
                LIMIT 1
                """,
                (user_id,),
            )
            perfil = cur.fetchone()

    if perfil is None:
        raise HTTPException(
            status_code=403,
            detail="El usuario autenticado no tiene perfil OpoCoach.",
        )

    if not perfil["activo"]:
        raise HTTPException(status_code=403, detail="El usuario está desactivado.")

    return UsuarioAutenticado(id=user_id, email=email)


def usuario_actual(
    credenciales: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> UsuarioAutenticado:
    if credenciales is None or credenciales.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=401,
            detail="Se requiere autenticación.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return validar_access_token(credenciales.credentials)
