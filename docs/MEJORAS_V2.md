# Mejoras previstas para Tu Coach V2

Este documento recoge mejoras detectadas durante el desarrollo y mantenimiento de Tu Coach que no son necesarias para cerrar la versión actual, pero conviene conservar para una futura versión 2.

No constituye un plan de implementación inmediato. Cada punto deberá revisarse contra el estado real del proyecto antes de desarrollarlo.

## 1. Auditoría de simulacros contra el temario oficial

### Situación actual

El script `auditar_simulacros_temario_oficial.py` se creó como herramienta de control cuando, durante pruebas de simulacros de determinadas convocatorias, aparecieron preguntas que no pertenecían al temario correspondiente.

La auditoría sigue siendo útil como control de calidad esporádico, pero actualmente requiere introducir manualmente en cada ejecución:

- el PDF oficial del temario;
- el PDF del simulacro, o una carpeta de simulacros.

El script trabaja en solo lectura y genera informes de auditoría.

### Mejora propuesta para V2

Organizar los documentos de prueba por convocatoria, por ejemplo mediante una estructura del tipo:

`test_simulacros/<convocatoria>/`

La convocatoria debería permitir resolver de forma automática y segura el PDF oficial del temario. Los simulacros destinados a control podrían almacenarse o seleccionarse dentro de la carpeta correspondiente.

Como evolución posterior, esta auditoría podría integrarse en `/admin/mantenimiento` como una operación de control esporádico, con selección de convocatoria y simulacro sin introducir rutas arbitrarias.

### Criterios de diseño

- Mantener la auditoría como herramienta de control, no como parte obligatoria de la generación normal de simulacros.
- No modificar la base de datos durante la auditoría.
- Evitar rutas arbitrarias recibidas desde el navegador.
- Reutilizar `auditar_simulacros_temario_oficial.py` en lugar de duplicar su lógica.
- Identificar claramente en la interfaz que utiliza IA y puede generar coste.
- Mantener trazabilidad de los resultados mediante los informes de auditoría.

