import stripe
from fastapi import Depends, FastAPI, HTTPException, Query, Request

from app.auth import UsuarioAutenticado, usuario_actual
from app.billing import crear_checkout_suscripcion
from app.subscriptions import procesar_webhook, obtener_estado_suscripcion
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
    EstadoSuscripcion,
)
from app.tests_opocoach import (
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
)

app = FastAPI(
    title="OpoCoach API",
    version="0.9.0",
    description=(
        "Backend paralelo de migración: contenidos SQLite, persistencia "
        "PostgreSQL y autenticación Supabase."
    ),
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/v1/postgres/estado")
def estado_postgres() -> dict[str, str]:
    try:
        return comprobar_postgres()
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=f"PostgreSQL no disponible: {exc}",
        ) from exc


@app.get("/api/v1/base/estado", response_model=EstadoBase)
def estado_base() -> EstadoBase:
    return EstadoBase(**comprobar_base())


@app.get("/api/v1/convocatorias", response_model=list[Convocatoria])
def listar_convocatorias() -> list[Convocatoria]:
    return [Convocatoria(**fila) for fila in obtener_convocatorias()]


@app.get(
    "/api/v1/convocatorias/{convocatoria_id}/resumen",
    response_model=ResumenConvocatoria,
)
def resumen_convocatoria(convocatoria_id: int) -> ResumenConvocatoria:
    fila = obtener_resumen_convocatoria(convocatoria_id)
    if fila is None:
        raise HTTPException(status_code=404, detail="Convocatoria no encontrada")
    return ResumenConvocatoria(**fila)


@app.get("/api/v1/me", response_model=UsuarioActual)
def me(usuario: UsuarioAutenticado = Depends(usuario_actual)) -> UsuarioActual:
    return UsuarioActual(id=str(usuario.id), email=usuario.email)




@app.post("/api/v1/billing/webhook")
async def stripe_webhook_api(request: Request) -> dict[str, str]:
    payload = await request.body()
    signature = request.headers.get("stripe-signature")

    if not signature:
        raise HTTPException(
            status_code=400,
            detail="Falta la cabecera Stripe-Signature.",
        )

    try:
        tipo = procesar_webhook(payload, signature)
        return {"received": "true", "type": tipo}
    except stripe.SignatureVerificationError as exc:
        raise HTTPException(
            status_code=400,
            detail="Firma Stripe no válida.",
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail="Payload Stripe no válido.",
        ) from exc
    except RuntimeError as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        ) from exc


@app.get(
    "/api/v1/billing/subscription",
    response_model=EstadoSuscripcion,
)
def estado_suscripcion_api(
    usuario: UsuarioAutenticado = Depends(usuario_actual),
) -> EstadoSuscripcion:
    return EstadoSuscripcion(
        **obtener_estado_suscripcion(usuario.id)
    )


