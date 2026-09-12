from __future__ import annotations

import atexit
import os
import subprocess
import sys
import time
from pathlib import Path


def _activar_unificacion_empleo() -> bool:
    if os.getenv("UNIFIED_EMPLOYMENT_ENABLED", "1").strip().lower() in {"0", "false", "no"}:
        return False
    return any("app.main:app" in argumento for argumento in sys.argv)


if _activar_unificacion_empleo():
    import fastapi
    import httpx
    from fastapi import Request, Response
    from fastapi.responses import JSONResponse

    _FastAPIOriginal = fastapi.FastAPI
    _BACKEND_DIR = Path(__file__).resolve().parent
    _EMPLOYMENT_BACKEND_DIR = _BACKEND_DIR / "employment_service" / "backend"
    _EMPLOYMENT_PORT = int(os.getenv("EMPLOYMENT_INTERNAL_PORT", "8765"))
    _EMPLOYMENT_BASE = f"http://127.0.0.1:{_EMPLOYMENT_PORT}"

    class UnifiedFastAPI(_FastAPIOriginal):
        """Añade NetReto Empleo al mismo servicio Render sin mezclar ambos códigos.

        El backend de Empleo vive como submódulo Git y se ejecuta en un proceso
        interno, inaccesible directamente desde Internet. Esta aplicación expone
        sus rutas bajo /empleo/* mediante un proxy local.
        """

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.state.employment_process = None

            def detener_empleo() -> None:
                proceso = getattr(self.state, "employment_process", None)
                if proceso is None or proceso.poll() is not None:
                    return
                proceso.terminate()
                try:
                    proceso.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    proceso.kill()
                    proceso.wait(timeout=5)

            def iniciar_empleo() -> None:
                if not _EMPLOYMENT_BACKEND_DIR.exists():
                    raise RuntimeError(
                        f"No se encuentra el submódulo de Empleo en {_EMPLOYMENT_BACKEND_DIR}"
                    )

                env = os.environ.copy()
                # Aísla el paquete `app` del backend principal: el hijo debe cargar
                # exclusivamente el `app` de NetReto-Web-Empleo.
                env["PYTHONPATH"] = str(_EMPLOYMENT_BACKEND_DIR)

                # El servicio unificado comparte proceso Render, pero NO base de datos.
                # Empleo conserva su PostgreSQL actual mediante una variable específica.
                employment_database_url = os.getenv("EMPLOYMENT_DATABASE_URL", "").strip()
                if employment_database_url:
                    env["DATABASE_URL"] = employment_database_url

                proceso = subprocess.Popen(
                    [
                        sys.executable,
                        "-m",
                        "uvicorn",
                        "app.main:app",
                        "--host",
                        "127.0.0.1",
                        "--port",
                        str(_EMPLOYMENT_PORT),
                    ],
                    cwd=str(_EMPLOYMENT_BACKEND_DIR),
                    env=env,
                )
                self.state.employment_process = proceso
                atexit.register(detener_empleo)

                limite = time.monotonic() + 45
                ultimo_error = ""
                while time.monotonic() < limite:
                    if proceso.poll() is not None:
                        raise RuntimeError(
                            f"El backend interno de Empleo terminó durante el arranque (código {proceso.returncode})."
                        )
                    try:
                        respuesta = httpx.get(f"{_EMPLOYMENT_BASE}/health", timeout=2.0)
                        if respuesta.status_code == 200:
                            return
                        ultimo_error = f"HTTP {respuesta.status_code}"
                    except Exception as exc:
                        ultimo_error = f"{type(exc).__name__}: {exc}"
                    time.sleep(0.5)

                detener_empleo()
                raise RuntimeError(
                    "El backend interno de Empleo no respondió a /health durante el arranque. "
                    f"Último error: {ultimo_error}"
                )

            async def reenviar(request: Request, path: str) -> Response:
                destino = f"{_EMPLOYMENT_BASE}/{path.lstrip('/')}"
                cabeceras = {
                    clave: valor
                    for clave, valor in request.headers.items()
                    if clave.lower() not in {"host", "content-length", "connection"}
                }
                cuerpo = await request.body()
                try:
                    async with httpx.AsyncClient(
                        timeout=httpx.Timeout(900.0, connect=10.0),
                        follow_redirects=False,
                    ) as cliente:
                        respuesta = await cliente.request(
                            request.method,
                            destino,
                            params=list(request.query_params.multi_items()),
                            headers=cabeceras,
                            content=cuerpo if cuerpo else None,
                        )
                except httpx.HTTPError as exc:
                    return JSONResponse(
                        status_code=503,
                        content={
                            "detail": f"Backend interno de Empleo no disponible: {type(exc).__name__}: {exc}"
                        },
                    )

                cabeceras_salida = {}
                for nombre in ("content-type", "content-disposition", "location", "cache-control"):
                    valor = respuesta.headers.get(nombre)
                    if valor:
                        cabeceras_salida[nombre] = valor

                return Response(
                    content=respuesta.content,
                    status_code=respuesta.status_code,
                    headers=cabeceras_salida,
                )

            async def proxy_empleo(request: Request, path: str) -> Response:
                return await reenviar(request, path)

            async def proxy_empleo_raiz(request: Request) -> Response:
                return await reenviar(request, "")

            metodos = ["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"]
            self.api_route("/empleo", methods=metodos, include_in_schema=False)(proxy_empleo_raiz)
            self.api_route("/empleo/{path:path}", methods=metodos, include_in_schema=False)(proxy_empleo)

            # Se arranca al construir la aplicación, no mediante los hooks antiguos
            # de Starlette/FastAPI (retirados en las versiones actuales). Si el hijo
            # no llega a estar sano, la importación falla y Render conserva el deploy
            # anterior.
            iniciar_empleo()

    fastapi.FastAPI = UnifiedFastAPI
