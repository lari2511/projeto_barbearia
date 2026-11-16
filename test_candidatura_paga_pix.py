"""
Taxa de candidatura (R$ 3,00) via Pix antes de liberar a candidatura a uma vaga de diária.

Fluxo completo com Mercado Pago falso (definir_provedor_para_testes) e SQLite temporário:
candidatar-se -> 402 -> gerar Pix -> copiar código -> pagamento aprovado -> webhook -> candidatura liberada.
Nenhum dinheiro real é movimentado.

    .venv/Scripts/python -m pytest test_candidatura_paga_pix.py -v
"""

import os
import tempfile
from datetime import datetime, timedelta

_DB = os.path.join(tempfile.mkdtemp(prefix="bm_cand_pix_"), "teste.db")
os.environ["DATABASE_URL"] = f"sqlite:///{_DB}"
os.environ.pop("MERCADOPAGO_WEBHOOK_SECRET", None)

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app import models, routes_on_demand  # noqa: E402
from app.cobrancas import candidatura_vaga, provedores  # noqa: E402
from app.database import Base, SessionLocal, engine, init_db  # noqa: E402
from app.main import app  # noqa: E402
from test_anuncio_vagas import BASE, _barbearia, _enviar_direto, _publicar  # noqa: E402
from test_anuncio_vagas import _freelancer as _freelancer_base  # noqa: E402

PIX = "/api/v1/cobrancas"


def _definir_cadastro(fid, criado_em):
    db = SessionLocal()
    try:
        db.query(models.Usuario).filter(models.Usuario.id == fid).update({models.Usuario.criado_em: criado_em})
        db.commit()
    finally:
        db.close()


def _freelancer(email, dias_de_cadastro=45):
    """Freelancer já fora dos 30 dias grátis (padrão), para exercitar a cobrança."""
    fid, headers = _freelancer_base(email)
    _definir_cadastro(fid, datetime.utcnow() - timedelta(days=dias_de_cadastro))
    return fid, headers


class MercadoPagoFalso(provedores.ProvedorPagamento):
    nome = "mercadopago"

    def __init__(self):
        self.pagamentos = {}
        self.criados = 0
        self.cancelados = []

    def criar_pix(self, *, identificador, valor, descricao, email_pagador, expira_em):
        self.criados += 1
        pid = str(700000 + self.criados)
        p = provedores.PagamentoProvedor(
            provedor_pagamento_id=pid, status="pending", valor=valor, referencia_externa=identificador,
            pix_copia_cola=f"00020126BR.GOV.BCB.PIX{pid}", qr_code_base64="iVBORw0KGgoFALSO", expira_em=expira_em)
        self.pagamentos[pid] = p
        return p

    def consultar(self, provedor_pagamento_id):
        return self.pagamentos[provedor_pagamento_id]

    def cancelar(self, provedor_pagamento_id):
        self.cancelados.append(provedor_pagamento_id)

    def pagar(self, pid):
        self.pagamentos[pid].status = "approved"


@pytest.fixture(autouse=True)
def sem_rota_externa(monkeypatch):
    monkeypatch.setattr(routes_on_demand, "_calcular_eta_osrm_minutos", lambda *a, **k: 3)


@pytest.fixture()
def ambiente(monkeypatch):
    Base.metadata.drop_all(bind=engine)
    init_db()
    mp = MercadoPagoFalso()
    provedores.definir_provedor_para_testes(mp)
    monkeypatch.setenv("TAXA_CANDIDATURA_VAGA_ATIVA", "1")
    yield TestClient(app), mp
    provedores.definir_provedor_para_testes(None)


def _cenario(http, vagas=1, email="dono@t.com"):
    loja = _barbearia(email, vagas)
    ids = _publicar(http, loja, vagas)
    return loja, ids


def _candidatos(http, loja, vaga_id):
    r = http.get(f"{BASE}/{vaga_id}/candidatos", headers=loja["headers"])
    assert r.status_code == 200, r.text
    return r.json()


