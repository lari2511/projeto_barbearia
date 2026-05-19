import requests
import json

# Coordenadas do cliente teste
cliente_lat = -23.5505
cliente_lon = -46.6333

# Endpoint para buscar freelancers próximos
url = f"http://localhost:8000/api/v1/freelancer/proximos?latitude={cliente_lat}&longitude={cliente_lon}&raio_km=5"

print(f"🔍 Testando: {url}\n")

try:
    response = requests.get(url)
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        freelancers = response.json()
        print(f"✅ Encontrados: {len(freelancers)} freelancers\n")
        
        for f in freelancers:
            print(f"📍 {f['nome']}")
            print(f"   Email: (usuario_id: {f['usuario_id']})")
            print(f"   Distância: {f['distancia_km']} km")
            print(f"   Avaliação: {f['media_avaliacoes']} ⭐ ({f['total_avaliacoes']} avaliações)")
            print()
    else:
        print(f"❌ Erro: {response.text}")
        
except Exception as e:
    print(f"❌ Erro de conexão: {e}")
