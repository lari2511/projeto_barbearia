from app.database import SessionLocal
from app import models
from passlib.context import CryptContext

db = SessionLocal()
pwd_context = CryptContext(schemes=['argon2', 'bcrypt'], deprecated='auto')

barbeiro = db.query(models.Usuario).filter(models.Usuario.id == 1).first()
if barbeiro:
    barbeiro.senha_hash = pwd_context.hash('teste123')
    db.commit()
    print(f'✓ Senha resetada para barbeiro ID {barbeiro.id}')
else:
    print('✗ Barbeiro não encontrado')
