from app.database import SessionLocal
from app import models
from datetime import datetime

if __name__ == '__main__':
    db = SessionLocal()
    ch = db.query(models.Chamado).filter(models.Chamado.barbeiro_id != None).first()
    if not ch:
        print('Nenhum chamado com barbeiro encontrado')
    else:
        print('Usando chamado id', ch.id)
        ativo = db.query(models.AgendamentoAtivo).filter(models.AgendamentoAtivo.chamado_id == ch.id).first()
        if not ativo:
            ativo = models.AgendamentoAtivo(chamado_id=ch.id, cliente_id=ch.cliente_id, barbearia_id=ch.barbearia_id, barbeiro_id=ch.barbeiro_id)
            db.add(ativo)
            db.commit()
            db.refresh(ativo)
            print('Criado AgendamentoAtivo id', ativo.id)
        print('Antes:', ativo.cliente_lat, ativo.cliente_lon, ativo.barbeiro_lat, ativo.barbeiro_lon)
        lat = -23.54933
        lon = -46.49509
        ativo.cliente_lat = lat
        ativo.cliente_lon = lon
        ativo.barbeiro_lat = lat
        ativo.barbeiro_lon = lon
        ativo.cliente_localizacao_em = datetime.utcnow()
        ativo.barbeiro_localizacao_em = datetime.utcnow()
        db.commit()
        db.refresh(ativo)
        print('Depois:', ativo.cliente_lat, ativo.cliente_lon, ativo.barbeiro_lat, ativo.barbeiro_lon)
    db.close()
