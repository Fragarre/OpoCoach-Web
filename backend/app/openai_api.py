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


def seleccionar_fragmento_json(
    prompt: str,
    modelo: str = "gpt-5.4-mini",
    operacion: str = "general",
):
    """
    Ejecuta una llamada a Responses API y convierte la salida en JSON.

    Admite JSON puro y, como tolerancia defensiva, elimina un único bloque
    Markdown ```json ... ``` si el modelo lo hubiera añadido.
    """
    import json
    import re

    api_key = os.getenv("OPENAI_API_KEY_OPOCOACH")
    if not api_key:
        raise RuntimeError(
            "Falta OPENAI_API_KEY_OPOCOACH en la configuración del backend."
        )

    cliente = OpenAI(api_key=api_key)
    respuesta = cliente.responses.create(
        model=modelo,
        input=prompt,
    )

    texto = str(respuesta.output_text or "").strip()
    bloque = re.fullmatch(
        r"```(?:json)?\s*(.*?)\s*```",
        texto,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if bloque:
        texto = bloque.group(1).strip()

    try:
        return json.loads(texto)
    except json.JSONDecodeError as exc:
        raise ValueError(
            "La API no devolvió un JSON válido. "
            f"Respuesta recibida: {texto[:500]}"
        ) from exc

def generar_respuesta_chat_ia(
    prompt: str,
    modelo: str = "gpt-5.4-nano",
    operacion: str = "chat_convocatoria",
) -> str:
    """Genera una respuesta textual del Chat mediante Responses API."""
    api_key = os.getenv("OPENAI_API_KEY_OPOCOACH")
    if not api_key:
        raise RuntimeError(
            "Falta OPENAI_API_KEY_OPOCOACH en la configuración del backend."
        )

    cliente = OpenAI(api_key=api_key)
    respuesta = cliente.responses.create(
        model=modelo,
        input=prompt,
    )

    texto = str(respuesta.output_text or "").strip()
    if not texto:
        raise RuntimeError(
            f"OpenAI no devolvió texto para la operación {operacion}."
        )

    return texto

