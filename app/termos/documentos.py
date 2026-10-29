"""
Catálogo dos documentos legais. É a única fonte de verdade de quais versões existem e
quais estão publicadas.

Como publicar uma versão (depois da aprovação jurídica):
1. Coloque o texto aprovado em textos/<arquivo>.md (uma versão nova = arquivo novo; não edite
   o texto de uma versão já publicada, porque os aceites guardam o hash do texto).
2. Acrescente/edite a entrada em VERSOES com estado="publicado" e vigente_desde.
3. exige_novo_aceite=False só para correções que não mudam direitos e deveres
   (quem aceitou a versão anterior continua liberado).

Rascunhos ficam legíveis (para revisão), mas nunca são exigidos nem aceitos.
"""

import hashlib
import pathlib
from dataclasses import dataclass
from datetime import date
from functools import lru_cache
from typing import List, Optional

PASTA_TEXTOS = pathlib.Path(__file__).parent / "textos"

TERMOS_USO = "termos_uso"
POLITICA_PRIVACIDADE = "politica_privacidade"

RASCUNHO = "rascunho"
PUBLICADO = "publicado"

PERFIS = ("cliente", "freelancer", "proprietario")

# Usuario.tipo -> perfil dos documentos. "admin" não tem documentos (painel web interno).
PERFIL_POR_TIPO = {
    "cliente": "cliente",
    "barbeiro": "freelancer",
    "freelancer": "freelancer",
    "barbearia": "proprietario",
}

# Marcador dos trechos que ainda dependem de definição do negócio/jurídico.
MARCADOR_PENDENTE = "[A DEFINIR"


@dataclass(frozen=True)
class VersaoDocumento:
    codigo: str  # identificador estável do documento (todas as versões)
    tipo: str  # TERMOS_USO | POLITICA_PRIVACIDADE
    titulo: str
    perfis: tuple  # escopo: perfis que precisam aceitar
    versao: str  # "1.0", "1.1", "2.0"
    arquivo: str
    vigente_desde: date
    estado: str = RASCUNHO
    exige_novo_aceite: bool = True

    @property
    def confirmacao(self) -> str:
        if self.tipo == POLITICA_PRIVACIDADE:
            return f"Li e estou ciente da {self.titulo} (versão {self.versao})"
        return f"Li e aceito os {self.titulo} (versão {self.versao})"

    @property
    def conteudo(self) -> str:
        return _ler_texto(self.arquivo)

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.conteudo.encode("utf-8")).hexdigest()

    def resumo(self) -> dict:
        return {
            "codigo": self.codigo,
            "tipo": self.tipo,
            "titulo": self.titulo,
            "perfis": list(self.perfis),
            "versao": self.versao,
            "vigente_desde": self.vigente_desde.isoformat(),
            "estado": self.estado,
            "exige_novo_aceite": self.exige_novo_aceite,
            "confirmacao": self.confirmacao,
        }


VERSOES: List[VersaoDocumento] = [
    VersaoDocumento(
        codigo="termos-cliente", tipo=TERMOS_USO, titulo="Termos de Uso do Cliente",
        perfis=("cliente",), versao="1.0", arquivo="termos-cliente-1.0.md",
        vigente_desde=date(2026, 10, 28),
    ),
    VersaoDocumento(
        codigo="termos-freelancer", tipo=TERMOS_USO, titulo="Termos de Uso do Freelancer",
        perfis=("freelancer",), versao="1.0", arquivo="termos-freelancer-1.0.md",
        vigente_desde=date(2026, 10, 28),
    ),
    VersaoDocumento(
        codigo="termos-proprietario", tipo=TERMOS_USO, titulo="Termos de Uso do Proprietário de Barbearia",
        perfis=("proprietario",), versao="1.0", arquivo="termos-proprietario-1.0.md",
        vigente_desde=date(2026, 10, 28),
    ),
    VersaoDocumento(
        codigo="politica-privacidade", tipo=POLITICA_PRIVACIDADE, titulo="Política de Privacidade",
        perfis=PERFIS, versao="1.0", arquivo="politica-privacidade-1.0.md",
        vigente_desde=date(2026, 10, 28),
    ),
]


@lru_cache(maxsize=None)
def _ler_texto(arquivo: str) -> str:
    return (PASTA_TEXTOS / arquivo).read_text(encoding="utf-8")


def perfil_do_tipo(tipo: Optional[str]) -> Optional[str]:
    return PERFIL_POR_TIPO.get((tipo or "").strip().lower())


def normalizar_perfil(valor: Optional[str]) -> Optional[str]:
    """Aceita o perfil ('freelancer') ou o tipo de usuário ('barbeiro')."""
    valor = (valor or "").strip().lower()
    return valor if valor in PERFIS else perfil_do_tipo(valor)


def chave_versao(versao: str) -> tuple:
    return tuple(int(parte) for parte in versao.split("."))


def _publicadas(codigo: str, hoje: Optional[date] = None) -> List[VersaoDocumento]:
    hoje = hoje or date.today()
    return sorted(
        (v for v in VERSOES if v.codigo == codigo and v.estado == PUBLICADO and v.vigente_desde <= hoje),
        key=lambda v: chave_versao(v.versao),
    )


def codigos_do_perfil(perfil: str) -> List[str]:
    vistos = []
    for v in VERSOES:
        if perfil in v.perfis and v.codigo not in vistos:
            vistos.append(v.codigo)
    return vistos


def versao_atual(codigo: str, hoje: Optional[date] = None) -> Optional[VersaoDocumento]:
    """Última versão publicada e vigente (a que é mostrada e aceita)."""
    publicadas = _publicadas(codigo, hoje)
    return publicadas[-1] if publicadas else None


def versao_minima_exigida(codigo: str, hoje: Optional[date] = None) -> Optional[VersaoDocumento]:
    """Versão mais nova que exigiu novo aceite. Aceite dessa versão ou de uma mais nova vale."""
    exigentes = [v for v in _publicadas(codigo, hoje) if v.exige_novo_aceite]
    return exigentes[-1] if exigentes else None


def documentos_vigentes(perfil: str, hoje: Optional[date] = None) -> List[VersaoDocumento]:
    """Documentos publicados que o perfil precisa aceitar. Vazio = nada exigido ainda."""
    return [v for v in (versao_atual(c, hoje) for c in codigos_do_perfil(perfil)) if v]


def ultima_versao(codigo: str) -> Optional[VersaoDocumento]:
    """Versão mais recente em qualquer estado (para leitura/revisão de rascunhos)."""
    versoes = sorted((v for v in VERSOES if v.codigo == codigo), key=lambda v: chave_versao(v.versao))
    return versoes[-1] if versoes else None


def buscar(codigo: str, versao: Optional[str] = None) -> Optional[VersaoDocumento]:
    if versao:
        return next((v for v in VERSOES if v.codigo == codigo and v.versao == versao), None)
    return versao_atual(codigo) or ultima_versao(codigo)
