import requests
from datetime import datetime

url_login = "http://localhost:8000/api/v1/login/cliente/"
data_login = {"username": "lari.nascimento20148@gmail.com", "password": "teste123"}

try:
    res_login = requests.post(url_login, data=data_login)
    if res_login.status_code != 200:
        print(f"Login falhou: {res_login.text}")
    else:
        login_resp = res_login.json()
        token = login_resp.get("access_token") or login_resp.get("token")
        print(f"Login OK - Token: {token[:50]}...")
        
        url_chamado = "http://localhost:8000/api/v1/chamados"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        }
        payload = {
            "barbeiro_id": 4,
            "barbeiro_selecionado_id": 4,
            "servico_id": 1,
            "barbearia_id": 1,
            "data_hora_inicio": datetime.now().isoformat(),
            "imediato": True
        }
        
        print(f"Payload: {payload}")
        res_chamado = requests.post(url_chamado, json=payload, headers=headers)
        print(f"Status: {res_chamado.status_code}")
        resp = res_chamado.json()
        print(f"Response: {resp}")
except Exception as e:
    print(f"Erro: {e}")
