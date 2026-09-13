# Tu Coach — Protocolo de pruebas reales de Empleo

**Inicio previsto:** septiembre de 2026  
**Duración mínima recomendada:** 5–7 días naturales  
**Objeto:** validar el comportamiento real de descubrimiento, inscripción, seguimiento, novedades y ciclo de vida de las convocatorias de Empleo sin introducir datos artificiales.

## 1. Principio de la prueba

Durante este periodo no se evaluará únicamente que la interfaz funcione. Se comprobará que Tu Coach representa correctamente lo que sucede en las fuentes oficiales y que los procesos automáticos diarios no producen duplicados, pérdidas de información ni falsas novedades.

Las pruebas se harán preferentemente con procesos reales de tres ámbitos:

- Generalitat Valenciana (GVA).
- Diputación de Valencia.
- Ayuntamientos de la provincia de Valencia.

Cuando exista una bolsa GVA adecuada, se incluirá también para comprobar su seguimiento específico.

## 2. Reglas durante el periodo

1. No corregir manualmente en la base de datos una incidencia detectada antes de registrarla.
2. No crear convocatorias artificiales para forzar resultados.
3. Conservar capturas cuando haya un comportamiento dudoso o incorrecto.
4. Contrastar siempre con la publicación o página oficial correspondiente.
5. Anotar la hora cuando sea relevante, especialmente en altas de seguimiento y novedades del mismo día.
6. Una incidencia no implica modificar inmediatamente el código: primero se registra y se determina si es reproducible.

## 3. Preparación — Día 0

Antes de comenzar:

- Comprobar que la aplicación carga normalmente.
- Comprobar las vistas GVA, Diputación y Ayuntamientos.
- Probar `Todas | Inscripción abierta` en los tres niveles previstos.
- Confirmar que dentro de un ayuntamiento concreto no aparece ese selector.
- Abrir al menos una convocatoria de cada ámbito y comprobar que el enlace oficial es válido.
- Anotar fecha y hora exactas de inicio de la prueba.

Para la prueba de seguimiento, seleccionar preferentemente:

- una oposición ordinaria GVA activa;
- una bolsa GVA activa, si existe una adecuada;
- una convocatoria de Diputación activa;
- una convocatoria municipal activa.

Antes de seguirlas, anotar qué publicaciones e información muestra cada una. Después pulsar `Seguir` y anotar la hora exacta.

**Resultado esperado:** `Mi seguimiento` contiene los procesos seleccionados, pero publicaciones históricas anteriores al alta no deben aparecer como novedades nuevas.

## 4. Prueba de inscripción

Comprobar diariamente alguna convocatoria con inscripción abierta y, cuando sea posible, otra cerrada o pendiente de apertura.

Debe verificarse:

- que `Inscripción abierta hasta DD/MM/AAAA` coincide con la fuente oficial cuando existe fecha calculable;
- que el filtro `Inscripción abierta` muestra únicamente oportunidades cuyo plazo está realmente abierto;
- que un ayuntamiento desaparece del listado filtrado si no tiene ninguna convocatoria abierta;
- que al entrar en un ayuntamiento se muestran todas sus convocatorias, no solamente las abiertas;
- que cerrar el plazo de inscripción no convierte el proceso selectivo en `FINALIZADO`.

Cuando el plazo oficial esté expresado en días hábiles, comprobar el cálculo contra BOE/BOP y calendario aplicable. Si no existe información suficiente para calcularlo con seguridad, es preferible mostrar el literal o un estado no determinado que inventar una fecha.

## 5. Prueba diaria del actualizador

El cron `netreto-empleo-periodic` está programado diariamente a las **17:00 UTC**.

Después de cada ejecución —dejando un margen razonable para que termine— comprobar:

- que la aplicación sigue funcionando;
- que no aparecen convocatorias duplicadas;
- si se han descubierto nuevas oportunidades;
- si han aparecido nuevas publicaciones de procesos ya existentes;
- si `Mi seguimiento` refleja las novedades de los procesos seguidos;
- si los enlaces oficiales continúan apuntando al documento o página adecuada;
- si algún estado ha cambiado y el cambio está justificado por una publicación oficial.

No es necesario que todos los días existan novedades. Cero novedades es un resultado válido si coincide con las fuentes oficiales.

## 6. Descubrimiento de nuevas convocatorias

Cuando aparezca una convocatoria nueva durante el periodo:

1. Identificar la fuente oficial en BOE, DOGV/GVA o BOP Valencia.
2. Comprobar si Tu Coach la ha descubierto.
3. Verificar organismo, denominación, número de plazas, tipo de proceso y datos de inscripción.
4. Abrir el enlace oficial desde Tu Coach.
5. Comprobar que no existe una segunda ficha que represente el mismo proceso.

Para ayuntamientos es especialmente importante observar si aparece algún municipio que todavía no figuraba en el catálogo. El descubrimiento debe poder incorporarlo dinámicamente sin necesitar una lista manual previa.

En procesos municipales con bases en BOP y posterior convocatoria en BOE, comprobar que ambas publicaciones quedan asociadas al mismo proceso y no generan dos convocatorias independientes.

