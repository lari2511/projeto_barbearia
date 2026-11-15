"""
Validade individual de cada cadeira: um mês de calendário em São Paulo, renovação por cadeira.

SQLite temporário, sem chamadas externas.

    .venv/Scripts/python -m pytest test_vencimento_cadeiras.py -v
"""

import os
import tempfile
from datetime import datetime

_DB = os.path.join(tempfile.mkdtemp(prefix="bm_venc_"), "teste.db")
os.environ["DATABASE_URL"] = f"sqlite:///{_DB}"

import pytest  # noqa: E402

from app import models, vencimento_cadeiras as venc  # noqa: E402
from app.cobrancas.efeitos import EFEITOS  # noqa: E402
from app.database import Base, SessionLocal, engine, init_db  # noqa: E402
from app.routes_assinaturas import aplicar_contratacao_cadeiras, aplicar_pagamento_mensalidade, mensalidade_devida  # noqa: E402
from app.routes_cadeiras import _assinatura_ativa_e_limite  # noqa: E402
from app.vagas import cadeiras_pagas  # noqa: E402


def sp(a, m, d, h=12, mi=0):
    """Horário de São Paulo -> UTC sem fuso (formato do banco)."""
    return venc.para_utc_naive(datetime(a, m, d, h, mi, tzinfo=venc.TZ_SP))


def em_sp(utc):
    return venc.para_sp(utc).replace(tzinfo=None)


# ------------------------------------------------------------------ calendário

@pytest.mark.parametrize("inicio, esperado", [
    ((2026, 11, 20), (2026, 12, 20)),
    ((2026, 11, 25), (2026, 12, 25)),
    ((2026, 12, 3), (2027, 1, 3)),     # virada de ano
    ((2027, 1, 31), (2027, 2, 28)),    # fevereiro de 28
    ((2028, 1, 31), (2028, 2, 29)),    # bissexto
    ((2028, 1, 30), (2028, 2, 29)),
    ((2027, 1, 28), (2027, 2, 28)),
    ((2027, 3, 31), (2027, 4, 30)),    # mês de 30
    ((2027, 4, 30), (2027, 5, 30)),    # mês de 31 a partir de 30
    ((2027, 2, 28), (2027, 3, 28)),
])
def test_um_mes_de_calendario(inicio, esperado):
    assert em_sp(venc.somar_um_mes(sp(*inicio, 15, 30))) == datetime(*esperado, 15, 30)


def test_contratacao_a_noite_em_sp_nao_perde_um_dia():
    """30/01 às 23h em SP já é 31/01 em UTC: a conta em UTC daria 28/02 02h UTC = 27/02 em SP."""
    contratacao = sp(2027, 1, 30, 23, 0)
    assert contratacao.day == 31  # em UTC
    vencimento = venc.somar_um_mes(contratacao)
    assert em_sp(vencimento) == datetime(2027, 2, 28, 23, 0)


def test_dia_ancora_volta_ao_31_depois_de_fevereiro():
    fev = venc.somar_um_mes(sp(2027, 1, 31), 31)
    mar = venc.somar_um_mes(fev, 31)
    assert em_sp(fev).date() == datetime(2027, 2, 28).date()
    assert em_sp(mar).date() == datetime(2027, 3, 31).date()


@pytest.mark.parametrize("dia", range(1, 32))
def test_nenhum_vencimento_antes_de_um_mes(dia):
    """Para qualquer dia de janeiro, o vencimento nunca é antes do mesmo dia (ou fim) de fevereiro."""
    inicio = sp(2027, 1, dia, 21, 45)
    fim = em_sp(venc.somar_um_mes(inicio))
    assert fim.month == 2 and fim.day == min(dia, 28) and fim.hour == 21


# ------------------------------------------------------------------ banco

@pytest.fixture()
def db():
    Base.metadata.drop_all(bind=engine)
    init_db()
    s = SessionLocal()
    dono = models.Usuario(nome="dono", email="dono@t.com", senha_hash="x", tipo="barbearia", perfil_aprovado=True)
    s.add(dono)
    s.flush()
    b = models.Barbearia(usuario_id=dono.id, nome="Barbearia T", endereco="Rua A", latitude=-23.55, longitude=-46.63)
    s.add(b)
    s.commit()
    yield s
    s.close()


def _barbearia(db):
    return db.query(models.Barbearia).first()


def _cadeiras(db):
    return {c.numero_referencia: c for c in db.query(models.CadeiraContratada).filter(
        models.CadeiraContratada.ativa.is_(True))}


