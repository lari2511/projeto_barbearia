# --- ARQUIVO: app/limite_requisicoes.py ---
# Limite de tentativas (anti força bruta) para login, cadastro e reset de senha.
#
# Janela deslizante em memória: o backend roda em uma única instância no Railway.
# Se um dia houver várias réplicas, trocar o armazenamento por Redis.
#
# Limites por IP são folgados porque, no 4G, muitos clientes saem pelo mesmo IP (CGNAT);
# o limite que realmente segura força bruta é o por e-mail.

import os
import threading
import time
from collections import defaultdict, deque

from fastapi import Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordRequestForm

_lock = threading.Lock()
_eventos: dict[str, deque] = defaultdict(deque)


def _desativado() -> bool:
    return os.getenv("RATE_LIMIT_DESATIVADO", "0") == "1"


def limpar_limites() -> None:
    """Zera os contadores (usado nos testes)."""
    with _lock:
        _eventos.clear()


def ip_do_cliente(request: Request) -> str:
    # O proxy do Railway preenche X-Real-IP com o IP de quem conectou.
    real = (request.headers.get("x-real-ip") or "").strip()
    if real:
        return real
    encaminhado = (request.headers.get("x-forwarded-for") or "").split(",")[0].strip()
    if encaminhado:
        return encaminhado
    return request.client.host if request.client else "desconhecido"


def registrar_tentativa(chave: str, maximo: int, janela_segundos: int) -> None:
    """Conta uma tentativa para `chave`; passa do limite → 429."""
    if _desativado():
        return
    agora = time.monotonic()
    with _lock:
        fila = _eventos[chave]
        while fila and agora - fila[0] > janela_segundos:
            fila.popleft()
        if len(fila) >= maximo:
            espera = int(janela_segundos - (agora - fila[0])) + 1
            raise HTTPException(
                status_code=429,
                detail="Muitas tentativas. Aguarde alguns minutos e tente de novo.",
                headers={"Retry-After": str(max(espera, 1))},
            )
        fila.append(agora)
        # Evita crescer sem fim com chaves que nunca mais aparecem.
        if len(_eventos) > 50_000:
            for k in [k for k, f in _eventos.items() if not f or agora - f[-1] > 3600]:
                _eventos.pop(k, None)


def limitar_por_ip(nome: str, maximo: int, janela_segundos: int):
    """Dependência FastAPI: limita a rota por IP."""
    def _dep(request: Request) -> None:
        registrar_tentativa(f"{nome}:ip:{ip_do_cliente(request)}", maximo, janela_segundos)
    return _dep


def limitar_login(request: Request, form_data: OAuth2PasswordRequestForm = Depends()) -> None:
    """Login: até 60 tentativas/5 min por IP e 10 tentativas/15 min por e-mail.

    O `form_data` é o mesmo objeto que a rota recebe (o FastAPI reaproveita a dependência).
    """
    registrar_tentativa(f"login:ip:{ip_do_cliente(request)}", 60, 5 * 60)
    email = (form_data.username or "").strip().lower()
    if email:
        registrar_tentativa(f"login:email:{email}", 10, 15 * 60)


# Prontas para uso nas rotas
limite_cadastro = limitar_por_ip("cadastro", 20, 60 * 60)
limite_reset_solicitar = limitar_por_ip("reset_solicitar", 10, 15 * 60)
limite_reset_confirmar = limitar_por_ip("reset_confirmar", 20, 15 * 60)
