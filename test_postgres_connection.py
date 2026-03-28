import psycopg2
import sys

print("Testando conexao PostgreSQL...")

try:
    conn = psycopg2.connect(
        host="localhost",
        port=5432,
        database="postgres",
        user="postgres",
        password="postgres"
    )
    print("✅ CONECTADO COM SUCESSO!")
    
    cursor = conn.cursor()
    cursor.execute("SELECT version();")
    version = cursor.fetchone()
    print(f"PostgreSQL version: {version[0]}")
    
    # Tentar criar banco
    conn.autocommit = True
    cursor.execute("SELECT 1 FROM pg_database WHERE datname='barbermove'")
    exists = cursor.fetchone()
    
    if not exists:
        print("\nCriando banco barbermove...")
        cursor.execute("CREATE DATABASE barbermove")
        print("✅ Banco criado!")
    else:
        print("\n✅ Banco barbermove já existe!")
    
    cursor.close()
    conn.close()
    
    print("\n📊 CREDENCIAIS PARA PGADMIN:")
    print("Host: localhost")
    print("Port: 5432")
    print("Database: barbermove")
    print("Username: postgres")
    print("Password: postgres")
    
except Exception as e:
    print(f"❌ ERRO: {e}")
    print("\nTente mudar a senha no teste:")
    senha = input("Qual a senha do seu postgres? ")
    
    try:
        conn = psycopg2.connect(
            host="localhost",
            port=5432,
            database="postgres",
            user="postgres",
            password=senha
        )
        print(f"✅ CONECTADO com a senha: {senha}")
        print(f"\nAtualize o .env:")
        print(f"DATABASE_URL=postgresql://postgres:{senha}@localhost:5432/barbermove")
    except Exception as e2:
        print(f"❌ Ainda erro: {e2}")
