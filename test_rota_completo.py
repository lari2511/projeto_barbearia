import requests
from datetime import datetime

API_URL = 'http://localhost:8000'

# Credenciais de teste
cliente_creds = {
    'username': 'teste.cliente@email.com',
    'password': 'teste123'
}

barbeiro_creds = {
    'username': 'barbeiro@teste.com',
    'password': 'teste123'
}

print("=== Teste de Rota com Dados Completos ===\n")

# Login como cliente
resp_cliente = requests.post(
    f'{API_URL}/api/v1/login/cliente/',
    data=cliente_creds
)

if resp_cliente.status_code != 200:
    print(f"✗ Falha ao autenticar cliente: {resp_cliente.text[:100]}")
    print("\n→ Criando nova conta de cliente...")
    
    # Criar novo cliente
    novo_cliente = {
        'nome': 'Cliente Teste Rota',
        'email': 'teste.cliente@email.com',
        'cpf': '11144477735',
        'telefone': '11987654321',
        'senha': 'teste123'
    }
    resp_criar = requests.post(f'{API_URL}/api/v1/clientes/', json=novo_cliente)
    if resp_criar.status_code == 200:
        print("✓ Cliente criado")
        # Tentar login novamente
        resp_cliente = requests.post(
            f'{API_URL}/api/v1/login/cliente/',
            data=cliente_creds
        )
    else:
        print(f"✗ Falha ao criar cliente: {resp_criar.text[:100]}")
        exit(1)

if resp_cliente.status_code == 200:
    cliente_token = resp_cliente.json()['access_token']
    print('✓ Cliente autenticado')
else:
    print('✗ Falha ao autenticar cliente')
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
    print('✗ Falha ao autenticar barbeiro')
    exit(1)

# Criar chamado de teste
print("→ Criando chamado...")
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
                    print('\n✓ DADOS COMPLETOS PARA RENDERIZAR ROTAS!')
                else:
                    print('\n✗ FALTAM COORDENADAS')
        else:
            print('✗ Falha ao listar agendamentos')
    else:
        print(f'✗ Barbeiro não conseguiu aceitar: {resp_aceita.text[:100]}')
else:
    print(f'✗ Falha ao criar chamado: {resp_chamado.text[:200]}')