def _webhook(http, pid):
    return http.post(f"{PIX}/webhook/mercadopago?type=payment&data.id={pid}", json={"type": "payment", "data": {"id": pid}})


def _contar(modelo, **filtros):
    db = SessionLocal()
    try:
        q = db.query(modelo)
        for k, v in filtros.items():
            q = q.filter(getattr(modelo, k) == v)
        return q.count()
    finally:
        db.close()


def test_fluxo_completo_candidatar_pagar_webhook_libera(ambiente):
    http, mp = ambiente
    loja, (vaga_id,) = _cenario(http)
    fid, fh = _freelancer("free@t.com")

    # 1. Clicar em candidatar-se: precisa pagar, nada registrado.
    r = http.post(f"{BASE}/{vaga_id}/candidatar-se", headers=fh)
    assert r.status_code == 402, r.text
    assert "R$ 3,00" in r.json()["detail"]
    assert _candidatos(http, loja, vaga_id) == []

    # 2. Gerar o Pix: valor fixo do servidor, copia e cola + QR.
    r = http.post(f"{PIX}/pix/candidatura-vaga", json={"vaga_id": vaga_id}, headers=fh)
    assert r.status_code == 200, r.text
    cob = r.json()
    assert cob["finalidade"] == "CANDIDATURA_VAGA"
    assert cob["valor"] == 3.0
    assert cob["status"] == "AGUARDANDO_PAGAMENTO"
    assert cob["pix_copia_cola"].startswith("000201")
    assert cob["qr_code_base64"]
    pid = mp.pagamentos[next(iter(mp.pagamentos))].provedor_pagamento_id

    # Tentar de novo (clique duplo / reabrir a tela) devolve o MESMO Pix.
    r2 = http.post(f"{PIX}/pix/candidatura-vaga", json={"vaga_id": vaga_id}, headers=fh)
    assert r2.json()["identificador"] == cob["identificador"]
    assert mp.criados == 1

    # 3. Pendente no MP: webhook não libera nada; o dono continua sem candidato.
    assert _webhook(http, pid).status_code == 200
    assert _candidatos(http, loja, vaga_id) == []
    assert http.post(f"{BASE}/{vaga_id}/candidatar-se", headers=fh).status_code == 402

    # 4. Pagamento aprovado + webhook oficial: candidatura liberada.
    mp.pagar(pid)
    r = _webhook(http, pid)
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "PAGO"
    candidatos = _candidatos(http, loja, vaga_id)
    assert [c["freelancer_id"] for c in candidatos] == [fid]
    assert _contar(models.Notificacao, usuario_id=loja["dono_id"], tipo="vaga_candidatura") == 1

    # 5. A tela do app (consulta) mostra PAGO + liberado.
    r = http.get(f"{PIX}/{cob['identificador']}", headers=fh)
    assert r.json()["status"] == "PAGO" and r.json()["liberado"] is True

    # 6. Notificações repetidas do MP não duplicam nada.
    for _ in range(3):
        assert _webhook(http, pid).status_code == 200
    assert len(_candidatos(http, loja, vaga_id)) == 1
    assert _contar(models.CandidaturaPaga) == 1
    assert _contar(models.Notificacao, usuario_id=loja["dono_id"], tipo="vaga_candidatura") == 1

    # 7. Candidatar-se de novo na mesma vaga: sem nova cobrança.
    assert http.post(f"{BASE}/{vaga_id}/candidatar-se", headers=fh).status_code == 200
    assert http.post(f"{PIX}/pix/candidatura-vaga", json={"vaga_id": vaga_id}, headers=fh).status_code == 409
    assert mp.criados == 1

    # 8. Histórico registrado.
    db = SessionLocal()
    try:
        origens = [h.origem for h in db.query(models.CobrancaHistorico).order_by(models.CobrancaHistorico.id)]
    finally:
        db.close()
    assert origens[0] == "criada" and "liberada" in origens


