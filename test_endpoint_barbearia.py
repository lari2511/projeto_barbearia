"""Testar endpoint de agendamentos da barbearia"""
import requests
from app.database import SessionLocal
from app import models

db = SessionLocal()

try:
    # Buscar usuário da barbearia
    barbearia_user = db.query(models.Usuario).filter(models.Usuario.tipo == "barbearia").first()
    
    if not barbearia_user:
        print("❌ Nenhuma barbearia encontrada!")
        exit(1)
    
    print(f"\n🏪 Barbearia User: {barbearia_user.nome}")
    print(f"📧 Email: {barbearia_user.email}")
    
    # Buscar dados da barbearia
    barbearia = db.query(models.Barbearia).filter(models.Barbearia.usuario_id == barbearia_user.id).first()
    print(f"🏪 Barbearia ID: {barbearia.id if barbearia else 'N/A'}")
    print(f"🏪 Nome: {barbearia.nome if barbearia else 'N/A'}")
    
    # Fazer login
    print("\n🔐 Fazendo login...")
    login_response = requests.post(
        "http://192.168.15.5:8000/api/v1/login/barbearia/",
        json={"email": barbearia_user.email, "senha": "123456"}
    )
    
    if login_response.status_code != 200:
        print(f"❌ Erro no login: {login_response.text}")
        exit(1)
    
    token = login_response.json()["access_token"]
    print(f"✅ Token obtido")
    
    # Buscar dados da barbearia via API
    print("\n🏪 Buscando dados da barbearia...")
    minha_barbearia_response = requests.get(
        "http://192.168.15.5:8000/api/v1/barbearia/minha",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    if minha_barbearia_response.status_code == 200:
        minha = minha_barbearia_response.json()
        print(f"✅ Barbearia ID: {minha['id']}")
        print(f"   Nome: {minha['nome']}")
        
        # Buscar agendamentos
        print(f"\n📋 Buscando agendamentos da barbearia ID {minha['id']}...")
        agendamentos_response = requests.get(
            f"http://192.168.15.5:8000/api/v1/barbearia/{minha['id']}/agendamentos",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        print(f"Status: {agendamentos_response.status_code}")
        print(f"Response: {agendamentos_response.text}")
        
        if agendamentos_response.status_code == 200:
            agendamentos = agendamentos_response.json()
            print(f"\n✅ Agendamentos encontrados: {len(agendamentos)}")
            for ag in agendamentos:
                print(f"\n  📋 Agendamento ID {ag.get('id')}:")
                print(f"     Cliente: {ag.get('nome_cliente')}")
                print(f"     Barbeiro: {ag.get('nome_barbeiro')}")
                print(f"     Serviço: {ag.get('descricao')}")
                print(f"     Status: {ag.get('status')}")
    else:
        print(f"❌ Erro ao buscar barbearia: {minha_barbearia_response.text}")
    
    # Verificar agendamentos direto no banco
    print("\n\n🗄️  VERIFICAÇÃO NO BANCO DE DADOS:")
    if barbearia:
        agendamentos = db.query(models.Chamado).filter(
            models.Chamado.barbearia_id == barbearia.id
        ).all()
        
        print(f"Agendamentos para barbearia ID {barbearia.id}: {len(agendamentos)}")
        for ag in agendamentos:
            print(f"  - ID {ag.id}: Status {ag.status}, Cliente ID {ag.cliente_id}, Barbeiro ID {ag.barbeiro_id}")
    
except Exception as e:
    print(f"❌ Erro: {str(e)}")
    import traceback
    traceback.print_exc()
finally:
    db.close()
