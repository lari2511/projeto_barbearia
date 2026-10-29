"""
Situação de aceite de cada usuário e registro das decisões.

Liberado = aceitou a versão mínima exigida de todos os documentos publicados do seu perfil
e, se for freelancer, tem 18 anos completos declarados. Se nenhum documento do perfil estiver
publicado, nada é exigido (rascunho nunca bloqueia ninguém).
"""

from datetime import date, datetime
from typing import Dict, List, Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app import models
from app.termos import documentos as docs

IDADE_MINIMA_FREELANCER = 18
ACEITO = "aceito"
RECUSADO = "recusado"

MSG_MENOR_FREELANCER = (
    "É preciso ter 18 anos completos para se cadastrar e atuar como freelancer no BarberMove."
)


def idade_em(nascimento: date, hoje: Optional[date] = None) -> int:
    hoje = hoje or date.today()
    return hoje.year - nascimento.year - ((hoje.month, hoje.day) < (nascimento.month, nascimento.day))


def interpretar_data_nascimento(valor) -> date:
    if isinstance(valor, date):
        nascimento = valor
    else:
        try:
            nascimento = date.fromisoformat(str(valor or "").strip()[:10])
        except ValueError:
            raise HTTPException(status_code=400, detail="Informe a data de nascimento (dd/mm/aaaa)")
    if nascimento > date.today() or nascimento.year < 1900:
        raise HTTPException(status_code=400, detail="Data de nascimento inválida")
    return nascimento


def exigir_maioridade_freelancer(nascimento: date) -> None:
    """403 para menor de 18. Quem chama não deve gravar a data quando isso falha."""
    if idade_em(nascimento) < IDADE_MINIMA_FREELANCER:
        raise HTTPException(status_code=403, detail=MSG_MENOR_FREELANCER)


def _decisoes(db: Session, usuario_id: int) -> List[models.AceiteDocumento]:
    return db.query(models.AceiteDocumento).filter(
        models.AceiteDocumento.usuario_id == usuario_id
    ).order_by(models.AceiteDocumento.registrado_em.asc(), models.AceiteDocumento.id.asc()).all()


def _aceite_vale(decisao: models.AceiteDocumento, minima: docs.VersaoDocumento) -> bool:
    try:
        return decisao.decisao == ACEITO and docs.chave_versao(decisao.versao) >= docs.chave_versao(minima.versao)
    except ValueError:
        return False


def situacao(db: Session, usuario: models.Usuario) -> dict:
    perfil = docs.perfil_do_tipo(usuario.tipo)
    if not perfil:
        return {"perfil": None, "liberado": True, "pendentes": [], "recusou": False,
                "exige_data_nascimento": False, "bloqueio_idade": False}

    decisoes = _decisoes(db, usuario.id)
    pendentes = []
    recusou = False
    for atual in docs.documentos_vigentes(perfil):
        minima = docs.versao_minima_exigida(atual.codigo)
        do_doc = [d for d in decisoes if d.documento_codigo == atual.codigo]
        if minima and not any(_aceite_vale(d, minima) for d in do_doc):
            pendentes.append({
                **atual.resumo(),
                "atualizacao": any(d.decisao == ACEITO for d in do_doc),  # já aceitou uma versão anterior
            })
            if do_doc and do_doc[-1].decisao == RECUSADO:
                recusou = True

    exige_nascimento = False
    bloqueio_idade = False
    if perfil == "freelancer":
        nascimento = getattr(usuario, "data_nascimento", None)
        if nascimento:
            bloqueio_idade = idade_em(nascimento) < IDADE_MINIMA_FREELANCER
        else:
            # Só cobra de quem já tem conta quando os termos do freelancer estiverem publicados.
            exige_nascimento = docs.versao_atual("termos-freelancer") is not None

    return {
        "perfil": perfil,
        "liberado": not pendentes and not exige_nascimento and not bloqueio_idade,
        "pendentes": pendentes,
        "recusou": recusou,
        "exige_data_nascimento": exige_nascimento,
        "bloqueio_idade": bloqueio_idade,
    }


