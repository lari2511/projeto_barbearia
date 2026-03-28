"""
Script para testar avaliações no backend
"""
import requests
import json

API_URL = "http://localhost:8000"

# Teste 1: Login como barbearia para pegar token
print("=" * 60)
print("1️⃣  FAZENDO LOGIN COMO BARBEARIA")
print("=" * 60)

login_res = requests.post(
    f"{API_URL}/api/v1/login/barbearia/",
    data={"username": "barbearia@test.com", "password": "senha123"}
)

print(f"Status: {login_res.status_code}")
if login_res.status_code != 200:
    print(f"Erro: {login_res.text}")
    exit(1)

login_data = login_res.json()
token = login_data.get('access_token')
print(f"✅ Token obtido: {token[:30]}...")

# Teste 2: Buscar agendamentos concluídos
print("\n" + "=" * 60)
print("2️⃣  BUSCANDO AGENDAagendamentos CONCLUÍDOS")
print("=" * 60)

# Primeiro, buscar a barbearia
barbearia_res = requests.get(
    f"{API_URL}/api/v1/barbearia/minha",
    headers={"Authorization": f"Bearer {token}"}
)

if barbearia_res.status_code != 200:
    print(f"Erro ao buscar barbearia: {barbearia_res.text}")
    exit(1)

barbearia = barbearia_res.json()
barbearia_id = barbearia.get('id')
print(f"Barbearia ID: {barbearia_id}")

# Buscar agendamentos
agendamentos_res = requests.get(
    f"{API_URL}/api/v1/barbearia/{barbearia_id}/agendamentos",
    headers={"Authorization": f"Bearer {token}"}
)

if agendamentos_res.status_code != 200:
    print(f"Erro ao buscar agendamentos: {agendamentos_res.text}")
    exit(1)

agendamentos = agendamentos_res.json()
agendamentos_concluidos = [a for a in agendamentos if "conclu" in str(a.get('status', '')).lower()]

print(f"Total de agendamentos: {len(agendamentos)}")
print(f"Agendamentos concluídos: {len(agendamentos_concluidos)}")

if not agendamentos_concluidos:
    print("⚠️  Nenhum agendamento concluído encontrado")
    # Mostrar todos os agendamentos e seus status
    print("\nTodos os agendamentos:")
    for a in agendamentos[:3]:
        print(f"  - ID: {a.get('id')}, Status: {a.get('status')}, Cliente: {a.get('nome_cliente')}, Barbeiro: {a.get('nome_barbeiro')}")
else:
    agendamento = agendamentos_concluidos[0]
    print(f"\nAgendamento de teste:")
    print(f"  - ID: {agendamento.get('id')}")
    print(f"  - Status: {agendamento.get('status')}")
    print(f"  - Cliente: {agendamento.get('nome_cliente')} (ID: {agendamento.get('cliente_id')})")
    print(f"  - Barbeiro: {agendamento.get('nome_barbeiro')} (ID: {agendamento.get('barbeiro_id')})")
    
    # Teste 3: Enviar avaliação
    print("\n" + "=" * 60)
    print("3️⃣  ENVIANDO AVALIAÇÃO DO CLIENTE")
    print("=" * 60)
    
    avaliacao_payload = {
        "chamado_id": agendamento.get('id'),
        "avaliado_id": agendamento.get('cliente_id'),
        "nota": 5,
        "comentario": "Teste de avaliação"
    }
    
    print(f"Payload: {json.dumps(avaliacao_payload, indent=2)}")
    
    avaliacao_res = requests.post(
        f"{API_URL}/api/v1/avaliacoes/criar",
        json=avaliacao_payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
    )
    
    print(f"\nStatus: {avaliacao_res.status_code}")
    print(f"Response: {avaliacao_res.text}")
    
    if avaliacao_res.status_code == 200:
        print("✅ Avaliação enviada com sucesso!")
        print(json.dumps(avaliacao_res.json(), indent=2))
    else:
        print(f"❌ Erro ao enviar avaliação")

print("\n" + "=" * 60)
