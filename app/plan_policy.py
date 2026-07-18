"""
Políticas de plano/assinatura para cenários especiais (ex.: perfil de teste).
"""

import os
from typing import Optional

from app import models


def _csv_set(value: str) -> set[str]:
    if not value:
        return set()
    return {item.strip().lower() for item in value.split(",") if item.strip()}


def _test_email_set() -> set[str]:
    return _csv_set(os.getenv("TEST_BARBERSHOP_EMAILS", ""))


def _test_user_id_set() -> set[str]:
    return _csv_set(os.getenv("TEST_BARBERSHOP_USER_IDS", ""))


def _test_barbershop_id_set() -> set[str]:
    return _csv_set(os.getenv("TEST_BARBERSHOP_IDS", ""))


def is_test_barbershop_profile(
    usuario: Optional[models.Usuario] = None,
    barbearia: Optional[models.Barbearia] = None,
) -> bool:
    """Define se a barbearia é perfil de teste com benefícios operacionais."""
    if os.getenv("TEST_BARBERSHOP_FREE_MODE", "0").strip().lower() in {"1", "true", "yes", "on"}:
        return True

    if usuario:
        if str(usuario.id).lower() in _test_user_id_set():
            return True
        email = (usuario.email or "").strip().lower()
        if email and email in _test_email_set():
            return True

    if barbearia and str(barbearia.id).lower() in _test_barbershop_id_set():
        return True

    return False


def free_chair_limit_for_test_profile(
    usuario: Optional[models.Usuario] = None,
    barbearia: Optional[models.Barbearia] = None,
) -> int:
    """Quantidade de cadeiras gratuitas para perfil de teste."""
    if is_test_barbershop_profile(usuario=usuario, barbearia=barbearia):
        return 1
    return 0


def merge_with_free_test_limit(
    paid_limit: int,
    usuario: Optional[models.Usuario] = None,
    barbearia: Optional[models.Barbearia] = None,
) -> int:
    """Retorna limite efetivo considerando plano pago + benefício de teste."""
    free_limit = free_chair_limit_for_test_profile(usuario=usuario, barbearia=barbearia)
    return max(int(paid_limit or 0), free_limit)