## 7. Seguimiento y novedades

Para cada proceso seguido, comprobar diariamente `Mi seguimiento`.

Una publicación posterior al momento en que se comenzó a seguir el proceso debe aparecer como novedad una sola vez y enlazar con su fuente oficial.

No deben aparecer como nuevas:

- publicaciones anteriores al alta en seguimiento;
- la misma publicación repetida en ejecuciones sucesivas;
- cambios técnicos internos sin significado para el opositor.

### Caso especialmente importante: alta y publicación el mismo día

Existe un caso que debe observarse expresamente durante estas pruebas:

1. comenzar a seguir un proceso a una hora conocida;
2. el mismo día, una publicación oficial posterior es detectada por el sistema;
3. comprobar si aparece correctamente como novedad.

Registrar siempre:

- hora de alta en seguimiento;
- fecha/hora conocida de detección;
- fecha oficial de la publicación;
- si apareció o no como `NUEVA`.

Este caso permitirá validar si la comparación temporal actual distingue correctamente una publicación detectada después de comenzar el seguimiento aunque ambas acciones ocurran el mismo día.

## 8. Dejar de seguir y volver a seguir

Realizar esta prueba con un proceso no crítico:

1. seguir el proceso;
2. comprobar `Mi seguimiento`;
3. dejar de seguirlo;
4. comprobar que desaparece de la vista activa de seguimiento;
5. volver a seguirlo y anotar la nueva hora.

**Resultado esperado:** al volver a seguirlo no deben reaparecer como novedades todas las publicaciones históricas anteriores a la nueva alta.

## 9. Ciclo de vida y finalización

No debe confundirse inscripción cerrada con proceso finalizado.

Un proceso ordinario solo debe pasar a terminal cuando una publicación oficial sea inequívoca: nombramiento, adjudicación definitiva, toma de posesión, finalización explícita, desistimiento o anulación, según proceda.

En una bolsa, la constitución o aprobación definitiva de la bolsa puede ser terminal, además de desistimiento o anulación.

No deben finalizar por sí solos un proceso:

- listas de admitidos/excluidos;
- tribunal;
- fecha de examen;
- notas;
- resultados provisionales;
- actuaciones parciales.

Si durante el periodo se produce una finalización real:

- debe desaparecer del catálogo de procesos activos;
- si el usuario lo seguía, debe conservarse en `Mi seguimiento` como histórico;
- la publicación terminal debe quedar registrada;
- no debe volver a activarse en la siguiente ejecución automática sin causa oficial.

Si no se produce ninguna finalización real durante los días de prueba, esta prueba queda pendiente de evidencia natural y no debe forzarse.

## 10. Navegación y persistencia

Al menos una vez durante el periodo:

- hacer F5 en Inicio;
- hacer F5 en Empleo;
- hacer F5 en `Mi seguimiento`;
- navegar Inicio → Empleo → detalle → Mi seguimiento → Inicio;
- cerrar sesión y volver a entrar.

Comprobar que identidad, suscripción y seguimiento se mantienen correctamente y que no aparecen valores provisionales falsos en la cabecera.

## 11. Administración manual

**No realizar todavía pruebas de producción creando procesos manuales.**

El módulo administrativo tiene aspectos pendientes de diseño relativos a fuente oficial, identidad/deduplicación y relación entre revisión/publicación. Se probará en una fase específica después de cerrar las pruebas automáticas reales.

## 12. Registro de evidencias

Usar una fila por comprobación o incidencia:

| Fecha/hora | Proceso | Acción / hecho | Esperado | Resultado real | Fuente oficial | Evidencia | Estado | Notas |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| | | | | | | | OK / ERROR / PENDIENTE | |

Para una incidencia, conservar además el ID del proceso si está disponible y una captura de pantalla.

## 13. Criterios para considerar superada la prueba

Al terminar el periodo, el bloque de pruebas reales podrá darse por satisfactorio si:

- las nuevas convocatorias relevantes se descubren sin duplicados significativos;
- los datos esenciales coinciden con las fuentes oficiales;
- los enlaces oficiales son correctos;
- los plazos de inscripción se representan correctamente;
- seguimiento y dejar de seguir son estables;
- las novedades posteriores al seguimiento aparecen una sola vez;
- no se presentan publicaciones históricas como novedades nuevas;
- los estados terminales solo se aplican con evidencia oficial suficiente;
- los procesos finalizados seguidos conservan su continuidad histórica;
- las ejecuciones periódicas son idempotentes;
- no aparecen errores funcionales después de las actualizaciones automáticas.

Las pruebas que dependan de un acontecimiento que no se produzca durante el periodo (por ejemplo, una finalización oficial) se marcarán como **PENDIENTES DE EVIDENCIA REAL**, no como fallidas.

## 14. Resultado final

Al finalizar los 5–7 días se elaborará un resumen con:

- pruebas superadas;
- incidencias confirmadas;
- incidencias no reproducibles;
- pruebas pendientes de evidencia real;
- correcciones necesarias antes de considerar estable el módulo Empleo.

Durante este periodo la prioridad es observar el comportamiento real. No se ampliará funcionalidad salvo que una incidencia impida continuar las pruebas.