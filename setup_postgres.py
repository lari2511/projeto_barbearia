#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para configurar banco de dados PostgreSQL no BarberMove
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os

load_dotenv()

# Conexão admin para criar o banco
ADMIN_URL = "postgresql://postgres:postgres@localhost:5432/postgres"
DB_NAME = "barbermove"

print("=" * 60)
print("🐘 CONFIGURAÇÃO POSTGRESQL - BarberMove")
print("=" * 60)

try:
    # Conecta como admin
    print("\n1️⃣ Conectando ao PostgreSQL...")
    admin_engine = create_engine(ADMIN_URL, isolation_level="AUTOCOMMIT")
    
    with admin_engine.connect() as conn:
        # Verifica se o banco existe
        result = conn.execute(text(f"SELECT 1 FROM pg_database WHERE datname='{DB_NAME}'"))
        exists = result.fetchone() is not None
        
        if exists:
            print(f"✅ Banco '{DB_NAME}' já existe!")
        else:
            print(f"📦 Criando banco '{DB_NAME}'...")
            conn.execute(text(f"CREATE DATABASE {DB_NAME}"))
            print(f"✅ Banco '{DB_NAME}' criado com sucesso!")
    
    # Agora cria as tabelas
    print("\n2️⃣ Criando tabelas...")
    from app.database import init_db, engine
    from app import models  # Importa os modelos
    
    init_db()
    print("✅ Tabelas criadas com sucesso!")
    
    print("\n" + "=" * 60)
    print("✅ CONFIGURAÇÃO CONCLUÍDA!")
    print("=" * 60)
    
    print("\n📊 CREDENCIAIS PARA PGADMIN:")
    print("-" * 60)
    print("🏠 Host/Address:     localhost")
    print("🔌 Port:             5432")
    print("💾 Database:         barbermove")
    print("👤 Username:         postgres")
    print("🔑 Password:         postgres")
    print("-" * 60)
    
    print("\n📝 COMO CONECTAR NO PGADMIN:")
    print("1. Abra o pgAdmin")
    print("2. Clique com botão direito em 'Servers' → 'Register' → 'Server'")
    print("3. Aba 'General': Nome = 'BarberMove'")
    print("4. Aba 'Connection':")
    print("   - Host: localhost")
    print("   - Port: 5432")
    print("   - Database: barbermove")
    print("   - Username: postgres")
    print("   - Password: postgres")
    print("5. Clique em 'Save'")
    
    print("\n🔍 TABELAS CRIADAS:")
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name
        """))
        for row in result:
            print(f"   ✓ {row[0]}")
    
except Exception as e:
    print(f"\n❌ ERRO: {e}")
    print("\n💡 SOLUÇÕES:")
    print("1. Certifique-se que o PostgreSQL está rodando")
    print("2. Verifique se a senha do postgres está correta")
    print("3. Se a senha não for 'postgres', atualize o .env:")
    print("   DATABASE_URL=postgresql://postgres:SUA_SENHA@localhost:5432/barbermove")
    print("\n🔧 Para verificar se PostgreSQL está rodando:")
    print("   - Windows: services.msc → procure 'postgresql'")
    print("   - Ou abra o pgAdmin e veja se conecta")
