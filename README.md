# OpoCoach-Web

Migración paralela de OpoCoach. No modifica la aplicación Streamlit ni
OpoCoach-Mantenimiento.

## Arquitectura actual

- `backend/data/oposiciones.sqlite3`: contenidos y bancos, SQLite solo lectura.
- Supabase PostgreSQL: usuarios, suscripciones y simulacros.
- Supabase Auth: autenticación.
- FastAPI: backend.

Los endpoints de simulacros ya no utilizan `DEV_USER_EMAIL`. Exigen un
`Authorization: Bearer <access_token>` válido de Supabase Auth.

## Configuración local

En `backend/.env`:

Arranque:  uvicorn app.main:app --reload --env-file .env

```env
DATABASE_URL=postgresql://...
SUPABASE_URL=https://TU_PROJECT_REF.supabase.co
SUPABASE_PUBLISHABLE_KEY=TU_CLAVE_PUBLICA
```

`SUPABASE_PUBLISHABLE_KEY` es una clave pública; la contraseña de PostgreSQL
sigue estando únicamente dentro de `DATABASE_URL`. No compartas ni subas
`backend/.env`.

## Prueba de autenticación

Desde `OpoCoach-Web/backend`:

```powershell
python -m scripts.test_auth
```

El script pide localmente el email y la contraseña del usuario de Supabase
Auth. La contraseña no se guarda.

Resultado esperado:

```text
Autenticación Supabase: OK
user_id: ...
email: ...
Token validado y perfil OpoCoach activo: OK
```

## Prueba del ciclo completo con usuario autenticado

```powershell
python -m scripts.test_simulacro_postgres
```

Crea un simulacro temporal, guarda dos respuestas, corrige y elimina el
simulacro al terminar.

## API

```powershell
uvicorn app.main:app --reload
```

Documentación:

`http://127.0.0.1:8000/docs`

Los endpoints de usuario muestran el candado de autenticación Bearer.
`GET /api/v1/me` permite comprobar qué usuario corresponde al token.

## Siguiente paso

Crear un segundo usuario y comprobar que no puede consultar, modificar ni
corregir simulacros pertenecientes al primero.


## Prueba de aislamiento entre dos usuarios

Crea previamente dos usuarios distintos en Supabase Authentication. Después:

```powershell
cd backend
python -m scripts.test_aislamiento_usuarios
```

El script solicita las credenciales de ambos usuarios localmente y no las guarda.

El usuario A crea un simulacro temporal. El usuario B intenta leerlo, obtener sus
preguntas, guardar una respuesta, finalizarlo y consultar su corrección. Los
cinco intentos deben devolver HTTP 404. El simulacro temporal se elimina al
finalizar la prueba.


## Frontend - primera fase

Se añade `frontend/` con Next.js App Router.

Funciones disponibles en esta primera entrega:

- login mediante Supabase Auth;
- identificación del usuario mediante `GET /api/v1/me`;
- listado de convocatorias;
- selección de orígenes y fuentes;
- creación de un simulacro;
- visualización de las preguntas, sin exponer la respuesta correcta.

El frontend no llama directamente a FastAPI desde el navegador. Utiliza el
Route Handler `frontend/app/api/backend/[...path]/route.ts`, que reenvía las
peticiones al backend. De este modo no es necesario modificar CORS en FastAPI.

### Configuración

Copia:

`frontend/.env.local.example`

como:

`frontend/.env.local`

y rellena:

```env
NEXT_PUBLIC_SUPABASE_URL=https://TU_PROJECT_REF.supabase.co
NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY=TU_CLAVE_PUBLICA
BACKEND_URL=http://127.0.0.1:8000
```

### Ejecución local

Terminal 1:

```powershell
cd OpoCoach-Web\backend
uvicorn app.main:app --reload
```

Terminal 2:

```powershell
cd OpoCoach-Web\frontend
npm install
npm run dev
```

Navega a:

`http://localhost:3000`

Usa uno de los usuarios creados en Supabase Authentication.


## Frontend - segunda fase

Se añade el circuito de realización y corrección:

- selección A/B/C/D;
- nivel de seguridad obligatorio si se contesta;
- dejar una pregunta en blanco;
- guardar respuestas sin finalizar;
- guardar y calificar;
- resultado con nota, aciertos, fallos y no contestadas;
- corrección pregunta por pregunta;
- desplazamiento al inicio al calificar.

La respuesta correcta solo se solicita al backend después de que el simulacro
haya quedado en estado FINALIZADO.


## Mis simulacros

Se incorpora el ciclo persistente de simulacros:

- listado de simulacros del usuario autenticado;
- estado Pendiente/Corregido;
- número, fecha, convocatoria, preguntas y contestadas;
- continuar un simulacro pendiente conservando sus respuestas;
- volver a abrir la corrección de un simulacro finalizado;
- eliminación con confirmación;
- aislamiento por `user_id` en todas las operaciones.

Los PDF y el análisis acumulado siguen pendientes y se incorporarán en fases
posteriores.


## Tests

Se incorpora la construcción y gestión de tests de la versión Streamlit:

- selección de convocatoria;
- número de preguntas;
- preguntas reales/importadas, IA o ambas;
- selección por puntos del temario o por ley/norma;
- disponibilidad mostrada por cada elemento;
- reparto proporcional por disponibilidad;
- protección frente a repetición reciente de preguntas;
- generación del máximo disponible si no se alcanza el número solicitado;
- Mis tests: continuar, ver corrección y eliminar;
- realización, seguridad, guardado y corrección compartidos con simulacros;
- la nota de un TEST se divide por el número real de preguntas del test.


## Stripe Checkout - sandbox

Primera fase de la pasarela de pago:

- usuario autenticado;
- creación server-side de Checkout Session;
- `mode=subscription`;
- Price ID configurado en `backend/.env`;
- redirección al Checkout alojado de Stripe;
- retorno a OpoCoach por éxito o cancelación.

Variables:

```env
STRIPE_SECRET_KEY=sk_test_...
STRIPE_PRICE_ID=price_...
FRONTEND_URL=http://localhost:3000
```

En esta fase un retorno `checkout=success` NO activa todavía la suscripción.
La activación se implementará mediante webhook Stripe firmado.


## Stripe webhook - sandbox local

El webhook se verifica con `Stripe-Signature` y `STRIPE_WEBHOOK_SECRET`.
Eventos tratados:

- `checkout.session.completed`
- `customer.subscription.created`
- `customer.subscription.updated`
- `customer.subscription.deleted`

Los datos se sincronizan con `public.subscriptions`.

Instalación Stripe CLI:

```powershell
npm install --global @stripe/cli
stripe login
```

Escucha local:

```powershell
stripe listen --events checkout.session.completed,customer.subscription.created,customer.subscription.updated,customer.subscription.deleted --forward-to http://127.0.0.1:8000/api/v1/billing/webhook
```

La salida muestra un secreto `whsec_...`. Copiarlo a:

```env
STRIPE_WEBHOOK_SECRET=whsec_...
```

y reiniciar Uvicorn antes de repetir el Checkout.
uvicorn app.main:app --reload

Modificar/importar/auditar contenidos en Mantenimiento
                    ↓
6. ADMINISTRACIÓN
                    ↓
2. Preparar publicación OpoCoach-Web
                    ↓
4. Actualizar contenidos Web en Supabase
