from pydantic import BaseModel, Field


class Convocatoria(BaseModel):
    id: int
    puesto: str
    numero: str
    anio: int
    codigo: str


class ResumenConvocatoria(BaseModel):
    id: int
    codigo: str
    puesto: str
    numero: str
    anio: int
    numero_preguntas: int
    temario_id: int | None
    temario_nombre: str | None
    total_temas: int
    total_banco: int


class EstadoBase(BaseModel):
    integridad: str
    convocatorias: int
    preguntas: int


class DisponibilidadParte(BaseModel):
    parte_id: int
    parte: str
    parte_orden: int
    necesarias: int
    disponibles: int


class CrearSimulacroRequest(BaseModel):
    convocatoria_id: int
    origenes: list[str] = Field(min_length=1)
    fuentes: list[str] = Field(default_factory=lambda: ["REAL", "IA"], min_length=1)


class SimulacroCreado(BaseModel):
    id: int


class Simulacro(BaseModel):
    id: int
    convocatoria_id: int
    numero: int
    fecha_generacion: str
    total_preguntas: int
    estado: str
    tipo_prueba: str
    es_prueba_gratuita: bool = False
    convocatoria_codigo: str | None
    convocatoria_puesto: str | None
    convocatoria_numero: str | None
    convocatoria_anio: int | None


class PreguntaSimulacro(BaseModel):
    simulacro_pregunta_id: int
    orden: int
    parte_nombre: str | None
    respuesta_usuario: str | None
    seguridad_usuario: str | None
    enunciado: str
    opcion_a: str
    opcion_b: str
    opcion_c: str
    opcion_d: str

class RespuestaPregunta(BaseModel):
    simulacro_pregunta_id: int
    respuesta: str | None = None
    seguridad: str | None = None


class GuardarRespuestasRequest(BaseModel):
    respuestas: list[RespuestaPregunta]


class ResultadoSimulacro(BaseModel):
    simulacro_id: int
    total: int
    contestadas: int
    aciertos: int
    fallos: int
    no_contestadas: int
    puntos: float
    nota: float
    tiempo_correccion_segundos: int = 0


class PreguntaCorregida(PreguntaSimulacro):
    respuesta_correcta: str
    resultado: str


class UsuarioActual(BaseModel):
    id: str
    email: str


class SimulacroListado(BaseModel):
    id: int
    convocatoria_id: int
    numero: int
    fecha_generacion: str
    total_preguntas: int
    estado: str
    tipo_prueba: str
    es_prueba_gratuita: bool = False
    convocatoria_codigo: str | None
    contestadas: int


class TemaTest(BaseModel):
    id: int
    parte: str
    numero_tema: int
    titulo: str
    tipo_contenido: str | None
    disponibles: int


class NormaTest(BaseModel):
    norma_clave: str
    norma_nombre: str
    disponibles: int


class CrearTestRequest(BaseModel):
    convocatoria_id: int
    numero_preguntas: int = Field(gt=0)
    modo_seleccion: str
    temas_seleccionados: list[int] = Field(default_factory=list)
    normas_seleccionadas: list[str] = Field(default_factory=list)
    fuentes: list[str] = Field(default_factory=lambda: ["REAL", "IA"], min_length=1)


class TestCreado(BaseModel):
    id: int
    numero: int
    total_solicitado: int
    total_generado: int
    avisos: list[str]



class CheckoutSessionResponse(BaseModel):
    id: str
    url: str



class EstadoSuscripcion(BaseModel):
    suscrito: bool
    status: str
    customer_id: str | None
    subscription_id: str | None
    plan: str | None
    current_period_end: str | None
    cancel_at_period_end: bool
    ended_at: str | None = None
    prueba_gratuita_disponible: bool = True
    prueba_gratuita_consumida_at: str | None = None
