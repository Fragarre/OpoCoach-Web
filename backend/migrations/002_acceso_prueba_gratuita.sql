-- OpoCoach-Web
-- Migración 002: prueba gratuita y preparación del acceso histórico tras baja.
--
-- Decisiones:
--   * una sola prueba gratuita por cuenta;
--   * máximo 10 preguntas;
--   * la prueba gratuita conserva la funcionalidad completa;
--   * el consumo persiste aunque el usuario elimine la prueba;
--   * ended_at prepara un futuro plazo configurable de acceso histórico.
--
-- Esta migración NO clasifica retroactivamente tests existentes como gratuitos.

BEGIN;

ALTER TABLE public.profiles
ADD COLUMN IF NOT EXISTS prueba_gratuita_consumida_at timestamptz;

ALTER TABLE public.subscriptions
ADD COLUMN IF NOT EXISTS ended_at timestamptz;

ALTER TABLE public.simulacros
ADD COLUMN IF NOT EXISTS es_prueba_gratuita boolean NOT NULL DEFAULT false;

CREATE UNIQUE INDEX IF NOT EXISTS uq_simulacros_prueba_gratuita_usuario
ON public.simulacros(user_id)
WHERE es_prueba_gratuita = true;

COMMIT;
