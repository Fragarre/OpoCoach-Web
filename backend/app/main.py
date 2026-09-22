import base64
import stripe
from fastapi import Depends, FastAPI, HTTPException, Query, Request
from pydantic import BaseModel

from app.analisis_rendimiento import generar_analisis_rendimiento
from app.admin_jobs import router as admin_jobs_router
from app.chat_convocatoria import responder_chat
from app.pdf_examen import generar_pdf_preguntas
from app.pdf_soluciones import generar_pdf_soluciones

from app.materiales import (
    listar_normas_materiales,
    obtener_articulos_extracto,
    obtener_articulos_texto_completo,
    obtener_convocatoria_materiales,
    obtener_resumen_preparado,
)
from app.pdf_materiales import generar_pdf_material
from app.auth import UsuarioAutenticado, exigir_admin, usuario_actual
from app.billing import crear_checkout_suscripcion, crear_portal_cliente
from app.subscriptions import (
    procesar_webhook,
    obtener_estado_suscripcion,
    obtener_customer_id_stripe,
)
from app.postgres import comprobar_postgres
from app.repositorio_contenidos import (
    comprobar_base,
    obtener_convocatorias,
    obtener_resumen_convocatoria,
)
from app.schemas import (
    Convocatoria,
    CrearSimulacroRequest,
    DisponibilidadParte,
    EstadoBase,
    GuardarRespuestasRequest,
    PreguntaCorregida,
    PreguntaSimulacro,
    ResultadoSimulacro,
    ResumenConvocatoria,
    Simulacro,
    SimulacroCreado,
    SimulacroListado,
    UsuarioActual,
    TemaTest,
    NormaTest,
    CrearTestRequest,
    TestCreado,
    CheckoutSessionResponse,
    PortalSessionResponse,
    EstadoSuscripcion,
)
from app.tests_tucoach import (
    obtener_puntos_temario_test,
    obtener_normas_test,
    crear_test,
)
from app.simulacros import (
    crear_simulacro,
    finalizar_simulacro,
    guardar_respuestas,
    obtener_correccion,
    obtener_disponibilidad,
    obtener_preguntas_para_realizar,
    obtener_simulacro,
    listar_simulacros,
    eliminar_simulacro,
    obtener_resultado_guardado,
    obtener_tiempo_correccion,
    obtener_resultado_para_analisis,
    obtener_resultado_acumulado,
    existe_simulacro_gratuito,
)

class ChatMensajeRequest(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    convocatoria_id: int
    pregunta: str
    mensajes_previos: list[ChatMensajeRequest] = []
    modo: str = "CONVOCATORIA"



def _estado_acceso(user_id):
    return obtener_estado_suscripcion(user_id)


def _exigir_suscripcion_activa(user_id) -> dict:
    estado = _estado_acceso(user_id)
    if not estado["suscrito"]:
        raise HTTPException(
            status_code=403,
            detail=(
                "Esta función requiere una suscripción activa a TuCoach."
            ),
        )
    return estado


def _obtener_prueba_accesible(simulacro_id: int, user_id):
    prueba = obtener_simulacro(simulacro_id, user_id)
    if prueba is None:
        raise HTTPException(status_code=404, detail="Simulacro no encontrado")
    return prueba


def _exigir_lectura_prueba(simulacro_id: int, user_id) -> tuple[dict, dict]:
    prueba = _obtener_prueba_accesible(simulacro_id, user_id)
    estado = _estado_acceso(user_id)

    if (
        bool(prueba.get("es_prueba_gratuita"))
        or estado["suscrito"]
        or estado.get("acceso_historico_activo", False)
    ):
        return prueba, estado

    raise HTTPException(
        status_code=403,
        detail=(
            "El plazo de acceso al histórico de esta suscripción ha finalizado."
        ),
    )


def _exigir_escritura_prueba(simulacro_id: int, user_id) -> tuple[dict, dict]:
    prueba = _obtener_prueba_accesible(simulacro_id, user_id)
    estado = _estado_acceso(user_id)

    if bool(prueba.get("es_prueba_gratuita")) or estado["suscrito"]:
        return prueba, estado

    if estado.get("acceso_historico_activo", False):
        raise HTTPException(
            status_code=403,
            detail=(
                "Tras la baja, el histórico está disponible únicamente en modo "
                "lectura y para descarga de PDFs."
            ),
        )

    raise HTTPException(
        status_code=403,
        detail=(
            "El plazo de acceso al histórico de esta suscripción ha finalizado."