def test_pagamento_libera_uma_unica_candidatura(ambiente):
    """O mesmo Pix não serve para outra vaga: a segunda vaga exige um Pix novo."""
    http, mp = ambiente
    loja, (v1, v2) = _cenario(http, vagas=2)
    fid, fh = _freelancer("free@t.com")

    cob = http.post(f"{PIX}/pix/candidatura-vaga", json={"vaga_id": v1}, headers=fh).json()
    pid = "700001"
    mp.pagar(pid)
    _webhook(http, pid)
    assert len(_candidatos(http, loja, v1)) == 1

    assert http.post(f"{BASE}/{v2}/candidatar-se", headers=fh).status_code == 402
    assert _candidatos(http, loja, v2) == []
    cob2 = http.post(f"{PIX}/pix/candidatura-vaga", json={"vaga_id": v2}, headers=fh).json()
    assert cob2["identificador"] != cob["identificador"]


def test_vaga_fechou_antes_da_confirmacao_vira_credito_sem_cobrar_de_novo(ambiente):
    http, mp = ambiente
    loja, (v1, v2) = _cenario(http, vagas=2)
    fid, fh = _freelancer("free@t.com")

    http.post(f"{PIX}/pix/candidatura-vaga", json={"vaga_id": v1}, headers=fh)
    db = SessionLocal()
    try:
        db.query(models.CadeiraAcionada).filter(models.CadeiraAcionada.id == v1).update({"status": "expirada"})
        db.commit()
    finally:
        db.close()

    mp.pagar("700001")
    assert _webhook(http, "700001").json()["status"] == "PAGO"
    assert _candidatos(http, loja, v1) == []
    assert _contar(models.CandidaturaPaga, status=candidatura_vaga.CREDITO) == 1
    assert _contar(models.Notificacao, usuario_id=fid, tipo="vaga_credito_candidatura") == 1

    # Não gera Pix novo enquanto houver crédito.
    assert http.post(f"{PIX}/pix/candidatura-vaga", json={"vaga_id": v2}, headers=fh).status_code == 409
    # Candidatar-se em outra vaga usa o crédito, sem novo Pix.
    assert http.post(f"{BASE}/{v2}/candidatar-se", headers=fh).status_code == 200
    assert [c["freelancer_id"] for c in _candidatos(http, loja, v2)] == [fid]
    assert mp.criados == 1
    assert _contar(models.CandidaturaPaga, status=candidatura_vaga.CONCLUIDA) == 1
    assert _contar(models.CandidaturaPaga, status=candidatura_vaga.CREDITO) == 0


def test_falha_ao_concluir_candidatura_recupera_sem_cobrar(ambiente, monkeypatch):
    http, mp = ambiente
    loja, (vaga_id,) = _cenario(http)
    fid, fh = _freelancer("free@t.com")
    http.post(f"{PIX}/pix/candidatura-vaga", json={"vaga_id": vaga_id}, headers=fh)

    original = routes_on_demand.registrar_candidatura

    def quebrar(*a, **k):
        raise RuntimeError("falha simulada ao gravar")

    monkeypatch.setattr(routes_on_demand, "registrar_candidatura", quebrar)
    mp.pagar("700001")
    r = _webhook(http, "700001")
    assert r.status_code == 200 and r.json()["status"] == "PAGO"
    assert _candidatos(http, loja, vaga_id) == []
    assert _contar(models.CandidaturaPaga, status=candidatura_vaga.CREDITO) == 1

    # Recuperação: tocar em candidatar-se de novo conclui com o crédito, sem novo Pix.
    monkeypatch.setattr(routes_on_demand, "registrar_candidatura", original)
    assert http.post(f"{BASE}/{vaga_id}/candidatar-se", headers=fh).status_code == 200
    assert [c["freelancer_id"] for c in _candidatos(http, loja, vaga_id)] == [fid]
    assert mp.criados == 1


