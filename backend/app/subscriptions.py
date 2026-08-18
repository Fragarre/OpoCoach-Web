from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

import os
import stripe
from psycopg.rows import dict_row

from app.billing import (
    obtener_stripe_secret_key,
    obtener_stripe_webhook_secret,
)
from app.postgres import conectar_postgres


ESTADOS_CON_ACCESO = {"active", "trialing", "past_due"}


def obtener_dias_historico_post_baja() -> int:
    """
    Número de días de acceso de solo lectura al histórico tras la baja efectiva.

    Si la variable no está configurada, el plazo es 0. Esto permite dejar
    preparada la política sin fijar todavía una duración comercial.
    """
    valor = os.getenv("HISTORICO_POST_BAJA_DIAS", "0").strip()
    try:
        dias = int(valor)
    except ValueError as exc:
        raise RuntimeError(
            "HISTORICO_POST_BAJA_DIAS debe ser un número entero mayor o igual que 0."
        ) from exc

    if dias < 0:
        raise RuntimeError(
            "HISTORICO_POST_BAJA_DIAS debe ser mayor o igual que 0."
        )
    return dias


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
        items = suscripcion.get("items") if hasattr(suscripcion, "get") else None
        datos = items.get("data") if hasattr(items, "get") else None
        if datos:
            primer_item = datos[0]
            valor = (
                primer_item.get("current_period_end")
                if hasattr(primer_item, "get")
                else getattr(primer_item, "current_period_end", None)
            )

    if valor is None:
        return None

    return datetime.fromtimestamp(int(valor), tz=timezone.utc)


def _timestamp_cancel_at(suscripcion) -> datetime | None:
    valor = getattr(suscripcion, "cancel_at", None)
    if valor is None and hasattr(suscripcion, "get"):
        valor = suscripcion.get("cancel_at")

    if valor is None:
        return None

    return datetime.fromtimestamp(int(valor), tz=timezone.utc)


def _timestamp_ended_at(suscripcion) -> datetime | None:
    valor = getattr(suscripcion, "ended_at", None)
    if valor is None and hasattr(suscripcion, "get"):
        valor = suscripcion.get("ended_at")

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
    cancel_at = _timestamp_cancel_at(suscripcion)
    ended_at = _timestamp_ended_at(suscripcion)
    if status == "canceled" and ended_at is None:
        ended_at = datetime.now(timezone.utc)

    plan = None
    items = suscripcion.get("items") if hasattr(suscripcion, "get") else None
    datos = items.get("data") if hasattr(items, "get") else None
    if datos:
        primer_item = datos[0]
        price = (
            primer_item.get("price")
            if hasattr(primer_item, "get")
            else getattr(primer_item, "price", None)
        )
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
                    cancel_at,
                    ended_at,
                    updated_at
                )
                VALUES (%s, 'STRIPE', %s, %s, %s, %s, %s, %s, %s, %s, now())
                ON CONFLICT (subscription_id)
                DO UPDATE SET
                    user_id = EXCLUDED.user_id,
                    customer_id = EXCLUDED.customer_id,
                    plan = EXCLUDED.plan,
                    status = EXCLUDED.status,
                    current_period_end = EXCLUDED.current_period_end,
                    cancel_at_period_end = EXCLUDED.cancel_at_period_end,
                    cancel_at = EXCLUDED.cancel_at,
                    ended_at = COALESCE(
                        EXCLUDED.ended_at,
                        public.subscriptions.ended_at
                    ),
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
                    cancel_at,
                    ended_at,
                ),
            )
        con.commit()


def _recuperar_suscripcion(subscription_id: str):
    stripe.api_key = obtener_stripe_secret_key()
    return stripe.Subscription.retrieve(subscription_id)


