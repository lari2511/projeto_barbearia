from datetime import datetime
import requests, sys, json
base = 'http://127.0.0.1:8000'
email = 'lari.nascimento20148@gmail.com'
senha = 'senha123'
print('Login como cliente', email)
r = requests.post(base + '/api/v1/login/cliente/', data={'username': email, 'password': senha})
print('login status', r.status_code, r.text)
r.raise_for_status()
token = r.json()['access_token']
headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
payload = {
    'servico_id': 1,
    'barbearia_id': 1,
    'barbeiro_id': 4,
    'barbeiro_selecionado_id': 4,
    'cadeira_id': None,
    'data_hora_inicio': datetime.now().isoformat(),
    'data_hora_fim': None,
    'cliente_latitude': -23.54935,
    'cliente_longitude': -46.49508,
}
print('Criando chamado...')
r2 = requests.post(base + '/api/v1/chamados', headers=headers, json=payload)
print('create status', r2.status_code, r2.text)
if r2.status_code >= 400:
    sys.exit(1)
print(json.dumps(r2.json(), ensure_ascii=False, indent=2))
