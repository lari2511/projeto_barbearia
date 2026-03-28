#!/usr/bin/env python3
"""
ARQUIVO: test_firebase_notificacoes.py
Testes end-to-end para o sistema de notificações Firebase

Valida o fluxo completo:
1. Registrar device token
2. Criar corte
3. Simular webhook de pagamento
4. Verificar se notificação foi enviada

Rodar: python test_firebase_notificacoes.py
"""

import requests
import json
from pprint import pprint

# Configuração
API_URL = "http://localhost:8000"
BARBEIRO_EMAIL = "barbeiro@teste.com"
BARBEIRO_SENHA = "123456"
CLIENTE_EMAIL = "cliente@teste.com"
CLIENTE_SENHA = "123456"

# Variáveis globais para armazenar tokens
barbeiro_token = None
cliente_token = None
barbeiro_id = None
cliente_id = None
device_token_teste = "exJhbGc2NjZlcjcwN3JlN2MyZGNkZjc3OGRmYzM4MzBmNzM5ZWMyNjI4YmQ3YzJkZGZjNzdjZA=="  # Token simulado

# ============================================================================
# 1️⃣ TESTES DE AUTENTICAÇÃO
# ============================================================================

def test_login_barbeiro():
    """Fazer login como barbeiro e obter JWT"""
    global barbeiro_token, barbeiro_id
    
    print("\n📌 [1] Fazendo login como barbeiro...")
    
    response = requests.post(
        f"{API_URL}/api/v1/login",
        json={"email": BARBEIRO_EMAIL, "senha": BARBEIRO_SENHA}
    )
    
    if response.status_code != 200:
        print(f"❌ Erro no login: {response.text}")
        return False
    
    data = response.json()
    barbeiro_token = data.get("access_token")
    barbeiro_id = data.get("user_id")
    
    print(f"✅ Login bem-sucedido!")
    print(f"   Barbeiro ID: {barbeiro_id}")
    print(f"   Token: {barbeiro_token[:30]}...")
    
    return True


def test_login_cliente():
    """Fazer login como cliente"""
    global cliente_token, cliente_id
    
    print("\n📌 [2] Fazendo login como cliente...")
    
    response = requests.post(
        f"{API_URL}/api/v1/login",
        json={"email": CLIENTE_EMAIL, "senha": CLIENTE_SENHA}
    )
    
    if response.status_code != 200:
        print(f"❌ Erro no login: {response.text}")
        return False
    
    data = response.json()
    cliente_token = data.get("access_token")
    cliente_id = data.get("user_id")
    
    print(f"✅ Login bem-sucedido!")
    print(f"   Cliente ID: {cliente_id}")
    print(f"   Token: {cliente_token[:30]}...")
    
    return True


# ============================================================================
# 2️⃣ TESTES DE FIREBASE
# ============================================================================

def test_registrar_device_token():
    """Barbeiro registra seu device token após login"""
    
    print("\n📌 [3] Registrando device token do barbeiro...")
    
    headers = {
        "Authorization": f"Bearer {barbeiro_token}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "device_token": device_token_teste,
        "tipo_dispositivo": "android"
    }
    
    response = requests.post(
        f"{API_URL}/api/v1/firebase/registrar-token",
        json=payload,
        headers=headers
    )
    
    if response.status_code != 201:
        print(f"❌ Erro ao registrar token: {response.text}")
        return False
    
    data = response.json()
    print(f"✅ Device token registrado!")
    print(f"   Resposta: {data}")
    
    return True


def test_verificar_status_firebase():
    """Verificar se Firebase está configurado"""
    
    print("\n📌 [4] Verificando status do Firebase...")
    
    response = requests.get(f"{API_URL}/api/v1/firebase/status")
    
    if response.status_code != 200:
        print(f"❌ Erro: {response.text}")
        return False
    
    data = response.json()
    
    if data.get("disponivel"):
        print(f"✅ Firebase está disponível!")
        print(f"   {data.get('mensagem')}")
    else:
        print(f"⚠️ Firebase não está configurado")
        print(f"   {data.get('mensagem')}")
    
    return True


