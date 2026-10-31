"""
Pagamento diário do freelancer: fechamento 21:00, bloqueio 22:00 e desbloqueio pelo Pix.

Relógio de São Paulo controlado (o job recebe `agora`), Mercado Pago falso
(definir_provedor_para_testes) e SQLite temporário. Nenhum dinheiro real é movimentado.

    .venv/Scripts/python -m pytest test_fechamento_diario_recorrente.py -v
"""

import hashlib
import hmac
import os
import tempfile
from datetime import date, datetime, timedelta

_DB = os.path.join(tempfile.mkdtemp(prefix="bm_pd_"), "teste.db")
os.environ["DATABASE_URL"] = f"sqlite:///{_DB}"
os.environ["MERCADOPAGO_WEBHOOK_SECRET"] = "segredo-de-teste"
os.environ.pop("COMISSAO_AUTOMATICA_DESDE", None)

import pytest  # noqa: E402
from fastapi import HTTPException  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app import models  # noqa: E402
from app import pagamento_diario as pd  # noqa: E402
from app.cobrancas import provedores  # noqa: E402
from app.cobrancas.constantes import Finalidade, StatusCobranca  # noqa: E402
from app.database import Base, SessionLocal, engine, init_db  # noqa: E402

D1, D2, D3 = date(2026, 10, 28), date(2026, 10, 29), date(2026, 10, 30)


def sp(d: date, hh: int, mm: int = 0) -> datetime:
    return datetime(d.year, d.month, d.day, hh, mm, tzinfo=pd.TZ_SP)


def utc(d: date, hh: int, mm: int = 0) -> datetime:
    """Horário de São Paulo convertido para o UTC naive que o banco guarda."""
    return pd._utc_naive(sp(d, hh, mm))


class MercadoPagoFalso(provedores.ProvedorPagamento):
    nome = "mercadopago"

    def __init__(self):
        self.pagamentos = {}  # id -> PagamentoProvedor
        self.criados = 0

    def criar_pix(self, *, identificador, valor, descricao, email_pagador, expira_em):
        self.criados += 1
        pid = str(900000 + self.criados)
        p = provedores.PagamentoProvedor(
            provedor_pagamento_id=pid, status="pending", valor=valor, referencia_externa=identificador,
            pix_copia_cola=f"00020126BR.GOV.BCB.PIX{pid}", qr_code_base64="iVBORw0KGgoFALSO", expira_em=expira_em)
        self.pagamentos[pid] = p
        return p

    def consultar(self, provedor_pagamento_id):
        return self.pagamentos[provedor_pagamento_id]

    def cancelar(self, provedor_pagamento_id):
        pass

    def definir(self, pid, status, aprovado_em=None):
        self.pagamentos[pid].status = status
        self.pagamentos[pid].aprovado_em = aprovado_em


@pytest.fixture()
def ambiente(monkeypatch):
    Base.metadata.drop_all(bind=engine)
    init_db()
    mp = MercadoPagoFalso()
    provedores.definir_provedor_para_testes(mp)
    pd._falhas_pix.clear()
    relogio = {"agora": sp(D1, 8)}
    monkeypatch.setattr(pd, "agora_sp", lambda: relogio["agora"])
    db = SessionLocal()
    yield db, mp, relogio
    db.close()
    provedores.definir_provedor_para_testes(None)


# ------------------------------------------------------------------ auxiliares

def criar_usuario(db, nome, tipo="barbeiro"):
    u = models.Usuario(nome=nome, email=f"{nome.lower()}@teste.dev", tipo=tipo, senha_hash="x",
                       email_verificado=True, perfil_aprovado=True)
    db.add(u)
    db.commit()
    return u


def atender(db, freelancer, cliente, qtd, quando, valor=50.0, **extra):
    for _ in range(qtd):
        db.add(models.Chamado(cliente_id=cliente.id, barbeiro_id=freelancer.id, valor_total=valor,
                              status=extra.get("status", models.StatusAgendamento.CONCLUIDO.value),
                              origem_cliente=extra.get("origem", models.OrigemCliente.APP.value),
                              concluido_em=quando))
    db.commit()


def ciclo(db, relogio, quando):
    relogio["agora"] = quando
    pd._ciclo_job(db=db, agora=quando)
    db.expire_all()


def saldo(db, u):
    c = db.query(models.CarteiraBarbeiro).filter(models.CarteiraBarbeiro.barbeiro_id == u.id).first()
    return round(float(c.saldo), 2) if c else 0.0


