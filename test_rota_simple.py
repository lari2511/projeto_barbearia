#!/usr/bin/env python3
import requests
import json

API_URL = 'http://localhost:8000'

print('=== Teste de Coordenadas no Endpoint Barbeiro ===\n')

# 1. Criar cliente
print('1. Criando cliente...')
resp = requests.post(f'{API_URL}/api/v1/clientes/', json={
    'email': f'teste.cliente.coords@test.com',
    'senha': '123456',
    'nome': 'Teste Cliente Coords',
    'telefone': '11999999999'
})
print(f'   Status: {resp.status_code}')
cliente_id = None
if resp.status_code in [200, 201]:
    cliente = resp.json().get('id') if isinstance(resp.json(), dict) else None
    print(f'   Cliente criado')
else:
    print(f'   Erro: {resp.text}')

# 2. Fazer login do cliente
print('\n2. Login do cliente...')
resp = requests.post(f'{API_URL}/api/v1/login/cliente/', data={
    'username': 'teste.cliente.coords@test.com',
    'password': '123456'
})
print(f'   Status: {resp.status_code}')
cliente_token = None
if resp.status_code == 200:
    cliente_token = resp.json().get('access_token')
    print(f'   ✓ Cliente logado')
else:
    print(f'   Erro: {resp.text}')

# 3. Criar barbeiro
print('\n3. Criando barbeiro...')
resp = requests.post(f'{API_URL}/api/v1/barbeiros/', json={
    'email': f'teste.barbeiro.coords@test.com',
    'senha': '123456',
    'nome': 'Teste Barbeiro Coords',
    'telefone': '11988888888'
})
print(f'   Status: {resp.status_code}')
if resp.status_code in [200, 201]:
    print(f'   Barbeiro criado')
else:
    print(f'   Erro: {resp.text}')

# 4. Login do barbeiro
print('\n4. Login do barbeiro...')
resp = requests.post(f'{API_URL}/api/v1/login/barbeiro/', data={
    'username': 'teste.barbeiro.coords@test.com',
    'password': '123456'
})
print(f'   Status: {resp.status_code}')
barbeiro_token = None
if resp.status_code == 200:
    barbeiro_token = resp.json().get('access_token')
    print(f'   ✓ Barbeiro logado')
else:
    print(f'   Erro: {resp.text}')

# 5. Verificar agendamentos do barbeiro (ainda deve estar vazio)
print('\n5. Listando agendamentos do barbeiro...')
if barbeiro_token:
    resp = requests.get(
        f'{API_URL}/api/v1/barbeiro/agendamentos/meus',
        headers={'Authorization': f'Bearer {barbeiro_token}'}
    )
    print(f'   Status: {resp.status_code}')
    if resp.status_code == 200:
        agendamentos = resp.json()
        print(f'   Total: {len(agendamentos)}')
        
        if agendamentos:
            print('\n   ✓ SUCESSO! Dados do primeiro agendamento:')
            agem = agendamentos[0]
            print(f'     ID: {agem.get("id")}')
            print(f'     Status: {agem.get("status")}')
            print(f'     Cliente Latitude: {agem.get("cliente_latitude")}')
            print(f'     Cliente Longitude: {agem.get("cliente_longitude")}')
            print(f'     Barbearia Latitude: {agem.get("barbearia_latitude")}')
            print(f'     Barbearia Longitude: {agem.get("barbearia_longitude")}')
        else:
            print('   (Sem agendamentos ainda - esperado)')
