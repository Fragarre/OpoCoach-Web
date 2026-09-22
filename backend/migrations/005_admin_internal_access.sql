-- TuCoach-Web
-- Migración 005: acceso interno permanente independiente de Stripe.
--
-- Este permiso se mantiene en admin_users, fuera de profiles, para impedir
-- que un usuario pueda concedérselo mediante la edición de su propio perfil.

BEGIN;

ALTER TABLE public.admin_users
ADD COLUMN IF NOT EXISTS acceso_total boolean NOT NULL DEFAULT false;

COMMIT;
