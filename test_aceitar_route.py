#!/usr/bin/env python
"""Testa GET status-rastreamento e PATCH aceitar rotas"""
import requests
import json
from app.database import SessionLocal
from app import models

BASE_URL = "http://127.0.0.1:8000/api/v1"

def main():
    db = SessionLocal()
    
    # 1. Buscar um barbeiro para login
    barbeiro = db.query(models.Usuario).filter(
        models.Usuario.tipo == 'barbeiro'
    ).first()
    
    if not barbeiro:
        print("❌ Nenhum barbeiro encontrado no banco")
        db.close()
        return
    
    print(f"✓ Barbeiro encontrado: {barbeiro.email}")
    
    # 2. Fazer login para obter token
    login_resp = requests.post(
        f"{BASE_URL}/login/barbeiro/",
        data={"username": barbeiro.email, "password": "senha123"}
    )
    
    if login_resp.status_code != 200:
        print(f"❌ Login falhou: {login_resp.status_code}")
        print(login_resp.text)
        db.close()
        return
    
    token = login_resp.json().get("access_token")
    print(f"✓ Token obtido: {token[:20]}...")
    
    # 3. Procurar um chamado PENDENTE para aceitar
    chamado = db.query(models.Chamado).filter(
        models.Chamado.status == models.StatusAgendamento.PENDENTE.value
    ).first()
    
    if not chamado:
        print("❌ Nenhum chamado PENDENTE encontrado")
        # Criar um para teste
        servico = db.query(models.Servico).first()
        cliente = db.query(models.Usuario).filter(
            models.Usuario.tipo == 'cliente'
        ).first()
        barbearia = db.query(models.Barbearia).first()
        
        if not (servico and cliente and barbearia):
            print("❌ Não há dados suficientes para criar teste")
            db.close()
            return
        
        chamado = models.Chamado(
            cliente_id=cliente.id,
            barbeiro_id=barbeiro.id,
            servico_id=servico.id,
            barbearia_id=barbearia.id,
            status=models.StatusAgendamento.PENDENTE.value,
        )
        db.add(chamado)
        db.commit()
        db.refresh(chamado)
        print(f"✓ Chamado teste criado: id={chamado.id}")
    else:
        print(f"✓ Chamado encontrado: id={chamado.id}, status={chamado.status}")
    
    chamado_id = chamado.id
    
    # 4. Testar GET status-rastreamento ANTES
    print(f"\n[GET] /agendamento/{chamado_id}/status-rastreamento")
    get_resp = requests.get(f"{BASE_URL}/agendamento/{chamado_id}/status-rastreamento")
    print(f"Status: {get_resp.status_code}")
    print(f"Response: {json.dumps(get_resp.json(), indent=2)}")
    
    # 5. Chamar PATCH aceitar
    print(f"\n[PATCH] /agendamento/{chamado_id}/aceitar")
    headers = {"Authorization": f"Bearer {token}"}
    patch_resp = requests.patch(
        f"{BASE_URL}/agendamento/{chamado_id}/aceitar",
        headers=headers
    )
    print(f"Status: {patch_resp.status_code}")
    print(f"Response: {json.dumps(patch_resp.json(), indent=2)}")
    
    # 6. Testar GET status-rastreamento DEPOIS
    print(f"\n[GET] /agendamento/{chamado_id}/status-rastreamento (APÓS aceitar)")
    get_resp2 = requests.get(f"{BASE_URL}/agendamento/{chamado_id}/status-rastreamento")
    print(f"Status: {get_resp2.status_code}")
    print(f"Response: {json.dumps(get_resp2.json(), indent=2)}")
    
    db.close()
    print("\n✓ Teste concluído")

if __name__ == "__main__":
    main()
