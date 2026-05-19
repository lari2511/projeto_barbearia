import requests

# Dados dos usuários de teste
cliente_email = 'cliente@test.com'
barbeiro_email = 'barbeiro@test.com'
barbearia_email = 'barbearia@test.com'

# Login como cliente
print('Fazendo login como cliente...')
res = requests.post('http://localhost:8000/api/v1/login/cliente/', 
    data={'username': cliente_email, 'password': 'senha123'})
cliente_token = res.json()['access_token']
cliente_id = res.json()['user_id']
print(f'Cliente token: {cliente_token[:20]}...')

# Login como barbeiro
print('Fazendo login como barbeiro...')
res = requests.post('http://localhost:8000/api/v1/login/barbeiro/', 
    data={'username': barbeiro_email, 'password': 'senha123'})
barbeiro_token = res.json()['access_token']
barbeiro_id = res.json()['user_id']
print(f'Barbeiro ID: {barbeiro_id}')

# Login como barbearia
print('Fazendo login como barbearia...')
res = requests.post('http://localhost:8000/api/v1/login/barbearia/', 
    data={'username': barbearia_email, 'password': 'senha123'})
barbearia_token = res.json()['access_token']
barbearia_id = res.json()['user_id']
print(f'Barbearia ID: {barbearia_id}')

# Criar chamado
print('\nCriando chamado...')
payload = {
    'barbeiro_id': barbeiro_id,
    'barbearia_id': barbearia_id,
    'servicos': ['Corte de cabelo'],
    'valor': 50.0,
}

res = requests.post('http://localhost:8000/api/v1/cliente/solicitar_barbeiro',
    json=payload,
    headers={'Authorization': f'Bearer {cliente_token}'})

if res.status_code in [200, 201]:
    chamado_data = res.json()
    chamado_id = chamado_data['id']
    print(f'Chamado criado com sucesso! ID: {chamado_id}')
    print(f'Status: {chamado_data.get("status", "desconhecido")}')
else:
    print(f'Erro ao criar chamado: {res.status_code}')
    print(res.json())
