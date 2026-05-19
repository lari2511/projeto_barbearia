from datetime import datetime, timedelta
import requests, sys
from app.database import SessionLocal
from app import models

base = 'http://127.0.0.1:8000'
barber_email = 'larissavideos2018@gmail.com'
barber_senha = 'senha123'
chamado_id = 37

print('Login como barbeiro', barber_email)
r = requests.post(base + '/api/v1/login/barbeiro/', data={'username': barber_email, 'password': barber_senha})
print('login status', r.status_code, r.text)
r.raise_for_status()
token = r.json()['access_token']
headers = {'Authorization': f'Bearer {token}'}

print('Aceitando chamado', chamado_id)
r2 = requests.put(base + f'/api/v1/chamados/{chamado_id}/aceitar', headers=headers)
print('aceitar status', r2.status_code, r2.text)
r2.raise_for_status()

print('Iniciando corte', chamado_id)
r3 = requests.put(base + f'/api/v1/chamados/{chamado_id}/iniciar-corte', headers=headers)
print('iniciar status', r3.status_code, r3.text)
r3.raise_for_status()

print('Ajustando horário para disparar prompt imediatamente...')
db = SessionLocal()
try:
    chamado = db.query(models.Chamado).filter(models.Chamado.id == chamado_id).first()
    if not chamado:
        print('Chamado não encontrado')
        sys.exit(1)
    chamado.data_hora_inicio = datetime.now() - timedelta(minutes=31)
    chamado.data_hora_fim = datetime.now() - timedelta(minutes=1)
    db.commit()
    print('Chamado atualizado:', chamado.id, chamado.status, chamado.data_hora_inicio, chamado.data_hora_fim)
finally:
    db.close()

print('Fluxo de teste concluído.')
