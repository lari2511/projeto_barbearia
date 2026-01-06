# --- ARQUIVO: app/routes_extras.py ---
# Rotas para funcionalidades extras (avaliações, favoritos, cupons, etc)

import os
import secrets
import math
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_

from . import models, schemas
from .database import get_db
from .email_utils import send_email
from .routes import get_current_user, oauth2_scheme, get_password_hash

router = APIRouter()

VERIFICATION_LINK_BASE = os.getenv(
    "VERIFICATION_LINK_BASE",
    "http://localhost:8000/api/v1/email/verificar?token=",
)
RESET_PASSWORD_LINK_BASE = os.getenv(
    "RESET_PASSWORD_LINK_BASE",
    "http://localhost:5173/resetar-senha?token=",
)
DEBUG_EMAIL_TOKENS = os.getenv("DEBUG_EMAIL_TOKENS", "0") == "1"

# ==================== AVALIAÇÕES ====================

@router.post("/avaliacoes/", response_model=schemas.AvaliacaoResponse)
def criar_avaliacao(avaliacao: schemas.AvaliacaoCreate, token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """Cliente avalia barbeiro/barbearia após serviço concluído"""
    user = get_current_user(token=token, db=db)
    
    # Verificar se chamado existe e foi concluído
    chamado = db.query(models.Chamado).filter(models.Chamado.id == avaliacao.chamado_id).first()
    if not chamado:
        raise HTTPException(status_code=404, detail="Chamado não encontrado")
    
    if chamado.status != "CONCLUÍDO":
        raise HTTPException(status_code=400, detail="Só pode avaliar chamados concluídos")
    
    if chamado.cliente_id != user.id:
        raise HTTPException(status_code=403, detail="Apenas o cliente pode avaliar")
    
    # Verificar se já avaliou
    avaliacao_existente = db.query(models.Avaliacao).filter(
        and_(models.Avaliacao.chamado_id == avaliacao.chamado_id,
             models.Avaliacao.avaliador_id == user.id)
    ).first()
    if avaliacao_existente:
        raise HTTPException(status_code=400, detail="Você já avaliou este serviço")
    
    nova_avaliacao = models.Avaliacao(
        chamado_id=avaliacao.chamado_id,
        avaliador_id=user.id,
        avaliado_id=avaliacao.avaliado_id,
        nota=avaliacao.nota,
        comentario=avaliacao.comentario
    )
    db.add(nova_avaliacao)
    
    # Adicionar pontos de fidelidade
    pontos = db.query(models.PontosFidelidade).filter(models.PontosFidelidade.usuario_id == user.id).first()
    if not pontos:
        pontos = models.PontosFidelidade(usuario_id=user.id, pontos=10)
        db.add(pontos)
    else:
        pontos.pontos += 10
        # Atualizar nível
        if pontos.pontos >= 1000:
            pontos.nivel = "PLATINA"
        elif pontos.pontos >= 500:
            pontos.nivel = "OURO"
        elif pontos.pontos >= 200:
            pontos.nivel = "PRATA"
    
    db.commit()
    db.refresh(nova_avaliacao)
    return nova_avaliacao


@router.get("/usuario/{usuario_id}/avaliacoes", response_model=List[schemas.AvaliacaoResponse])
def listar_avaliacoes_usuario(usuario_id: int, db: Session = Depends(get_db)):
    """Listar todas as avaliações de um barbeiro/barbearia"""
    avaliacoes = db.query(models.Avaliacao).filter(models.Avaliacao.avaliado_id == usuario_id).all()
    return avaliacoes


@router.get("/usuario/{usuario_id}/media_avaliacao")
def media_avaliacao_usuario(usuario_id: int, db: Session = Depends(get_db)):
    """Obter média de avaliações de um usuário"""
    media = db.query(func.avg(models.Avaliacao.nota)).filter(models.Avaliacao.avaliado_id == usuario_id).scalar()
    total = db.query(func.count(models.Avaliacao.id)).filter(models.Avaliacao.avaliado_id == usuario_id).scalar()
    
    return {
        "media": round(media, 2) if media else 0,
        "total_avaliacoes": total or 0
    }


# ==================== FAVORITOS ====================

@router.post("/favoritos/", response_model=schemas.FavoritoResponse)
def adicionar_favorito(favorito: schemas.FavoritoCreate, token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """Adicionar barbeiro/barbearia aos favoritos"""
    user = get_current_user(token=token, db=db)
    
    # Verificar se já está nos favoritos
    favorito_existente = db.query(models.Favorito).filter(
        and_(models.Favorito.usuario_id == user.id,
             models.Favorito.favorito_id == favorito.favorito_id)
    ).first()
    
    if favorito_existente:
        raise HTTPException(status_code=400, detail="Já está nos favoritos")
    
    novo_favorito = models.Favorito(
        usuario_id=user.id,
        favorito_id=favorito.favorito_id
    )
    db.add(novo_favorito)
    db.commit()
    db.refresh(novo_favorito)
    return novo_favorito


@router.get("/favoritos/", response_model=List[schemas.FavoritoResponse])
def listar_favoritos(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """Listar favoritos do usuário"""
    user = get_current_user(token=token, db=db)
    favoritos = db.query(models.Favorito).filter(models.Favorito.usuario_id == user.id).all()
    return favoritos


@router.delete("/favoritos/{favorito_id}")
def remover_favorito(favorito_id: int, token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """Remover dos favoritos"""
    user = get_current_user(token=token, db=db)
    
    favorito = db.query(models.Favorito).filter(
        and_(models.Favorito.usuario_id == user.id,
             models.Favorito.favorito_id == favorito_id)
    ).first()
    
    if not favorito:
        raise HTTPException(status_code=404, detail="Favorito não encontrado")
    
    db.delete(favorito)
    db.commit()
    return {"detail": "Removido dos favoritos"}


# ==================== CUPONS ====================

@router.post("/cupons/", response_model=schemas.CupomResponse)
def criar_cupom(cupom: schemas.CupomCreate, token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """Criar cupom de desconto (apenas admin/barbearia)"""
    user = get_current_user(token=token, db=db)
    
    if user.tipo not in ("barbearia",):
        raise HTTPException(status_code=403, detail="Apenas barbearias podem criar cupons")
    
    # Verificar se cupom já existe
    cupom_existente = db.query(models.Cupom).filter(models.Cupom.codigo == cupom.codigo.upper()).first()
    if cupom_existente:
        raise HTTPException(status_code=400, detail="Código de cupom já existe")
    
    valido_ate = None
    if cupom.valido_ate:
        valido_ate = datetime.fromisoformat(cupom.valido_ate)
    
    novo_cupom = models.Cupom(
        codigo=cupom.codigo.upper(),
        desconto_percentual=cupom.desconto_percentual,
        desconto_fixo=cupom.desconto_fixo,
        valido_ate=valido_ate,
        uso_maximo=cupom.uso_maximo
    )
    db.add(novo_cupom)
    db.commit()
    db.refresh(novo_cupom)
    return novo_cupom


@router.post("/cupons/validar")
def validar_cupom(cupom: schemas.CupomValidar, db: Session = Depends(get_db)):
    """Validar se cupom é válido"""
    cupom_db = db.query(models.Cupom).filter(models.Cupom.codigo == cupom.codigo.upper()).first()
    
    if not cupom_db:
        raise HTTPException(status_code=404, detail="Cupom não encontrado")
    
    if not cupom_db.ativo:
        raise HTTPException(status_code=400, detail="Cupom inativo")
    
    if cupom_db.valido_ate and cupom_db.valido_ate < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Cupom expirado")
    
    if cupom_db.uso_maximo and cupom_db.uso_atual >= cupom_db.uso_maximo:
        raise HTTPException(status_code=400, detail="Cupom esgotado")
    
    return {
        "valido": True,
        "desconto_percentual": cupom_db.desconto_percentual,
        "desconto_fixo": cupom_db.desconto_fixo
    }


@router.get("/cupons/", response_model=List[schemas.CupomResponse])
def listar_cupons(db: Session = Depends(get_db)):
    """Listar cupons ativos"""
    cupons = db.query(models.Cupom).filter(
        and_(models.Cupom.ativo == True,
             or_(models.Cupom.valido_ate == None, models.Cupom.valido_ate > datetime.utcnow()))
    ).all()
    return cupons


# ==================== PONTOS DE FIDELIDADE ====================

@router.get("/fidelidade/", response_model=schemas.PontosFidelidadeResponse)
def consultar_pontos(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """Consultar pontos de fidelidade do cliente"""
    user = get_current_user(token=token, db=db)
    
    pontos = db.query(models.PontosFidelidade).filter(models.PontosFidelidade.usuario_id == user.id).first()
    if not pontos:
        # Criar registro de pontos
        pontos = models.PontosFidelidade(usuario_id=user.id)
        db.add(pontos)
        db.commit()
        db.refresh(pontos)
    
    return pontos


# ==================== FOTOS ====================

@router.post("/fotos/", response_model=schemas.FotoResponse)
def adicionar_foto(foto: schemas.FotoCreate, token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """Adicionar foto de serviço (barbeiro/barbearia)"""
    user = get_current_user(token=token, db=db)
    
    nova_foto = models.Foto(
        usuario_id=user.id,
        servico_id=foto.servico_id,
        url=foto.url,
        descricao=foto.descricao
    )
    db.add(nova_foto)
    db.commit()
    db.refresh(nova_foto)
    return nova_foto


@router.get("/usuario/{usuario_id}/fotos", response_model=List[schemas.FotoResponse])
def listar_fotos_usuario(usuario_id: int, db: Session = Depends(get_db)):
    """Listar fotos de um barbeiro/barbearia"""
    fotos = db.query(models.Foto).filter(models.Foto.usuario_id == usuario_id).all()
    return fotos


# ==================== GEOLOCALIZAÇÃO ====================

def calcular_distancia(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calcular distância em km usando fórmula de Haversine"""
    R = 6371  # Raio da Terra em km
    
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    return R * c


@router.post("/barbearias/proximas")
def buscar_barbearias_proximas(localizacao: schemas.BarbeariasProximasRequest, db: Session = Depends(get_db)):
    """Buscar barbearias próximas à localização do cliente"""
    barbearias = db.query(models.Barbearia).filter(
        and_(models.Barbearia.latitude != None,
             models.Barbearia.longitude != None)
    ).all()
    
    barbearias_com_distancia = []
    for barbearia in barbearias:
        distancia = calcular_distancia(
            localizacao.latitude,
            localizacao.longitude,
            barbearia.latitude,
            barbearia.longitude
        )
        
        if distancia <= localizacao.raio_km:
            barbearias_com_distancia.append({
                "id": barbearia.id,
                "nome": barbearia.nome,
                "endereco": barbearia.endereco,
                "distancia_km": round(distancia, 2),
                "cadeira_livre": barbearia.cadeira_livre
            })
    
    # Ordenar por distância
    barbearias_com_distancia.sort(key=lambda x: x["distancia_km"])
    
    return barbearias_com_distancia


# ==================== AGENDAMENTO FUTURO ====================

@router.post("/chamados/agendar")
def agendar_chamado_futuro(agendamento: schemas.AgendamentoFuturo, token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """Agendar chamado para data/hora específica"""
    user = get_current_user(token=token, db=db)
    
    if user.tipo != "cliente":
        raise HTTPException(status_code=403, detail="Apenas clientes podem agendar")
    
    # Verificar se serviço existe
    servico = db.query(models.Servico).filter(models.Servico.id == agendamento.servico_id).first()
    if not servico:
        raise HTTPException(status_code=404, detail="Serviço não encontrado")
    
    data_agendamento = datetime.fromisoformat(agendamento.data_agendamento)
    
    novo_chamado = models.Chamado(
        cliente_id=user.id,
        servico_id=agendamento.servico_id,
        barbearia_id=agendamento.barbearia_id,
        status="AGENDADO",
        data_agendamento=data_agendamento,
        valor_original=servico.valor,
        valor_final=servico.valor
    )
    
    db.add(novo_chamado)
    
    # Criar histórico
    historico = models.ChamadoHistorico(
        chamado_id=novo_chamado.id,
        status_novo="AGENDADO",
        usuario_id=user.id,
        observacao=f"Agendado para {data_agendamento.strftime('%d/%m/%Y %H:%M')}"
    )
    db.add(historico)
    
    # Criar notificação
    notificacao = models.Notificacao(
        usuario_id=user.id,
        titulo="Agendamento Confirmado",
        mensagem=f"Seu agendamento para {data_agendamento.strftime('%d/%m/%Y às %H:%M')} foi confirmado!",
        tipo="chamado"
    )
    db.add(notificacao)
    
    db.commit()
    db.refresh(novo_chamado)
    
    return novo_chamado


# ==================== HISTÓRICO DE CHAMADOS ====================

@router.get("/chamados/{chamado_id}/historico")
def obter_historico_chamado(chamado_id: int, db: Session = Depends(get_db)):
    """Obter timeline completa de um chamado"""
    historico = db.query(models.ChamadoHistorico).filter(
        models.ChamadoHistorico.chamado_id == chamado_id
    ).order_by(models.ChamadoHistorico.criado_em).all()
    
    return historico


# ==================== NOTIFICAÇÕES ====================

@router.get("/notificacoes/", response_model=List[schemas.NotificacaoResponse])
def listar_notificacoes(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """Listar notificações do usuário"""
    user = get_current_user(token=token, db=db)
    
    notificacoes = db.query(models.Notificacao).filter(
        models.Notificacao.usuario_id == user.id
    ).order_by(models.Notificacao.criado_em.desc()).limit(50).all()
    
    return notificacoes


@router.put("/notificacoes/{notificacao_id}/ler")
def marcar_notificacao_lida(notificacao_id: int, token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """Marcar notificação como lida"""
    user = get_current_user(token=token, db=db)
    
    notificacao = db.query(models.Notificacao).filter(
        and_(models.Notificacao.id == notificacao_id,
             models.Notificacao.usuario_id == user.id)
    ).first()
    
    if not notificacao:
        raise HTTPException(status_code=404, detail="Notificação não encontrada")
    
    notificacao.lida = True
    db.commit()
    
    return {"detail": "Notificação marcada como lida"}


# ==================== CHAT ====================

@router.post("/chat/mensagem", response_model=schemas.MensagemChatResponse)
def enviar_mensagem(mensagem: schemas.MensagemChatCreate, token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """Enviar mensagem no chat do chamado"""
    user = get_current_user(token=token, db=db)
    
    # Verificar se chamado existe e usuário faz parte dele
    chamado = db.query(models.Chamado).filter(models.Chamado.id == mensagem.chamado_id).first()
    if not chamado:
        raise HTTPException(status_code=404, detail="Chamado não encontrado")
    
    if user.id not in (chamado.cliente_id, chamado.barbeiro_id):
        raise HTTPException(status_code=403, detail="Você não faz parte deste chamado")
    
    nova_mensagem = models.MensagemChat(
        chamado_id=mensagem.chamado_id,
        remetente_id=user.id,
        mensagem=mensagem.mensagem
    )
    
    db.add(nova_mensagem)
    db.commit()
    db.refresh(nova_mensagem)
    
    return nova_mensagem


@router.get("/chat/{chamado_id}/mensagens", response_model=List[schemas.MensagemChatResponse])
def listar_mensagens_chat(chamado_id: int, token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """Listar mensagens do chat de um chamado"""
    user = get_current_user(token=token, db=db)
    
    chamado = db.query(models.Chamado).filter(models.Chamado.id == chamado_id).first()
    if not chamado:
        raise HTTPException(status_code=404, detail="Chamado não encontrado")
    
    if user.id not in (chamado.cliente_id, chamado.barbeiro_id):
        raise HTTPException(status_code=403, detail="Você não faz parte deste chamado")
    
    mensagens = db.query(models.MensagemChat).filter(
        models.MensagemChat.chamado_id == chamado_id
    ).order_by(models.MensagemChat.criado_em).all()
    
    return mensagens


# ==================== VERIFICAÇÃO DE EMAIL ====================

@router.get("/email/verificar")
def verificar_email(token: str, db: Session = Depends(get_db)):
    """Confirmar email a partir do token enviado ao usuário"""
    user = db.query(models.Usuario).filter(models.Usuario.token_verificacao == token).first()

    if not user:
        raise HTTPException(status_code=400, detail="Token inválido ou expirado")

    user.email_verificado = True
    user.token_verificacao = None
    db.commit()

    return {"detail": "Email verificado com sucesso"}


@router.post("/email/reenvio")
def reenviar_email_verificacao(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """Reenviar link de verificação para o usuário autenticado"""
    user = get_current_user(token=token, db=db)

    if user.email_verificado:
        return {"detail": "Email já verificado"}

    user.token_verificacao = secrets.token_urlsafe(32)
    db.commit()
    db.refresh(user)

    verification_url = f"{VERIFICATION_LINK_BASE}{user.token_verificacao}"
    html_body = (
        f"<p>Olá, {user.nome}!</p>"
        f"<p>Confirme seu email para ativar a conta.</p>"
        f"<p><a href='{verification_url}'>Verificar email</a></p>"
        f"<p>Ou copie e cole no navegador: {verification_url}</p>"
    )
    text_body = (
        f"Olá, {user.nome}!\n"
        "Confirme seu email para ativar a conta.\n"
        f"Link: {verification_url}\n"
    )
    send_email(
        subject="Verifique seu email - BarberMove",
        to_email=user.email,
        html_body=html_body,
        text_body=text_body,
    )

    response = {"detail": "Link de verificação reenviado"}
    if DEBUG_EMAIL_TOKENS:
        response["token_debug"] = user.token_verificacao
    return response


# ==================== RECUPERAÇÃO DE SENHA ====================

@router.post("/recuperar-senha")
def solicitar_recuperacao_senha(request: schemas.RecuperarSenhaRequest, db: Session = Depends(get_db)):
    """Solicitar recuperação de senha (envia email com token)"""
    usuario = db.query(models.Usuario).filter(models.Usuario.email == request.email).first()
    
    if not usuario:
        # Não revelar se email existe ou não (segurança)
        return {"detail": "Se o email existir, você receberá instruções"}
    
    # Gerar token
    token = secrets.token_urlsafe(32)
    expira_em = datetime.utcnow() + timedelta(hours=24)
    
    token_recuperacao = models.TokenRecuperacao(
        usuario_id=usuario.id,
        token=token,
        expira_em=expira_em
    )
    
    db.add(token_recuperacao)
    db.commit()

    reset_link = f"{RESET_PASSWORD_LINK_BASE}{token}"
    html_body = (
        f"<p>Olá, {usuario.nome}!</p>"
        "<p>Recebemos um pedido para redefinir sua senha. Se não foi você, ignore este email.</p>"
        f"<p><a href='{reset_link}'>Resetar senha</a></p>"
        f"<p>Ou copie e cole no navegador: {reset_link}</p>"
        "<p>O link expira em 24h.</p>"
    )
    text_body = (
        f"Olá, {usuario.nome}!\n"
        "Recebemos um pedido para redefinir sua senha. Se não foi você, ignore este email.\n"
        f"Link: {reset_link}\n"
        "O link expira em 24h.\n"
    )
    send_email(
        subject="Recuperação de senha - BarberMove",
        to_email=usuario.email,
        html_body=html_body,
        text_body=text_body,
    )

    response = {"detail": "Se o email existir, você receberá instruções"}
    if DEBUG_EMAIL_TOKENS:
        response["token_debug"] = token
    return response


@router.post("/resetar-senha")
def resetar_senha(request: schemas.ResetarSenhaRequest, db: Session = Depends(get_db)):
    """Resetar senha usando token"""
    token_db = db.query(models.TokenRecuperacao).filter(
        and_(models.TokenRecuperacao.token == request.token,
             models.TokenRecuperacao.usado == False,
             models.TokenRecuperacao.expira_em > datetime.utcnow())
    ).first()
    
    if not token_db:
        raise HTTPException(status_code=400, detail="Token inválido ou expirado")
    
    # Atualizar senha
    usuario = db.query(models.Usuario).filter(models.Usuario.id == token_db.usuario_id).first()
    usuario.senha_hash = get_password_hash(request.nova_senha)
    
    # Marcar token como usado
    token_db.usado = True
    
    db.commit()
    
    return {"detail": "Senha resetada com sucesso"}


# ==================== ESTATÍSTICAS ====================

@router.get("/estatisticas/", response_model=schemas.EstatisticasResponse)
def obter_estatisticas(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """Obter estatísticas do barbeiro/barbearia"""
    user = get_current_user(token=token, db=db)
    
    if user.tipo == "barbearia":
        # Estatísticas da barbearia
        barbearia = db.query(models.Barbearia).filter(models.Barbearia.usuario_id == user.id).first()
        chamados = db.query(models.Chamado).filter(models.Chamado.barbearia_id == barbearia.id)
    elif user.tipo == "barbeiro":
        # Estatísticas do barbeiro
        chamados = db.query(models.Chamado).filter(models.Chamado.barbeiro_id == user.id)
    else:
        raise HTTPException(status_code=403, detail="Apenas barbeiros/barbearias têm estatísticas")
    
    total_chamados = chamados.count()
    receita_total = db.query(func.sum(models.Chamado.valor_final)).filter(
        and_(models.Chamado.barbeiro_id == user.id if user.tipo == "barbeiro" else models.Chamado.barbearia_id == barbearia.id,
             models.Chamado.status == "CONCLUÍDO")
    ).scalar() or 0
    
    # Serviço mais pedido
    servico_mais_pedido = db.query(
        models.Servico.nome,
        func.count(models.Chamado.id).label('total')
    ).join(models.Chamado).filter(
        models.Chamado.barbeiro_id == user.id if user.tipo == "barbeiro" else models.Chamado.barbearia_id == barbearia.id
    ).group_by(models.Servico.nome).order_by(func.count(models.Chamado.id).desc()).first()
    
    # Média de avaliação
    media_aval = db.query(func.avg(models.Avaliacao.nota)).filter(
        models.Avaliacao.avaliado_id == user.id
    ).scalar()
    
    return {
        "total_chamados": total_chamados,
        "total_receita": float(receita_total),
        "servico_mais_pedido": servico_mais_pedido[0] if servico_mais_pedido else None,
        "media_avaliacao": round(float(media_aval), 2) if media_aval else None
    }


# ==================== 2FA ====================

@router.post("/2fa/ativar", response_model=schemas.Enable2FAResponse)
def ativar_2fa(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """Ativar autenticação de dois fatores"""
    import pyotp
    import qrcode
    from io import BytesIO
    import base64
    
    user = get_current_user(token=token, db=db)
    
    # Gerar secret
    secret = pyotp.random_base32()
    
    # Gerar QR Code
    totp = pyotp.TOTP(secret)
    provisioning_uri = totp.provisioning_uri(name=user.email, issuer_name="BarberUber")
    
    # Criar QR Code
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(provisioning_uri)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Converter para base64
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode()
    
    # Salvar secret (mas não ativar ainda)
    user.twofa_secret = secret
    db.commit()
    
    return {
        "secret": secret,
        "qr_code_url": f"data:image/png;base64,{img_str}"
    }


@router.post("/2fa/verificar")
def verificar_2fa(request: schemas.Verify2FARequest, token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """Verificar código 2FA e ativar"""
    import pyotp
    
    user = get_current_user(token=token, db=db)
    
    if not user.twofa_secret:
        raise HTTPException(status_code=400, detail="2FA não configurado")
    
    totp = pyotp.TOTP(user.twofa_secret)
    
    if not totp.verify(request.token):
        raise HTTPException(status_code=400, detail="Código inválido")
    
    # Ativar 2FA
    user.twofa_ativo = True
    db.commit()
    
    return {"detail": "2FA ativado com sucesso"}


@router.post("/2fa/desativar")
def desativar_2fa(request: schemas.Verify2FARequest, token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """Desativar 2FA"""
    import pyotp
    
    user = get_current_user(token=token, db=db)
    
    if not user.twofa_ativo:
        raise HTTPException(status_code=400, detail="2FA não está ativo")
    
    totp = pyotp.TOTP(user.twofa_secret)
    
    if not totp.verify(request.token):
        raise HTTPException(status_code=400, detail="Código inválido")
    
    user.twofa_ativo = False
    user.twofa_secret = None
    db.commit()
    
    return {"detail": "2FA desativado"}