def bloqueado(db, u, quando):
    return pd.fechamento_bloqueante(db, u.id, quando) is not None


def pix_aberto(db, u):
    return pd.cobranca_pix_em_aberto(db, u.id)


def execucao(db, d, rotina):
    return db.query(models.ExecucaoPagamentoDiario).filter(
        models.ExecucaoPagamentoDiario.data_referencia == d,
        models.ExecucaoPagamentoDiario.rotina == rotina).first()


def contagens(db):
    return (db.query(models.HistoricoMovimentacaoFinanceira).count(),
            db.query(models.FechamentoDiarioFreelancer).count(),
            db.query(models.Cobranca).count(),
            db.query(models.Notificacao).count())


def assinar(data_id, request_id="req-1", ts="1700000000"):
    manifesto = f"id:{data_id};request-id:{request_id};ts:{ts};"
    v1 = hmac.new(b"segredo-de-teste", manifesto.encode(), hashlib.sha256).hexdigest()
    return {"x-signature": f"ts={ts},v1={v1}", "x-request-id": request_id}


@pytest.fixture()
def cliente_http():
    from app.main import app
    return TestClient(app)  # sem "with": o job em background não sobe durante o teste


def token(u):
    from app.routes import create_access_token
    return {"Authorization": f"Bearer {create_access_token({'sub': str(u.id)})}"}


# ------------------------------------------------------------------ cenário de 3 dias

