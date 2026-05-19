from app.database import SessionLocal
from app import models
from passlib.context import CryptContext
from app.routes import verify_password

pwd = CryptContext(schemes=["argon2"], deprecated="auto")

emails = ['allansiqueira06@gmail.com','larissavideos2018@gmail.com','lari.nascimento20148@gmail.com']
new = 'senha123'

db = SessionLocal()
for e in emails:
    u = db.query(models.Usuario).filter(models.Usuario.email==e).first()
    if not u:
        print(e, 'NAO ENCONTRADO')
        continue
    u.senha_hash = pwd.hash(new)
    db.add(u)
    print('Atualizado:', e)

db.commit()

# verificar
for e in emails:
    u = db.query(models.Usuario).filter(models.Usuario.email==e).first()
    ok = verify_password(new, u.senha_hash)
    print(e, 'senha123?', ok)

db.close()