def test_nao_cobra_quem_nao_pode_se_candidatar(ambiente):
    http, mp = ambiente
    loja, (vaga_id,) = _cenario(http)
    fid, fh = _freelancer("free@t.com")
    db = SessionLocal()
    try:
        db.query(models.RadarFreelancer).filter(models.RadarFreelancer.freelancer_id == fid).update({"is_online": False})
        db.commit()
    finally:
        db.close()
    r = http.post(f"{PIX}/pix/candidatura-vaga", json={"vaga_id": vaga_id}, headers=fh)
    assert r.status_code == 400
    assert mp.criados == 0 and _contar(models.Cobranca) == 0


def test_pix_de_outra_vaga_e_cancelado_ao_trocar(ambiente):
    """Uma cobrança em aberto por vez: gerar o Pix de outra vaga cancela o anterior."""
    http, mp = ambiente
    loja, (v1, v2) = _cenario(http, vagas=2)
    fid, fh = _freelancer("free@t.com")
    c1 = http.post(f"{PIX}/pix/candidatura-vaga", json={"vaga_id": v1}, headers=fh).json()
    c2 = http.post(f"{PIX}/pix/candidatura-vaga", json={"vaga_id": v2}, headers=fh).json()
    assert c1["identificador"] != c2["identificador"]
    assert mp.cancelados == ["700001"]
    # Se o Pix antigo for pago mesmo assim, a aprovação é honrada (candidatura na vaga 1).
    mp.pagar("700001")
    _webhook(http, "700001")
    assert [c["freelancer_id"] for c in _candidatos(http, loja, v1)] == [fid]


def test_taxa_desligada_mantem_candidatura_como_antes(ambiente, monkeypatch):
    http, mp = ambiente
    monkeypatch.setenv("TAXA_CANDIDATURA_VAGA_ATIVA", "0")
    loja, (vaga_id,) = _cenario(http)
    fid, fh = _freelancer("free@t.com")
    assert http.post(f"{BASE}/{vaga_id}/candidatar-se", headers=fh).status_code == 200
    assert [c["freelancer_id"] for c in _candidatos(http, loja, vaga_id)] == [fid]
    assert _contar(models.Cobranca) == 0
    assert http.post(f"{PIX}/pix/candidatura-vaga", json={"vaga_id": vaga_id}, headers=fh).status_code == 409
    cfg = http.get(f"{PIX}/config").json()
    assert cfg["taxa_candidatura_vaga"] == {"ativa": False, "valor": 3.0}


def test_sem_mercado_pago_configurado_nao_cobra(ambiente, monkeypatch):
    http, mp = ambiente
    provedores.definir_provedor_para_testes(None)
    monkeypatch.delenv("MERCADOPAGO_ACCESS_TOKEN", raising=False)
    loja, (vaga_id,) = _cenario(http)
    fid, fh = _freelancer("free@t.com")
    assert http.post(f"{BASE}/{vaga_id}/candidatar-se", headers=fh).status_code == 200


# ============================================================
# 30 DIAS GRÁTIS (individual, a partir do cadastro) + VAGA DIRETA
# ============================================================

def test_dentro_dos_30_dias_candidata_sem_pagar(ambiente):
    http, mp = ambiente
    loja, (v1, v2) = _cenario(http, vagas=2)
    fid, fh = _freelancer("novo@t.com", dias_de_cadastro=10)

    for vaga_id in (v1, v2):  # quantas vagas quiser, sem taxa
        r = http.post(f"{BASE}/{vaga_id}/candidatar-se", headers=fh)
        assert r.status_code == 200, r.text
        assert [c["freelancer_id"] for c in _candidatos(http, loja, vaga_id)] == [fid]

    # Nem consegue gerar Pix: não há o que cobrar.
    assert http.post(f"{PIX}/pix/candidatura-vaga", json={"vaga_id": v1}, headers=fh).status_code in (400, 409)
    assert mp.criados == 0
    assert _contar(models.Cobranca) == 0


