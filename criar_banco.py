import psycopg2

conn = psycopg2.connect(
    host='localhost',
    port=5432,
    database='postgres',
    user='postgres',
    password='Root'
)

conn.autocommit = True
cursor = conn.cursor()

# Verifica se banco existe
cursor.execute("SELECT 1 FROM pg_database WHERE datname='barbermove'")
exists = cursor.fetchone()

if not exists:
    print("Criando banco barbermove...")
    cursor.execute('CREATE DATABASE barbermove')
    print("✅ Banco barbermove criado!")
else:
    print("✅ Banco barbermove já existe!")

cursor.close()
conn.close()

# Agora cria as tabelas
print("\nCriando tabelas...")
from app.database import init_db
init_db()

print("\n✅ CONFIGURAÇÃO COMPLETA!")
print("\n📊 CREDENCIAIS PARA PGADMIN:")
print("Host: localhost")
print("Port: 5432")
print("Database: barbermove")
print("Username: postgres")
print("Password: Root")
