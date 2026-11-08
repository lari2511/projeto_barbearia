# --- ARQUIVO: app/routes_conta.py ---
# LGPD: exclusão da conta pelo próprio usuário.
#
# Não apaga a linha de `usuarios`: atendimentos, avaliações, cobranças e fechamentos
# diários apontam para ela e precisam continuar existindo (obrigação fiscal/contábil e
# histórico da outra parte). Em vez disso, ANONIMIZA: tira tudo que identifica a pessoa
# (nome, e-mail, telefone, CPF/CNPJ, RG, documentos, fotos, localização, dados bancários),
# bloqueia o login e revoga as sessões.

import logging
import secrets
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from . import models
from .database import get_db
from .limite_requisicoes import ip_do_cliente, registrar_tentativa
from .routes import get_current_user, get_password_hash, verify_password
from .seguranca import nome_arquivo_documento
from .sessoes import revogar_sessoes_do_usuario

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/conta", tags=["Conta"])

NOME_ANONIMO = "Usuário excluído"
MOTIVO_EXCLUSAO = "Conta excluída pelo usuário"
_STATUS_EM_ABERTO = [
    models.StatusAgendamento.PENDENTE.value,
    models.StatusAgendamento.CONFIRMADO.value,
    models.StatusAgendamento.EM_ATENDIMENTO.value,
]
_UPLOADS = Path("uploads")


class ExcluirContaRequest(BaseModel):
    senha: str
    confirmacao: str  # o usuário digita EXCLUIR


def _apagar_arquivo_local(url: str | None) -> None:
    """Remove do disco um arquivo servido em /uploads/... (ignora URLs externas)."""
    if not url:
        return
    pos = url.find("/uploads/")
    if pos < 0:
        return
    relativo = url[pos + len("/uploads/"):].split("?", 1)[0]
    if not relativo or ".." in relativo or relativo.startswith(("/", "\\")):
        return
    caminho = (_UPLOADS / relativo)
    try:
        if caminho.resolve().is_relative_to(_UPLOADS.resolve()) and caminho.is_file():
            caminho.unlink()
    except OSError:
        logger.warning("exclusão de conta: não consegui apagar um arquivo de upload")


def _atendimentos_em_aberto(db: Session, usuario: models.Usuario) -> int:
    filtro = models.Chamado.status.in_(_STATUS_EM_ABERTO)
    q = db.query(models.Chamado.id).filter(filtro)
    if usuario.tipo == "cliente":
        q = q.filter(models.Chamado.cliente_id == usuario.id)
    elif usuario.tipo == "barbeiro":
        q = q.filter(models.Chamado.barbeiro_id == usuario.id)
    elif usuario.tipo == "barbearia":
        ids = [b.id for b in db.query(models.Barbearia.id).filter(models.Barbearia.usuario_id == usuario.id)]
        if not ids:
            return 0
        q = q.filter(models.Chamado.barbearia_id.in_(ids))
    else:
        return 0
    return q.count()


