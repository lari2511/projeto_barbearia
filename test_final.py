#!/usr/bin/env python3
"""
Script compilado para testar o sistema BarberMove
Verifica migração, banco de dados e endpoints principais
"""

import requests
import json
import sys

API_URL = "http://localhost:8000/api/v1"

def print_header(text):
    print("\n" + "=" * 70)
    print(text.center(70))
    print("=" * 70)

def print_check(msg):
    print(f"✅ {msg}")

def print_warn(msg):
    print(f"⚠️  {msg}")

def print_error(msg):
    print(f"❌ {msg}")

def test_api_connection():
    print_header("1️⃣  TESTANDO CONEXÃO COM API")
    try:
        response = requests.get(f"{API_URL}/teste", timeout=5)
        if response.status_code >= 200 and response.status_code < 300:
            print_check("API está respondendo!")
            return True
        else:
            print_warn(f"API respondeu com status {response.status_code}")
            return False
    except Exception as e:
        print_error(f"API não está disponível em {API_URL}")
        print(f"   Erro: {str(e)[:100]}")
        return False

def test_database():
    print_header("2️⃣  VERIFICANDO BANCO DE DADOS")
    try:
        from sqlalchemy import create_engine, text, inspect
        from dotenv import load_dotenv
        import os
        
        load_dotenv()
        DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./barbearia.db")
        engine = create_engine(DATABASE_URL)
        
        with engine.begin() as conn:
            result = conn.execute(text("SELECT COUNT(*) FROM usuarios"))
            count = result.scalar()
            print_check(f"Banco de dados conectado! ({count} usuários)")
            
            inspector = inspect(engine)
            columns = [col['name'] for col in inspector.get_columns('usuarios')]
            
            if 'presente_em_local' in columns:
                print_check("Coluna 'presente_em_local' existe")
            else:
                print_error("Coluna 'presente_em_local' NÃO ENCONTRADA")
                
            if 'horario_chegada' in columns:
                print_check("Coluna 'horario_chegada' existe")
            else:
                print_error("Coluna 'horario_chegada' NÃO ENCONTRADA")
        
        return True
    except Exception as e:
        print_error(f"Erro ao verificar banco: {str(e)[:100]}")
        return False

