#!/usr/bin/env python3
"""
Script de migração para adicionar colunas de presença ao banco de dados
Adiciona presente_em_local e horario_chegada à tabela usuario
"""

import os
import sys
from dotenv import load_dotenv
from sqlalchemy import create_engine, text, inspect, MetaData

load_dotenv()

# Configurar conexão com o banco
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./barbearia.db")

print("=" * 60)
print("🔄 MIGRAÇÃO - ADICIONAR COLUNAS DE PRESENÇA")
print("=" * 60)
print(f"\n📊 Banco de dados: {DATABASE_URL}")

# Criar engine
engine = create_engine(DATABASE_URL)

# Verificar se é PostgreSQL ou SQLite
is_postgres = "postgresql" in DATABASE_URL
is_sqlite = "sqlite" in DATABASE_URL

print(f"🗄️  Tipo de banco: {'PostgreSQL' if is_postgres else 'SQLite'}")

try:
    with engine.begin() as conn:
        # Inspecionar as tabelas disponíveis
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        print(f"\n📋 Tabelas disponíveis: {tables}")
        
        # Procurar pela tabela de usuários (pode ter nome diferente)
        table_name = None
        if 'usuario' in tables:
            table_name = 'usuario'
        elif 'usuarios' in tables:
            table_name = 'usuarios'
        elif 'user' in tables:
            table_name = 'user'
        elif 'users' in tables:
            table_name = 'users'
        
        if not table_name:
            print(f"\n❌ Tabela de usuários não encontrada!")
            print(f"Tabelas disponíveis: {tables}")
            sys.exit(1)
        
        print(f"\n✅ Usando tabela: '{table_name}'")
        
        # Inspecionar colunas da tabela
        columns = [col['name'] for col in inspector.get_columns(table_name)]
        print(f"📋 Colunas atuais: {columns}\n")
        
        # Verificar se as colunas já existem
        has_presente = 'presente_em_local' in columns
        has_horario = 'horario_chegada' in columns
        
        if has_presente and has_horario:
            print("✅ Colunas de presença já existem! Nada a fazer.")
            sys.exit(0)
        
        # Adicionar colunas faltantes
        if not has_presente:
            print("➕ Adicionando coluna 'presente_em_local'...")
            try:
                if is_postgres:
                    conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN presente_em_local BOOLEAN DEFAULT FALSE"))
                elif is_sqlite:
                    conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN presente_em_local BOOLEAN DEFAULT 0"))
                print("✅ Coluna 'presente_em_local' adicionada!")
            except Exception as e:
                if "already exists" in str(e):
                    print(f"⚠️  Coluna 'presente_em_local' já existe: {e}")
                else:
                    raise
        
        if not has_horario:
            print("➕ Adicionando coluna 'horario_chegada'...")
            try:
                if is_postgres:
                    conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN horario_chegada TIMESTAMP NULL"))
                elif is_sqlite:
                    conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN horario_chegada DATETIME NULL"))
                print("✅ Coluna 'horario_chegada' adicionada!")
            except Exception as e:
                if "already exists" in str(e):
                    print(f"⚠️  Coluna 'horario_chegada' já existe: {e}")
                else:
                    raise

    print("\n" + "=" * 60)
    print("✅ MIGRAÇÃO CONCLUÍDA COM SUCESSO!")
    print("=" * 60)
    
except Exception as e:
    print(f"\n❌ ERRO na migração: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
