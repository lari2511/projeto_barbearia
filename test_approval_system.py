"""
Script de teste para o sistema de aprovações bidirecional
Testa:
1. Criação de novo agendamento
2. Aprovação do barbeiro
3. Aprovação da barbearia
4. Verificação de mudança de status para CONFIRMADO
5. Bloqueio de cadeira
"""

import requests
import json
from datetime import datetime, timedelta

BASE_URL = "http://localhost:8000/api/v1"

# ===== TESTE 1: LOGIN COMO CLIENTE =====
print("\n" + "="*60)
print("TESTE 1: LOGIN COMO CLIENTE")
print("="*60)

cliente_login = {
    "username": "clientes@test.com",
    "password": "123456"
}

response = requests.post(f"{BASE_URL}/login/cliente/", data=cliente_login)
if response.status_code == 200:
    cliente_token = response.json()["access_token"]
    cliente_id = response.json()["usuario_id"]
    print(f"✓ Login cliente bem-sucedido")
    print(f"  Token: {cliente_token[:30]}...")
    print(f"  ID: {cliente_id}")
else:
    print(f"✗ Erro no login cliente: {response.text}")
    exit()

# ===== TESTE 2: LOGIN COMO BARBEIRO =====
print("\n" + "="*60)
print("TESTE 2: LOGIN COMO BARBEIRO")
print("="*60)

barbeiro_login = {
    "username": "barbeiros@test.com",
    "password": "123456"
}

response = requests.post(f"{BASE_URL}/login/barbeiro/", data=barbeiro_login)
if response.status_code == 200:
    barbeiro_token = response.json()["access_token"]
    barbeiro_id = response.json()["usuario_id"]
    print(f"✓ Login barbeiro bem-sucedido")
    print(f"  Token: {barbeiro_token[:30]}...")
    print(f"  ID: {barbeiro_id}")
else:
    print(f"✗ Erro no login barbeiro: {response.text}")
    exit()

# ===== TESTE 3: LOGIN COMO BARBEARIA =====
print("\n" + "="*60)
print("TESTE 3: LOGIN COMO BARBEARIA")
print("="*60)

barbearia_login = {
    "username": "barbearias@test.com",
    "password": "123456"
}

response = requests.post(f"{BASE_URL}/login/barbearia/", data=barbearia_login)
if response.status_code == 200:
    barbearia_token = response.json()["access_token"]
    barbearia_id = response.json()["usuario_id"]
    print(f"✓ Login barbearia bem-sucedido")
    print(f"  Token: {barbearia_token[:30]}...")
    print(f"  ID: {barbearia_id}")
else:
    print(f"✗ Erro no login barbearia: {response.text}")
    exit()

# ===== TESTE 4: CRIAR NOVO AGENDAMENTO =====
print("\n" + "="*60)
print("TESTE 4: CRIAR NOVO AGENDAMENTO")
print("="*60)

# Primeiro, obter um barbeiro válido
response = requests.get(f"{BASE_URL}/barbeiros", headers={"Authorization": f"Bearer {cliente_token}"})
if response.status_code == 200 and len(response.json()) > 0:
    barbeiros = response.json()
    barbeiro_selecionado = barbeiros[0]
    print(f"✓ Barbeiros obtidos: {len(barbeiros)} barbeiros disponíveis")
    print(f"  Barbeiro selecionado ID: {barbeiro_selecionado['id']}")
else:
    print(f"✗ Erro ao obter barbeiros: {response.text}")
    barbeiro_selecionado = {"id": barbeiro_id}

# Obter uma barbearia válida
response = requests.get(f"{BASE_URL}/barbearias", headers={"Authorization": f"Bearer {cliente_token}"})
if response.status_code == 200 and len(response.json()) > 0:
    barbearias = response.json()
    barbearia_selecionada = barbearias[0]
    print(f"✓ Barbearias obtidas: {len(barbearias)} barbearias disponíveis")
    print(f"  Barbearia selecionada ID: {barbearia_selecionada['id']}")
else:
    print(f"✗ Erro ao obter barbearias: {response.text}")
    barbearia_selecionada = {"id": barbearia_id}

# Criar agendamento
nova_data = datetime.now() + timedelta(days=1)
novo_agendamento = {
    "data": nova_data.strftime("%Y-%m-%d"),
    "horario": "10:00",
    "barbeiro_id": barbeiro_selecionado["id"],
    "barbearia_id": barbearia_selecionada["id"],
    "servico": "Corte de cabelo",
    "observacao": "Teste automatizado"
}

response = requests.post(
    f"{BASE_URL}/cliente/agendar",
    json=novo_agendamento,
    headers={"Authorization": f"Bearer {cliente_token}"}
)

if response.status_code in [200, 201]:
    chamado = response.json()
    if isinstance(chamado, dict) and "id" in chamado:
        chamado_id = chamado["id"]
    elif isinstance(chamado, list) and len(chamado) > 0:
        chamado_id = chamado[0].get("id")
    else:
        chamado_id = None
    
    if chamado_id:
        print(f"✓ Agendamento criado com sucesso")
        print(f"  ID do Chamado: {chamado_id}")
        print(f"  Dados: {json.dumps(novo_agendamento, indent=2)}")
    else:
        print(f"✗ Resposta inesperada ao criar agendamento")
        print(f"  Response: {response.json()}")
        exit()
else:
    print(f"✗ Erro ao criar agendamento: {response.status_code}")
    print(f"  {response.text}")
    exit()

# ===== TESTE 5: VERIFICAR STATUS INICIAL =====
print("\n" + "="*60)
print("TESTE 5: VERIFICAR STATUS INICIAL DO CHAMADO")
print("="*60)