def test_endpoints():
    print_header("3️⃣  TESTANDO ENDPOINTS")
    
    try:
        # Testar GET /barbeiros/proximos
        print("\n📍 Testando busca de barbeiros próximos...")
        response = requests.get(
            f"{API_URL}/barbeiros/proximos",
            params={"latitude": -23.5505, "longitude": -46.6333, "raio_km": 10},
            timeout=5
        )
        if response.status_code == 200:
            data = response.json()
            print_check(f"Endpoint /barbeiros/proximos funcionando ({len(data)} barbeiros)")
        else:
            print_error(f"Erro no endpoint /barbeiros/proximos: {response.status_code}")
        
        # Testar GET /barbeiros/todos
        print("\n📋 Testando listagem de todos os barbeiros...")
        response = requests.get(f"{API_URL}/barbeiros/todos", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print_check(f"Endpoint /barbeiros/todos funcionando ({len(data)} barbeiros)")
        else:
            print_error(f"Erro no endpoint /barbeiros/todos: {response.status_code}")
        
        return True
    except Exception as e:
        print_error(f"Erro ao testar endpoints: {str(e)[:100]}")
        return False

def test_authentication():
    print_header("4️⃣  TESTANDO AUTENTICAÇÃO E PRESENÇA")
    
    try:
        # Buscar um usuário existente
        from sqlalchemy import create_engine, text
        from dotenv import load_dotenv
        import os
        
        load_dotenv()
        DATABASE_URL = os.getenv("DATABASE_URL")
        engine = create_engine(DATABASE_URL)
        
        with engine.begin() as conn:
            result = conn.execute(text("SELECT email, tipo FROM usuarios LIMIT 1"))
            user = result.fetchone()
            
            if not user:
                print_warn("Nenhum usuário encontrado no banco")
                return False
            
            email, tipo = user
            print(f"\n👤 Usando usuário teste: {email} (tipo: {tipo})")
            
            # Tentar login
            login_data = {"username": email, "password": "123456"}
            
            endpoints = {
                "cliente": "/login/cliente/",
                "barbeiro": "/login/barbeiro/",
                "barbearia": "/login/barbearia/",
                "admin": "/login/admin/"
            }
            
            endpoint = endpoints.get(tipo, "/login/cliente/")
            response = requests.post(f"{API_URL}{endpoint}", data=login_data, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                token = data.get("access_token")
                print_check(f"Login bem-sucedido em {endpoint}")
                
                # Testar /documentos/status
                headers = {"Authorization": f"Bearer {token}"}
                response = requests.get(f"{API_URL}/documentos/status", headers=headers, timeout=5)
                
                if response.status_code == 200:
                    user_data = response.json()
                    print_check("Endpoint /documentos/status funcionando")
                    print(f"   Nome: {user_data.get('nome')}")
                    print(f"   Presente no local: {user_data.get('presente_em_local')}")
                    
                    # Testar presença (só para barbeiros/barbearias)
                    if tipo in ["barbeiro", "barbearia"]:
                        print("\n🔔 Testando endpoint de presença...")
                        response = requests.patch(
                            f"{API_URL}/usuarios/me/presenca",
                            headers=headers,
                            json={"presente_em_local": True},
                            timeout=5
                        )
                        
                        if response.status_code == 200:
                            result = response.json()
                            print_check("Endpoint /usuarios/me/presenca funcionando!")
                            print(f"   Presente: {result.get('presente_em_local')}")
                            print(f"   Horário: {result.get('horario_chegada')}")
                        else:
                            print_error(f"Erro no endpoint de presença: {response.status_code}")
                else:
                    print_error(f"Erro ao obter status: {response.status_code}")
                
                return True
            else:
                print_error(f"Erro de login: {response.status_code}")
                print(f"   {response.text[:100]}")
                return False
        
    except Exception as e:
        print_error(f"Erro ao testar autenticação: {str(e)[:100]}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print_header("🧪 TESTE COMPLETO DO SISTEMA BARBERMOVE")
    
    results = {
        "API": test_api_connection(),
        "Database": test_database(),
        "Endpoints": test_endpoints(),
        "Auth": test_authentication()
    }
    
    print_header("📊 RESUMO DOS TESTES")
    
    for test_name, passed in results.items():
        status = "✅ PASSOU" if passed else "❌ FALHOU"
        print(f"{test_name}...... {status}")
    
    print_header("✅ RESUMO FINAL")
    
    print("""
🎉 SISTEMA PRONTO PARA TESTAR!

📱 Próximos passos:

1. TESTAR NO NAVEGADOR:
   - Abra http://192.168.15.6:5173
   - Abra o DevTools (F12 → Console)
   - Faça login como Cliente
   
2. TESTAR GEOLOCALIZAÇÃO:
   - Clique em "Permitir" quando pedir localização
   - Veja os logs de geolocalização no Console (F12)
   - Verifique se barbeiros próximos aparecem

3. TESTAR BOTÃO DE PRESENÇA (Barbeiro):
   - Faça login como Barbeiro
   - Vá para Dashboard
   - Clique em "Presente no local"
   - Deve mudar para verde e salvar no banco

4. LOGS PARA DEBUG:
   - Console do navegador: F12 → Console
   - Terminal do servidor: veja as requisições HTTP
   - Banco PostgreSQL: verifique dados com pgAdmin

💡 Se algo quebrar:
   - Verifique console do navegador (F12)
   - Verifique logs do servidor
   - Rode novamente migrate_presenca.py se precisar
   
""")

if __name__ == "__main__":
    main()
