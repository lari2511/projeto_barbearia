from app.database import SessionLocal
from app import models

TARGET_BARBEARIA_ID = 1
NEW_LAT = -23.54936
NEW_LON = -46.49516

if __name__ == '__main__':
    db = SessionLocal()
    barbearia = db.query(models.Barbearia).filter(models.Barbearia.id == TARGET_BARBEARIA_ID).first()
    if not barbearia:
        print(f'Barbearia id={TARGET_BARBEARIA_ID} nao encontrada')
    else:
        print('Barbearia antes:', barbearia.id, barbearia.latitude, barbearia.longitude, 'usuario_id=', barbearia.usuario_id)
        barbearia.latitude = NEW_LAT
        barbearia.longitude = NEW_LON
        db.add(barbearia)
        # Atualizar usuario associado, se existir
        if barbearia.usuario_id:
            usuario = db.query(models.Usuario).filter(models.Usuario.id == barbearia.usuario_id).first()
            if usuario:
                print('Usuario dono antes:', usuario.id, usuario.latitude, usuario.longitude)
                usuario.latitude = NEW_LAT
                usuario.longitude = NEW_LON
                db.add(usuario)
                print('Usuario dono atualizado:', usuario.id, usuario.latitude, usuario.longitude)
        db.commit()
        db.refresh(barbearia)
        print('Barbearia depois:', barbearia.id, barbearia.latitude, barbearia.longitude)
    db.close()
