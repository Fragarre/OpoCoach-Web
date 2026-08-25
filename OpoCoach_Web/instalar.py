from __future__ import annotations

import argparse
import hashlib
import shutil
from datetime import datetime
from pathlib import Path

ARCHIVOS = {'backend/app/repositorio_contenidos.py': {'expected_before': 'bf783177f06821f2fe02568ceeaee0cea69f44a32dc44d719d79a1e6fd13be8d', 'payload': '497794090619ef0a69207a0befff0fc1fcc8d0e4f77c51993e7ea915df0032f6'}, 'backend/app/simulacros.py': {'expected_before': '87541418bf41f421aa0fc5ad2536f3c99963e54b5b7973f46592976e6f8b4ba4', 'payload': '9925e73e77c361aa89f6ee694ef8f981761b1883d7322d7a1d6e728c7b40c0db'}, 'backend/app/tests_opocoach.py': {'expected_before': '06f614c435ed9d58feed0095eb53d5b31ac757a56157008f1eddf142ee52f655', 'payload': '37704c9a7cce54433fabf84cb07ca687cd0f92ceb703af143fa04d900ec3b2ca'}, 'backend/app/main.py': {'expected_before': '8b258bbfb394c78cfff9152469866f2ad06bd616b95822172878728aadcc5d88', 'payload': 'da0bbbc44984fe4451905de34416a4ea80f6d4184836df3af56f28bc4ade0af8'}, 'frontend/app/page.tsx': {'expected_before': '994227fc5460a2d4a0ab5d11cf5707c4026aba387f63c04df6e1cd317f7ac810', 'payload': '7ee09ab5b827237b0295ab592e1965428b336b38375085b0fc078e55a301f0a0'}}

def sha256(ruta: Path) -> str:
    h = hashlib.sha256()
    with ruta.open("rb") as f:
        for bloque in iter(lambda: f.read(1024 * 1024), b""):
            h.update(bloque)
    return h.hexdigest()

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".", help="Raíz de OpoCoach-Web")
    args = parser.parse_args()
    raiz = Path(args.root).resolve()
    paquete = Path(__file__).resolve().parent
    payload = paquete / "payload"

    errores = []
    for rel, firmas in ARCHIVOS.items():
        destino = raiz / rel
        origen = payload / rel
        if not destino.is_file():
            errores.append(f"No existe destino: {destino}")
        elif sha256(destino) != firmas["expected_before"]:
            errores.append(f"{rel} no coincide con la versión revisada; no se sobrescribe.")
        if not origen.is_file():
            errores.append(f"Falta payload: {origen}")
        elif sha256(origen) != firmas["payload"]:
            errores.append(f"Payload alterado: {rel}")

    if errores:
        print("ERROR: actualización cancelada antes de modificar archivos.")
        for e in errores:
            print("-", e)
        return 1

    marca = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = raiz / "copias_actualizacion" / f"antes_convocatorias_activas_web_{marca}"
    for rel in ARCHIVOS:
        destino = raiz / rel
        copia = backup / rel
        copia.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(destino, copia)

    temporales = []
    try:
        for rel in ARCHIVOS:
            destino = raiz / rel
            origen = payload / rel
            temporal = destino.with_suffix(destino.suffix + ".tmp_opocoach")
            shutil.copy2(origen, temporal)
            temporales.append((rel, temporal))
        for rel, temporal in temporales:
            temporal.replace(raiz / rel)
    except Exception:
        for rel in ARCHIVOS:
            copia = backup / rel
            if copia.is_file():
                shutil.copy2(copia, raiz / rel)
        for _, temporal in temporales:
            if temporal.exists():
                temporal.unlink()
        raise

    print("=" * 78)
    print("ACTUALIZACIÓN WEB INSTALADA")
    print("=" * 78)
    print(f"Proyecto: {raiz}")
    print(f"Backup:   {backup}")
    print("Archivos actualizados:")
    for rel in ARCHIVOS:
        print(f"- {rel}")
    print("La base de datos NO ha sido modificada por este instalador.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