response = requests.get(
    f"{BASE_URL}/chamados/{chamado_id}",
    headers={"Authorization": f"Bearer {cliente_token}"}
)

if response.status_code == 200:
    chamado_data = response.json()
    print(f"✓ Chamado obtido")
    print(f"  Status: {chamado_data.get('status')}")
    print(f"  Aprovado Barbeiro: {chamado_data.get('aprovado_barbeiro', False)}")
    print(f"  Aprovado Barbearia: {chamado_data.get('aprovado_barbearia', False)}")
else:
    print(f"✗ Erro ao obter chamado: {response.text}")

# ===== TESTE 6: APROVAR COMO BARBEIRO =====
print("\n" + "="*60)
print("TESTE 6: APROVAR COMO BARBEIRO")
print("="*60)

response = requests.post(
    f"{BASE_URL}/chamados/{chamado_id}/aprovacao-barbeiro",
    headers={"Authorization": f"Bearer {barbeiro_token}"}
)

if response.status_code == 200:
    resultado = response.json()
    print(f"✓ Barbeiro aprovou o agendamento")
    print(f"  Resposta: {json.dumps(resultado, indent=2)}")
else:
    print(f"✗ Erro ao aprovar como barbeiro: {response.status_code}")
    print(f"  {response.text}")

# ===== TESTE 7: VERIFICAR STATUS APÓS APROVAÇÃO DO BARBEIRO =====
print("\n" + "="*60)
print("TESTE 7: VERIFICAR STATUS APÓS APROVAÇÃO DO BARBEIRO")
print("="*60)

response = requests.get(
    f"{BASE_URL}/chamados/{chamado_id}",
    headers={"Authorization": f"Bearer {cliente_token}"}
)

if response.status_code == 200:
    chamado_data = response.json()
    print(f"✓ Chamado obtido após aprovação barbeiro")
    print(f"  Status: {chamado_data.get('status')}")
    print(f"  Aprovado Barbeiro: {chamado_data.get('aprovado_barbeiro', False)}")
    print(f"  Aprovado Barbearia: {chamado_data.get('aprovado_barbearia', False)}")
else:
    print(f"✗ Erro ao obter chamado: {response.text}")

# ===== TESTE 8: APROVAR COMO BARBEARIA =====
print("\n" + "="*60)
print("TESTE 8: APROVAR COMO BARBEARIA")
print("="*60)

response = requests.post(
    f"{BASE_URL}/chamados/{chamado_id}/aprovacao-barbearia",
    headers={"Authorization": f"Bearer {barbearia_token}"}
)

if response.status_code == 200:
    resultado = response.json()
    print(f"✓ Barbearia aprovou o agendamento")
    print(f"  Resposta: {json.dumps(resultado, indent=2)}")
else:
    print(f"✗ Erro ao aprovar como barbearia: {response.status_code}")
    print(f"  {response.text}")

# ===== TESTE 9: VERIFICAR STATUS FINAL (DEVE SER CONFIRMADO) =====
print("\n" + "="*60)
print("TESTE 9: VERIFICAR STATUS FINAL (DEVE SER CONFIRMADO)")
print("="*60)

response = requests.get(
    f"{BASE_URL}/chamados/{chamado_id}",
    headers={"Authorization": f"Bearer {cliente_token}"}
)

if response.status_code == 200:
    chamado_data = response.json()
    status_final = chamado_data.get('status')
    
    print(f"✓ Chamado obtido")
    print(f"  Status FINAL: {status_final}")
    print(f"  Aprovado Barbeiro: {chamado_data.get('aprovado_barbeiro', False)}")
    print(f"  Aprovado Barbearia: {chamado_data.get('aprovado_barbearia', False)}")
    
    if status_final == "CONFIRMADO":
        print(f"\n✓✓✓ SUCESSO! Status mudou para CONFIRMADO após ambas as aprovações! ✓✓✓")
    else:
        print(f"\n⚠ AVISO: Status é {status_final}, esperado CONFIRMADO")
else:
    print(f"✗ Erro ao obter chamado: {response.text}")

# ===== TESTE 10: VERIFICAR BLOQUEIO DE CADEIRA =====
print("\n" + "="*60)
print("TESTE 10: VERIFICAR STATUS DE CADEIRAS")
print("="*60)

response = requests.get(
    f"{BASE_URL}/barbearia/{barbearia_selecionada['id']}/cadeiras-status",
    headers={"Authorization": f"Bearer {barbearia_token}"}
)

if response.status_code == 200:
    cadeiras = response.json()
    print(f"✓ Status de cadeiras obtido: {len(cadeiras)} cadeiras")
    
    # Procurar por cadeiras bloqueadas
    cadeiras_bloqueadas = [c for c in cadeiras if c.get('status') == 'BLOQUEADA']
    
    if cadeiras_bloqueadas:
        print(f"  ✓ {len(cadeiras_bloqueadas)} cadeira(s) bloqueada(s):")
        for cadeira in cadeiras_bloqueadas:
            print(f"    - Cadeira {cadeira.get('numero')}: {cadeira.get('status')} (Chamado: {cadeira.get('chamado_id')})")
    else:
        print(f"  ⚠ Nenhuma cadeira bloqueada encontrada")
    
    # Mostrar todas as cadeiras
    print(f"\n  Todas as cadeiras:")
    for cadeira in cadeiras:
        print(f"    - Cadeira {cadeira.get('numero')}: {cadeira.get('status')}")
else:
    print(f"✗ Erro ao obter status de cadeiras: {response.text}")

print("\n" + "="*60)
print("TESTES CONCLUÍDOS")
print("="*60)
