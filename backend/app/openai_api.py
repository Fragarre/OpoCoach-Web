from __future__ import annotations

import os

from dotenv import load_dotenv
from openai import OpenAI


load_dotenv()


def generar_analisis_rendimiento_ia(
    prompt: str,
    modelo: str | None = None,
) -> str:
    """
    Genera el comentario interpretativo del rendimiento acumulado.

    La clave se lee exclusivamente del entorno. Por compatibilidad con la
    versión Streamlit se utiliza OPENAI_API_KEY_OPOCOACH.
    """

    api_key = os.getenv("OPENAI_API_KEY_OPOCOACH")
    if not api_key:
        raise RuntimeError(
            "Falta OPENAI_API_KEY_OPOCOACH en la configuración del backend."
        )

    modelo_final = (
        modelo
        or os.getenv("OPENAI_MODEL_ANALISIS_RENDIMIENTO")
        or "gpt-5.4"
    )

    cliente = OpenAI(api_key=api_key)
    respuesta = cliente.responses.create(
        model=modelo_final,
        input=prompt,
    )

    texto = str(respuesta.output_text or "").strip()
    if not texto:
        raise RuntimeError(
            "OpenAI no devolvió texto para el análisis de rendimiento."
        )

    return texto
