from app.database import SessionLocal
from app import models
from passlib.context import CryptContext

db = SessionLocal()
pwd_context = CryptContext(schemes=['argon2', 'bcrypt'], deprecated='auto')

# Criar novo barbeiro
novo_barbeiro = models.Usuario(
    nome='Barbeiro Rota Test',
    email='barbeiro.rota@test.com',
    telefone='11999999999',
    tipo='barbeiro',
    senha_hash=pwd_context.hash('teste123'),
    latitude=-23.5505,
    longitude=-46.6333
)

db.add(novo_barbeiro)
db.commit()
print(f'✓ Barbeiro criado: ID {novo_barbeiro.id}, Email: {novo_barbeiro.email}')