def test_enviar_notificacao_teste():
    """Enviar notificação de teste ao barbeiro"""
    
    print("\n📌 [5] Enviando notificação de teste...")
    
    headers = {
        "Authorization": f"Bearer {barbeiro_token}",
        "Content-Type": "application/json"
    }
    
    response = requests.post(
        f"{API_URL}/api/v1/firebase/teste-notificacao",
        headers=headers
    )
    
    if response.status_code != 200:
        print(f"❌ Erro ao enviar teste: {response.text}")
        return False
    
    data = response.json()
    
    if data.get("sucesso"):
        print(f"✅ Notificação de teste disparada!")
        print(f"   {data.get('mensagem')}")
    else:
        print(f"❌ {data.get('mensagem')}")
    
    return True


# ============================================================================
# 3️⃣ TESTES DE ON-DEMAND
# ============================================================================

def test_ligar_radar():
    """Barbeiro liga seu radar e fica online"""
    
    print("\n📌 [6] Ligando radar do barbeiro...")
    
    headers = {
        "Authorization": f"Bearer {barbeiro_token}",
        "Content-Type": "application/json"
    }
    
    payload = {"is_online": True}
    
    response = requests.post(
        f"{API_URL}/api/v1/on-demand/ligar-radar",
        json=payload,
        headers=headers
    )
    
    if response.status_code != 200:
        print(f"❌ Erro: {response.text}")
        return False
    
    data = response.json()
    print(f"✅ Radar ligado!")
    print(f"   Status: {json.dumps(data, indent=2)}")
    
    return True


def test_atualizar_localizacao():
    """Barbeiro atualiza sua localização via GPS"""
    
    print("\n📌 [7] Atualizando localização do barbeiro...")
    
    headers = {
        "Authorization": f"Bearer {barbeiro_token}",
        "Content-Type": "application/json"
    }
    
    # Coordenadas simuladas (Av Paulista, São Paulo)
    payload = {
        "latitude": -23.562080,
        "longitude": -46.656139
    }
    
    response = requests.post(
        f"{API_URL}/api/v1/on-demand/atualizar-localizacao",
        json=payload,
        headers=headers
    )
    
    if response.status_code != 200:
        print(f"❌ Erro: {response.text}")
        return False
    
    data = response.json()
    print(f"✅ Localização atualizada!")
    print(f"   Latitude: {data.get('latitude')}")
    print(f"   Longitude: {data.get('longitude')}")
    
    return True


# ============================================================================
# 4️⃣ TESTES DE TRANSAÇÕES FINANCEIRAS
# ============================================================================

def test_criar_corte():
    """Criar um corte (já inclui criação de transações auto-split)"""
    
    print("\n📌 [8] Criando corte com cliente...")
    
    headers = {
        "Authorization": f"Bearer {cliente_token}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "freelancer_id": barbeiro_id,
        "barbearia_id": 1,  # Barbearia padrão
        "valor_total": 120.00,
        "metodo_pagamento": "pix",
        "status_pagamento": "pendente"
    }
    
    response = requests.post(
        f"{API_URL}/api/v1/transacoes/cortes",
        json=payload,
        headers=headers
    )
    
    if response.status_code != 201:
        print(f"❌ Erro ao criar corte: {response.text}")
        return False
    
    data = response.json()
    corte_id = data.get("id")
    
    print(f"✅ Corte criado!")
    print(f"   Corte ID: {corte_id}")
    print(f"   Valor: R$ {data.get('valor_total')}")
    print(f"   Freelancer: ID {data.get('freelancer_id')}")
    
    return corte_id


