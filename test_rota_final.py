import requests
from datetime import datetime
from datetime import timedelta
import time

API_URL = 'http://localhost:8000'

# Usar credenciais de cliente e barbeiro já existentes
cliente_creds = {
    'username': 'lari.nascimento20148@gmail.com',
    'password': 'teste123'
}

barbeiro_creds = {
    'username': 'barbeiro@test.com',
    'password': 'teste123'
}

print("=== Teste de Rota com Dados Completos ===\n")

# Login como cliente
resp_cliente = requests.post(
    f'{API_URL}/api/v1/login/cliente/',
    data=cliente_creds
)

if resp_cliente.status_code == 200:
    cliente_token = resp_cliente.json()['access_token']
    print('✓ Cliente autenticado')
else:
    print(f'✗ Falha ao autenticar cliente: {resp_cliente.text[:100]}')
    exit(1)

# Login como barbeiro
resp_barbeiro = requests.post(
    f'{API_URL}/api/v1/login/barbeiro/',
    data=barbeiro_creds
)

if resp_barbeiro.status_code == 200:
    barbeiro_token = resp_barbeiro.json()['access_token']
    print('✓ Barbeiro autenticado\n')
else:
    print(f'✗ Falha ao autenticar barbeiro: {resp_barbeiro.text[:100]}')
    exit(1)

# Criar chamado de teste
print("→ Criando chamado...")
chamado_data = {
    'barbeiro_id': 7,
    'barbeiro_selecionado_id': 7,
    'servico_id': 3,
    'barbearia_id': 2,
    'data_hora_inicio': (datetime.utcnow() + timedelta(hours=24)).isoformat(),
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
    print("→ Barbeiro aceitando chamado...")
    resp_aceita = requests.put(
        f'{API_URL}/api/v1/chamados/{chamado_id}/aceitar',
        headers={'Authorization': f'Bearer {barbeiro_token}'}
    )
    if resp_aceita.status_code == 200:
        print(f'✓ Chamado aceito\n')
        
        # Listar agendamentos meus do barbeiro
        resp_agend = requests.get(
            f'{API_URL}/api/v1/barbeiro/agendamentos/meus',
            headers={'Authorization': f'Bearer {barbeiro_token}'}
        )
        if resp_agend.status_code == 200:
            agendamentos = resp_agend.json()
            if agendamentos and len(agendamentos) > 0:
                ag = agendamentos[0]
                print('📍 DADOS DO AGENDAMENTO CONFIRMADO:')
                print(f'  ID: {ag.get("id")}')
                print(f'  Status: {ag.get("status")}')
                print(f'  Cliente:')
                print(f'    - Nome: {ag.get("cliente_nome")}')
                print(f'    - Latitude: {ag.get("cliente_latitude")}')
                print(f'    - Longitude: {ag.get("cliente_longitude")}')
                print(f'  Barbearia:')
                print(f'    - Nome: {ag.get("barbearia_nome")}')
                print(f'    - Latitude: {ag.get("barbearia_latitude")}')
                print(f'    - Longitude: {ag.get("barbearia_longitude")}')
                print(f'    - Endereço: {ag.get("barbearia_endereco")}')
                print(f'    - Telefone: {ag.get("barbearia_telefone")}')
                print(f'  Serviço: {ag.get("servico_nome")} - R${ag.get("valor")}')
                
                # Validar dados essenciais para a rota
                coords_validas = all([
                    ag.get("cliente_latitude") is not None,
                    ag.get("cliente_longitude") is not None,
                    ag.get("barbearia_latitude") is not None,
                    ag.get("barbearia_longitude") is not None,
                ])
                
                if coords_validas:
                    print('\n✅ DADOS COMPLETOS PARA RENDERIZAR ROTAS!')
                    
                    # Calcular ETA
                    from math import radians, sin, cos, atan2, sqrt
                    
                    lat1 = radians(ag.get("cliente_latitude"))
                    lon1 = radians(ag.get("cliente_longitude"))
                    lat2 = radians(ag.get("barbearia_latitude"))
                    lon2 = radians(ag.get("barbearia_longitude"))
                    
                    dlat = lat2 - lat1
                    dlon = lon2 - lon1
                    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
                    c = 2 * atan2(sqrt(a), sqrt(1-a))
                    km = 6371 * c
                    minutos = int((km / 40) * 60)
                    
                    print(f'\n📊 CÁLCULO DE ROTA:')
                    print(f'  - Distância: {km:.2f} km')
                    print(f'  - Tempo estimado: {minutos} minutos (40 km/h)')
                else:
                    print('\n❌ FALTAM COORDENADAS')
        else:
            print('✗ Falha ao listar agendamentos')
    else:
        print(f'✗ Barbeiro não conseguiu aceitar: {resp_aceita.text[:100]}')
else:
    print(f'✗ Falha ao criar chamado: {resp_chamado.text[:200]}')
