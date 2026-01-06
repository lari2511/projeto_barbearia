"""Script simples para testar se o servidor está funcionando"""
import sys
import time
import requests

def test_server():
    print("🧪 Testando servidor BarberMove...\n")
    
    # Esperar servidor iniciar
    print("⏳ Aguardando servidor...")
    time.sleep(2)
    
    try:
        # Teste 1: Endpoint raiz
        print("\n1️⃣ Testando endpoint raiz...")
        r = requests.get("http://localhost:8000/")
        print(f"   Status: {r.status_code}")
        print(f"   Response: {r.json()}")
        
        # Teste 2: Docs
        print("\n2️⃣ Testando documentação...")
        r = requests.get("http://localhost:8000/docs")
        print(f"   Status: {r.status_code} {'✅' if r.status_code == 200 else '❌'}")
        
        # Teste 3: Cadastrar cliente
        print("\n3️⃣ Testando cadastro de cliente...")
        cliente_data = {
            "nome": "Teste Cliente",
            "email": "teste@example.com",
            "senha": "senha123",
            "telefone": "11999999999"
        }
        
        r = requests.post("http://localhost:8000/api/v1/clientes/", json=cliente_data)
        if r.status_code == 200:
            print(f"   ✅ Cliente cadastrado com sucesso!")
            print(f"   {r.json()}")
        else:
            print(f"   ❌ Erro: {r.status_code}")
            print(f"   {r.text}")
            
        print("\n✅ Testes básicos concluídos!")
        print("\n📚 Acesse http://localhost:8000/docs para testar mais funcionalidades")
        
    except requests.exceptions.ConnectionError:
        print("❌ Erro: Servidor não está respondendo")
        print("   Execute: uvicorn app.main:app --reload")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")
        sys.exit(1)

if __name__ == "__main__":
    test_server()
