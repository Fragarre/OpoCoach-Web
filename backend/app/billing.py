from __future__ import annotations

import os
from dataclasses import dataclass
from uuid import UUID

import stripe


@dataclass(frozen=True)
class CheckoutCreado:
    id: str
    url: str


def _variable(nombre: str) -> str:
    valor = os.getenv(nombre, "").strip()
    if not valor:
        raise RuntimeError(f"{nombre} no está configurado en backend/.env.")
    return valor


def obtener_stripe_secret_key() -> str:
    clave = _variable("STRIPE_SECRET_KEY")
    if not clave.startswith("sk_test_"):
        raise RuntimeError(
            "STRIPE_SECRET_KEY no parece una clave de sandbox/test. "
            "Durante esta fase solo se admiten claves sk_test_."
        )
    return clave


def obtener_stripe_price_id() -> str:
    precio = _variable("STRIPE_PRICE_ID")
    if not precio.startswith("price_"):
        raise RuntimeError("STRIPE_PRICE_ID no parece un Price ID válido.")
    return precio


def obtener_frontend_url() -> str:
    return _variable("FRONTEND_URL").rstrip("/")


def crear_checkout_suscripcion(
    user_id: UUID,
    email: str,
) -> CheckoutCreado:
    stripe.api_key = obtener_stripe_secret_key()

    frontend = obtener_frontend_url()

    session = stripe.checkout.Session.create(
        mode="subscription",
        line_items=[
            {
                "price": obtener_stripe_price_id(),
                "quantity": 1,
            }
        ],
        customer_email=email,
        client_reference_id=str(user_id),
        metadata={
            "opocoach_user_id": str(user_id),
        },
        subscription_data={
            "metadata": {
                "opocoach_user_id": str(user_id),
            }
        },
        success_url=(
            f"{frontend}/?checkout=success"
            "&session_id={CHECKOUT_SESSION_ID}"
        ),
        cancel_url=f"{frontend}/?checkout=cancel",
    )

    if not session.url:
        raise RuntimeError("Stripe no ha devuelto una URL de Checkout.")

    return CheckoutCreado(
        id=str(session.id),
        url=str(session.url),
    )



def obtener_stripe_webhook_secret() -> str:
    secreto = _variable("STRIPE_WEBHOOK_SECRET")
    if not secreto.startswith("whsec_"):
        raise RuntimeError(
            "STRIPE_WEBHOOK_SECRET no parece un secreto de firma de webhook válido."
        )
    return secreto
