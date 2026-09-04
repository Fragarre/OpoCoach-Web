"""Reglas de acceso del módulo de empleo.

Este módulo no altera la lógica de suscripciones existente. La integración
real deberá adaptar `tiene_employment_access` al mecanismo central de NetReto.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class EmploymentAccess:
    user_id: UUID
    authenticated: bool
    subscribed: bool
    employment_access: bool


def tiene_employment_access(*, authenticated: bool, subscribed: bool) -> bool:
    """Regla inicial: autenticación + suscripción activa.

    `employment_access` queda como capacidad separada para permitir en el
    futuro un plan específico o un complemento sin rediseñar el módulo.
    """
    return bool(authenticated and subscribed)
