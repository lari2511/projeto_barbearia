import requests
import json
from datetime import datetime
from urllib.parse import urlencode

API_URL = 'http://localhost:8000'

# Credenciais de teste
cliente_creds = {
    'username': 'lari.nascimento20148@gmail.com',
    'password': 'teste123'
}

barbeiro_creds = {
    'username': 'barbeiro@teste.com',
    'password': 'teste123'
}

# Login como cliente
resp_cliente = requests.post(
    f'{API_URL}/api/v1/login/cliente/',
    data=cliente_creds
)
if resp_cliente.status_code == 200:
    cliente_token = resp_cliente.json()['access_token']
    print('✓ Cliente autenticado')
else:
    print('✗ Falha ao autenticar cliente:', resp_cliente.text[:100])
    exit(1)

# Login como barbeiro
resp_barbeiro = requests.post(
    f'{API_URL}/api/v1/login/barbeiro/',
    data=barbeiro_creds
)
if resp_barbeiro.status_code == 200:
    barbeiro_token = resp_barbeiro.json()['access_token']
    print('✓ Barbeiro autenticado')
else:
    print('✗ Falha ao autenticar barbeiro:', resp_barbeiro.text[:100])
    exit(1)

# Criar chamado de teste
chamado_data = {
    'barbeiro_id': 4,
    'barbeiro_selecionado_id': 4,
    'servico_id': 1,
    'barbearia_id': 1,
    'data_hora_inicio': datetime.utcnow().isoformat(),
    'imediato': True
}

resp_chamado = requests.post(
    f'{API_URL}/api/v1/chamados',
    json=chamado_data,
    headers={'Authorization': f'Bearer {cliente_token}'}
)

if resp_chamado.status_code == 200:
    chamado = resp_chamado.json()
    print(f'✓ Chamado criado: ID {chamado.get("id")}')
    chamado_id = chamado.get('id')
    
    # Barbeiro aceita o chamado
    resp_aceita = requests.put(
        f'{API_URL}/api/v1/chamados/{chamado_id}/aceitar',
        headers={'Authorization': f'Bearer {barbeiro_token}'}
    )
    if resp_aceita.status_code == 200:
        print(f'✓ Chamado aceito por barbeiro')
    
    # Listar agendamentos meus do barbeiro
    resp_agend = requests.get(
        f'{API_URL}/api/v1/barbeiro/agendamentos/meus',
        headers={'Authorization': f'Bearer {barbeiro_token}'}
    )
    if resp_agend.status_code == 200:
        agendamentos = resp_agend.json()
        if agendamentos and len(agendamentos) > 0:
            ag = agendamentos[0]
            print('\n📍 Dados do agendamento:')
            print(f'  - cliente_latitude: {ag.get("cliente_latitude")}')
            print(f'  - cliente_longitude: {ag.get("cliente_longitude")}')
            print(f'  - barbearia_latitude: {ag.get("barbearia_latitude")}')
            print(f'  - barbearia_longitude: {ag.get("barbearia_longitude")}')
            print(f'  - barbearia_nome: {ag.get("barbearia_nome")}')
            print(f'  - status: {ag.get("status")}')
    else:
        print('✗ Falha ao listar agendamentos:', resp_agend.text[:200])
else:
    print('✗ Falha ao criar chamado:', resp_chamado.text[:200])