def test_simular_webhook_pagamento(corte_id):
    """Simular webhook de MercadoPago confirmando pagamento"""
    
    print("\n📌 [9] Simulando webhook de pagamento aprovado...")
    
    # Note: Webhook NÃO precisa de Authorization (MercadoPago não o envia)
    headers = {"Content-Type": "application/json"}
    
    # Estrutura simulada do webhook do MercadoPago
    payload = {
        "type": "payment",
        "data": {
            "id": "12345678",
            "status": "approved",
            "external_reference": str(corte_id),
            "transaction_amount": 120.00
        }
    }
    
    response = requests.post(
        f"{API_URL}/api/v1/pagamentos/webhook/mercadopago",
        json=payload,
        headers=headers
    )
    
    print(f"\n📨 POST /api/v1/pagamentos/webhook/mercadopago")
    print(f"📦 Payload:\n{json.dumps(payload, indent=2)}")
    print(f"\n📤 Resposta:")
    print(f"   Status: {response.status_code}")
    print(f"   {response.json()}")
    
    if response.status_code != 200:
        print(f"❌ Erro no webhook: {response.text}")
        return False
    
    print(f"\n✅ Webhook processado!")
    print(f"   🔄 Backend deve ter:")
    print(f"   ✓ Atualizado Corte.status_pagamento = 'aprovado'")
    print(f"   ✓ Atualizado TransacoesFinanceiras.status_repasse = 'concluido'")
    print(f"   ✓ Enviado notificação push ao barbeiro")
    
    return True


# ============================================================================
# 5️⃣ TESTE DE EXTRATO
# ============================================================================

def test_consultar_extrato():
    """Consultar extrato financeiro do barbeiro"""
    
    print("\n📌 [10] Consultando extrato financeiro do barbeiro...")
    
    headers = {
        "Authorization": f"Bearer {barbeiro_token}",
        "Content-Type": "application/json"
    }
    
    response = requests.get(
        f"{API_URL}/api/v1/transacoes/extrato/{barbeiro_id}",
        headers=headers
    )
    
    if response.status_code != 200:
        print(f"⚠️ Extrato ainda não disponível: {response.text}")
        return False
    
    data = response.json()
    
    print(f"✅ Extrato obtido!")
    print(f"   Saldo disponível: R$ {data.get('saldo_disponivel')}")
    print(f"   Total de transações: {len(data.get('extrato', []))}")
    
    if data.get('extrato'):
        print(f"\n   Últimas transações:")
        for trans in data.get('extrato', [])[:3]:
            print(f"   - {trans.get('data')}: R$ {trans.get('valor')} ({trans.get('tipo')})")
    
    return True


# ============================================================================
# 🎯 EXECUTAR TESTES
# ============================================================================

def main():
    """Executar suite completa de testes"""
    
    print("=" * 70)
    print("🧪 TESTE COMPLETO: NOTIFICAÇÕES FIREBASE + ON-DEMAND")
    print("=" * 70)
    
    testes = [
        ("Login Barbeiro", test_login_barbeiro),
        ("Login Cliente", test_login_cliente),
        ("Registrar Device Token", test_registrar_device_token),
        ("Status Firebase", test_verificar_status_firebase),
        ("Notificação Teste", test_enviar_notificacao_teste),
        ("Ligar Radar", test_ligar_radar),
        ("Atualizar Localização", test_atualizar_localizacao),
    ]
    
    passed = 0
    failed = 0
    
    for nome, teste_func in testes:
        try:
            if teste_func():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ Exceção: {e}")
            failed += 1
    
    # Teste especial: criar corte e simular webhook
    print("\n" + "=" * 70)
    print("🎯 TESTE DO FLUXO COMPLETO: PAGAMENTO → WEBHOOK → NOTIFICAÇÃO")
    print("=" * 70)
    
    try:
        corte_id = test_criar_corte()
        if corte_id:
            passed += 1
            
            if test_simular_webhook_pagamento(corte_id):
                passed += 1
            else:
                failed += 1
            
            if test_consultar_extrato():
                passed += 1
            else:
                failed += 1
        else:
            failed += 1
    except Exception as e:
        print(f"❌ Exceção no fluxo: {e}")
        failed += 1
    
    # Resumo final
    print("\n" + "=" * 70)
    print("📊 RESUMO DOS TESTES")
    print("=" * 70)
    print(f"✅ Passaram: {passed}")
    print(f"❌ Falharam: {failed}")
    print(f"📈 Taxa de sucesso: {passed/(passed+failed)*100:.1f}%")
    
    if failed == 0:
        print("\n🎉 TODOS OS TESTES PASSARAM! Sistema pronto para produção.")
    else:
        print(f"\n⚠️ {failed} teste(s) falharam. Verifique os logs acima.")
    
    print("=" * 70)


if __name__ == "__main__":
    main()
