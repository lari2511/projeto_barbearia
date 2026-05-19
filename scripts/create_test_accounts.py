from app.database import SessionLocal, init_db
from app import models
from passlib.context import CryptContext

pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")

if __name__ == '__main__':
    init_db()
    db = SessionLocal()

    def upsert(email, name, tipo, password):
        user = db.query(models.Usuario).filter(models.Usuario.email == email).first()
        if user:
            user.nome = name
            user.tipo = tipo
            user.senha_hash = pwd.hash(password)
            user.email_verificado = True
            user.perfil_aprovado = True
            db.add(user)
            print("updated", email)
        else:
            user = models.Usuario(
                email=email,
                nome=name,
                tipo=tipo,
                senha_hash=pwd.hash(password),
                email_verificado=True,
                perfil_aprovado=True,
            )
            db.add(user)
            print("created", email)

    upsert('allansiqueira06@gmail.com', 'Allan Siqueira', 'barbearia', 'senha123')
    upsert('larissavideos2018@gmail.com', 'Lari', 'barbeiro', 'senha123')
    upsert('lari.nascimento20148@gmail.com', 'Lari Nascimento', 'cliente', 'senha123')

    db.commit()
    db.close()
    print('done')
