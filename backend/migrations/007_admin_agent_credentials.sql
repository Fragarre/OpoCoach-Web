-- TuCoach-Web
-- Migración 007: credencial del agente local.
--
-- Solo se almacena el hash SHA-256 de la credencial. El secreto original
-- se entrega/configura fuera de la base de datos y nunca se persiste en claro.

BEGIN;

ALTER TABLE public.admin_agents
ADD COLUMN IF NOT EXISTS token_hash text;

CREATE UNIQUE INDEX IF NOT EXISTS uq_admin_agents_token_hash
    ON public.admin_agents (token_hash)
    WHERE token_hash IS NOT NULL;

COMMIT;
