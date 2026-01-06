from typing import Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict, EmailStr, field_validator


class UsuarioBase(BaseModel):
    """Dados de entrada para criação de usuário (inclui senha)."""

    nome: str
    email: EmailStr
    senha: str
    telefone: Optional[str] = None

    @field_validator("nome")
    @classmethod
    def validate_nome(cls, v: str) -> str:
        if len(v.strip()) < 3:
            raise ValueError("Nome precisa de pelo menos 3 caracteres")
        return v

    @field_validator("senha")
    @classmethod
    def validate_senha(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError("Senha precisa ter 6 caracteres ou mais")
        return v

    @field_validator("telefone")
    @classmethod
    def validate_telefone(cls, v: Optional[str]) -> Optional[str]:
        if v and len(v) < 8:
            raise ValueError("Telefone deve ter DDD e número")
        return v


class Login(BaseModel):
    email: EmailStr
    senha: str


class UsuarioPublic(BaseModel):
    """Dados expostos em respostas (nunca inclui senha)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str
    email: EmailStr
    telefone: Optional[str] = None
    tipo: Optional[str] = None
    endereco: Optional[str] = None
    email_verificado: Optional[bool] = None
    criado_em: Optional[datetime] = None


class ClienteCreate(UsuarioBase):
    cpf: Optional[str] = None

    @field_validator("cpf")
    @classmethod
    def validate_cpf(cls, v: Optional[str]) -> Optional[str]:
        if v:
            # Remove pontuação
            cpf_limpo = v.replace(".", "").replace("-", "")
            if len(cpf_limpo) != 11 or not cpf_limpo.isdigit():
                raise ValueError("CPF deve ter 11 dígitos")
        return v


class BarbeiroCreate(UsuarioBase):
    cpf: Optional[str] = None

    @field_validator("cpf")
    @classmethod
    def validate_cpf(cls, v: Optional[str]) -> Optional[str]:
        if v:
            # Remove pontuação
            cpf_limpo = v.replace(".", "").replace("-", "")
            if len(cpf_limpo) != 11 or not cpf_limpo.isdigit():
                raise ValueError("CPF deve ter 11 dígitos")
        return v


class BarbeariaCreate(UsuarioBase):
    endereco: str
    cep: Optional[str] = None
    cpf: Optional[str] = None  # CPF do dono
    cnpj: Optional[str] = None  # CNPJ da empresa

    @field_validator("cpf")
    @classmethod
    def validate_cpf(cls, v: Optional[str]) -> Optional[str]:
        if v:
            cpf_limpo = v.replace(".", "").replace("-", "")
            if len(cpf_limpo) != 11 or not cpf_limpo.isdigit():
                raise ValueError("CPF deve ter 11 dígitos")
        return v

    @field_validator("cnpj")
    @classmethod
    def validate_cnpj(cls, v: Optional[str]) -> Optional[str]:
        if v:
            cnpj_limpo = v.replace(".", "").replace("/", "").replace("-", "")
            if len(cnpj_limpo) != 14 or not cnpj_limpo.isdigit():
                raise ValueError("CNPJ deve ter 14 dígitos")
        return v

    @field_validator("endereco")
    @classmethod
    def validate_endereco(cls, v: str) -> str:
        if len(v.strip()) < 5:
            raise ValueError("Endereço muito curto")
        return v

    @field_validator("cep")
    @classmethod
    def validate_cep(cls, v: Optional[str]) -> Optional[str]:
        if v and len(v.replace("-", "")) not in (8,):
            raise ValueError("CEP deve ter 8 dígitos")
        return v


class BarbeariaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str
    endereco: str
    telefone: Optional[str] = None
    cadeira_livre: bool


class ServicoCreate(BaseModel):
    """Para criar um novo serviço na barbearia"""
    nome: str  # Nome criativo (ex: "O Rei do Disfarce")
    categoria: str  # Categoria padrão (ex: "corte", "barba", "combo")
    descricao: Optional[str] = None
    valor: float
    duracao_minutos: Optional[int] = 30

    @field_validator("nome")
    @classmethod
    def validate_nome(cls, v: str) -> str:
        if len(v.strip()) < 3:
            raise ValueError("Nome do serviço muito curto")
        return v

    @field_validator("categoria")
    @classmethod
    def validate_categoria(cls, v: str) -> str:
        categorias_validas = [
            "corte", "barba", "sobrancelha", "quimica", 
            "infantil", "tratamento", "combo", "outros"
        ]
        if v.lower() not in categorias_validas:
            raise ValueError(f"Categoria inválida. Válidas: {', '.join(categorias_validas)}")
        return v.lower()

    @field_validator("valor")
    @classmethod
    def validate_valor(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("Valor deve ser maior que zero")
        return v

    @field_validator("duracao_minutos")
    @classmethod
    def validate_duracao(cls, v: Optional[int]) -> int:
        if v and (v < 5 or v > 480):
            raise ValueError("Duração deve estar entre 5 e 480 minutos")
        return v or 30


class ServicoResponse(BaseModel):
    """Resposta com dados do serviço"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    barbearia_id: int
    nome: str
    categoria: str
    descricao: Optional[str] = None
    valor: float
    duracao_minutos: int
    ativo: bool
    criado_em: datetime


class ServicoUpdate(BaseModel):
    """Para atualizar um serviço existente"""
    nome: Optional[str] = None
    categoria: Optional[str] = None
    descricao: Optional[str] = None
    valor: Optional[float] = None
    duracao_minutos: Optional[int] = None
    ativo: Optional[bool] = None


class TemplateSevico(BaseModel):
    """Template/Sugestão de serviço com valores padrão"""
    nome: str
    descricao: str
    valor_padrao: float
    duracao_minutos_padrao: int
    categoria: str  # "cabelo", "barba", "combo", "outro"
    
    class Config:
        json_schema_extra = {
            "example": {
                "nome": "Corte Masculino",
                "descricao": "Corte clássico com máquina e tesoura",
                "valor_padrao": 35.00,
                "duracao_minutos_padrao": 30,
                "categoria": "cabelo"
            }
        }


class ChamadoCreate(BaseModel):
    servico_id: int
    barbearia_id: int
    barbeiro_id: Optional[int] = None  # Barbeiro específico (opcional)
    data_hora_inicio: Optional[datetime] = None  # Novo campo
    data_hora_fim: Optional[datetime] = None  # Novo campo


class ChamadoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: str
    valor_total: Optional[float] = None
    comissao_plataforma: Optional[float] = None
    valor_freelancer: Optional[float] = None
    valor_dono: Optional[float] = None
    data_hora_inicio: Optional[datetime] = None
    data_hora_fim: Optional[datetime] = None
    criado_em: datetime


# --- Novos Schemas para funcionalidades extras ---

class AvaliacaoCreate(BaseModel):
    chamado_id: int
    avaliado_id: int
    nota: int
    comentario: Optional[str] = None

    @field_validator("nota")
    @classmethod
    def validate_nota(cls, v: int) -> int:
        if v < 1 or v > 5:
            raise ValueError("Nota deve ser entre 1 e 5")
        return v


class AvaliacaoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nota: int
    comentario: Optional[str]
    criado_em: datetime


class FavoritoCreate(BaseModel):
    favorito_id: int  # ID do barbeiro ou barbearia


class FavoritoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    favorito_id: int
    criado_em: datetime


class FotoCreate(BaseModel):
    servico_id: Optional[int] = None
    url: str
    descricao: Optional[str] = None


class FotoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    url: str
    descricao: Optional[str]
    criado_em: datetime


class CupomCreate(BaseModel):
    codigo: str
    desconto_percentual: Optional[float] = None
    desconto_fixo: Optional[float] = None
    valido_ate: Optional[str] = None
    uso_maximo: Optional[int] = None

    @field_validator("codigo")
    @classmethod
    def validate_codigo(cls, v: str) -> str:
        if len(v.strip()) < 3:
            raise ValueError("Código deve ter pelo menos 3 caracteres")
        return v.upper()


class CupomResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    codigo: str
    desconto_percentual: Optional[float]
    desconto_fixo: Optional[float]
    ativo: bool


class CupomValidar(BaseModel):
    codigo: str


class PontosFidelidadeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    pontos: int
    nivel: str


class NotificacaoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    titulo: str
    mensagem: str
    lida: bool
    tipo: str
    criado_em: datetime


class MensagemChatCreate(BaseModel):
    chamado_id: int
    mensagem: str


class MensagemChatResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    remetente_id: int
    mensagem: str
    lida: bool
    criado_em: datetime


class RecuperarSenhaRequest(BaseModel):
    email: EmailStr


class ResetarSenhaRequest(BaseModel):
    token: str
    nova_senha: str

    @field_validator("nova_senha")
    @classmethod
    def validate_senha(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError("Senha precisa ter 6 caracteres ou mais")
        return v


class VerificarEmailRequest(BaseModel):
    token: str


class BarbeariasProximasRequest(BaseModel):
    latitude: float
    longitude: float
    raio_km: Optional[float] = 10.0


class AgendamentoFuturo(BaseModel):
    servico_id: int
    barbearia_id: int
    data_agendamento: str  # ISO format

    @field_validator("data_agendamento")
    @classmethod
    def validate_data(cls, v: str) -> str:
        from datetime import datetime
        try:
            data = datetime.fromisoformat(v)
            if data < datetime.now():
                raise ValueError("Data de agendamento deve ser futura")
        except ValueError as e:
            raise ValueError(f"Data inválida: {str(e)}")
        return v


class EstatisticasResponse(BaseModel):
    total_chamados: int
    total_receita: float
    servico_mais_pedido: Optional[str]
    media_avaliacao: Optional[float]


class Enable2FAResponse(BaseModel):
    secret: str
    qr_code_url: str


class Verify2FARequest(BaseModel):
    token: str


# --- Disponibilidade (modo on-demand) ---

class DisponibilidadeCreate(BaseModel):
    inicio: Optional[str] = None  # ISO; se None, agora
    fim: Optional[str] = None     # ISO; se None, agora + 2h
    raio_km: float = 3.0


class DisponibilidadeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    usuario_id: int
    inicio: datetime
    fim: datetime
    raio_km: float
    ativo: bool
    criado_em: datetime

    # Dados do profissional/barbearia
    nome: Optional[str] = None
    tipo: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    distancia_km: Optional[float] = None


# --- Schemas para Documentos ---

class DocumentoUpload(BaseModel):
    rg: str
    documento_frente_url: str
    documento_verso_url: str
    selfie_documento_url: str


class DocumentoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str
    rg: Optional[str]
    documento_frente_url: Optional[str]
    documento_verso_url: Optional[str]
    selfie_documento_url: Optional[str]
    documento_verificado: bool
    documento_verificado_em: Optional[datetime]
    documento_rejeitado_motivo: Optional[str]


class DocumentoVerificar(BaseModel):
    usuario_id: int
    aprovado: bool
    motivo_rejeicao: Optional[str] = None