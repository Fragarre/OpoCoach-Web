from __future__ import annotations

import getpass

import httpx
from fastapi.testclient import TestClient

from app.auth import obtener_supabase_public_key, obtener_supabase_url
from app.main import app
from app.postgres import conectar_postgres


def login(etiqueta: str) -> tuple[str, str]:
    print(f"\n--- {etiqueta} ---")
    email = input("Email: ").strip()
    password = getpass.getpass("Contraseña: ")

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
            f"Login de {etiqueta} fallido ({respuesta.status_code}): "
            f"{respuesta.text}"
        )

    return email, respuesta.json()["access_token"]


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def exigir_codigo(nombre: str, respuesta, esperado: int) -> None:
    if respuesta.status_code != esperado:
        raise RuntimeError(
            f"{nombre}: se esperaba HTTP {esperado} y se recibió "
            f"{respuesta.status_code}. Respuesta: {respuesta.text}"
        )
    print(f"{nombre}: OK ({respuesta.status_code})")


def main() -> None:
    email_a, token_a = login("USUARIO A - propietario")
    email_b, token_b = login("USUARIO B - intruso de prueba")

    if email_a.lower() == email_b.lower():
        raise RuntimeError("Los usuarios A y B deben ser distintos.")

    client = TestClient(app)
    simulacro_id = None

    me_a = client.get("/api/v1/me", headers=auth(token_a))
    me_b = client.get("/api/v1/me", headers=auth(token_b))
    exigir_codigo("Autenticación usuario A", me_a, 200)
    exigir_codigo("Autenticación usuario B", me_b, 200)

    id_a = me_a.json()["id"]
    id_b = me_b.json()["id"]
    if id_a == id_b:
        raise RuntimeError("Los dos logins han devuelto el mismo user_id.")

    print(f"Usuario A: {email_a} -> {id_a}")
    print(f"Usuario B: {email_b} -> {id_b}")

    try:
        crear = client.post(
            "/api/v1/simulacros",
            headers=auth(token_a),
            json={
                "convocatoria_id": 1,
                "origenes": ["A1", "A2", "C1", "C2"],
                "fuentes": ["REAL", "IA"],
            },
        )
        exigir_codigo("Usuario A crea simulacro", crear, 201)
        simulacro_id = int(crear.json()["id"])
        print(f"Simulacro temporal: {simulacro_id}")

        exigir_codigo(
            "Usuario A lee su simulacro",
            client.get(
                f"/api/v1/simulacros/{simulacro_id}",
                headers=auth(token_a),
            ),
            200,
        )

        preguntas_a = client.get(
            f"/api/v1/simulacros/{simulacro_id}/preguntas",
            headers=auth(token_a),
        )
        exigir_codigo("Usuario A obtiene sus preguntas", preguntas_a, 200)

        if len(preguntas_a.json()) != 110:
            raise RuntimeError("El simulacro de prueba no contiene 110 preguntas.")

        primera_id = int(
            preguntas_a.json()[0]["simulacro_pregunta_id"]
        )

        exigir_codigo(
            "Usuario B NO puede leer simulacro de A",
            client.get(
                f"/api/v1/simulacros/{simulacro_id}",
                headers=auth(token_b),
            ),
            404,
        )

        exigir_codigo(
            "Usuario B NO puede obtener preguntas de A",
            client.get(
                f"/api/v1/simulacros/{simulacro_id}/preguntas",
                headers=auth(token_b),
            ),
            404,
        )

        exigir_codigo(
            "Usuario B NO puede guardar respuestas en A",
            client.put(
                f"/api/v1/simulacros/{simulacro_id}/respuestas",
                headers=auth(token_b),
                json={
                    "respuestas": [
                        {
                            "simulacro_pregunta_id": primera_id,
                            "respuesta": "A",
                            "seguridad": "MUY_SEGURO",
                        }
                    ]
                },
            ),
            404,
        )

        exigir_codigo(
            "Usuario B NO puede finalizar simulacro de A",
            client.post(
                f"/api/v1/simulacros/{simulacro_id}/finalizar",
                headers=auth(token_b),
            ),
            404,
        )

        exigir_codigo(
            "Usuario B NO puede consultar corrección de A",
            client.get(
                f"/api/v1/simulacros/{simulacro_id}/correccion",
                headers=auth(token_b),
            ),
            404,
        )

        preguntas_a_despues = client.get(
            f"/api/v1/simulacros/{simulacro_id}/preguntas",
            headers=auth(token_a),
        )
        exigir_codigo(
            "Simulacro de A sigue accesible tras intentos de B",
            preguntas_a_despues,
            200,
        )

        primera = preguntas_a_despues.json()[0]
        if primera["respuesta_usuario"] is not None:
            raise RuntimeError(
                "El intento del usuario B modificó indebidamente el simulacro."
            )

        print("\nAISLAMIENTO ENTRE USUARIOS: OK")
        print(
            "El usuario B no ha podido leer, responder, finalizar ni "
            "consultar la corrección del simulacro del usuario A."
        )

    finally:
        if simulacro_id is not None:
            with conectar_postgres() as con:
                with con.cursor() as cur:
                    cur.execute(
                        "DELETE FROM public.simulacros WHERE id = %s",
                        (simulacro_id,),
                    )
                con.commit()
            print("Simulacro temporal eliminado: OK")


if __name__ == "__main__":
    main()
