"""Script de teste para verificar e criar agendamentos no banco de dados"""
from datetime import datetime, timedelta
from app.database import SessionLocal
from app import models

db = SessionLocal()

try:
    # Buscar dados necessários
    cliente = db.query(models.Usuario).filter(models.Usuario.tipo == "cliente").first()
    barbeiro = db.query(models.Usuario).filter(models.Usuario.tipo == "barbeiro").first()
    barbearia = db.query(models.Barbearia).first()
    servico = db.query(models.Servico).first()
    
    print("\n📊 STATUS DO BANCO DE DADOS:")
    print(f"  Cliente: {cliente.nome if cliente else '❌ NENHUM'}")
    print(f"  Barbeiro: {barbeiro.nome if barbeiro else '❌ NENHUM'} (ID: {barbeiro.id if barbeiro else 'N/A'})")
    print(f"  Barbearia: {barbearia.nome if barbearia else '❌ NENHUMA'}")
    print(f"  Serviço: {servico.nome if servico else '❌ NENHUM'}")
    
    if not all([cliente, barbeiro, barbearia, servico]):
        print("\n❌ Faltam dados cadastrados! Execute o seed_database.py primeiro")
        exit(1)
    
    # Listar agendamentos PENDENTE do barbeiro
    print(f"\n📋 AGENDAMENTOS PENDENTES PARA {barbeiro.nome}:")
    agendamentos = db.query(models.Chamado).filter(
        models.Chamado.barbeiro_id == barbeiro.id,
        models.Chamado.status == models.StatusAgendamento.PENDENTE.value
    ).all()
    
    if agendamentos:
        for ag in agendamentos:
            print(f"  ✓ ID {ag.id}: {ag.data_hora_inicio.strftime('%d/%m/%Y %H:%M') if ag.data_hora_inicio else 'Sem data'}")
    else:
        print("  ❌ Nenhum agendamento PENDENTE encontrado")
        print("\n🔨 Criando agendamento de teste...")
        
        # Criar agendamento de teste
        amanha = datetime.now() + timedelta(days=1)
        data_hora_inicio = amanha.replace(hour=14, minute=0, second=0, microsecond=0)
        data_hora_fim = data_hora_inicio + timedelta(minutes=30)
        
        novo_agendamento = models.Chamado(
            cliente_id=cliente.id,
            barbeiro_id=barbeiro.id,
            servico_id=servico.id,
            barbearia_id=barbearia.id,
            data_hora_inicio=data_hora_inicio,
            data_hora_fim=data_hora_fim,
            status=models.StatusAgendamento.PENDENTE.value,
            valor_total=servico.valor,
            comissao_plataforma=servico.valor * 0.10,
            valor_freelancer=servico.valor * 0.70,
            valor_dono=servico.valor * 0.20,
            valor_original=servico.valor,
            valor_final=servico.valor
        )
        
        db.add(novo_agendamento)
        db.commit()
        db.refresh(novo_agendamento)
        
        print(f"  ✅ Agendamento criado! ID: {novo_agendamento.id}")
        print(f"  📅 Data/Hora: {data_hora_inicio.strftime('%d/%m/%Y %H:%M')}")
    
    # Listar TODOS os agendamentos do barbeiro
    print(f"\n📊 TODOS OS AGENDAMENTOS DE {barbeiro.nome}:")
    todos = db.query(models.Chamado).filter(models.Chamado.barbeiro_id == barbeiro.id).all()
    for ag in todos:
        print(f"  - ID {ag.id}: Status {ag.status}, Data: {ag.data_hora_inicio.strftime('%d/%m/%Y %H:%M') if ag.data_hora_inicio else 'N/A'}")
    
except Exception as e:
    print(f"❌ Erro: {str(e)}")
    import traceback
    traceback.print_exc()
    db.rollback()
finally:
    db.close()
