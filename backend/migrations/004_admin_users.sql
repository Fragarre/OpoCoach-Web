-- TuCoach-Web
-- Migración 004: autorización administrativa.
--
-- La pertenencia a /admin se mantiene separada de public.profiles para que
-- un usuario no pueda concederse privilegios mediante la política que le
-- permite actualizar su propio perfil.

BEGIN;

CREATE TABLE IF NOT EXISTS public.admin_users (
    user_id uuid PRIMARY KEY REFERENCES public.profiles(id) ON DELETE CASCADE,
    activo boolean NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE public.admin_users ENABLE ROW LEVEL SECURITY;

-- No se crea ninguna política para usuarios autenticados.
-- La autorización administrativa se consulta exclusivamente desde el backend
-- mediante su conexión PostgreSQL de confianza.

COMMIT;