def anonimizar_usuario(db: Session, usuario: models.Usuario) -> None:
    """Apaga os dados pessoais do usuário, mantendo a linha para o histórico. Sem commit."""
    agora = datetime.utcnow()

    # Arquivos: documentos, foto de perfil e portfólio
    for url in (usuario.documento_frente_url, usuario.documento_verso_url, usuario.selfie_documento_url):
        if nome_arquivo_documento(url) or (url and "/uploads/" in url):
            _apagar_arquivo_local(url)
    _apagar_arquivo_local(usuario.foto_perfil)
    for foto in db.query(models.Foto).filter(models.Foto.usuario_id == usuario.id).all():
        _apagar_arquivo_local(foto.url)
        db.delete(foto)

    # Identificação
    usuario.nome = NOME_ANONIMO
    usuario.email = f"excluido-{usuario.id}-{secrets.token_hex(4)}@excluido.invalid"
    usuario.senha_hash = get_password_hash(secrets.token_urlsafe(32))  # ninguém sabe esta senha
    for campo in (
        "endereco", "telefone", "cpf", "cnpj", "rg",
        "documento_frente_url", "documento_verso_url", "selfie_documento_url", "documento_rejeitado_motivo",
        "token_verificacao", "twofa_secret", "latitude", "longitude", "foto_perfil",
        "data_nascimento", "device_token", "device_token_atualizado_em", "tempo_experiencia",
        "barbearia_atual_id", "horario_chegada", "saida_pendente", "clientes_app_liberado_barbearia_id",
    ):
        if hasattr(usuario, campo):
            setattr(usuario, campo, None)
    usuario.twofa_ativo = False
    usuario.disponivel = False
    usuario.online_regiao = False
    usuario.presente_em_local = False
    usuario.em_atendimento = False
    usuario.perfil_aprovado = False
    # Some das listagens públicas (que já filtram bloqueados) e do painel aparece como excluída
    usuario.bloqueado_por_admin = True
    usuario.motivo_bloqueio = MOTIVO_EXCLUSAO
    usuario.bloqueado_em = agora
    usuario.excluido_em = agora

    # Dados bancários / Pix
    conta = db.query(models.ContaPagamentoUsuario).filter(models.ContaPagamentoUsuario.usuario_id == usuario.id).first()
    if conta is not None:
        for campo in ("chave_pix", "banco", "agencia", "conta", "titular_nome", "titular_documento"):
            setattr(conta, campo, None)
        conta.ativo = False

    # Localização (freelancer e atendimentos antigos)
    radar = db.query(models.RadarFreelancer).filter(models.RadarFreelancer.freelancer_id == usuario.id).first()
    if radar is not None:
        radar.is_online = False
        if hasattr(radar, "latitude"):
            radar.latitude = None
            radar.longitude = None
    freelancer = db.query(models.Freelancer).filter(models.Freelancer.usuario_id == usuario.id).first()
    if freelancer is not None:
        freelancer.latitude = None
        freelancer.longitude = None
    db.query(models.AgendamentoAtivo).filter(models.AgendamentoAtivo.cliente_id == usuario.id).update(
        {models.AgendamentoAtivo.cliente_lat: None, models.AgendamentoAtivo.cliente_lon: None}, synchronize_session=False)
    db.query(models.AgendamentoAtivo).filter(models.AgendamentoAtivo.barbeiro_id == usuario.id).update(
        {models.AgendamentoAtivo.barbeiro_lat: None, models.AgendamentoAtivo.barbeiro_lon: None}, synchronize_session=False)
    db.query(models.SolicitacaoBarbeiro).filter(models.SolicitacaoBarbeiro.cliente_id == usuario.id).update(
        {models.SolicitacaoBarbeiro.endereco: None}, synchronize_session=False)

    # Barbearia do proprietário: sai do ar. O nome fica (aparece no histórico dos clientes);
    # telefone, endereço e CEP saem.
    if usuario.tipo == "barbearia":
        for barbearia in db.query(models.Barbearia).filter(models.Barbearia.usuario_id == usuario.id).all():
            barbearia.telefone = None
            barbearia.endereco = None
            barbearia.cep = None
            barbearia.status_online = False
            barbearia.presente_em_local = False
            barbearia.bloqueada = True
            barbearia.motivo_bloqueio = MOTIVO_EXCLUSAO
            barbearia.bloqueada_em = agora

    revogar_sessoes_do_usuario(db, usuario.id)


@router.post("/excluir")
def excluir_minha_conta(
    dados: ExcluirContaRequest,
    request: Request,
    usuario: models.Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Exclui (anonimiza) a conta de quem está logado. Pede a senha de novo."""
    registrar_tentativa(f"excluir_conta:ip:{ip_do_cliente(request)}", 10, 15 * 60)
    if usuario.tipo == "admin":
        raise HTTPException(status_code=403, detail="Conta de ADM não pode ser excluída por aqui.")
    if (dados.confirmacao or "").strip().upper() != "EXCLUIR":
        raise HTTPException(status_code=400, detail='Digite EXCLUIR para confirmar.')
    if not verify_password(dados.senha or "", usuario.senha_hash or ""):
        # 400 (não 401): 401 no app significa "sessão expirada" e dispara a renovação do token.
        raise HTTPException(status_code=400, detail="Senha incorreta.")
    if _atendimentos_em_aberto(db, usuario):
        raise HTTPException(
            status_code=409,
            detail="Você tem atendimentos em aberto. Conclua ou cancele antes de excluir a conta.",
        )

    usuario_id = usuario.id
    anonimizar_usuario(db, usuario)
    db.commit()
    logger.info("conta excluída (anonimizada) a pedido do usuário id=%s", usuario_id)
    return {"mensagem": "Sua conta foi excluída e seus dados pessoais foram apagados."}