def test_tres_dias_fechamento_bloqueio_e_desbloqueio(ambiente, cliente_http):
    db, mp, relogio = ambiente
    cliente = criar_usuario(db, "Cliente", tipo="cliente")
    ana = criar_usuario(db, "Ana")        # paga depois das 22h (webhook assinado)
    bruno = criar_usuario(db, "Bruno")    # não paga: acumula duas pendências
    carla = criar_usuario(db, "Carla")    # Pix pendente e depois recusado
    davi = criar_usuario(db, "Davi")      # sem atendimento elegível
    elis = criar_usuario(db, "Elis")      # só cancelado e cliente próprio

    # ---------------- DIA 1
    atender(db, ana, cliente, 5, utc(D1, 10))      # 5 x 50 = 250 -> 25
    atender(db, bruno, cliente, 10, utc(D1, 11))   # 10 x 50 = 500 -> 50
    atender(db, carla, cliente, 2, utc(D1, 12), valor=40.0)  # 80 -> 8
    atender(db, elis, cliente, 1, utc(D1, 13), status=models.StatusAgendamento.CANCELADO.value)
    atender(db, elis, cliente, 1, utc(D1, 14), origem=models.OrigemCliente.PROPRIO.value)
    atender(db, ana, cliente, 1, utc(D1, 21, 30))  # depois das 21h: entra no dia 2
    # Atendimento anterior à data de corte: não é cobrado retroativamente
    atender(db, bruno, cliente, 3, utc(D1, 10) - timedelta(days=2))

    ciclo(db, relogio, sp(D1, 20, 59))
    assert execucao(db, D1, pd.ROTINA_FECHAMENTO) is None, "não fecha antes das 21:00"
    assert saldo(db, ana) == 0.0

    ciclo(db, relogio, sp(D1, 21, 0))
    ex = execucao(db, D1, pd.ROTINA_FECHAMENTO)
    assert ex.status == "concluido", ex.erros
    assert (ex.atendimentos_contabilizados, ex.comissoes_calculadas, ex.valor_comissoes) == (17, 17, 83.0)
    assert (ex.fechamentos_criados, ex.pix_criados, ex.freelancers_analisados) == (3, 3, 3)
    assert ex.fuso_horario == "America/Sao_Paulo" and ex.iniciado_em and ex.concluido_em
    assert (saldo(db, ana), saldo(db, bruno), saldo(db, carla), saldo(db, davi), saldo(db, elis)) == \
        (-25.0, -50.0, -8.0, 0.0, 0.0)
    for u, valor in ((ana, 25.0), (bruno, 50.0), (carla, 8.0)):
        c = pix_aberto(db, u)
        assert c and c.pix_copia_cola and c.qr_code_base64 and float(c.valor) == valor
    assert pix_aberto(db, davi) is None and pix_aberto(db, elis) is None

    # 21:00-22:00: ninguém bloqueado; reprocessar não duplica nada
    antes = contagens(db)
    for minuto in (1, 15, 40, 59):
        ciclo(db, relogio, sp(D1, 21, minuto))
    assert contagens(db) == antes
    assert not bloqueado(db, bruno, sp(D1, 21, 59))

    # Freelancer online antes das 22h: a restrição o coloca OFFLINE (sem ligar ninguém depois)
    bruno.online_regiao = True
    bruno.disponivel = True
    db.commit()

    ciclo(db, relogio, sp(D1, 22, 0))
    ex22 = execucao(db, D1, pd.ROTINA_BLOQUEIO)
    assert ex22.status == "concluido" and ex22.freelancers_bloqueados == 3
    for u in (ana, bruno, carla):
        assert bloqueado(db, u, sp(D1, 22, 0))
    assert not bloqueado(db, davi, sp(D1, 22, 0)) and not bloqueado(db, elis, sp(D1, 22, 0))
    db.refresh(bruno)
    assert (bruno.online_regiao, bruno.disponivel) == (False, False)

    # Bloqueio validado no backend (rota HTTP real), login/consulta da carteira continuam liberados
    r = cliente_http.post(f"/api/v1/freelancer/{bruno.id}/alterar-status", json={"status": "online"},
                          headers=token(bruno))
    assert r.status_code == 403, r.text
    r = cliente_http.get("/api/v1/freelancer/carteira/resumo", headers=token(bruno))
    assert r.status_code == 200 and r.json()["pagamento_diario"]["bloqueado"] is True
    assert r.json()["pagamento_diario"]["cobranca_pix"]["pix_copia_cola"]
    r = cliente_http.post(f"/api/v1/freelancer/{davi.id}/alterar-status", json={"status": "online"},
                          headers=token(davi))
    assert r.status_code != 403, "freelancer sem débito não é bloqueado"

    # Ana paga às 22:30 -> webhook assinado do Mercado Pago -> liberada na hora
    relogio["agora"] = sp(D1, 22, 30)
    pix_ana = pix_aberto(db, ana)
    mp.definir(pix_ana.provedor_pagamento_id, "approved", aprovado_em=utc(D1, 22, 30))
    r = cliente_http.post(f"/api/v1/cobrancas/webhook/mercadopago?data.id={pix_ana.provedor_pagamento_id}&type=payment",
                          json={"type": "payment", "data": {"id": pix_ana.provedor_pagamento_id}},
                          headers=assinar(pix_ana.provedor_pagamento_id))
    assert r.status_code == 200 and r.json()["status"] == StatusCobranca.PAGO.value, r.text
    db.expire_all()
    assert not bloqueado(db, ana, sp(D1, 22, 31))
    assert saldo(db, ana) == 0.0
    db.refresh(ana)
    assert (ana.online_regiao, ana.presente_em_local) == (False, False), "não liga online/presente sozinho"
    # Webhook repetido (o MP reenvia) não credita de novo
    cliente_http.post(f"/api/v1/cobrancas/webhook/mercadopago?data.id={pix_ana.provedor_pagamento_id}&type=payment",
                      json={}, headers=assinar(pix_ana.provedor_pagamento_id))
    db.expire_all()
    assert saldo(db, ana) == 0.0
    assert db.query(models.HistoricoMovimentacaoFinanceira).filter_by(
        barbeiro_id=ana.id, tipo="quitacao_debito_pix").count() == 1
    # Ana escolhe ficar online: agora é permitido
    r = cliente_http.post(f"/api/v1/freelancer/{ana.id}/alterar-status", json={"status": "online"},
                          headers=token(ana))
    assert r.status_code != 403, r.text

    # Carla: Pix pendente não libera; recusado também não
    pix_carla = pix_aberto(db, carla)
    from app.cobrancas import servico
    servico.processar_notificacao(db, pix_carla.provedor_pagamento_id)
    db.expire_all()
    assert bloqueado(db, carla, sp(D1, 23))
    mp.definir(pix_carla.provedor_pagamento_id, "rejected")
    servico.processar_notificacao(db, pix_carla.provedor_pagamento_id)
    db.expire_all()
    assert bloqueado(db, carla, sp(D1, 23))
    assert saldo(db, carla) == -8.0
    # Webhook sem assinatura válida não aprova nada (o status vem sempre do MP)
    r = cliente_http.post(f"/api/v1/cobrancas/webhook/mercadopago?data.id={pix_carla.provedor_pagamento_id}&type=payment",
                          json={}, headers={"x-signature": "ts=1,v1=falso"})
    db.expire_all()
    assert bloqueado(db, carla, sp(D1, 23))
    # Pix recusado: o job gera outro para ela poder pagar
    ciclo(db, relogio, sp(D1, 23, 5))
    novo_carla = pix_aberto(db, carla)
    assert novo_carla and novo_carla.id != pix_carla.id

    # ---------------- DIA 2: bloqueio persiste de madrugada
    ciclo(db, relogio, sp(D2, 3))
    assert bloqueado(db, bruno, sp(D2, 3)) and bloqueado(db, carla, sp(D2, 3))
    with pytest.raises(HTTPException) as e:
        pd.exigir_freelancer_liberado(db, bruno.id)
    assert e.value.status_code == 403

    atender(db, bruno, cliente, 2, utc(D2, 15))  # Bruno trabalhava em atendimento já aceito: 2 x 50
    ciclo(db, relogio, sp(D2, 21, 0))
    ex = execucao(db, D2, pd.ROTINA_FECHAMENTO)
    assert ex.status == "concluido", ex.erros
    # Ana: 1 atendimento das 21:30 do dia 1 (R$ 5); Bruno: 2 (R$ 10)
    assert (ex.atendimentos_contabilizados, ex.valor_comissoes) == (3, 15.0)
    assert saldo(db, bruno) == -60.0
    abertos_bruno = pd.fechamentos_abertos(db, bruno.id)
    assert [(f.data_referencia, f.valor_devido) for f in abertos_bruno] == [(D1, 50.0), (D2, 10.0)]
    pix_bruno = pix_aberto(db, bruno)
    assert float(pix_bruno.valor) == 60.0, "um Pix cobre as duas pendências"
    pix_ana_d2 = pix_aberto(db, ana)
    assert float(pix_ana_d2.valor) == 5.0
    ciclo(db, relogio, sp(D2, 22, 0))
    assert bloqueado(db, ana, sp(D2, 22, 0)), "nova taxa não paga bloqueia de novo"
    assert execucao(db, D2, pd.ROTINA_BLOQUEIO).freelancers_bloqueados == 3

    # ---------------- DIA 3: Bruno quita tudo; confirmação chega pela conciliação (sem webhook)
    ciclo(db, relogio, sp(D3, 9))
    mp.definir(pix_bruno.provedor_pagamento_id, "approved", aprovado_em=utc(D3, 9))
    c = db.query(models.Cobranca).get(pix_bruno.id)
    c.criado_em = datetime.utcnow() - timedelta(minutes=10)  # conciliação só olha Pix com mais de 5 min
    db.commit()
    ciclo(db, relogio, sp(D3, 9, 1))
    assert not bloqueado(db, bruno, sp(D3, 9, 1))
    assert saldo(db, bruno) == 0.0
    assert all(f.status == "confirmado" for f in db.query(models.FechamentoDiarioFreelancer).filter_by(
        freelancer_id=bruno.id))
    db.refresh(bruno)
    assert (bruno.online_regiao, bruno.presente_em_local, bruno.disponivel) == (False, False, False)

    ciclo(db, relogio, sp(D3, 21, 0))
    ciclo(db, relogio, sp(D3, 22, 0))
    for d in (D1, D2, D3):
        assert execucao(db, d, pd.ROTINA_FECHAMENTO).status == "concluido"
        assert execucao(db, d, pd.ROTINA_BLOQUEIO).status == "concluido"
    # Dia 3 sem atendimentos novos: rotina registrada mesmo assim, sem cobrança nova
    ex3 = execucao(db, D3, pd.ROTINA_FECHAMENTO)
    assert (ex3.comissoes_calculadas, ex3.fechamentos_criados, ex3.pix_criados) == (0, 0, 0)
    assert not bloqueado(db, bruno, sp(D3, 22, 0)) and not bloqueado(db, davi, sp(D3, 22, 0))
    assert bloqueado(db, ana, sp(D3, 22, 0)) and bloqueado(db, carla, sp(D3, 22, 0))


