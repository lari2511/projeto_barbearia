"""
Script de teste para verificar se os endpoints de assinatura estão funcionando.
"""
import requests
import json

BASE_URL = "http://localhost:8000/api/v1"

print("=" * 60)
print("🧪 TESTANDO ENDPOINTS DE ASSINATURA")
print("=" * 60)

# Dados de teste - utilizando um token simples
tests = [
    {
        "name": "1️⃣  Calcular Mensalidade (1 cadeira)",
        "method": "POST",
        "endpoint": f"{BASE_URL}/assinatura/calcular",
        "data": {"quantidade_cadeiras": 1}
    },
    {
        "name": "2️⃣  Calcular Mensalidade (3 cadeiras)",
        "method": "POST",
        "endpoint": f"{BASE_URL}/assinatura/calcular",
        "data": {"quantidade_cadeiras": 3}
    },
    {
        "name": "3️⃣  Calcular Mensalidade (6 cadeiras)",
        "method": "POST",
        "endpoint": f"{BASE_URL}/assinatura/calcular",
        "data": {"quantidade_cadeiras": 6}
    },
    {
        "name": "4️⃣  Calcular Mensalidade (10 cadeiras)",
        "method": "POST",
        "endpoint": f"{BASE_URL}/assinatura/calcular",
        "data": {"quantidade_cadeiras": 10}
    },
    {
        "name": "5️⃣  Obter Tabela de Preços",
        "method": "GET",
        "endpoint": f"{BASE_URL}/assinatura/tabela-precos?ate_cadeiras=10",
        "data": None
    }
]

success_count = 0
failure_count = 0

for test in tests:
    try:
        print(f"\n📋 {test['name']}")
        print(f"   Endpoint: {test['endpoint']}")
        
        if test['method'] == 'POST':
            print(f"   Body: {json.dumps(test['data'], indent=2)}")
            response = requests.post(test['endpoint'], json=test['data'], timeout=5)
        else:
            response = requests.get(test['endpoint'], timeout=5)
        
        print(f"   Status: {response.status_code}")
        
        if response.status_code in [200, 201]:
            result = response.json()
            print(f"   ✅ SUCCESS")
            print(f"   Response: {json.dumps(result, indent=2, ensure_ascii=False, default=str)[:500]}...")
            success_count += 1
        else:
            print(f"   ❌ FAILED (HTTP {response.status_code})")
            print(f"   Error: {response.text[:200]}")
            failure_count += 1
            
    except requests.exceptions.ConnectionError:
        print(f"   ❌ CONNECTION ERROR - Backend não está rodando em {BASE_URL}")
        print(f"   → Inicie o backend com: uvicorn app.main:app --reload")
        failure_count += 1
    except Exception as e:
        print(f"   ❌ ERROR: {str(e)}")
        failure_count += 1

print("\n" + "=" * 60)
print(f"📊 RESUMO: {success_count} ✅ | {failure_count} ❌")
print("=" * 60)
