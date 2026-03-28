#!/usr/bin/env python3
"""
Script de teste para verificar se o sistema está funcionando
Testa:
1. Conexão com banco de dados
2. Novo endpoint de presença
3. Serialização correta de dados
"""

import requests
import json
from datetime import datetime

API_URL = "http://localhost:8000/api/v1"

print("=" * 70)
print("🧪 TESTE DO SISTEMA - PRESENÇA E GEOLOCALIZAÇÃO")
print("=" * 70)

# Teste 1: Verificar disponibilidade da API
print("\n1️⃣  Testando conexão com API...")
try:
    response = requests.get(f"{API_URL}/teste", timeout=5)
    if response.status_code == 200:
        print("✅ API está respondendo!")
    else:
        print(f"⚠️  API respondeu com status {response.status_code}")
except Exception as e:
    print(f"❌ ERRO: API não está disponível em {API_URL}")
    print(f"   {e}")
    print("\n💡 Certifique-se de que:")
    print("   - Backend está rodando (python -m uvicorn app.main:app)")
    print("   - PostgreSQL está rodando")
    exit(1)

# Teste 2: Verificar dados do banco
print("\n2️⃣  Verificando tabela de usuários...")
try:
    from sqlalchemy import create_engine, text
    from dotenv import load_dotenv
    import os
    
    load_dotenv()
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./barbearia.db")
    engine = create_engine(DATABASE_URL)
    
    with engine.begin() as conn:
        result = conn.execute(text("SELECT COUNT(*) FROM usuarios"))
        count = result.scalar()
        print(f"✅ Banco de dados conectado! ({count} usuários)")
        
        # Verificar se colunas existem
        from sqlalchemy import inspect
        inspector = inspect(engine)
        columns = [col['name'] for col in inspector.get_columns('usuarios')]
        
        if 'presente_em_local' in columns:
            print("✅ Coluna 'presente_em_local' existe")
        else:
            print("❌ Coluna 'presente_em_local' NÃO ENCONTRADA")
            
        if 'horario_chegada' in columns:
            print("✅ Coluna 'horario_chegada' existe")
        else:
            print("❌ Coluna 'horario_chegada' NÃO ENCONTRADA")
            
except Exception as e:
    print(f"⚠️  Não foi possível verificar banco: {e}")

# Teste 3: Simulando login (se houver um usuário teste)
print("\n3️⃣  Testando autenticação...")
try:
    # Tentar diferentes endpoints de login
    login_endpoints = [
        "/login/cliente/",
        "/login/barbeiro/",
        "/login/barbearia/",
        "/login/admin/"
    ]
    
    login_data = {
        "username": "teste@gmail.com",
        "password": "123456"
    }
    
    token = None
    for endpoint in login_endpoints:
        response = requests.post(f"{API_URL}{endpoint}", data=login_data, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            token = data.get("access_token")
            print(f"✅ Autenticação bem-sucedida em {endpoint}!")
            print(f"   Token: {token[:30]}...")
            break
        elif response.status_code == 401:
            continue
        else:
            print(f"  {endpoint}: {response.status_code}")
    
    if not token:
        print(f"⚠️  Nenhuma conta 'teste@gmail.com' encontrada")
        print(f"   Criando conta teste...")
        
        # Registrar novo usuário
        register_data = {
            "email": "teste@gmail.com",
            "nome": "Usuário Teste",
            "senha": "123456",
            "telefone": "11999999999"
        }
        
        response = requests.post(f"{API_URL}/clientes/", json=register_data, timeout=5)
        if response.status_code in [200, 201]:
            print(f"✅ Usuário criado!")
            
            # Tentar login novamente
            response = requests.post(f"{API_URL}/login/cliente/", data=login_data, timeout=5)
            if response.status_code == 200:
                data = response.json()
                token = data.get("access_token")
                print(f"✅ Login bem-sucedido!")
        else:
            print(f"⚠️  Erro ao criar usuário: {response.status_code}")
    
    if token:
        # Teste 4: Verificar endpoint de status/profile
        print("\n4️⃣  Testando endpoint de status...")
        headers = {"Authorization": f"Bearer {token}"}
        
        response = requests.get(f"{API_URL}/documentos/status", headers=headers, timeout=5)
        if response.status_code == 200:
            user_data = response.json()
            print(f"✅ Status obtido!")
            print(f"   Nome: {user_data.get('nome')}")
            print(f"   Tipo: {user_data.get('tipo')}")
            print(f"   Presente no local: {user_data.get('presente_em_local')}")
            
            # Teste 5: Testar endpoint de presença
            print("\n5️⃣  Testando endpoint de presença...")
            response = requests.patch(
                f"{API_URL}/usuarios/me/presenca",
                headers=headers,
                json={"presente_em_local": True},
                timeout=5
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Presença atualizada!")
                print(f"   Presente: {result.get('presente_em_local')}")
                print(f"   Horário chegada: {result.get('horario_chegada')}")
            else:
                print(f"❌ Erro ao atualizar presença: {response.status_code}")
                print(f"   {response.text}")
        else:
            print(f"❌ Erro ao obter status: {response.status_code}")
            print(f"   {response.text}")
            
except Exception as e:
    print(f"⚠️  Erro ao testar autenticação: {e}")

print("\n" + "=" * 70)
print("✅ TESTES CONCLUÍDOS!")
print("=" * 70)
print("""
📝 Próximos passos:
1. Testar no navegador com F12 → Console
2. Fazer login como Cliente para testar geolocalização
3. Fazer login como Barbeiro para testar botão de presença
4. Verificar console para logs de debug
""")
