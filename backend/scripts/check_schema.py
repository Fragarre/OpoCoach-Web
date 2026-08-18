from __future__ import annotations

from app.postgres import conectar_postgres

TABLAS = (
    "profiles",
    "subscriptions",
    "simulacros",
    "simulacro_preguntas",
    "simulacro_snapshot",
)


def main() -> None:
    with conectar_postgres() as con:
        with con.cursor() as cur:
            cur.execute(
                """
                SELECT tablename, rowsecurity
                FROM pg_tables
                WHERE schemaname = 'public' AND tablename = ANY(%s)
                ORDER BY tablename
                """,
                (list(TABLAS),),
            )
            filas = cur.fetchall()

            encontradas = {nombre for nombre, _ in filas}
            faltan = set(TABLAS) - encontradas
            if faltan:
                raise RuntimeError(f"Faltan tablas: {', '.join(sorted(faltan))}")

            for nombre, rls in filas:
                if not rls:
                    raise RuntimeError(f"RLS no está activado en {nombre}")

            cur.execute(
                """
                SELECT COUNT(*)
                FROM pg_trigger t
                JOIN pg_class c ON c.oid = t.tgrelid
                JOIN pg_namespace n ON n.oid = c.relnamespace
                WHERE n.nspname = 'auth'
                  AND c.relname = 'users'
                  AND t.tgname = 'on_auth_user_created'
                  AND NOT t.tgisinternal
                """
            )
            if cur.fetchone()[0] != 1:
                raise RuntimeError("No se encuentra el trigger on_auth_user_created")

    print("Esquema PostgreSQL: OK")
    for nombre, _ in filas:
        print(f"- {nombre}: OK, RLS activado")
    print("- trigger auth.users -> profiles: OK")


if __name__ == "__main__":
    main()
