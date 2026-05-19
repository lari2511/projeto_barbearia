import requests
import json

API_URL = 'http://localhost:8000'

# Login do barbeiro - tentar com JSON
resp = requests.post(f'{API_URL}/api/v1/login/barbeiro/', 
    data={
        'username': 'barbeiro.rota2@test.com',
        'password': '123456'
    }
)

print(f'Status: {resp.status_code}')
if resp.status_code != 200:
    print(f'Response: {resp.text}')
else:
    token = resp.json().get('access_token')
    print(f'✓ Barbeiro logado')
    
    # Listar agendamentos
    resp = requests.get(
        f'{API_URL}/api/v1/barbeiro/agendamentos/meus',
        headers={'Authorization': f'Bearer {token}'}
    )
    
    if resp.status_code == 200:
        agendamentos = resp.json()
        print(f'✓ Agendamentos: {len(agendamentos)}')
        
        if agendamentos:
            agem = agendamentos[0]
            print(f'Primeiro:')
            print(f'  ID: {agem.get("id")}')
            print(f'  Status: {agem.get("status")}')
            print(f'  Cliente Lat: {agem.get("cliente_latitude")}')
            print(f'  Cliente Lon: {agem.get("cliente_longitude")}')
            print(f'  Barbearia Lat: {agem.get("barbearia_latitude")}')
            print(f'  Barbearia Lon: {agem.get("barbearia_longitude")}')
    else:
        print(f'Erro: {resp.text}')
