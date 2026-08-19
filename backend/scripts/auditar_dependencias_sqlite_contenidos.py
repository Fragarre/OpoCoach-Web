from __future__ import annotations

import ast
import re
from dataclasses import dataclass, asdict
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]

CARPETAS_AUDITAR = (
    BACKEND_DIR / "app",
    BACKEND_DIR / "scripts",
)

EXCLUIR_DIRS = {
    "__pycache__",
    ".venv",
    "venv",
    "node_modules",
    ".git",
}

TABLAS_CONTENIDOS = {
    "articulos_fuente",
    "banco_preguntas",
    "banco_preguntas_temas",
    "convocatoria_documentos_corpus",
    "convocatoria_modelo_bloques",
    "convocatoria_parte_reglas",
    "convocatoria_partes",
    "convocatorias",
    "documentos_corpus",
    "equivalencias_normas",
    "equivalencias_temas_no_juridicos",
    "lote_preguntas",
    "normas",
    "temario_referencias",
    "temario_temas",
    "temarios",
}

PATRONES = {
    "conectar_contenidos": re.compile(r"\bconectar_contenidos\s*\("),
    "conectar_contenidos_sqlite": re.compile(r"\bconectar_contenidos_sqlite\s*\("),
    "sqlite3": re.compile(r"\bsqlite3\b"),
    "sqlite_master": re.compile(r"\bsqlite_master\b", re.I),
    "pragma": re.compile(r"\bPRAGMA\b", re.I),
    "sqlite_file": re.compile(r"[A-Za-z0-9_./\\-]+\.sqlite3\b", re.I),
    "opocoach_db_path": re.compile(r"\bOPOCOACH_DB_PATH\b"),
}

SQL_KEYWORDS = re.compile(
    r"\b(SELECT|INSERT|UPDATE|DELETE|FROM|JOIN|WHERE|GROUP BY|ORDER BY|VALUES)\b",
    re.I,
)


@dataclass
class Incidencia:
    fichero: str
    linea: int
    tipo: str
    texto: str


def iterar_python():
    for carpeta in CARPETAS_AUDITAR:
        if not carpeta.exists():
            continue
        for ruta in carpeta.rglob("*.py"):
            if any(parte in EXCLUIR_DIRS for parte in ruta.parts):
                continue
            yield ruta


def ruta_relativa(ruta: Path) -> str:
    try:
        return str(ruta.relative_to(BACKEND_DIR))
    except ValueError:
        return str(ruta)


def buscar_texto(ruta: Path) -> list[Incidencia]:
    incidencias: list[Incidencia] = []
    texto = ruta.read_text(encoding="utf-8", errors="replace")
    lineas = texto.splitlines()

    for numero, linea in enumerate(lineas, 1):
        limpia = linea.strip()
        if not limpia or limpia.startswith("#"):
            continue

        for nombre, patron in PATRONES.items():
            if patron.search(linea):
                incidencias.append(
                    Incidencia(
                        fichero=ruta_relativa(ruta),
                        linea=numero,
                        tipo=nombre,
                        texto=limpia[:220],
                    )
                )

        # Referencias de tablas de contenidos.
        for tabla in sorted(TABLAS_CONTENIDOS):
            if re.search(rf"\b{re.escape(tabla)}\b", linea, re.I):
                incidencias.append(
                    Incidencia(
                        fichero=ruta_relativa(ruta),
                        linea=numero,
                        tipo=f"tabla:{tabla}",
                        texto=limpia[:220],
                    )
                )
                break

        # Posible placeholder SQLite en una sentencia SQL.
        # Se marca como indicio, no como error automático.
        if "?" in linea and SQL_KEYWORDS.search(linea):
            incidencias.append(
                Incidencia(
                    fichero=ruta_relativa(ruta),
                    linea=numero,
                    tipo="placeholder_sqlite_posible",
                    texto=limpia[:220],
                )
            )

    return incidencias


def buscar_imports_ast(ruta: Path) -> list[Incidencia]:
    incidencias: list[Incidencia] = []
    try:
        arbol = ast.parse(ruta.read_text(encoding="utf-8", errors="replace"))
    except SyntaxError as exc:
        incidencias.append(
            Incidencia(
                fichero=ruta_relativa(ruta),
                linea=exc.lineno or 0,
                tipo="syntax_error",
                texto=str(exc),
            )
        )
        return incidencias

    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Import):
            for alias in nodo.names:
                if alias.name == "sqlite3":
                    incidencias.append(
                        Incidencia(
                            fichero=ruta_relativa(ruta),
                            linea=getattr(nodo, "lineno", 0),
                            tipo="import_sqlite3",
                            texto="import sqlite3",
                        )
                    )

        elif isinstance(nodo, ast.ImportFrom):
            modulo = nodo.module or ""
            nombres = {alias.name for alias in nodo.names}
            if modulo == "app.database":
                for nombre in (
                    "conectar_contenidos",
                    "conectar_contenidos_sqlite",
                    "conectar_contenidos_postgres",
                    "obtener_origen_contenidos",
                ):
                    if nombre in nombres:
                        incidencias.append(
                            Incidencia(
                                fichero=ruta_relativa(ruta),
                                linea=getattr(nodo, "lineno", 0),
                                tipo=f"import:{nombre}",
                                texto=f"from app.database import ... {nombre}",
                            )
                        )

    return incidencias


