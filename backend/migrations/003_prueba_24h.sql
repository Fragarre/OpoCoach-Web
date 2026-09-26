BEGIN;

ALTER TABLE public.profiles
ADD COLUMN IF NOT EXISTS prueba_24h_inicio_at timestamptz,
ADD COLUMN IF NOT EXISTS prueba_24h_tests_usados integer NOT NULL DEFAULT 0,
ADD COLUMN IF NOT EXISTS prueba_24h_simulacros_usados integer NOT NULL DEFAULT 0,
ADD COLUMN IF NOT EXISTS prueba_24h_materiales_descargados integer NOT NULL DEFAULT 0;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'profiles_prueba_24h_tests_usados_check'
          AND conrelid = 'public.profiles'::regclass
    ) THEN
        ALTER TABLE public.profiles
        ADD CONSTRAINT profiles_prueba_24h_tests_usados_check
        CHECK (prueba_24h_tests_usados >= 0);
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'profiles_prueba_24h_simulacros_usados_check'
          AND conrelid = 'public.profiles'::regclass
    ) THEN
        ALTER TABLE public.profiles
        ADD CONSTRAINT profiles_prueba_24h_simulacros_usados_check
        CHECK (prueba_24h_simulacros_usados >= 0);
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'profiles_prueba_24h_materiales_descargados_check'
          AND conrelid = 'public.profiles'::regclass
    ) THEN
        ALTER TABLE public.profiles
        ADD CONSTRAINT profiles_prueba_24h_materiales_descargados_check
        CHECK (prueba_24h_materiales_descargados >= 0);
    END IF;
END
$$;

COMMIT;