def registrar_aceite(db: Session, usuario: models.Usuario, aceites: List[dict], data_nascimento=None) -> dict:
    """
    Grava o aceite dos documentos pendentes. Todos os pendentes precisam vir confirmados,
    na versão publicada atual. Freelancer sem data de nascimento precisa informá-la (18+).
    """
    atual = situacao(db, usuario)
    perfil = atual["perfil"]
    if not perfil:
        raise HTTPException(status_code=400, detail="Este perfil não tem documentos para aceitar")

    if perfil == "freelancer" and (atual["exige_data_nascimento"] or data_nascimento):
        if not usuario.data_nascimento:
            if not data_nascimento:
                raise HTTPException(status_code=400, detail="Informe sua data de nascimento")
            nascimento = interpretar_data_nascimento(data_nascimento)
            exigir_maioridade_freelancer(nascimento)
            usuario.data_nascimento = nascimento
    if perfil == "freelancer" and usuario.data_nascimento:
        exigir_maioridade_freelancer(usuario.data_nascimento)

    enviados: Dict[str, dict] = {}
    for item in aceites or []:
        codigo = str((item or {}).get("codigo") or "")
        if codigo:
            enviados[codigo] = item

    agora = datetime.utcnow()
    for pendente in atual["pendentes"]:
        codigo = pendente["codigo"]
        item = enviados.get(codigo)
        if not item or item.get("confirmado") is not True:
            raise HTTPException(status_code=400, detail=f"Confirme a leitura de: {pendente['titulo']}")
        if str(item.get("versao") or "") != pendente["versao"]:
            raise HTTPException(
                status_code=409,
                detail=f"{pendente['titulo']} foi atualizado. Leia a versão {pendente['versao']} para continuar.",
            )

    for codigo, item in enviados.items():
        versao = docs.versao_atual(codigo)
        if not versao or perfil not in versao.perfis or item.get("confirmado") is not True:
            continue
        if str(item.get("versao") or "") != versao.versao:
            raise HTTPException(status_code=409, detail=f"{versao.titulo} foi atualizado. Leia a nova versão.")
        db.add(models.AceiteDocumento(
            usuario_id=usuario.id,
            perfil=perfil,
            documento_codigo=versao.codigo,
            tipo_documento=versao.tipo,
            versao=versao.versao,
            conteudo_sha256=versao.sha256,
            decisao=ACEITO,
            confirmacao=versao.confirmacao,
            registrado_em=agora,
        ))

    db.commit()
    db.refresh(usuario)
    return situacao(db, usuario)


def registrar_recusa(db: Session, usuario: models.Usuario) -> dict:
    """Registra a recusa dos pendentes. Não exclui a conta nem dados; só mantém o bloqueio."""
    atual = situacao(db, usuario)
    agora = datetime.utcnow()
    for pendente in atual["pendentes"]:
        versao = docs.buscar(pendente["codigo"], pendente["versao"])
        db.add(models.AceiteDocumento(
            usuario_id=usuario.id,
            perfil=atual["perfil"],
            documento_codigo=versao.codigo,
            tipo_documento=versao.tipo,
            versao=versao.versao,
            conteudo_sha256=versao.sha256,
            decisao=RECUSADO,
            confirmacao=f"Recusou: {versao.titulo} (versão {versao.versao})",
            registrado_em=agora,
        ))
    db.commit()
    return situacao(db, usuario)


def historico(db: Session, usuario: models.Usuario) -> List[dict]:
    """Decisões do usuário, com a indicação de qual aceite está vigente hoje."""
    perfil = docs.perfil_do_tipo(usuario.tipo)
    decisoes = _decisoes(db, usuario.id)
    vigentes = set()
    for codigo in docs.codigos_do_perfil(perfil) if perfil else []:
        minima = docs.versao_minima_exigida(codigo)
        validos = [d for d in decisoes if d.documento_codigo == codigo and minima and _aceite_vale(d, minima)]
        if validos:
            vigentes.add(validos[-1].id)
    return [
        {
            "id": d.id,
            "perfil": d.perfil,
            "documento_codigo": d.documento_codigo,
            "tipo_documento": d.tipo_documento,
            "versao": d.versao,
            "decisao": d.decisao,
            "confirmacao": d.confirmacao,
            "registrado_em": d.registrado_em.isoformat() + "Z" if d.registrado_em else None,
            "vigente": d.id in vigentes,
        }
        for d in reversed(decisoes)
    ]
