# Tu Coach — arquitectura y nomenclatura

**Estado verificado:** 13/09/2026

## 1. Objetivo

Este documento aclara la correspondencia entre los nombres históricos `OpoCoach` y `NetReto` y el nombre actual del producto, **Tu Coach**.

Los nombres históricos son identificadores técnicos heredados. No implican que existan productos distintos y no deben renombrarse solo por motivos estéticos mientras los recursos actuales funcionen correctamente.

## 2. Regla de nomenclatura

- **Nombre del producto para el usuario:** Tu Coach.
- **Módulo de empleo:** Tu Coach · Empleo / Empleo público.
- `OpoCoach` y `NetReto` se consideran nombres técnicos heredados.
- No renombrar repositorios, servicios, bases de datos, variables, rutas o submódulos existentes sin analizar antes sus dependencias.
- Para recursos nuevos, preferir nombres basados en `tu-coach` y en la función del recurso, salvo que deban seguir una convención técnica ya existente.

## 3. Mapa actual

| Nombre técnico actual | Plataforma / ubicación | Función actual | Nombre funcional |
| --- | --- | --- | --- |
| `Fragarre/OpoCoach-Web` | GitHub | Repositorio principal: frontend y backend de la aplicación | Tu Coach |
| `Fragarre/NetReto-Web-Empleo` | GitHub | Código específico del módulo de Empleo | Tu Coach · Empleo |
| `backend/employment_service` | Submódulo dentro de `OpoCoach-Web` | Integra el backend de Empleo en el backend principal | Servicio Empleo |
| `opocoach-web-staging-backend` | Render | Único servicio web backend activo; sirve Tu Coach e integra las rutas de Empleo | Backend Tu Coach |
| `netreto-empleo-periodic` | Render | Cron activo que ejecuta periódicamente la actualización de Empleo | Actualizador Empleo |
| `opocoach-web-test` (`fgvnzgyrejobubccikfn`) | Supabase | Base de datos principal: aplicación, usuarios y datos principales | BD Tu Coach |
| `netreto-empleo` (`deuhjpnonwulntnryczd`) | Supabase | Base de datos separada del módulo Empleo: procesos, publicaciones, cambios, seguimiento, etc. | BD Empleo |

## 4. Render: recursos que deben existir

Actualmente hay **dos recursos activos** y ambos son necesarios:

### `opocoach-web-staging-backend`

- Tipo: Web Service.
- Repositorio: `Fragarre/OpoCoach-Web`.
- Rama: `main`.
- Directorio raíz: `backend`.
- Región: Frankfurt.
- Inicio: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`.
- Integra el backend general y el backend de Empleo.

### `netreto-empleo-periodic`

- Tipo: Cron Job.
- Repositorio: `Fragarre/NetReto-Web-Empleo`.
- Rama: `main`.
- Directorio raíz: `backend`.
- Programación: `0 17 * * *` (17:00 UTC diariamente).
- Comando: `python scripts/run_periodic_http.py --aplicar --dias 7`.
- Su función es lanzar la actualización periódica de Empleo contra el backend unificado.

**Importante:** `netreto-empleo-periodic` no es un backend antiguo ni un recurso sobrante. No debe eliminarse mientras se mantenga esta arquitectura de actualización automática.

## 5. Recurso antiguo ya eliminado

`netreto-empleo-api` era el antiguo servicio web independiente del módulo Empleo. Se consolidó su función en `opocoach-web-staging-backend` y posteriormente se eliminó de Render.

No debe confundirse `netreto-empleo-api` (eliminado) con `netreto-empleo-periodic` (activo y necesario).

## 6. Bases de datos Supabase

Se mantienen deliberadamente dos bases de datos separadas:

### Principal — `opocoach-web-test`

Project ref: `fgvnzgyrejobubccikfn`.

Es la base principal de Tu Coach. El backend principal accede a ella mediante su conexión principal (`DATABASE_URL`).

### Empleo — `netreto-empleo`

Project ref: `deuhjpnonwulntnryczd`.

Contiene el dominio específico de Empleo. El backend unificado accede a ella mediante una conexión independiente (`EMPLOYMENT_DATABASE_URL`).

**No intercambiar estas dos conexiones.** El backend necesita ambas y cada una apunta a un esquema funcional diferente.

## 7. Relación entre los repositorios

`OpoCoach-Web` es el repositorio principal desplegable. El código específico del backend de Empleo se conserva en `NetReto-Web-Empleo` y se incorpora al repositorio principal mediante el submódulo:

`backend/employment_service`

Por tanto, un cambio del backend de Empleo puede requerir dos pasos:

1. commit del cambio en `NetReto-Web-Empleo`;
2. actualización del puntero del submódulo en `OpoCoach-Web` para que el backend principal despliegue esa versión.

No asumir que un commit en `NetReto-Web-Empleo` actualiza automáticamente la versión integrada en `OpoCoach-Web`.

## 8. Despliegues

### Frontend

El frontend Next.js de `OpoCoach-Web` se despliega mediante Vercel a partir del repositorio principal.

### Backend

El backend se despliega en Render mediante `opocoach-web-staging-backend`, con auto-deploy desde `main`.

### Actualización periódica de Empleo

El cron `netreto-empleo-periodic` se mantiene separado del servicio web y ejecuta diariamente el proceso de actualización.

## 9. Qué no hacer sin una revisión previa

Antes de cualquier limpieza de nombres, no realizar directamente ninguna de estas operaciones:

- renombrar `OpoCoach-Web`;
- renombrar o eliminar `NetReto-Web-Empleo`;
- eliminar `backend/employment_service`;
- eliminar `netreto-empleo-periodic`;
- cambiar `DATABASE_URL` por `EMPLOYMENT_DATABASE_URL` o viceversa;
- fusionar las dos bases Supabase;
- cambiar nombres de servicios Render o proyectos Supabase suponiendo que el nombre es solo decorativo;
- modificar rutas o variables de entorno para sustituir `opocoach`/`netreto` sin buscar primero todas sus referencias.

## 10. Criterio para el futuro

La prioridad es **estabilidad antes que uniformidad nominal**. Los nombres heredados pueden mantenerse indefinidamente si están documentados y no generan una limitación técnica.

Si en el futuro se decide unificar la nomenclatura, debe tratarse como una migración independiente: inventario de dependencias, cambios uno a uno, pruebas y posibilidad de reversión.

Mientras tanto, toda documentación y toda interfaz dirigida al usuario debe utilizar **Tu Coach**; los nombres `OpoCoach` y `NetReto` quedan reservados para identificar componentes técnicos heredados.