def _contratar(db, total, quando):
    a = aplicar_contratacao_cadeiras(db, _barbearia(db), total, "pix", agora=quando)
    db.commit()
    return a


def _pagar_mensalidade(db, monkeypatch, quando, cadeira_ids=None):
    monkeypatch.setattr(venc, "agora_utc", lambda: quando)
    a = db.query(models.AssinaturaBarbearia).first()
    aplicar_pagamento_mensalidade(db, _barbearia(db), a, "pix", cadeira_ids=cadeira_ids)
    db.commit()


def test_cada_cadeira_vence_um_mes_apos_a_propria_contratacao(db):
    _contratar(db, 1, sp(2026, 11, 20, 10))
    _contratar(db, 2, sp(2026, 11, 25, 18))
    _contratar(db, 3, sp(2026, 12, 3, 22, 30))
    c = _cadeiras(db)
    assert em_sp(c[1].data_proxima_cobranca) == datetime(2026, 12, 20, 10)
    assert em_sp(c[2].data_proxima_cobranca) == datetime(2026, 12, 25, 18)
    assert em_sp(c[3].data_proxima_cobranca) == datetime(2027, 1, 3, 22, 30)
    eventos = db.query(models.HistoricoCadeiraContratada).filter_by(evento=venc.EVENTO_CONTRATACAO).count()
    assert eventos == 3


def test_renovacao_antecipada_soma_ao_vencimento_e_nao_mexe_nas_outras(db, monkeypatch):
    _contratar(db, 1, sp(2026, 11, 20, 10))
    _contratar(db, 2, sp(2026, 11, 25, 18))
    c = _cadeiras(db)
    _pagar_mensalidade(db, monkeypatch, sp(2026, 12, 15, 9), cadeira_ids=[c[1].id])
    db.expire_all()
    c = _cadeiras(db)
    assert em_sp(c[1].data_proxima_cobranca) == datetime(2027, 1, 20, 10)   # +1 mês sobre 20/12
    assert em_sp(c[2].data_proxima_cobranca) == datetime(2026, 12, 25, 18)  # intacta
    h = db.query(models.HistoricoCadeiraContratada).filter_by(cadeira_contratada_id=c[1].id,
                                                             evento=venc.EVENTO_RENOVACAO_ANTECIPADA).one()
    assert em_sp(h.vencimento_anterior) == datetime(2026, 12, 20, 10)


def test_renovacao_apos_vencimento_conta_um_mes_do_pagamento(db, monkeypatch):
    _contratar(db, 1, sp(2026, 9, 11, 15))
    _contratar(db, 2, sp(2026, 11, 2, 13))
    # 26/10 era o caso real: pagar com a cadeira vencida desde 11/10 dava vencimento 11/11 (15 dias).
    _pagar_mensalidade(db, monkeypatch, sp(2026, 11, 26, 8))  # cadeira 1 vencida desde 11/10
    db.expire_all()
    c = _cadeiras(db)
    assert em_sp(c[1].data_proxima_cobranca) == datetime(2026, 12, 26, 8)
    assert em_sp(c[2].data_proxima_cobranca) == datetime(2026, 12, 2, 13)   # a paga não muda
    # Ciclo seguinte ancorado no novo início (dia 26).
    _pagar_mensalidade(db, monkeypatch, sp(2026, 12, 20, 8), cadeira_ids=[c[1].id])
    db.expire_all()
    assert em_sp(_cadeiras(db)[1].data_proxima_cobranca) == datetime(2027, 1, 26, 8)


def test_mensalidade_cobra_so_as_vencidas(db, monkeypatch):
    _contratar(db, 1, sp(2026, 10, 11, 15))
    _contratar(db, 2, sp(2026, 11, 2, 13))
    a = db.query(models.AssinaturaBarbearia).first()
    valor, qtd = mensalidade_devida(db, a, sp(2026, 11, 12, 0))
    assert (valor, qtd) == (47.90, 1)


