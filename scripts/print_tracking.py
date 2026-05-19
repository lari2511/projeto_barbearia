from app.database import SessionLocal
from app import models
from app import routes

if __name__ == '__main__':
    db = SessionLocal()
    ch = db.query(models.Chamado).filter(models.Chamado.barbeiro_id != None).first()
    if not ch:
        print('Nenhum chamado com barbeiro encontrado')
    else:
        ativo = routes._obter_ou_criar_agendamento_ativo(db, ch)
        db.commit()
        db.refresh(ativo)
        payload = routes._montar_payload_tracking(db, ch, ativo)
        import json
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    db.close()
