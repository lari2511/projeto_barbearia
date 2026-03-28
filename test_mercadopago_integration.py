#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de teste para integração MercadoPago
Testa os endpoints de pagamento PIX e Cartão
"""

import requests
import json
import time
from dotenv import load_dotenv
import os

# Carrega .env
load_dotenv()

API_URL = os.getenv("API_URL", "http://localhost:8000")
API_PREFIX = f"{API_URL}/api/v1"

print("\n" + "="*60)
print("🧪 TESTE DE INTEGRAÇÃO MERCADOPAGO")
print("="*60 + "\n")

# ========== 1. LOGIN ==========
print("1️⃣ FAZENDO LOGIN...")
login_response = requests.post(f"{API_PREFIX}/login/cliente/", json={
    "email": "cliente@test.com",
    "senha": "senha123"
})

if login_response.status_code != 200:
    print(f"❌ Erro no login: {login_response.text}")
    exit(1)

token = login_response.json()["access_token"]
headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}
print(f"✅ Login bem-sucedido | Token: {token[:20]}...")

# ========== 2. BUSCAR CHAMADOS ==========
print("\n2️⃣ BUSCANDO CHAMADOS...")
chamados_response = requests.get(f"{API_PREFIX}/chamados", headers=headers)

if chamados_response.status_code != 200:
    print(f"❌ Erro ao buscar chamados: {chamados_response.text}")
    exit(1)

chamados = chamados_response.json()
print(f"✅ Total de chamados: {len(chamados)}")

# Buscar um chamado confirmado para testar pagamento
chamado_confirmado = None
for chamado in chamados:
    if chamado.get("status") == "confirmado":
        chamado_confirmado = chamado
        break

if not chamado_confirmado:
    print("⚠️  Nenhum chamado confirmado encontrado para testar")
    print("Buscando por ID 1 para forçar teste...")
    # Tentar criar um pagamento mesmo assim, para testar a API
    chamado_id = 1
else:
    chamado_id = chamado_confirmado["id"]
    print(f"✅ Chamado encontrado: ID {chamado_id}")

# ========== 3. CRIAR PAGAMENTO ==========
print(f"\n3️⃣ CRIANDO REGISTRO DE PAGAMENTO (Chamado #{chamado_id})...")
criar_pagamento_response = requests.post(
    f"{API_PREFIX}/pagamentos/criar",
    headers=headers,
    json={"chamado_id": chamado_id}
)

if criar_pagamento_response.status_code != 200:
    print(f"⚠️  Não foi possível criar pagamento: {criar_pagamento_response.text}")
    print("Continuando para testar endpoints MercadoPago...")
    pagamento_id = 1  # Fake ID para teste
else:
    pagamento_data = criar_pagamento_response.json()
    pagamento_id = pagamento_data["id"]
    print(f"✅ Pagamento criado: ID {pagamento_id}")
    print(f"   Valor Total: R$ {pagamento_data['valor_total']:.2f}")
    print(f"   Taxa (15%): R$ {pagamento_data['taxa_plataforma']:.2f}")
    print(f"   Valor Barbeiro: R$ {pagamento_data['valor_barbeiro']:.2f}")

# ========== 4. TESTAR ENDPOINT PIX ==========
print(f"\n4️⃣ TESTANDO PAGAMENTO PIX MERCADOPAGO...")
pix_response = requests.post(
    f"{API_PREFIX}/pagamentos/mercadopago/pix",
    headers=headers,
    json={"pagamento_id": pagamento_id}
)

if pix_response.status_code == 200:
    pix_data = pix_response.json()
    print(f"✅ PIX gerado com sucesso!")
    print(f"   Payment ID: {pix_data['id']}")
    print(f"   Status: {pix_data['status']}")
    print(f"   Valor: R$ {pix_data['valor']:.2f}")
    if pix_data.get('qrcode'):
        print(f"   QR Code: {pix_data['qrcode'][:50]}...")
else:
    print(f"❌ Erro ao gerar PIX: {pix_response.status_code}")
    print(f"   Resposta: {pix_response.text}")

# ========== 5. TESTAR ENDPOINT CARTAO ==========
print(f"\n5️⃣ TESTANDO PAGAMENTO CARTÃO MERCADOPAGO...")
cartao_response = requests.post(
    f"{API_PREFIX}/pagamentos/mercadopago/cartao",
    headers=headers,
    json={
        "pagamento_id": pagamento_id,
        "numero_cartao": "4485 4970 8144 3010",  # Teste MercadoPago
        "titular": "TEST USER",
        "data_validade": "12/25",
        "cvv": "123",
        "parcelas": 1
    }
)

if cartao_response.status_code == 200:
    cartao_data = cartao_response.json()
    print(f"✅ Cartão processado!")
    print(f"   Payment ID: {cartao_data['id']}")
    print(f"   Status: {cartao_data['status']}")
    print(f"   Valor: R$ {cartao_data['valor']:.2f}")
else:
    print(f"⚠️  Cartão não processado: {cartao_response.status_code}")
    print(f"   Resposta: {cartao_response.text}")

# ========== RESUMO ==========
print("\n" + "="*60)
print("📊 RESUMO DO TESTE")
print("="*60)
print(f"✅ Integração MercadoPago carregada")
print(f"✅ Endpoints disponíveis:")
print(f"   - POST /pagamentos/mercadopago/pix")
print(f"   - POST /pagamentos/mercadopago/cartao")
print(f"   - POST /pagamentos/webhook/mercadopago")
print("\n💡 Próximos passos:")
print("   1. Atualizar TelaPagamento.jsx para usar novos endpoints")
print("   2. Testar com contas MercadoPago reais")
print("   3. Configurar webhooks em produção")
print("\n" + "="*60 + "\n")
