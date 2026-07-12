from app.database import SessionLocal
from app import models
from app.routes import verify_password


def main() -> None:
    db = SessionLocal()
    try:
        emails = [
            "cliente@test.com",
            "barbeiro@test.com",
            "barbearia@test.com",
            "allansiqueira06@gmail.com",
        ]
        users = (
            db.query(models.Usuario)
            .filter(models.Usuario.email.in_(emails))
            .all()
        )

        output = [
            (
                u.email,
                u.tipo,
                u.email_verificado,
                bool(u.senha_hash),
                verify_password("senha123", u.senha_hash) if u.senha_hash else None,
            )
            for u in users
        ]
        print(output)
    finally:
        db.close()


if __name__ == "__main__":
    main()
