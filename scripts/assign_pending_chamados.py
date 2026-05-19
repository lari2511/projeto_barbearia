from app.database import SessionLocal
from app import models

if __name__ == '__main__':
    db = SessionLocal()
    barbeiro = db.query(models.Usuario).filter(models.Usuario.tipo=='barbeiro').first()
    if not barbeiro:
        print('No barber found')
    else:
        pendentes = db.query(models.Chamado).filter(models.Chamado.status==models.StatusAgendamento.PENDENTE.value).all()
        for c in pendentes:
            print('Updating chamado', c.id, '-> barbeiro', barbeiro.id)
            c.barbeiro_id = barbeiro.id
        db.commit()
        print('Done')
    db.close()
