#!/usr/bin/env python3
"""
Script para resetar o banco de dados - APAGA TUDO E RECRIA
"""
import psycopg2
import time

print("=" * 60)
print("🗑️  RESETANDO BANCO DE DADOS (APAGANDO TUDO)")
print("=" * 60)

# Conectar ao servidor PostgreSQL (não ao banco específico)
conn = psycopg2.connect(
    host='localhost',
    port=5432,
    database='postgres',
    user='postgres',
    password='Root'
)

conn.autocommit = True
cursor = conn.cursor()

try:
    # Verifica se banco existe
    cursor.execute("SELECT 1 FROM pg_database WHERE datname='barbermove'")
    exists = cursor.fetchone()
    
    if exists:
        print("\n🔴 Desconectando usuários do banco...")
        cursor.execute("""
            SELECT pg_terminate_backend(pg_stat_activity.pid)
            FROM pg_stat_activity
            WHERE pg_stat_activity.datname = 'barbermove'
            AND pid <> pg_backend_pid()
        """)
        time.sleep(1)
        
        print("🗑️  Deletando banco barbermove...")
        cursor.execute('DROP DATABASE IF EXISTS barbermove')
        print("✅ Banco deletado!")
    else:
        print("ℹ️  Banco não existe, criando novo...")
    
    print("\n✨ Criando banco barbermove novo...")
    cursor.execute('CREATE DATABASE barbermove')
    print("✅ Banco criado!")
    
finally:
    cursor.close()
    conn.close()

# Agora cria as tabelas
print("\n📊 Criando estrutura de tabelas...")
from app.database import init_db
init_db()

print("\n" + "=" * 60)
print("✅ RESET COMPLETO - BANCO LIMPO E PRONTO!")
print("=" * 60)
print("\n💾 Você pode agora:")
print("   1. Recarregar a página do navegador")
print("   2. Criar novas contas de teste")
print("   3. Começar do zero sem dados sujos")
print("\n")
