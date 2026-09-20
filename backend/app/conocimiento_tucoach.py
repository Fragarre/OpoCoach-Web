"""
==============================================================================
OpoCoach-Web
Archivo: app/conocimiento_opocoach.py
==============================================================================

Base de conocimiento interna sobre el funcionamiento de OpoCoach.

No accede a la base de datos y no modifica el corpus normativo.
==============================================================================
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EntradaConocimientoOpoCoach:
    clave: str
    titulo: str
    palabras_clave: tuple[str, ...]
    texto: str


ENTRADAS_CONOCIMIENTO_OPOCOACH: tuple[EntradaConocimientoOpoCoach, ...] = (
    EntradaConocimientoOpoCoach(
        clave="descripcion_general",
        titulo="Qué es OpoCoach y para qué sirve",
        palabras_clave=(
            "opocoach", "aplicacion", "funcionamiento", "para que sirve",
            "objetivo", "entrenamiento", "oposicion", "oposiciones",
        ),
        texto=(
            "OpoCoach es una aplicación de entrenamiento para oposiciones. "
            "Permite seleccionar una convocatoria, generar simulacros basados "
            "en su estructura y banco de preguntas, responderlos dentro de la "
            "aplicación o mediante un PDF, corregirlos y consultar resultados y "
            "explicaciones. Su finalidad es ayudar a practicar, detectar puntos "
            "fuertes y débiles y revisar los errores. No sustituye las bases de "
            "la convocatoria, la legislación vigente ni los materiales oficiales."
        ),
    ),
    EntradaConocimientoOpoCoach(
        clave="convocatoria_activa",
        titulo="Convocatoria activa",
        palabras_clave=(
            "convocatoria", "convocatoria activa", "seleccionar convocatoria",
            "cambiar convocatoria", "temario", "reglas puntuacion",
        ),
        texto=(
            "La convocatoria activa determina el ámbito de trabajo de OpoCoach. "
            "Cada convocatoria dispone de su propio temario, banco de preguntas, "
            "corpus documental, estructura del examen y reglas de puntuación. "
            "Al cambiar de convocatoria, el chat debe iniciar una conversación "
            "independiente para evitar mezclar contenidos de convocatorias distintas."
        ),
    ),
    EntradaConocimientoOpoCoach(
        clave="banco_preguntas",
        titulo="Banco de preguntas",
        palabras_clave=(
            "banco", "banco de preguntas", "preguntas disponibles",
            "origen preguntas", "preguntas oficiales", "repetir preguntas",
            "seleccion preguntas", "numero de preguntas disponibles",
        ),
        texto=(
            "Los simulacros se generan a partir del banco de preguntas asociado "
            "a la convocatoria activa. Las preguntas están clasificadas y "
            "vinculadas al temario correspondiente. La aplicación selecciona las "
            "preguntas necesarias para respetar la estructura configurada del "
            "simulacro. En la Web pública, los simulacros utilizan internamente "
            "todos los orígenes A1, A2, C1 y C2 y tanto preguntas reales/importadas "
            "como generadas por IA; esas opciones no se muestran al usuario."
        ),
    ),
    EntradaConocimientoOpoCoach(
        clave="generacion_simulacro",
        titulo="Generación de simulacros",
        palabras_clave=(
            "generar", "crear simulacro", "nuevo simulacro", "simulacro",
            "estructura examen", "bloques", "teoricas", "practicas",
            "informatica", "preguntas generales",
        ),
        texto=(
            "OpoCoach genera cada simulacro respetando la estructura definida "
            "para la convocatoria activa y el orden de sus bloques. La selección "
            "se realiza entre las preguntas válidas del banco para esa convocatoria. "
            "El simulacro queda guardado para poder realizarlo, descargarlo, "
            "corregirlo o consultar posteriormente sus resultados."
        ),
    ),
    EntradaConocimientoOpoCoach(
        clave="construccion_test",
        titulo="Construcción de tests",
        palabras_clave=(
            "test", "construir test", "crear test", "tema", "ley", "norma",
            "puntos temario", "numero preguntas",
        ),
        texto=(
            "Los tests permiten elegir el número de preguntas y construir la prueba "
            "por puntos del temario o por ley o norma. En la Web pública se utilizan "
            "internamente preguntas reales/importadas y generadas por IA, sin mostrar "
            "al usuario un selector de fuente ni los recuentos internos de disponibilidad."
        ),
    ),
    EntradaConocimientoOpoCoach(
        clave="realizacion_prueba",
        titulo="Cómo responder una prueba",
        palabras_clave=(
            "responder", "contestar", "respuesta", "a b c d", "sin contestar",
            "dejar en blanco", "realizar examen", "hacer simulacro", "hacer test",
        ),
        texto=(
            "En una prueba puede seleccionarse una respuesta A, B, C o D para cada "
            "pregunta. También es posible dejar una pregunta sin contestar. Una "
            "respuesta solo se considera contestada cuando se ha seleccionado una opción."
        ),
    ),
    EntradaConocimientoOpoCoach(
        clave="nivel_seguridad",
        titulo="Nivel de seguridad de una respuesta",
        palabras_clave=(
            "seguridad", "nivel de seguridad", "seguro", "menos seguro",
            "confianza", "grado de seguridad", "para que se usa",
        ),
        texto=(
            "La valoración de seguridad es opcional. Si se activa, cada pregunta "
            "contestada debe marcarse como Seguro o Menos seguro. Este dato no modifica "
            "directamente la nota; sirve para comparar el resultado real con la "
            "confianza del usuario y detectar errores cometidos con exceso de seguridad."
        ),
    ),
    EntradaConocimientoOpoCoach(
        clave="correccion_resultados",
        titulo="Corrección y resultados",
        palabras_clave=(
            "corregir", "correccion", "resultado", "resultados", "nota",
            "acertadas", "falladas", "no contestadas", "puntuacion",
            "estadisticas por tema", "estadisticas por ley",
        ),
        texto=(
            "La corrección compara las respuestas del usuario con las respuestas "
            "correctas guardadas en la prueba. El resultado muestra preguntas "
            "acertadas, falladas y no contestadas, y calcula la nota aplicando las "
            "reglas de puntuación de la convocatoria. También existen resultados "
            "acumulados por tema, ley o norma y nivel de seguridad."
        ),
    ),
    EntradaConocimientoOpoCoach(
        clave="modificar_respuestas",
        titulo="Modificar respuestas después de calificar",
        palabras_clave=(
            "modificar respuestas", "cambiar respuesta", "recalificar",
            "editar corregido", "volver a corregir",
        ),
        texto=(
            "Una prueba ya calificada puede volver a edición mediante Modificar "
            "respuestas. Se conservan las respuestas anteriores, pueden cambiarse y "
            "al volver a calificar se recalcula el resultado de esa misma prueba."
        ),
    ),
    EntradaConocimientoOpoCoach(
        clave="cronometro",
        titulo="Cronómetro de corrección",
        palabras_clave=(
            "cronometro", "tiempo", "tiempo empleado", "mostrar cronometro",
        ),
        texto=(
            "Cada simulacro o test mantiene su propio tiempo de corrección. El "
            "cronómetro puede mostrarse u ocultarse y el tiempo sigue contando aunque "
            "esté oculto. Al volver a modificar respuestas, el nuevo tramo se suma al "
            "tiempo ya empleado en esa misma prueba."
        ),
    ),
    EntradaConocimientoOpoCoach(
        clave="pdf_preguntas",
        titulo="PDF de preguntas",
        palabras_clave=(
            "pdf preguntas", "descargar preguntas", "imprimir examen",
            "hacer fuera aplicacion", "documento preguntas",
        ),
        texto=(
            "El PDF de preguntas permite realizar la prueba fuera de la aplicación "
            "o imprimirla. Puede descargarse sin necesidad de haber calificado la "
            "prueba. Las respuestas hechas en papel deben trasladarse a OpoCoach si "
            "se desea obtener la corrección y las estadísticas en la aplicación."
        ),
    ),
    EntradaConocimientoOpoCoach(
        clave="pdf_soluciones",
        titulo="PDF de soluciones",
        palabras_clave=(
            "pdf soluciones", "descargar soluciones", "comentario solucion",
            "explicacion respuesta", "soluciones", "respuesta correcta",
        ),
        texto=(
            "El PDF de soluciones puede descargarse aunque la prueba no haya sido "
            "calificada en la aplicación. Contiene las respuestas correctas y puede "
            "incluir comentarios explicativos. Los comentarios pendientes se generan "
            "bajo petición y se reutilizan posteriormente."
        ),
    ),
    EntradaConocimientoOpoCoach(
        clave="analisis_rendimiento",
        titulo="Análisis acumulado de rendimiento",
        palabras_clave=(
            "analisis rendimiento", "rendimiento acumulado", "puntos debiles",
            "fortalezas", "riesgos", "plan actuacion",
        ),
        texto=(
            "Tras corregir una prueba puede solicitarse un análisis de rendimiento. "
            "Utiliza la prueba actual y los resultados acumulados conservados del "
            "mismo tipo y convocatoria para señalar riesgos, estrategia y un plan "
            "de actuación."
        ),
    ),
    EntradaConocimientoOpoCoach(
        clave="chat_convocatoria",
        titulo="Chat de la convocatoria",
        palabras_clave=(
            "chat", "asistente", "preguntar", "que puede responder",
            "fuentes chat", "corpus", "conocimiento externo", "no responde",
            "limpiar conversacion",
        ),
        texto=(
            "En modo Convocatoria y OpoCoach, el chat responde únicamente con dos "
            "fuentes internas: el corpus asignado a la convocatoria activa y esta "
            "base de conocimiento sobre el funcionamiento de OpoCoach. Si las fuentes "
            "recuperadas no contienen información suficiente, debe decirlo. Existe "
            "también un modo separado de conocimiento general de GPT."
        ),
    ),
    EntradaConocimientoOpoCoach(
        clave="limites_uso",
        titulo="Alcance y limitaciones de OpoCoach",
        palabras_clave=(
            "limitaciones", "fiabilidad", "legislacion vigente", "oficial",
            "asesoramiento", "errores", "garantia", "sustituye", "actualizado",
        ),
        texto=(
            "OpoCoach es una herramienta de entrenamiento. Sus simulacros, "
            "explicaciones y estadísticas ayudan a estudiar, pero no sustituyen "
            "las bases oficiales, la legislación vigente ni los materiales "
            "publicados por la administración convocante. El chat no presta "
            "asesoramiento jurídico para casos reales."
        ),
    ),
)