def test_uma_cadeira_vencida_nao_derruba_a_que_segue_paga(db, monkeypatch):
    """Caso real de 11/11/2026: a cadeira 1 venceu e a cadeira paga em 02/11 deixava de valer."""
    _contratar(db, 1, sp(2026, 10, 11, 15))
    _contratar(db, 2, sp(2026, 11, 2, 13))
    monkeypatch.setattr(venc, "agora_utc", lambda: sp(2026, 11, 12, 10))
    import app.vagas as vagas_mod
    monkeypatch.setattr(vagas_mod, "agora_utc", lambda: sp(2026, 11, 12, 10))
    a = db.query(models.AssinaturaBarbearia).first()
    assert _assinatura_ativa_e_limite(a) == (True, 1)
    assert cadeiras_pagas(db, _barbearia(db)) == 1
    # Com as duas vencidas, nada em dia.
    monkeypatch.setattr(venc, "agora_utc", lambda: sp(2026, 12, 3, 10))
    assert _assinatura_ativa_e_limite(a) == (False, 0)


def test_reduzir_tira_primeiro_a_vencida_e_preserva_a_paga(db):
    _contratar(db, 1, sp(2026, 10, 11, 15))
    _contratar(db, 2, sp(2026, 11, 2, 13))
    paga = _cadeiras(db)[2]
    _contratar(db, 1, sp(2026, 11, 12, 0))
    ativas = _cadeiras(db)
    assert list(ativas) == [2] and ativas[2].id == paga.id
    assert em_sp(ativas[2].data_proxima_cobranca) == datetime(2026, 12, 2, 13)
    assert db.query(models.HistoricoCadeiraContratada).filter_by(evento=venc.EVENTO_CANCELAMENTO).count() == 1


def test_pix_da_mensalidade_renova_exatamente_as_cadeiras_cobradas(db, monkeypatch):
    """Se outra cadeira vencer entre gerar e pagar o Pix, ela não é renovada de graça."""
    _contratar(db, 1, sp(2026, 10, 11, 15))
    _contratar(db, 2, sp(2026, 11, 2, 13))
    usuario = db.query(models.Usuario).first()
    monkeypatch.setattr(venc, "agora_utc", lambda: sp(2026, 11, 20, 10))
    preparo = EFEITOS["MENSALIDADE_BARBEARIA"].preparar(db, usuario, {})
    c = _cadeiras(db)
    assert preparo.valor == 47.90 and preparo.referencia["cadeira_ids"] == [c[1].id]

    monkeypatch.setattr(venc, "agora_utc", lambda: sp(2026, 12, 5, 10))  # a 2 venceu em 02/12
    cobranca = models.Cobranca(identificador="x", usuario_id=usuario.id, finalidade="MENSALIDADE_BARBEARIA",
                               chave_referencia=preparo.chave_referencia, valor=preparo.valor, status="PAGO")
    EFEITOS["MENSALIDADE_BARBEARIA"].aplicar(db, cobranca, preparo.referencia)
    db.commit()
    db.expire_all()
    c = _cadeiras(db)
    assert em_sp(c[1].data_proxima_cobranca) == datetime(2027, 1, 5, 10)
    assert em_sp(c[2].data_proxima_cobranca) == datetime(2026, 12, 2, 13)
    fatura = db.query(models.FaturaAssinatura).one()
    assert fatura.valor_fatura == 47.90 and fatura.quantidade_cadeiras == 1


def test_migracao_de_assinatura_antiga_mantem_o_vencimento_pago(db):
    b = _barbearia(db)
    pago_ate = sp(2026, 12, 10, 12)
    db.add(models.AssinaturaBarbearia(barbearia_id=b.id, quantidade_cadeiras=2, valor_mensalidade=85.8,
                                      dia_vencimento=10, proximo_vencimento=pago_ate, status="ativa",
                                      criado_em=sp(2026, 6, 10, 12)))
    db.commit()
    _contratar(db, 3, sp(2026, 11, 20, 12))
    c = _cadeiras(db)
    assert c[1].data_proxima_cobranca == pago_ate and c[2].data_proxima_cobranca == pago_ate
    assert em_sp(c[3].data_proxima_cobranca) == datetime(2026, 12, 20, 12)


def test_status_de_cada_cadeira(db, monkeypatch):
    _contratar(db, 1, sp(2026, 11, 1, 12))
    c = _cadeiras(db)[1]
    assert venc.status_cadeira(c, sp(2026, 11, 20)) == venc.STATUS_ATIVA
    assert venc.status_cadeira(c, sp(2026, 11, 28)) == venc.STATUS_PROXIMA
    assert venc.status_cadeira(c, sp(2026, 12, 1, 11, 59)) == venc.STATUS_PROXIMA
    assert venc.status_cadeira(c, sp(2026, 12, 1, 12, 1)) == venc.STATUS_VENCIDA
