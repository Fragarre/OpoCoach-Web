-- TuCoach-Web
-- Migración 006: infraestructura de trabajos administrativos y agentes locales.
--
-- Esta migración crea únicamente la cola/auditoría. No ejecuta procesos,
-- no modifica contenidos y no concede acceso directo a usuarios autenticados.

BEGIN;

CREATE TABLE IF NOT EXISTS public.admin_agents (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    nombre text NOT NULL UNIQUE,
    activo boolean NOT NULL DEFAULT true,
    ultimo_heartbeat_at timestamptz,
    version text,
    metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.admin_jobs (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tipo text NOT NULL,
    estado text NOT NULL DEFAULT 'PENDIENTE'
        CHECK (estado IN (
            'PENDIENTE',
            'RECOGIDO',
            'EJECUTANDO',
            'ESPERANDO_CONFIRMACION',
            'COMPLETADO',
            'ERROR',
            'INTERRUMPIDO'
        )),
    parametros jsonb NOT NULL DEFAULT '{}'::jsonb,
    solicitado_por uuid NOT NULL REFERENCES public.profiles(id),
    agente_id uuid REFERENCES public.admin_agents(id),
    requiere_confirmacion boolean NOT NULL DEFAULT false,
    confirmado_por uuid REFERENCES public.profiles(id),
    confirmado_at timestamptz,
    resultado jsonb,
    error_texto text,
    creado_at timestamptz NOT NULL DEFAULT now(),
    recogido_at timestamptz,
    iniciado_at timestamptz,
    finalizado_at timestamptz,
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_admin_jobs_estado_creado
    ON public.admin_jobs (estado, creado_at);

CREATE INDEX IF NOT EXISTS idx_admin_jobs_agente_estado
    ON public.admin_jobs (agente_id, estado);

CREATE TABLE IF NOT EXISTS public.admin_job_events (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    job_id uuid NOT NULL REFERENCES public.admin_jobs(id) ON DELETE CASCADE,
    evento text NOT NULL,
    actor_tipo text NOT NULL CHECK (actor_tipo IN ('USUARIO', 'AGENTE', 'SISTEMA')),
    actor_usuario_id uuid REFERENCES public.profiles(id),
    agente_id uuid REFERENCES public.admin_agents(id),
    detalle jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_admin_job_events_job
    ON public.admin_job_events (job_id, id);

ALTER TABLE public.admin_agents ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.admin_jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.admin_job_events ENABLE ROW LEVEL SECURITY;

-- Sin políticas para anon/authenticated. El acceso se realizará exclusivamente
-- mediante endpoints backend protegidos y, para agentes, credenciales de máquina.

COMMIT;
