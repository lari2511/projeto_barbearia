#!/usr/bin/env python3
"""
Script para testar os endpoints que foram corrigidos.
"""

import requests
import json

BASE_URL = "http://localhost:8000/api/v1"

def test_profile_endpoint():
    """Testa o endpoint público de perfil"""
    print("===== Testando GET /api/v1/usuario/{id} =====")
    
    # Testando com ID 1 (assuming existe um usuário)
    response = requests.get(f"{BASE_URL}/usuario/1")
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print("Resposta (amostra):")
        print(f"  - id: {data.get('id')}")
        print(f"  - nome: {data.get('nome')}")
        print(f"  - tipo: {data.get('tipo')}")
        print(f"  - foto_perfil: {data.get('foto_perfil')}")
        print(f"  - portfolio_fotos: {data.get('portfolio_fotos')}")
    else:
        print(f"Erro: {response.text}")
    
    print()

def test_media_avaliacao_endpoint():
    """Testa o endpoint de média de avaliação"""
    print("===== Testando GET /api/v1/usuario/{id}/media_avaliacao =====")
    
    response = requests.get(f"{BASE_URL}/usuario/1/media_avaliacao")
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print("Resposta:")
        print(f"  - media: {data.get('media')}")
        print(f"  - total_avaliacoes: {data.get('total_avaliacoes')}")
    else:
        print(f"Erro: {response.text}")
    
    print()

def test_chamados_pendentes(token):
    """Testa o endpoint de chamados pendentes"""
    print("===== Testando GET /api/v1/cliente/meus_pedidos =====")
    
    headers = {'Authorization': f'Bearer {token}'}
    response = requests.get(f"{BASE_URL}/cliente/meus_pedidos", headers=headers)
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        if isinstance(data, list) and len(data) > 0:
            chamado = data[0]
            print(f"Primeiro chamado:")
            print(f"  - id: {chamado.get('id')}")
            print(f"  - status: {chamado.get('status')}")
            print(f"  - avaliado: {chamado.get('avaliado')}")
            print(f"  Total de chamados: {len(data)}")
        else:
            print("Sem chamados")
    else:
        print(f"Erro: {response.text}")
    
    print()

if __name__ == "__main__":
    print("🧪 Iniciando testes dos endpoints...\n")
    
    test_profile_endpoint()
    test_media_avaliacao_endpoint()
    
    # Para testar endpoints protegidos, você precisa de um token
    # test_chamados_pendentes("seu_token_aqui")
    
    print("✅ Testes completados!")