# ------------------------------------------------------------------ limite das 21:00

def test_chamados_depois_das_21h_vao_para_o_proximo_ciclo(ambiente, cliente_http):
    db, mp, relogio = ambiente
    cliente = criar_usuario(db, "Cliente", tipo="cliente")
    lia = criar_usuario(db, "Lia")

    def concluir(hh, mm, valor):
        c = models.Chamado(cliente_id=cliente.id, barbeiro_id=lia.id, valor_total=valor,
                           status=models.StatusAgendamento.CONCLUIDO.value,
                           origem_cliente=models.OrigemCliente.APP.value, concluido_em=utc(D1, hh, mm))
        db.add(c)
        db.commit()
        return c.id

    # Serviços de valores diferentes: a soma identifica exatamente quem entrou em cada Pix
    ate_o_limite = [concluir(20, 50, 100.0), concluir(21, 0, 80.0)]
    depois = [concluir(21, 5, 60.0), concluir(21, 30, 40.0), concluir(22, 10, 20.0)]
    horarios = {c.id: c.concluido_em for c in db.query(models.Chamado).all()}

    def carteira(quando):
        relogio["agora"] = quando
        r = cliente_http.get("/api/v1/freelancer/carteira/resumo", headers=token(lia))
        assert r.status_code == 200, r.text
        return r.json()

    def chamados_do_fechamento(d):
        f = db.query(models.FechamentoDiarioFreelancer).filter_by(freelancer_id=lia.id, data_referencia=d).one()
        return f, sorted(m.chamado_id for m in f.movimentacoes)

    # Enquanto o fechamento não roda, tudo aparece como pendente e o saldo não muda
    pendentes = carteira(sp(D1, 22, 15))["pagamento_diario"]["pendentes_proximo_fechamento"]
    assert [a["chamado_id"] for a in pendentes["atendimentos"]] == ate_o_limite + depois
    assert saldo(db, lia) == 0.0

    # Ciclo 1: 20:50 e 21:00 (limite inclusivo) entram; 21:05, 21:30 e 22:10 ficam pendentes
    ciclo(db, relogio, sp(D1, 21, 0))
    f1, chamados_f1 = chamados_do_fechamento(D1)
    assert chamados_f1 == ate_o_limite
    assert f1.valor_devido == 18.0 and saldo(db, lia) == -18.0
    pix1 = pix_aberto(db, lia)
    assert float(pix1.valor) == 18.0, "o Pix cobre só os serviços do ciclo"

    # Às 22:15 e na manhã seguinte os pendentes continuam visíveis na carteira, com o horário real
    for quando in (sp(D1, 22, 15), sp(D2, 12, 0)):
        ciclo(db, relogio, quando)
        pd_resumo = carteira(quando)["pagamento_diario"]
        pendentes = pd_resumo["pendentes_proximo_fechamento"]
        assert [a["chamado_id"] for a in pendentes["atendimentos"]] == depois
        assert pendentes["comissao_prevista"] == 12.0
        assert pendentes["proximo_fechamento"] == sp(D2, 21).isoformat()
        assert pendentes["atendimentos"][0]["concluido_em"] == utc(D1, 21, 5).isoformat() + "Z"
    assert saldo(db, lia) == -18.0, "pendente aparece, mas só é lançado no fechamento"

    # Paga o ciclo 1 pelo caminho real do Mercado Pago
    from app.cobrancas import servico
    mp.definir(pix1.provedor_pagamento_id, "approved", aprovado_em=utc(D2, 12))
    servico.processar_notificacao(db, pix1.provedor_pagamento_id)
    db.expire_all()
    assert saldo(db, lia) == 0.0

    # Ciclo 2: todos os pendentes entram e somem da lista; comissão prevista = comissão lançada
    ciclo(db, relogio, sp(D2, 21, 0))
    f2, chamados_f2 = chamados_do_fechamento(D2)
    assert chamados_f2 == depois
    assert f2.valor_devido == 12.0 and saldo(db, lia) == -12.0
    assert float(pix_aberto(db, lia).valor) == 12.0
    assert carteira(sp(D2, 21, 1))["pagamento_diario"]["pendentes_proximo_fechamento"]["atendimentos"] == []

    # Reprocessar o fechamento não duplica; cada chamado tem exatamente uma comissão
    antes = contagens(db)
    ex = execucao(db, D2, pd.ROTINA_FECHAMENTO)
    ex.status = "parcial"
    ex.atualizado_em = utc(D2, 20)
    db.commit()
    ciclo(db, relogio, sp(D2, 21, 30))
    ciclo(db, relogio, sp(D3, 21, 0))
    assert contagens(db) == antes
    assert saldo(db, lia) == -12.0
    for chamado_id in ate_o_limite + depois:
        assert db.query(models.HistoricoMovimentacaoFinanceira).filter_by(
            chamado_id=chamado_id, tipo="debito_taxa_dinheiro").count() == 1
    # O horário real de finalização é preservado
    assert {c.id: c.concluido_em for c in db.query(models.Chamado).all()} == horarios


