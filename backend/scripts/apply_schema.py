from __future__ import annotations

from pathlib import Path

from app.postgres import conectar_postgres

SCHEMA_FILE = Path(__file__).resolve().parents[1] / "migrations" / "001_usuario_schema.sql"


def main() -> None:
    sql = SCHEMA_FILE.read_text(encoding="utf-8")
    with conectar_postgres() as con:
        with con.cursor() as cur:
            cur.execute(sql)
        con.commit()

    print("Esquema PostgreSQL OpoCoach: OK")
    print("Tablas creadas/verificadas:")
    print("- profiles")
    print("- subscriptions")
    print("- simulacros")
    print("- simulacro_preguntas")
    print("- simulacro_snapshot")
    print("RLS: activado")
    print("Persistencia activa de la API: sigue siendo usuario_pruebas.sqlite3")


if __name__ == "__main__":
    main()
