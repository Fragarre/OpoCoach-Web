from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

import stripe
from psycopg.rows import dict_row

from app.billing import (
    obtener_stripe_secret_key,
    obtener_stripe_webhook_secret,
)
from app.postgres import conectar_postgres


ESTADOS_CON_ACCESO = {"active", "trialing"}


def _id_stripe(valor) -> str | None:
    if valor is None:
        return None
    if isinstance(valor, str):
        return valor
    return str(getattr(valor, "id", "") or "") or None


def _timestamp_fin_periodo(suscripcion) -> datetime | None:
    """
    Compatibilidad con versiones recientes de Stripe:
    primero intenta el campo de la suscripción y, si no existe,
    usa el periodo del primer subscription item.
    """
    valor = getattr(suscripcion, "current_period_end", None)

    if valor is None:
        items = getattr(suscripcion, "items", None)
        datos = getattr(items, "data", None) if items is not None else None
        if datos:
            valor = getattr(datos[0], "current_period_end", None)

    if valor is None:
        return None

    return datetime.fromtimestamp(int(valor), tz=timezone.utc)


def _user_id_desde_metadata(objeto) -> UUID | None:
    metadata = getattr(objeto, "metadata", None) or {}
    valor = metadata.get("opocoach_user_id")
    if not valor:
        return None
    try:
        return UUID(str(valor))
    except (TypeError, ValueError):
        return None


def _user_id_desde_subscription_id(subscription_id: str) -> UUID | None:
    with conectar_postgres() as con:
        with con.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT user_id
                FROM public.subscriptions
                WHERE subscription_id = %s
                LIMIT 1
                """,
                (subscription_id,),
            )
            fila = cur.fetchone()
    return fila["user_id"] if fila else None


def _guardar_suscripcion(
    user_id: UUID,
    suscripcion,
) -> None:
    subscription_id = _id_stripe(suscripcion)
    customer_id = _id_stripe(getattr(suscripcion, "customer", None))
    status = str(getattr(suscripcion, "status", "") or "unknown")
    cancel_at_period_end = bool(
        getattr(suscripcion, "cancel_at_period_end", False)
    )
    current_period_end = _timestamp_fin_periodo(suscripcion)

    plan = None
    items = getattr(suscripcion, "items", None)
    datos = getattr(items, "data", None) if items is not None else None
    if datos:
        price = getattr(datos[0], "price", None)
        plan = _id_stripe(price)

    with conectar_postgres() as con:
        with con.cursor() as cur:
            cur.execute(
                """
                INSERT INTO public.subscriptions (
                    user_id,
                    proveedor,
                    customer_id,
                    subscription_id,
                    plan,
                    status,
                    current_period_end,
                    cancel_at_period_end,
                    updated_at
                )
                VALUES (%s, 'STRIPE', %s, %s, %s, %s, %s, %s, now())
                ON CONFLICT (subscription_id)
                DO UPDATE SET
                    user_id = EXCLUDED.user_id,
                    customer_id = EXCLUDED.customer_id,
                    plan = EXCLUDED.plan,
                    status = EXCLUDED.status,
                    current_period_end = EXCLUDED.current_period_end,
                    cancel_at_period_end = EXCLUDED.cancel_at_period_end,
                    updated_at = now()
                """,
                (
                    user_id,
                    customer_id,
                    subscription_id,
                    plan,
                    status,
                    current_period_end,
                    cancel_at_period_end,
                ),
            )
        con.commit()


def _recuperar_suscripcion(subscription_id: str):
    stripe.api_key = obtener_stripe_secret_key()
    return stripe.Subscription.retrieve(subscription_id)


def procesar_webhook(payload: bytes, signature: str) -> str:
    evento = stripe.Webhook.construct_event(
        payload=payload,
        sig_header=signature,
        secret=obtener_stripe_webhook_secret(),
    )

    tipo = str(evento["type"])
    objeto = evento["data"]["object"]

    if tipo == "checkout.session.completed":
        if getattr(objeto, "mode", None) != "subscription":
            return tipo

        user_id = _user_id_desde_metadata(objeto)
        if user_id is None:
            referencia = getattr(objeto, "client_reference_id", None)
            try:
                user_id = UUID(str(referencia))
            except (TypeError, ValueError):
                user_id = None

        subscription_id = _id_stripe(
            getattr(objeto, "subscription", None)
        )

        if user_id is None or not subscription_id:
            raise RuntimeError(
                "Checkout completado sin user_id o subscription_id de OpoCoach."
            )

        suscripcion = _recuperar_suscripcion(subscription_id)
        _guardar_suscripcion(user_id, suscripcion)
        return tipo

    if tipo in {
        "customer.subscription.created",
        "customer.subscription.updated",
        "customer.subscription.deleted",
    }:
        subscription_id = _id_stripe(objeto)
        if not subscription_id:
            raise RuntimeError("Evento de suscripción sin subscription_id.")

        user_id = (
            _user_id_desde_metadata(objeto)
            or _user_id_desde_subscription_id(subscription_id)
        )

        if user_id is None:
            raise RuntimeError(
                "No se puede asociar la suscripción Stripe con un usuario OpoCoach."
            )

        _guardar_suscripcion(user_id, objeto)
        return tipo

    return tipo


def obtener_estado_suscripcion(user_id: UUID) -> dict:
    with conectar_postgres() as con:
        with con.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT
                    customer_id,
                    subscription_id,
                    plan,
                    status,
                    current_period_end,
                    cancel_at_period_end
                FROM public.subscriptions
                WHERE user_id = %s
                  AND proveedor = 'STRIPE'
                ORDER BY updated_at DESC, id DESC
                LIMIT 1
                """,
                (user_id,),
            )
            fila = cur.fetchone()

    if fila is None:
        return {
            "suscrito": False,
            "status": "SIN_SUSCRIPCION",
            "customer_id": None,
            "subscription_id": None,
            "plan": None,
            "current_period_end": None,
            "cancel_at_period_end": False,
        }

    resultado = dict(fila)
    resultado["suscrito"] = resultado["status"] in ESTADOS_CON_ACCESO

    if resultado["current_period_end"] is not None:
        resultado["current_period_end"] = (
            resultado["current_period_end"].isoformat()
        )

    return resultado
