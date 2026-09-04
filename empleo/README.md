# NetReto — Módulo de Empleo Público

Módulo independiente para seguimiento de convocatorias de empleo público en la Comunitat Valenciana.

## Principios

- No modifica la base de datos actual de NetReto.
- No modifica `frontend/proxy.ts` ni el mecanismo actual de protección del sitio.
- Identidad de usuario mediante el mismo Supabase que NetReto.
- Acceso funcional inicialmente reservado a usuarios autenticados con suscripción activa.
- Preparado para evolucionar a una capacidad independiente (`employment_access`) sin acoplarla a un precio concreto.
- Las fuentes oficiales son la autoridad de los datos; la IA, si se incorpora, sólo ayuda a clasificar/normalizar.

## Modelo inicial

`organismos -> procesos -> publicaciones -> cambios`

Los usuarios se relacionan con los procesos mediante `suscripciones` y las notificaciones se generan a partir de cambios significativos.

## Alcance temporal

La interfaz debe priorizar procesos vigentes, abiertos o previsibles del año actual y del siguiente. No se debe confundir el año de una OEP con el año de publicación de una convocatoria.

## Estado de esta fase

Sólo se crea la estructura y el modelo de datos. Todavía no se conecta con la navegación de NetReto ni se publica ninguna ruta nueva en producción.
