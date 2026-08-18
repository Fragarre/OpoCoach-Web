from __future__ import annotations

import getpass

import httpx
from psycopg.rows import dict_row

from app.auth import (
    obtener_supabase_public_key,
    obtener_supabase_url,
    validar_access_token,
)
from app.postgres import conectar_postgres
from app.simulacros import (
    crear_simulacro,
    finalizar_simulacro,
    guardar_respuestas,
    obtener_correccion,
    obtener_preguntas_para_realizar,
)


def iniciar_sesion():
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
    return validar_access_token(respuesta.json()["access_token"])


def main() -> None:
    usuario = iniciar_sesion()
    simulacro_id = None

    print(f"Usuario autenticado: {usuario.email}")
    print(f"user_id: {usuario.id}")

    try:
        simulacro_id = crear_simulacro(
            convocatoria_id=1,
            origenes=["A1", "A2", "C1", "C2"],
            fuentes=["REAL", "IA"],
            user_id=usuario.id,
        )
        preguntas = obtener_preguntas_para_realizar(
            simulacro_id,
            usuario.id,
        )
        if len(preguntas) != 110:
            raise RuntimeError(
                f"Se esperaban 110 preguntas y se han obtenido {len(preguntas)}."
            )

        with conectar_postgres() as con:
            with con.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    SELECT sp.id, ss.respuesta_correcta
                    FROM public.simulacro_preguntas sp
                    JOIN public.simulacro_snapshot ss
                      ON ss.simulacro_pregunta_id = sp.id
                    WHERE sp.simulacro_id = %s
                    ORDER BY sp.orden
                    LIMIT 2
                    """,
                    (simulacro_id,),
                )
                soluciones = cur.fetchall()

        correcta_1 = soluciones[0]["respuesta_correcta"].upper()
        correcta_2 = soluciones[1]["respuesta_correcta"].upper()
        incorrecta_2 = next(
            opcion
            for opcion in ("A", "B", "C", "D")
            if opcion != correcta_2
        )

        guardar_respuestas(
            simulacro_id,
            [
                {
                    "simulacro_pregunta_id": soluciones[0]["id"],
                    "respuesta": correcta_1,
                    "seguridad": "MUY_SEGURO",
                },
                {
                    "simulacro_pregunta_id": soluciones[1]["id"],
                    "respuesta": incorrecta_2,
                    "seguridad": "POCO_SEGURO",
                },
            ],
            usuario.id,
        )

        resultado = finalizar_simulacro(simulacro_id, usuario.id)
        correccion = obtener_correccion(simulacro_id, usuario.id)

        assert resultado["total"] == 110
        assert resultado["aciertos"] == 1
        assert resultado["fallos"] == 1
        assert resultado["no_contestadas"] == 108
        assert len(correccion) == 110

        print("Persistencia PostgreSQL con usuario autenticado: OK")
        print(
            "Resultado controlado: "
            f'{resultado["aciertos"]} acierto, '
            f'{resultado["fallos"]} fallo, '
            f'{resultado["no_contestadas"]} no contestadas, '
            f'nota {resultado["nota"]:.2f}'
        )

    finally:
        if simulacro_id is not None:
            with conectar_postgres() as con:
                with con.cursor() as cur:
                    cur.execute(
                        """
                        DELETE FROM public.simulacros
                        WHERE id = %s
                          AND user_id = %s
                        """,
                        (simulacro_id, usuario.id),
                    )
                con.commit()
            print("Simulacro temporal eliminado: OK")


if __name__ == "__main__":
    main()