def test_gratuidade_e_individual_e_vence_no_dia_30(ambiente):
    http, mp = ambiente
    loja, (vaga_id,) = _cenario(http)
    _, novo_h = _freelancer("novo@t.com", dias_de_cadastro=0)
    antigo_id, antigo_h = _freelancer("antigo@t.com", dias_de_cadastro=31)

    assert http.post(f"{BASE}/{vaga_id}/candidatar-se", headers=novo_h).status_code == 200
    assert http.post(f"{BASE}/{vaga_id}/candidatar-se", headers=antigo_h).status_code == 402

    # Borda: um minuto antes de completar 30 dias ainda é grátis; um minuto depois, cobra.
    db = SessionLocal()
    try:
        u = db.query(models.Usuario).filter(models.Usuario.id == antigo_id).first()
        agora = datetime.utcnow()
        u.criado_em = agora - timedelta(days=30) + timedelta(minutes=1)
        assert candidatura_vaga.em_gratuidade(u, agora) is True
        u.criado_em = agora - timedelta(days=30) - timedelta(minutes=1)
        assert candidatura_vaga.em_gratuidade(u, agora) is False
        assert candidatura_vaga.fim_gratuidade(u) == u.criado_em + timedelta(days=30)
    finally:
        db.rollback()
        db.close()


def test_aceitar_vaga_enviada_direto_tambem_cobra(ambiente):
    http, mp = ambiente
    loja = _barbearia("dono@t.com", 1)
    fid, fh = _freelancer("conv@t.com")
    r = _enviar_direto(http, loja, fid)
    assert r.status_code == 201, r.text
    vaga_id = r.json()["publicadas"][0]

    # "Aceitar" = candidatar-se: pede o Pix antes.
    assert http.post(f"{BASE}/{vaga_id}/candidatar-se", headers=fh).status_code == 402
    assert _candidatos(http, loja, vaga_id) == []

    r = http.post(f"{PIX}/pix/candidatura-vaga", json={"vaga_id": vaga_id}, headers=fh)
    assert r.status_code == 200, r.text
    pid = next(iter(mp.pagamentos))
    mp.pagar(pid)
    assert _webhook(http, pid).status_code == 200
    assert [c["freelancer_id"] for c in _candidatos(http, loja, vaga_id)] == [fid]


def test_aceitar_vaga_direta_dentro_dos_30_dias_nao_cobra(ambiente):
    http, mp = ambiente
    loja = _barbearia("dono@t.com", 1)
    fid, fh = _freelancer("conv@t.com", dias_de_cadastro=5)
    vaga_id = _enviar_direto(http, loja, fid).json()["publicadas"][0]
    assert http.post(f"{BASE}/{vaga_id}/candidatar-se", headers=fh).status_code == 200
    assert mp.criados == 0


def test_nao_cobra_duas_vezes_a_mesma_vaga(ambiente):
    http, mp = ambiente
    loja, (vaga_id,) = _cenario(http)
    fid, fh = _freelancer("free@t.com")

    assert http.post(f"{BASE}/{vaga_id}/candidatar-se", headers=fh).status_code == 402
    http.post(f"{PIX}/pix/candidatura-vaga", json={"vaga_id": vaga_id}, headers=fh)
    pid = next(iter(mp.pagamentos))
    mp.pagar(pid)
    _webhook(http, pid)
    _webhook(http, pid)  # notificação repetida
    assert _contar(models.CandidaturaPaga, freelancer_id=fid) == 1

    # Clique repetido: já é candidato, não cobra nem duplica.
    assert http.post(f"{BASE}/{vaga_id}/candidatar-se", headers=fh).status_code == 200
    assert _contar(models.CadeiraAcionadaCandidatura, vaga_id=vaga_id, barbeiro_id=fid) == 1

    # Mesmo se a candidatura sumir (ex.: removida), a taxa desta vaga já foi paga: não cobra de novo.
    db = SessionLocal()
    try:
        db.query(models.CadeiraAcionadaCandidatura).filter(
            models.CadeiraAcionadaCandidatura.vaga_id == vaga_id).delete()
        db.commit()
    finally:
        db.close()
    assert http.post(f"{BASE}/{vaga_id}/candidatar-se", headers=fh).status_code == 200
    assert mp.criados == 1
    assert _contar(models.Cobranca) == 1