# ------------------------------------------------------------------ fuso horário

def test_finalizacao_grava_utc_em_servidor_com_qualquer_fuso(ambiente, cliente_http):
    """O corte das 21:00 assume UTC no banco: finalizar não pode depender do fuso do servidor."""
    db, mp, relogio = ambiente
    cliente = criar_usuario(db, "Cliente", tipo="cliente")
    nina = criar_usuario(db, "Nina")
    c = models.Chamado(cliente_id=cliente.id, barbeiro_id=nina.id, valor_total=50.0,
                       status=models.StatusAgendamento.EM_ATENDIMENTO.value,
                       origem_cliente=models.OrigemCliente.APP.value)
    db.add(c)
    db.commit()

    r = cliente_http.put(f"/api/v1/chamados/{c.id}/finalizar", headers=token(nina))
    assert r.status_code == 200, r.text
    db.expire_all()
    c = db.get(models.Chamado, c.id)
    agora_real = datetime.now(pd.TZ_SP)
    assert abs((pd._sp_de_utc_naive(c.concluido_em) - agora_real).total_seconds()) < 60
    assert abs((c.concluido_em - c.data_hora_fim).total_seconds()) < 60


def test_checkin_usa_o_dia_de_brasilia(ambiente, cliente_http):
    """Depois das 21:00 já é outro dia em UTC: o agendamento da noite ainda é de hoje."""
    db, mp, relogio = ambiente
    cliente = criar_usuario(db, "Cliente", tipo="cliente")
    dono = criar_usuario(db, "Dono", tipo="barbearia")
    otto = criar_usuario(db, "Otto")
    loja = models.Barbearia(usuario_id=dono.id, nome="Loja", endereco="", latitude=-23.5, longitude=-46.6)
    db.add(loja)
    db.commit()
    db.add(models.Chamado(cliente_id=cliente.id, barbeiro_id=otto.id, barbearia_id=loja.id, valor_total=50.0,
                          status=models.StatusAgendamento.CONFIRMADO.value, data_hora_inicio=utc(D1, 21, 45)))
    db.commit()

    def checkin(quando):
        relogio["agora"] = quando
        r = cliente_http.post("/api/v1/geo/check-proximity", json={"latitude": 0.0, "longitude": 0.0},
                              headers=token(otto))
        assert r.status_code == 200, r.text
        return r.json()

    nenhum = "Nenhum agendamento confirmado para hoje"
    assert checkin(sp(D1, 21, 30)).get("mensagem") != nenhum, "21:30 em Brasília: ainda é o mesmo dia"
    assert checkin(sp(D2, 8, 0)).get("mensagem") == nenhum, "na manhã seguinte não é mais de hoje"


