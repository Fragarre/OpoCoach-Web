-- OpoCoach-Web
-- Migración 003: fecha explícita de cancelación programada Stripe.
--
-- Stripe Customer Portal puede programar la baja mediante cancel_at
-- manteniendo cancel_at_period_end = false.
-- El acceso seguirá dependiendo del status real de la suscripción.

BEGIN;

ALTER TABLE public.subscriptions
ADD COLUMN IF NOT EXISTS cancel_at timestamptz;

COMMIT;
