#!/usr/bin/env python3
"""
Script de teste E2E para validar fluxo completo:
1. Cadastro de cliente
2. Login de cliente
3. Buscar barbearias
4. Buscar serviços
5. Criar chamado (agendamento)
"""

import json
import time
from datetime import datetime

import pytest
import requests

API_URL = "http://localhost:8000"


def _unique_email(prefix: str) -> str:
    return f"{prefix}_{int(time.time())}@test.com"


@pytest.fixture(scope="module")
def cliente_payload():
    return {
        "email": _unique_email("cliente"),
        "senha": "senha123",
        "nome": "João Silva Teste",
        "telefone": "11999999999",
    }


@pytest.fixture(scope="module")
def cliente(cliente_payload):
    resp = requests.post(f"{API_URL}/api/v1/clientes/", json=cliente_payload)
    assert resp.status_code == 200, f"Cadastro cliente falhou: {resp.status_code} {resp.text}"
    return resp.json()


@pytest.fixture(scope="module")
def cliente_token(cliente_payload):
    login_data = {"email": cliente_payload["email"], "senha": cliente_payload["senha"]}
    resp = requests.post(f"{API_URL}/api/v1/login/cliente/", json=login_data)
    assert resp.status_code == 200, f"Login cliente falhou: {resp.status_code} {resp.text}"
    return resp.json()["access_token"]


@pytest.fixture(scope="module")
def barbearia_payload():
    return {
        "email": _unique_email("barbearia"),
        "senha": "senha123",
        "nome": "Barbearia Teste",
        "telefone": "11988887777",
        "endereco": "Av. Teste, 123",
        "cep": "01310-100",
    }


@pytest.fixture(scope="module")
def barbearia(barbearia_payload):
    resp = requests.post(f"{API_URL}/api/v1/barbearias/", json=barbearia_payload)
    assert resp.status_code == 200, f"Cadastro barbearia falhou: {resp.status_code} {resp.text}"
    data = resp.json()
    # endpoint retorna {"usuario": ..., "barbearia": ...}
    return data.get("barbearia") or data


@pytest.fixture(scope="module")
def barbearia_token(barbearia_payload):
    login_data = {"email": barbearia_payload["email"], "senha": barbearia_payload["senha"]}
    resp = requests.post(f"{API_URL}/api/v1/login/barbearia/", json=login_data)
    assert resp.status_code == 200, f"Login barbearia falhou: {resp.status_code} {resp.text}"
    return resp.json()["access_token"]


@pytest.fixture(scope="module")
def servico(barbearia, barbearia_token):
    headers = {"Authorization": f"Bearer {barbearia_token}"}
    payload = {"nome": "Corte Teste", "valor": 50.0}
    resp = requests.post(f"{API_URL}/api/v1/barbearia/servicos", json=payload, headers=headers)
    assert resp.status_code == 200, f"Criar serviço falhou: {resp.status_code} {resp.text}"
    return resp.json()

def print_section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")

def test_cadastro_cliente(cliente):
    """Cadastro de cliente deve responder 200 e retornar id/email."""
    assert cliente.get("id")
    assert cliente.get("email")

def test_login_cliente(cliente_token):
    """Login retorna token válido."""
    assert isinstance(cliente_token, str) and cliente_token

def test_listar_barbearias(barbearia):
    resp = requests.get(f"{API_URL}/api/v1/barbearias/todas")
    assert resp.status_code == 200, resp.text
    lista = resp.json()
    assert any(b.get("id") == barbearia.get("id") for b in lista)

def test_listar_servicos(barbearia, servico):
    resp = requests.get(f"{API_URL}/api/v1/barbearia/{barbearia.get('id')}/servicos")
    assert resp.status_code == 200, resp.text
    servicos = resp.json()
    assert any(s.get("id") == servico.get("id") for s in servicos)

def test_criar_chamado(cliente_token, barbearia, servico):
    headers = {"Authorization": f"Bearer {cliente_token}", "Content-Type": "application/json"}
    payload = {"barbearia_id": barbearia.get("id"), "servico_id": servico.get("id")}
    resp = requests.post(f"{API_URL}/api/v1/chamados", json=payload, headers=headers)
    assert resp.status_code == 200, resp.text
    chamado = resp.json()
    assert chamado.get("status")

def test_listar_meus_pedidos(cliente_token):
    headers = {"Authorization": f"Bearer {cliente_token}", "Content-Type": "application/json"}
    resp = requests.get(f"{API_URL}/api/v1/cliente/meus_pedidos", headers=headers)
    assert resp.status_code == 200, resp.text
    pedidos = resp.json()
    assert isinstance(pedidos, list)

def main():
    print("\n" + "="*60)
    print("  🧪 TESTE E2E - FLUXO COMPLETO DO APP")
    print("="*60)
    print(f"  Data/Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  API: {API_URL}\n")
    
    try:
        # Teste 1: Cadastro
        client_data, cliente = test_cadastro_cliente()
        if not cliente:
            print("❌ Teste interrompido: erro no cadastro")
            return
        
        # Teste 2: Login
        token, user_id = test_login_cliente(client_data)
        if not token:
            print("❌ Teste interrompido: erro no login")
            return
        
        # Teste 3: Listar barbearias
        barbearia = test_listar_barbearias()
        if not barbearia:
            print("❌ Teste interrompido: nenhuma barbearia encontrada")
            return
        
        # Teste 4: Listar serviços
        servico = test_listar_servicos(barbearia.get("id"))
        if not servico:
            print("❌ Teste interrompido: nenhum serviço encontrado")
            return
        
        # Teste 5: Criar chamado
        chamado = test_criar_chamado(token, barbearia.get("id"), servico.get("id"))
        if not chamado:
            print("❌ Teste interrompido: erro ao criar chamado")
            return
        
        # Teste 6: Listar meus pedidos
        pedidos = test_listar_meus_pedidos(token)
        
        print_section("✅ TODOS OS TESTES PASSARAM!")
        print("📊 Resumo:")
        print(f"   - Cliente criado: {cliente.get('email')}")
        print(f"   - Barbearia selecionada: {barbearia.get('nome')}")
        print(f"   - Serviço agendado: {servico.get('nome')} (R$ {servico.get('valor')})")
        print(f"   - Chamado criado com ID: {chamado.get('id')}")
        print(f"   - Total de pedidos: {len(pedidos)}")
        
    except Exception as e:
        print(f"\n❌ Erro durante testes: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
