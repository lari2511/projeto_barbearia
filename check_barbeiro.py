from app.database import SessionLocal
from app.models import Usuario

db = SessionLocal()
b = db.query(Usuario).filter(Usuario.email == 'larissavideos2018@gmail.com').first()

if b:
    print(f'Barbeiro: {b.nome}')
    print(f'  Email: {b.email}')
    print(f'  disponivel: {b.disponivel}')
    print(f'  presente_em_local: {b.presente_em_local}')
    print(f'  barbearia_atual_id: {b.barbearia_atual_id}')
    print(f'  online_regiao: {b.online_regiao}')
    print(f'  perfil_aprovado: {b.perfil_aprovado}')
    print(f'  documento_verificado: {b.documento_verificado}')
else:
    print('❌ Barbeiro não encontrado')

db.close()
