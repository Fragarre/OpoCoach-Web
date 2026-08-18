from __future__ import annotations

import getpass
import os

import httpx

from app.auth import (
    obtener_supabase_public_key,
    obtener_supabase_url,
    validar_access_token,
)


def main() -> None:
    email = input("Email del usuario Supabase: ").strip()
    password = getpass.getpass("Contraseña del usuario: ")

    respuesta = httpx.post(
        f"{obtener_supabase_url()}/auth/v1/token",
        params={"grant_type": "password"},
        headers={
            "apikey": obtener_supabase_public_key(),
            "Content-Type": "application/json",
        },
        json={"email": email, "password": password},
        timeout=10.0,
    )

    if respuesta.status_code != 200:
        raise RuntimeError(
            f"Login Supabase fallido ({respuesta.status_code}): "
            f"{respuesta.text}"
        )

    token = respuesta.json()["access_token"]
    usuario = validar_access_token(token)

    print("Autenticación Supabase: OK")
    print(f"user_id: {usuario.id}")
    print(f"email: {usuario.email}")
    print("Token validado y perfil OpoCoach activo: OK")


if __name__ == "__main__":
    main()
