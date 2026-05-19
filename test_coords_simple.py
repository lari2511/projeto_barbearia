#!/usr/bin/env python3
import requests

API_URL = 'http://localhost:8000'

print('=== Teste de Coordenadas ===\n')

# Login barbeiro 13 
print('1. Login do barbeiro...')
resp = requests.post(f'{API_URL}/api/v1/login/barbeiro/', data={
    'username': 'barbeiro.rota@test.com',
    'password': '123456'
})
print(f'   Status: {resp.status_code}')
if resp.status_code != 200:
    print(f'   Erro: {resp.text}')
    exit(1)

barbeiro_token = resp.json().get('access_token')
print(f'   ✓ Logado')

# Listar agendamentos
print('\n2. Listando agendamentos...')
resp = requests.get(
    f'{API_URL}/api/v1/barbeiro/agendamentos/meus',
    headers={'Authorization': f'Bearer {barbeiro_token}'}
)
print(f'   Status: {resp.status_code}')
if resp.status_code != 200:
    print(f'   Erro: {resp.text}')
    exit(1)

agendamentos = resp.json()
print(f'   Total: {len(agendamentos)}')

if agendamentos:
    print('\n✓ Coordenadas encontradas:')
    for i, agem in enumerate(agendamentos[:1]):
        print(f'\n   Agendamento ID {agem.get("id")}:')
        print(f'   Status: {agem.get("status")}')
        print(f'   Cliente Lat: {agem.get("cliente_latitude")}')
        print(f'   Cliente Lon: {agem.get("cliente_longitude")}')
        print(f'   Barbearia Lat: {agem.get("barbearia_latitude")}')
        print(f'   Barbearia Lon: {agem.get("barbearia_longitude")}')
else:
    print('   Sem agendamentos')
