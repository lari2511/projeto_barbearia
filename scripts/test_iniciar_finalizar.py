import requests,sys,time
email="larissavideos2018@gmail.com"
senha="senha123"
base="http://127.0.0.1:8000"
print('Login como', email)
r=requests.post(base+"/api/v1/login/barbeiro/", data={"username":email,"password":senha})
print('login status', r.status_code, r.text)
try:
    tok = r.json().get('access_token') or r.json().get('token') or r.json().get('accessToken') or r.json().get('token')
except Exception:
    tok = None
if not tok:
    print('token não obtido; abortando')
    sys.exit(1)
headers={"Authorization":f"Bearer {tok}"}
chamado_id=36
print('Iniciando corte', chamado_id)
r2=requests.put(base+f"/api/v1/chamados/{chamado_id}/iniciar-corte", headers=headers)
print('iniciar status', r2.status_code, r2.text)
print('Aguardando 3s...')
time.sleep(3)
print('Finalizando corte', chamado_id)
r3=requests.put(base+f"/api/v1/chamados/{chamado_id}/finalizar", headers=headers)
print('finalizar status', r3.status_code, r3.text)