# ------------------------------------------------------------------ idempotência e recuperação

def test_reprocessar_execucao_nao_duplica(ambiente):
    db, mp, relogio = ambiente
    cliente = criar_usuario(db, "Cliente", tipo="cliente")
    fabi = criar_usuario(db, "Fabi")
    atender(db, fabi, cliente, 4, utc(D1, 10))

    ciclo(db, relogio, sp(D1, 21, 0))
    antes = contagens(db)
    assert saldo(db, fabi) == -20.0

    # Força o reprocessamento da rotina já concluída
    ex = execucao(db, D1, pd.ROTINA_FECHAMENTO)
    ex.status = "parcial"
    ex.atualizado_em = utc(D1, 20)
    db.commit()
    ciclo(db, relogio, sp(D1, 21, 30))
    assert execucao(db, D1, pd.ROTINA_FECHAMENTO).tentativas == 2
    assert contagens(db) == antes
    assert saldo(db, fabi) == -20.0
    assert mp.criados == 1, "Pix reaproveitado, não criado de novo"

    # Reinicialização simulada: estado em memória zerado e sessão nova
    pd._falhas_pix.clear()
    db2 = SessionLocal()
    pd._ciclo_job(db=db2, agora=sp(D1, 21, 45))
    db2.close()
    db.expire_all()
    assert contagens(db) == antes and mp.criados == 1

    # Duas "instâncias" no mesmo instante: só uma roda a rotina do dia
    atender(db, fabi, cliente, 1, utc(D2, 10))
    db_a, db_b = SessionLocal(), SessionLocal()
    assert pd._reivindicar_execucao(db_a, D2, pd.ROTINA_FECHAMENTO, sp(D2, 21)) is not None
    assert pd._reivindicar_execucao(db_b, D2, pd.ROTINA_FECHAMENTO, sp(D2, 21)) is None
    db_a.close()
    db_b.close()


