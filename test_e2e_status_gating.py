#!/usr/bin/env python
"""
Teste End-to-End: Fluxo completo de aceite de chamado com WebSocket
Simula:
1. Cliente aguardando aceite (GET retorna mostrar_mapa: false)
2. Barbeiro aceita (PATCH status CONFIRMADO)
3. WebSocket notifica ambos
4. Cliente vê mapa (GET retorna mostrar_mapa: true)
"""
import requests
import json
import time
from datetime import datetime
from app.database import SessionLocal
from app import models

BASE_URL = "http://127.0.0.1:8000/api/v1"

def log(msg, level="INFO"):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] [{level}] {msg}")

def main():
    log("=" * 60)
    log("TESTE E-TO-E: Status-Based Gating para Rastreamento")
    log("=" * 60)
    
    db = SessionLocal()
    
    try:
        # 1. Obter cliente e barbeiro de teste
        cliente = db.query(models.Usuario).filter(
            models.Usuario.tipo == 'cliente'
        ).first()
        
        barbeiro = db.query(models.Usuario).filter(
            models.Usuario.tipo == 'barbeiro'
        ).first()
        
        if not (cliente and barbeiro):
            log("❌ Usuários de teste não encontrados", "ERROR")
            return
        
        log(f"✓ Cliente: {cliente.email}")
        log(f"✓ Barbeiro: {barbeiro.email}")
        
        # 2. Login de cliente
        log("\n[STEP 1] Login do Cliente...")
        cliente_login = requests.post(
            f"{BASE_URL}/login/cliente/",
            data={"username": cliente.email, "password": "senha123"}
        )
        if cliente_login.status_code != 200:
            log(f"❌ Login cliente falhou: {cliente_login.status_code}", "ERROR")
            return
        
        cliente_token = cliente_login.json().get("access_token")
        log(f"✓ Token cliente: {cliente_token[:20]}...")
        
        # 3. Login de barbeiro
        log("\n[STEP 2] Login do Barbeiro...")
        barbeiro_login = requests.post(
            f"{BASE_URL}/login/barbeiro/",
            data={"username": barbeiro.email, "password": "senha123"}
        )
        if barbeiro_login.status_code != 200:
            log(f"❌ Login barbeiro falhou: {barbeiro_login.status_code}", "ERROR")
            return
        
        barbeiro_token = barbeiro_login.json().get("access_token")
        log(f"✓ Token barbeiro: {barbeiro_token[:20]}...")
        
        # 4. Procurar ou criar um chamado PENDENTE
        log("\n[STEP 3] Preparar Chamado...")
        chamado = db.query(models.Chamado).filter(
            models.Chamado.status == models.StatusAgendamento.PENDENTE.value,
            models.Chamado.barbeiro_id.isnot(None)  # Tem barbeiro designado
        ).first()
        
        if not chamado:
            # Criar chamado de teste
            servico = db.query(models.Servico).first()
            barbearia = db.query(models.Barbearia).first()
            
            if not (servico and barbearia):
                log("❌ Dados insuficientes para criar teste", "ERROR")
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
            log(f"✓ Chamado criado: id={chamado.id}")
            
            # Criar AgendamentoAtivo com coordenadas
            ativo = models.AgendamentoAtivo(
                chamado_id=chamado.id,
                cliente_id=cliente.id,
                barbearia_id=barbearia.id,
                barbeiro_id=barbeiro.id,
                cliente_lat=-23.5493,
                cliente_lon=-46.4951,
                barbeiro_lat=-23.5495,
                barbeiro_lon=-46.4950,
            )
            db.add(ativo)
            db.commit()
            log(f"  ✓ Coordenadas adicionadas")
        else:
            log(f"✓ Chamado encontrado: id={chamado.id}")
            
            # Verificar se há coordenadas
            ativo = db.query(models.AgendamentoAtivo).filter(
                models.AgendamentoAtivo.chamado_id == chamado.id
            ).first()
            
            if not ativo:
                ativo = models.AgendamentoAtivo(
                    chamado_id=chamado.id,
                    cliente_id=cliente.id,
                    barbearia_id=chamado.barbearia_id,
                    barbeiro_id=barbeiro.id,
                    cliente_lat=-23.5493,
                    cliente_lon=-46.4951,
                    barbeiro_lat=-23.5495,
                    barbeiro_lon=-46.4950,
                )
                db.add(ativo)
                db.commit()
                log(f"  ✓ Coordenadas adicionadas")
        
        chamado_id = chamado.id
        
        # 5. Cliente verifica status ANTES de barbeiro aceitar
        log(f"\n[STEP 4] Cliente verifica status (ANTES)...")
        status_antes = requests.get(
            f"{BASE_URL}/agendamento/{chamado_id}/status-rastreamento"
        )
        
        if status_antes.status_code != 200:
            log(f"❌ GET status falhou: {status_antes.status_code}", "ERROR")
            return
        
        data_antes = status_antes.json()
        log(f"✓ Status: {data_antes.get('status')}")
        log(f"✓ Mostrar Mapa: {data_antes.get('mostrar_mapa')}")
        
        if data_antes.get('mostrar_mapa') != False:
            log("⚠️  FALHA: Mapa deveria estar bloqueado (PENDENTE)", "WARN")
        else:
            log("✓ SUCESSO: Mapa bloqueado quando PENDENTE", "SUCCESS")
        
        # 6. Barbeiro aceita o chamado
        log(f"\n[STEP 5] Barbeiro ACEITA o chamado...")
        headers = {"Authorization": f"Bearer {barbeiro_token}"}
        aceitar = requests.patch(
            f"{BASE_URL}/agendamento/{chamado_id}/aceitar",
            headers=headers
        )
        
        if aceitar.status_code != 200:
            log(f"❌ PATCH aceitar falhou: {aceitar.status_code}", "ERROR")
            log(f"   Response: {aceitar.text}", "ERROR")
            return
        
        data_aceitar = aceitar.json()
        log(f"✓ Response: {data_aceitar.get('status')}")
        log(f"✓ Novo Status: {data_aceitar.get('novo_status')}")
        
        # 7. Aguardar WebSocket processing
        log("\n[STEP 6] Aguardando WebSocket broadcast (500ms)...")
        time.sleep(0.5)
        
        # 8. Cliente verifica status DEPOIS de barbeiro aceitar
        log(f"\n[STEP 7] Cliente verifica status (DEPOIS)...")
        status_depois = requests.get(
            f"{BASE_URL}/agendamento/{chamado_id}/status-rastreamento"
        )
        
        if status_depois.status_code != 200:
            log(f"❌ GET status falhou: {status_depois.status_code}", "ERROR")
            return
        
        data_depois = status_depois.json()
        log(f"✓ Status: {data_depois.get('status')}")
        log(f"✓ Mostrar Mapa: {data_depois.get('mostrar_mapa')}")
        
        if data_depois.get('mostrar_mapa') != True:
            log("⚠️  FALHA: Mapa deveria estar liberado (CONFIRMADO)", "WARN")
        else:
            log("✓ SUCESSO: Mapa liberado quando CONFIRMADO", "SUCCESS")
        
        # 9. Validar coordenadas
        log(f"\n[STEP 8] Validar Coordenadas...")
        coords_keys = ['cliente_lat', 'cliente_lon', 'barbeiro_lat', 'barbeiro_lon']
        for key in coords_keys:
            if key in data_depois:
                log(f"✓ {key}: {data_depois[key]}")
            else:
                log(f"⚠️  {key}: Não encontrada", "WARN")
        
        # 10. Resumo final
        log("\n" + "=" * 60)
        log("RESUMO DO TESTE", "INFO")
        log("=" * 60)
        
        tests_passed = [
            ("Status-based gating PENDENTE", data_antes.get('mostrar_mapa') == False),
            ("Status-based gating CONFIRMADO", data_depois.get('mostrar_mapa') == True),
            ("Status alterado corretamente", data_depois.get('status') == 'confirmado'),
            ("Coordenadas presentes", all(key in data_depois for key in coords_keys)),
        ]
        
        passed = sum(1 for _, result in tests_passed if result)
        total = len(tests_passed)
        
        for test_name, result in tests_passed:
            status_icon = "✓" if result else "❌"
            log(f"{status_icon} {test_name}")
        
        log(f"\nResultado: {passed}/{total} testes passaram", "SUCCESS" if passed == total else "WARN")
        
        if passed == total:
            log("\n🎉 TESTE E-TO-E PASSOU! Fluxo está funcionando corretamente.", "SUCCESS")
        else:
            log(f"\n⚠️  {total - passed} teste(s) falharam", "WARN")
        
    finally:
        db.close()

if __name__ == "__main__":
    main()
