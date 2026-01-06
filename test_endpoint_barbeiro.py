"""Testar endpoint de chamados abertos para barbeiro"""
import requests
from app.database import SessionLocal
from app import models

db = SessionLocal()

try:
    # Buscar barbeiro
    barbeiro = db.query(models.Usuario).filter(models.Usuario.tipo == "barbeiro").first()
    
    if not barbeiro:
        print("❌ Nenhum barbeiro encontrado no banco!")
        exit(1)
    
    print(f"\n👤 Barbeiro: {barbeiro.nome}")
    print(f"📧 Email: {barbeiro.email}")
    print(f"🔑 ID: {barbeiro.id}")
    
    # Fazer login para obter token
    print("\n🔐 Fazendo login...")
    login_response = requests.post(
        "http://192.168.15.5:8000/api/v1/login/barbeiro/",
        json={"email": barbeiro.email, "senha": "123456"}
    )
    
    print(f"Status: {login_response.status_code}")
    
    if login_response.status_code != 200:
        print(f"❌ Erro no login: {login_response.text}")
        exit(1)
    
    token = login_response.json()["access_token"]
    print(f"✅ Token obtido: {token[:20]}...")
    
    # Buscar chamados abertos
    print("\n📞 Buscando chamados abertos...")
    chamados_response = requests.get(
        "http://192.168.15.5:8000/api/v1/chamados/abertos",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    print(f"Status: {chamados_response.status_code}")
    print(f"Response: {chamados_response.text}")
    
    if chamados_response.status_code == 200:
        chamados = chamados_response.json()
        print(f"\n✅ Chamados encontrados: {len(chamados)}")
        for chamado in chamados:
            print(f"\n  📋 Chamado ID {chamado.get('id')}:")
            print(f"     Cliente: {chamado.get('nome_cliente')}")
            print(f"     Serviço: {chamado.get('descricao')}")
            print(f"     Barbearia: {chamado.get('nome_barbearia')}")
            print(f"     Data/Hora: {chamado.get('data_hora_inicio')}")
            print(f"     Valor: R$ {chamado.get('valor')}")
    else:
        print(f"❌ Erro: {chamados_response.text}")
    
    # Verificar agendamentos direto no banco
    print("\n\n🗄️  VERIFICAÇÃO NO BANCO DE DADOS:")
    agendamentos = db.query(models.Chamado).filter(
        models.Chamado.barbeiro_id == barbeiro.id,
        models.Chamado.status == models.StatusAgendamento.PENDENTE.value
    ).all()
    
    print(f"Agendamentos PENDENTE para barbeiro ID {barbeiro.id}: {len(agendamentos)}")
    for ag in agendamentos:
        print(f"  - ID {ag.id}: Cliente ID {ag.cliente_id}, Status: {ag.status}")
    
except Exception as e:
    print(f"❌ Erro: {str(e)}")
    import traceback
    traceback.print_exc()
finally:
    db.close()