def test_execucao_interrompida_e_falha_parcial_sao_retomadas(ambiente, monkeypatch):
    db, mp, relogio = ambiente
    cliente = criar_usuario(db, "Cliente", tipo="cliente")
    gabi = criar_usuario(db, "Gabi")
    atender(db, gabi, cliente, 3, utc(D1, 10))

    # Processo morreu no meio da rotina: ficou 'em_execucao'
    db.add(models.ExecucaoPagamentoDiario(data_referencia=D1, rotina=pd.ROTINA_FECHAMENTO,
                                          status="em_execucao", tentativas=1, instancia="morta",
                                          iniciado_em=utc(D1, 21), atualizado_em=utc(D1, 21)))
    db.commit()
    ciclo(db, relogio, sp(D1, 21, 5))
    assert execucao(db, D1, pd.ROTINA_FECHAMENTO).status == "em_execucao", "espera a trava vencer"
    assert saldo(db, gabi) == 0.0
    ciclo(db, relogio, sp(D1, 21, 11))
    ex = execucao(db, D1, pd.ROTINA_FECHAMENTO)
    assert ex.status == "concluido" and ex.tentativas == 2
    assert saldo(db, gabi) == -15.0

    # Falha no Mercado Pago ao gerar o Pix: fica 'parcial' (não 'concluido') e é retomada
    hugo = criar_usuario(db, "Hugo")
    atender(db, hugo, cliente, 2, utc(D2, 10))
    original = mp.criar_pix

    def falha(**kw):
        raise provedores.ErroProvedor("MP fora do ar")
    monkeypatch.setattr(mp, "criar_pix", falha)
    ciclo(db, relogio, sp(D2, 21, 0))
    ex = execucao(db, D2, pd.ROTINA_FECHAMENTO)
    assert ex.status == "parcial" and "sem Pix" in ex.erros
    assert saldo(db, hugo) == -10.0 and pix_aberto(db, hugo) is None

    monkeypatch.setattr(mp, "criar_pix", original)
    pd._falhas_pix.clear()
    ciclo(db, relogio, sp(D2, 21, 2))
    assert execucao(db, D2, pd.ROTINA_FECHAMENTO).status == "parcial", "respeita o intervalo de retentativa"
    ciclo(db, relogio, sp(D2, 21, 6))
    ex = execucao(db, D2, pd.ROTINA_FECHAMENTO)
    assert ex.status == "concluido" and pix_aberto(db, hugo) is not None
    assert saldo(db, hugo) == -10.0, "retomar não lança a comissão de novo"
    assert "tentativa 1" in ex.erros, "o erro da tentativa anterior fica registrado"


def test_fechamento_perdido_e_recuperado_com_prazo_minimo(ambiente):
    db, mp, relogio = ambiente
    cliente = criar_usuario(db, "Cliente", tipo="cliente")
    ivo = criar_usuario(db, "Ivo")
    atender(db, ivo, cliente, 2, utc(D1, 10))

    # Servidor fora do ar das 20:50 às 01:30: nenhum ciclo às 21h/22h do dia 1
    ciclo(db, relogio, sp(D1, 20, 50))
    ciclo(db, relogio, sp(D2, 1, 30))
    ex = execucao(db, D1, pd.ROTINA_FECHAMENTO)
    assert ex.status == "concluido", "o fechamento perdido do dia 1 roda ao voltar"
    f = pd.fechamentos_abertos(db, ivo.id)[0]
    assert f.data_referencia == D1 and f.valor_devido == 10.0
    assert pd.prazo_do_fechamento(f) == sp(D2, 2, 30), "uma hora para pagar, em vez de bloquear na hora"
    assert not bloqueado(db, ivo, sp(D2, 2, 29))
    ciclo(db, relogio, sp(D2, 2, 31))
    assert bloqueado(db, ivo, sp(D2, 2, 31))
    assert execucao(db, D1, pd.ROTINA_BLOQUEIO).status == "concluido"
