#!/usr/bin/env python3
"""
Script para testar a rota de reenvio de email
Usa a conta de teste criada
"""
import requests
import json
import sys

API_URL = "http://localhost:8000"

# Credenciais de teste
EMAIL = "cliente@teste.com"
SENHA = "senha123"

def login():
    """Fazer login e obter token"""
    print("[*] Tentando fazer login...")
    response = requests.post(
        f"{API_URL}/api/v1/login/cliente/",
        json={"email": EMAIL, "senha": SENHA}
    )
    
    if response.status_code != 200:
        print(f"❌ Erro ao fazer login: {response.status_code}")
        print(response.text)
        return None
    
    data = response.json()
    token = data.get('access_token')
    print(f"✅ Login realizado! Token: {token[:20]}...")
    return token

def test_reenvio_email(token):
    """Testar reenvio de email"""
    print("\n[*] Testando reenvio de email...")
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    response = requests.post(
        f"{API_URL}/api/v1/email/reenvio",
        headers=headers
    )
    
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
    
    if response.status_code == 200:
        print("✅ Email reenviado com sucesso!")
    else:
        print(f"❌ Erro ao reenviar email: {response.status_code}")
    
    return response.status_code == 200

def test_usuarios_me(token):
    """Testar obtenção de dados do usuário"""
    print("\n[*] Testando GET /api/v1/usuarios/me...")
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    response = requests.get(
        f"{API_URL}/api/v1/usuarios/me",
        headers=headers
    )
    
    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Dados do usuário: {json.dumps(data, indent=2, ensure_ascii=False)}")
    else:
        print(f"❌ Erro: {response.text}")
    
    return response.status_code == 200

if __name__ == "__main__":
    print("=" * 60)
    print("TESTE DE CONEXÃO COM BACKEND - BarberMove")
    print("=" * 60)
    
    # Test 1: Login
    token = login()
    if not token:
        print("\n❌ Não foi possível fazer login. Abortando testes.")
        sys.exit(1)
    
    # Test 2: Reenvio de email
    test_reenvio_email(token)
    
    # Test 3: Dados do usuário
    test_usuarios_me(token)
    
    print("\n" + "=" * 60)
    print("TESTES COMPLETOS")
    print("=" * 60)
