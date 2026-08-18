from __future__ import annotations

import os
from uuid import UUID

from psycopg.rows import dict_row

from app.postgres import conectar_postgres


def obtener_dev_user_email() -> str:
    email = os.getenv("DEV_USER_EMAIL", "").strip()
    if not email:
        raise RuntimeError(
            "DEV_USER_EMAIL no está configurado en backend/.env. "
            "Durante esta fase debe contener el email de un usuario real "
            "creado en Supabase Auth."
        )
    return email


def obtener_dev_user_id() -> UUID:
    """
    Usuario temporal para las pruebas del backend antes de integrar login real.

    Esta función desaparecerá cuando FastAPI obtenga el user_id del token
    autenticado de Supabase.
    """
    email = obtener_dev_user_email()
    with conectar_postgres() as con:
        with con.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT id, email, activo
                FROM public.profiles
                WHERE lower(email) = lower(%s)
                LIMIT 1
                """,
                (email,),
            )
            fila = cur.fetchone()

    if fila is None:
        raise RuntimeError(
            f"No existe en public.profiles el usuario de prueba {email!r}. "
            "Créalo primero en Supabase Auth; el trigger generará su perfil."
        )
    if not fila["activo"]:
        raise RuntimeError("El usuario de prueba está desactivado.")

    return fila["id"]
