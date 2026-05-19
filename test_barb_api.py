import requests
import json

API_URL = "http://localhost:8000"

# 1. Login do cliente
login_data = {
    "username": "lari.nascimento20148@gmail.com",
    "password": "senha123"  # ajuste a senha se necessário
}

print("🔐 Fazendo login...")
login_res = requests.post(
    f"{API_URL}/api/v1/login/cliente/",
    data=login_data,  # OAuth2PasswordRequestForm espera form data, não JSON
    headers={"Content-Type": "application/x-www-form-urlencoded"}
)

if login_res.status_code != 200:
    print(f"❌ Erro no login: {login_res.text}")
    exit(1)

token = login_res.json().get("access_token")
print(f"✅ Token obtido!")

# 2. Buscar barbearias
print("\n📍 Buscando barbearias...")
headers = {"Authorization": f"Bearer {token}"}
barb_res = requests.get(f"{API_URL}/api/v1/barbearias/todas-aprovadas", headers=headers)

if barb_res.status_code != 200:
    print(f"❌ Erro ao buscar barbearias: {barb_res.text}")
    exit(1)

data = barb_res.json()
print(f"✅ Total de barbearias: {data.get('total', 0)}")

# 3. Buscar especificamente a barbearia de Allan
barbearias = data.get('barbearias', [])
allan_barb = next((b for b in barbearias if 'Allan' in b.get('nome', '')), None)

if allan_barb:
    print(f"\n✅ BARBEARIA ALLAN ENCONTRADA NA RESPOSTA:")
    print(f"   Nome: {allan_barb['nome']}")
    print(f"   ID: {allan_barb['id']}")
    print(f"   Distância: {allan_barb['distancia_km']} km")
    print(f"   Cadeira disponível: {allan_barb['cadeira_disponivel']}")
else:
    print(f"\n❌ Barbearia 'Allan' NÃO ENCONTRADA!")
    print(f"\n📋 Barbearias retornadas:")
    for b in barbearias:
        print(f"   - {b['nome']} ({b['id']})")
