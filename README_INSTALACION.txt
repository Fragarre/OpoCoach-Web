OpoCoach-Web / Materiales de estudio - FINAL

Objetivo
-------
Extender a OpoCoach-Web la funcionalidad validada en Streamlit:
- Resumen para estudiar
- Extracto para esta oposición
- Ley completa

Arquitectura
------------
1. Supabase / PostgreSQL contenidos.*
   - Se usa para convocatoria, temario, normas y artículos.
   - Extracto y Ley completa se generan desde estos datos.
   - NO se crea ninguna tabla nueva.
   - NO se modifica el proceso de publicación SQLite -> Supabase.

2. Backend
   - backend/app/materiales.py                   NUEVO
   - backend/app/pdf_materiales.py               NUEVO
   - backend/app/main.py                         SUSTITUIR por esta versión
   - backend/materiales/resumenes/               NUEVO (31 PDF + catálogo)
   - backend/scripts/verificar_materiales_supabase.py NUEVO

3. Frontend
   - frontend/app/page.tsx                       SUSTITUIR por esta versión

4. backend/app/database.py
   - Se incluye copia de la versión usada como base de esta integración.
   - Si el proyecto actual ya contiene la misma función
     conectar_contenidos_postgres(), no es necesario sustituirlo.

Orden de instalación recomendado
--------------------------------
A. Hacer backup/commit del estado Web actual.
B. Copiar los archivos respetando carpetas.
C. Desde backend:
       python -m scripts.verificar_materiales_supabase
   Resultado esperado:
       Resúmenes en catálogo: 31
       Normas activas sin resumen: 0
       RESULTADO: OK
D. Arrancar backend:
       uvicorn app.main:app --reload
E. Arrancar frontend como habitualmente.
F. Probar:
       Materiales -> Ley 40/2015 -> Resumen para estudiar
       Materiales -> Ley 40/2015 -> Extracto para esta oposición
       Materiales -> Ley 40/2015 -> Ley completa

Acceso
------
Materiales exige suscripción activa, igual que Chat.

No se modifica
--------------
- Auth
- Stripe
- usuarios
- suscripciones
- simulacros
- tests
- esquema de Supabase
- scripts de publicación de contenidos