@app.post(
    "/api/v1/billing/checkout",
    response_model=CheckoutSessionResponse,
    status_code=201,
)
def crear_checkout_api(
    usuario: UsuarioAutenticado = Depends(usuario_actual),
) -> CheckoutSessionResponse:
    try:
        checkout = crear_checkout_suscripcion(
            user_id=usuario.id,
            email=usuario.email,
        )
        return CheckoutSessionResponse(
            id=checkout.id,
            url=checkout.url,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except stripe.StripeError as exc:
        mensaje = getattr(exc, "user_message", None) or str(exc)
        raise HTTPException(
            status_code=502,
            detail=f"Stripe no ha podido crear el Checkout: {mensaje}",
        ) from exc


@app.get(
    "/api/v1/convocatorias/{convocatoria_id}/simulacro/disponibilidad",
    response_model=list[DisponibilidadParte],
)
def disponibilidad_simulacro(
    convocatoria_id: int,
    origen: list[str] = Query(...),
    fuente: list[str] = Query(default=["REAL", "IA"]),
    _usuario: UsuarioAutenticado = Depends(usuario_actual),
) -> list[DisponibilidadParte]:
    try:
        return [
            DisponibilidadParte(**x)
            for x in obtener_disponibilidad(convocatoria_id, origen, fuente)
        ]
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc



@app.get("/api/v1/simulacros", response_model=list[SimulacroListado])
def mis_simulacros_api(
    convocatoria_id: int | None = None,
    usuario: UsuarioAutenticado = Depends(usuario_actual),
) -> list[SimulacroListado]:
    try:
        return [
            SimulacroListado(**fila)
            for fila in listar_simulacros(
                usuario.id,
                convocatoria_id=convocatoria_id,
                tipo_prueba="SIMULACRO",
            )
        ]
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc



@app.get(
    "/api/v1/convocatorias/{convocatoria_id}/tests/temas",
    response_model=list[TemaTest],
)
def temas_disponibles_test_api(
    convocatoria_id: int,
    fuente: list[str] = Query(default=["REAL", "IA"]),
    _usuario: UsuarioAutenticado = Depends(usuario_actual),
) -> list[TemaTest]:
    try:
        return [
            TemaTest(**fila)
            for fila in obtener_puntos_temario_test(convocatoria_id, fuente)
        ]
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get(
    "/api/v1/convocatorias/{convocatoria_id}/tests/normas",
    response_model=list[NormaTest],
)
def normas_disponibles_test_api(
    convocatoria_id: int,
    fuente: list[str] = Query(default=["REAL", "IA"]),
    _usuario: UsuarioAutenticado = Depends(usuario_actual),
) -> list[NormaTest]:
    try:
        return [
            NormaTest(**fila)
            for fila in obtener_normas_test(convocatoria_id, fuente)
        ]
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/v1/tests", response_model=list[SimulacroListado])
def mis_tests_api(
    convocatoria_id: int | None = None,
    usuario: UsuarioAutenticado = Depends(usuario_actual),
) -> list[SimulacroListado]:
    return [
        SimulacroListado(**fila)
        for fila in listar_simulacros(
            usuario.id,
            convocatoria_id=convocatoria_id,
            tipo_prueba="TEST",
        )
    ]


@app.post("/api/v1/tests", response_model=TestCreado, status_code=201)
def nuevo_test_api(
    datos: CrearTestRequest,
    usuario: UsuarioAutenticado = Depends(usuario_actual),
) -> TestCreado:
    try:
        return TestCreado(
            **crear_test(
                convocatoria_id=datos.convocatoria_id,
                numero_preguntas=datos.numero_preguntas,
                temas_seleccionados=datos.temas_seleccionados,
                normas_seleccionadas=datos.normas_seleccionadas,
                modo_seleccion=datos.modo_seleccion,
                fuentes=datos.fuentes,
                user_id=usuario.id,
            )
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post(
    "/api/v1/simulacros",
    response_model=SimulacroCreado,
    status_code=201,
)
def nuevo_simulacro(
    datos: CrearSimulacroRequest,
    usuario: UsuarioAutenticado = Depends(usuario_actual),
) -> SimulacroCreado:
    try:
        sid = crear_simulacro(
            datos.convocatoria_id,
            datos.origenes,
            datos.fuentes,
            usuario.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return SimulacroCreado(id=sid)


@app.get("/api/v1/simulacros/{simulacro_id}", response_model=Simulacro)
def ver_simulacro(
    simulacro_id: int,
    usuario: UsuarioAutenticado = Depends(usuario_actual),
) -> Simulacro:
    fila = obtener_simulacro(simulacro_id, usuario.id)
    if fila is None:
        raise HTTPException(status_code=404, detail="Simulacro no encontrado")
    return Simulacro(**fila)


@app.get(
    "/api/v1/simulacros/{simulacro_id}/preguntas",
    response_model=list[PreguntaSimulacro],
)
def preguntas_simulacro(
    simulacro_id: int,
    usuario: UsuarioAutenticado = Depends(usuario_actual),
) -> list[PreguntaSimulacro]:
    if obtener_simulacro(simulacro_id, usuario.id) is None:
        raise HTTPException(status_code=404, detail="Simulacro no encontrado")
    return [
        PreguntaSimulacro(**x)
        for x in obtener_preguntas_para_realizar(simulacro_id, usuario.id)
    ]


@app.put(
    "/api/v1/simulacros/{simulacro_id}/respuestas",
    status_code=204,
)
def guardar_respuestas_simulacro(
    simulacro_id: int,
    datos: GuardarRespuestasRequest,
    usuario: UsuarioAutenticado = Depends(usuario_actual),
) -> None:
    try:
        guardar_respuestas(
            simulacro_id,
            [x.model_dump() for x in datos.respuestas],
            usuario.id,
        )
    except ValueError as exc:
        mensaje = str(exc)
        codigo = 404 if "no existe" in mensaje.lower() else 400
        raise HTTPException(status_code=codigo, detail=mensaje) from exc


@app.post(
    "/api/v1/simulacros/{simulacro_id}/finalizar",
    response_model=ResultadoSimulacro,
)
def finalizar_simulacro_api(
    simulacro_id: int,
    usuario: UsuarioAutenticado = Depends(usuario_actual),
) -> ResultadoSimulacro:
    try:
        return ResultadoSimulacro(
            **finalizar_simulacro(simulacro_id, usuario.id)
        )
    except ValueError as exc:
        mensaje = str(exc)
        codigo = 404 if "no existe" in mensaje.lower() else 400
        raise HTTPException(status_code=codigo, detail=mensaje) from exc



@app.get(
    "/api/v1/simulacros/{simulacro_id}/resultado",
    response_model=ResultadoSimulacro,
)
def resultado_simulacro_guardado_api(
    simulacro_id: int,
    usuario: UsuarioAutenticado = Depends(usuario_actual),
) -> ResultadoSimulacro:
    try:
        return ResultadoSimulacro(
            **obtener_resultado_guardado(simulacro_id, usuario.id)
        )
    except ValueError as exc:
        mensaje = str(exc)
        codigo = 404 if "no existe" in mensaje.lower() else 400
        raise HTTPException(status_code=codigo, detail=mensaje) from exc


@app.delete("/api/v1/simulacros/{simulacro_id}", status_code=204)
def eliminar_simulacro_api(
    simulacro_id: int,
    usuario: UsuarioAutenticado = Depends(usuario_actual),
) -> None:
    if not eliminar_simulacro(simulacro_id, usuario.id):
        raise HTTPException(status_code=404, detail="Simulacro no encontrado")


@app.get(
    "/api/v1/simulacros/{simulacro_id}/correccion",
    response_model=list[PreguntaCorregida],
)
def correccion_simulacro(
    simulacro_id: int,
    usuario: UsuarioAutenticado = Depends(usuario_actual),
) -> list[PreguntaCorregida]:
    try:
        return [
            PreguntaCorregida(**x)
            for x in obtener_correccion(simulacro_id, usuario.id)
        ]
    except ValueError as exc:
        mensaje = str(exc)
        codigo = 404 if "no existe" in mensaje.lower() else 400
        raise HTTPException(status_code=codigo, detail=mensaje) from exc