def obtener_customer_id_stripe(user_id: UUID) -> str | None:
    with conectar_postgres() as con:
        with con.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT customer_id
                FROM public.subscriptions
                WHERE user_id = %s
                  AND proveedor = 'STRIPE'
                  AND customer_id IS NOT NULL
                ORDER BY updated_at DESC, id DESC
                LIMIT 1
                """,
                (user_id,),
            )
            fila = cur.fetchone()

    return str(fila["customer_id"]) if fila else None


def _subscription_id_desde_invoice(invoice) -> str | None:
    # Stripe puede exponer la suscripción directamente o dentro de
    # parent.subscription_details según la versión del objeto Invoice.
    subscription_id = _id_stripe(getattr(invoice, "subscription", None))
    if subscription_id:
        return subscription_id

    parent = invoice.get("parent") if hasattr(invoice, "get") else None
    details = (
        parent.get("subscription_details")
        if hasattr(parent, "get")
        else None
    )
    if details:
        return _id_stripe(
            details.get("subscription")
            if hasattr(details, "get")
            else getattr(details, "subscription", None)
        )

    return None


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

    if tipo in {"invoice.paid", "invoice.payment_failed"}:
        subscription_id = _subscription_id_desde_invoice(objeto)
        if not subscription_id:
            # Una factura que no pertenezca a una suscripción no afecta
            # al acceso de OpoCoach.
            return tipo

        user_id = _user_id_desde_subscription_id(subscription_id)
        if user_id is None:
            # Puede ocurrir si el evento de factura llega antes de que
            # checkout.session.completed haya persistido la suscripción.
            suscripcion = _recuperar_suscripcion(subscription_id)
            user_id = _user_id_desde_metadata(suscripcion)
            if user_id is None:
                raise RuntimeError(
                    "No se puede asociar la factura Stripe con un usuario OpoCoach."
                )
        else:
            suscripcion = _recuperar_suscripcion(subscription_id)

        # Stripe sigue siendo la fuente de verdad del estado. En un pago
        # correcto o fallido refrescamos la suscripción completa y dejamos
        # que su status determine el acceso.
        _guardar_suscripcion(user_id, suscripcion)
        return tipo

    return tipo


def obtener_estado_suscripcion(user_id: UUID) -> dict:
    with conectar_postgres() as con:
        with con.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT prueba_gratuita_consumida_at
                FROM public.profiles
                WHERE id = %s
                LIMIT 1
                """,
                (user_id,),
            )
            perfil = cur.fetchone()

            cur.execute(
                """
                SELECT
                    customer_id,
                    subscription_id,
                    plan,
                    status,
                    current_period_end,
                    cancel_at_period_end,
                    cancel_at,
                    ended_at
                FROM public.subscriptions
                WHERE user_id = %s
                  AND proveedor = 'STRIPE'
                ORDER BY updated_at DESC, id DESC
                LIMIT 1
                """,
                (user_id,),
            )
            fila = cur.fetchone()

    consumida_at = (
        perfil["prueba_gratuita_consumida_at"]
        if perfil is not None
        else None
    )

    if fila is None:
        resultado = {
            "suscrito": False,
            "status": "SIN_SUSCRIPCION",
            "customer_id": None,
            "subscription_id": None,
            "plan": None,
            "current_period_end": None,
            "cancel_at_period_end": False,
            "cancel_at": None,
            "ended_at": None,
        }
    else:
        resultado = dict(fila)
        resultado["suscrito"] = resultado["status"] in ESTADOS_CON_ACCESO

    for campo in (
        "current_period_end",
        "cancel_at",
        "ended_at",
    ):
        if resultado.get(campo) is not None:
            resultado[campo] = resultado[campo].isoformat()

    resultado["prueba_gratuita_consumida_at"] = (
        consumida_at.isoformat() if consumida_at is not None else None
    )
    resultado["prueba_gratuita_disponible"] = (
        consumida_at is None and fila is None
    )
    resultado["cancelacion_programada"] = bool(
        resultado.get("cancel_at_period_end")
        or resultado.get("cancel_at")
    )
    resultado["pago_pendiente"] = resultado.get("status") == "past_due"

    dias_historico = obtener_dias_historico_post_baja()
    ended_at_dt = fila["ended_at"] if fila is not None else None
    historico_hasta = (
        ended_at_dt + timedelta(days=dias_historico)
        if ended_at_dt is not None and dias_historico > 0
        else None
    )

    resultado["historico_post_baja_dias"] = dias_historico
    resultado["acceso_historico_hasta"] = (
        historico_hasta.isoformat() if historico_hasta is not None else None
    )
    resultado["acceso_historico_activo"] = bool(
        not resultado["suscrito"]
        and historico_hasta is not None
        and datetime.now(timezone.utc) < historico_hasta
    )

    return resultado

