from __future__ import annotations

from app.postgres import conectar_postgres


def main() -> None:
    """Prueba conexión, escritura y lectura sin dejar datos persistentes."""
    with conectar_postgres() as con:
        with con.cursor() as cur:
            cur.execute("SELECT current_database(), current_setting('server_version')")
            database, version = cur.fetchone()

            # TEMP existe solo durante esta conexión y desaparece al cerrarla.
            cur.execute("CREATE TEMP TABLE opocoach_test_conexion (valor integer NOT NULL)")
            cur.execute("INSERT INTO opocoach_test_conexion(valor) VALUES (42)")
            cur.execute("SELECT valor FROM opocoach_test_conexion")
            valor = cur.fetchone()[0]

            if valor != 42:
                raise RuntimeError("La prueba de lectura/escritura no ha devuelto el valor esperado.")

        con.rollback()

    print("Conexión PostgreSQL: OK")
    print(f"Base: {database}")
    print(f"PostgreSQL: {version}")
    print("Lectura/escritura temporal: OK")
    print("No se ha dejado ninguna tabla ni dato de prueba persistente.")


if __name__ == "__main__":
    main()