def clasificar(incidencias: list[Incidencia]):
    por_fichero: dict[str, list[Incidencia]] = {}
    for inc in incidencias:
        por_fichero.setdefault(inc.fichero, []).append(inc)

    candidatos_revisar = []
    esperados = []
    solo_referencias = []

    for fichero, items in sorted(por_fichero.items()):
        tipos = {x.tipo for x in items}

        # database.py y scripts de migración/auditoría pueden usar SQLite
        # deliberadamente; se muestran, pero no se consideran por sí solos
        # dependencia funcional de producción.
        es_infra = (
            fichero == "app/database.py"
            or fichero.startswith("scripts/")
        )

        usa_conexion_legacy = (
            "conectar_contenidos" in tipos
            or "import:conectar_contenidos" in tipos
        )
        usa_sqlite_directo = bool(
            {
                "sqlite3",
                "import_sqlite3",
                "sqlite_master",
                "pragma",
                "sqlite_file",
                "conectar_contenidos_sqlite",
                "import:conectar_contenidos_sqlite",
            }
            & tipos
        )
        tiene_tablas = any(t.startswith("tabla:") for t in tipos)

        if not es_infra and (usa_conexion_legacy or usa_sqlite_directo):
            candidatos_revisar.append(fichero)
        elif es_infra and (usa_conexion_legacy or usa_sqlite_directo):
            esperados.append(fichero)
        elif tiene_tablas:
            solo_referencias.append(fichero)

    return candidatos_revisar, esperados, solo_referencias, por_fichero


def main() -> int:
    print("=" * 78)
    print("AUDITORÍA DE DEPENDENCIAS SQLITE DE CONTENIDOS")
    print("=" * 78)
    print(f"Backend: {BACKEND_DIR}")
    print("Modo: SOLO LECTURA")
    print()

    rutas = list(iterar_python())
    if not rutas:
        print("ERROR: no se han encontrado archivos .py en app/ ni scripts/.")
        return 1

    incidencias: list[Incidencia] = []
    for ruta in rutas:
        incidencias.extend(buscar_imports_ast(ruta))
        incidencias.extend(buscar_texto(ruta))

    candidatos, esperados, referencias, por_fichero = clasificar(incidencias)

    print(f"Archivos Python revisados....................... {len(rutas)}")
    print(f"Archivos con indicios SQLite/contenidos......... {len(por_fichero)}")
    print()

    print("DEPENDENCIAS FUNCIONALES A REVISAR")
    print("-" * 78)
    if not candidatos:
        print("Ninguna detectada.")
    else:
        for fichero in candidatos:
            tipos = sorted({x.tipo for x in por_fichero[fichero]})
            print(f"{fichero}")
            print("  " + ", ".join(tipos))

    print()
    print("USOS ESPERADOS EN INFRAESTRUCTURA / SCRIPTS")
    print("-" * 78)
    if not esperados:
        print("Ninguno.")
    else:
        for fichero in esperados:
            tipos = sorted({x.tipo for x in por_fichero[fichero]})
            print(f"{fichero}")
            print("  " + ", ".join(tipos))

    print()
    print("ARCHIVOS CON REFERENCIAS A TABLAS, SIN DEPENDENCIA SQLITE DIRECTA")
    print("-" * 78)
    if not referencias:
        print("Ninguno.")
    else:
        for fichero in referencias:
            tablas = sorted(
                t.split(":", 1)[1]
                for t in {x.tipo for x in por_fichero[fichero]}
                if t.startswith("tabla:")
            )
            print(f"{fichero}: {', '.join(tablas)}")

    print()
    print("DETALLE DE DEPENDENCIAS FUNCIONALES")
    print("-" * 78)
    if not candidatos:
        print("Sin incidencias funcionales.")
    else:
        for fichero in candidatos:
            print()
            print(f"[{fichero}]")
            vistos = set()
            for inc in sorted(
                por_fichero[fichero],
                key=lambda x: (x.linea, x.tipo, x.texto),
            ):
                clave = (inc.linea, inc.tipo, inc.texto)
                if clave in vistos:
                    continue
                vistos.add(clave)
                if (
                    inc.tipo.startswith("tabla:")
                    or inc.tipo == "placeholder_sqlite_posible"
                ):
                    continue
                print(f"  L{inc.linea:<5} {inc.tipo:<32} {inc.texto}")

    print()
    print("=" * 78)
    if candidatos:
        print("RESULTADO FINAL: REVISAR")
        print("=" * 78)
        print(
            "Quedan archivos funcionales que todavía presentan indicios de "
            "dependencia SQLite."
        )
        print("No se ha modificado ningún archivo ni ninguna base de datos.")
        return 2

    print("RESULTADO FINAL: CORRECTO")
    print("=" * 78)
    print(
        "No se han detectado dependencias SQLite funcionales fuera de la "
        "infraestructura esperada."
    )
    print("No se ha modificado ningún archivo ni ninguna base de datos.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
