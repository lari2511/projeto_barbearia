from typing import Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict, EmailStr, field_validator, Field


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


class RegistroResponse(BaseModel):
    """Resposta para endpoints de cadastro."""
    usuario: UsuarioPublic
    access_token: str
    token_type: str


class ClienteCreate(UsuarioBase):
    cpf: str  # Agora obrigatório

    @field_validator("cpf")
    @classmethod
    def validate_cpf(cls, v: str) -> str:
        # Remove pontuação
        cpf_limpo = v.replace(".", "").replace("-", "")
        if len(cpf_limpo) != 11 or not cpf_limpo.isdigit():
            raise ValueError("CPF deve ter 11 dígitos")
        
        # Validação do algoritmo do CPF
        if cpf_limpo == cpf_limpo[0] * 11:
            raise ValueError("CPF inválido")
        
        # Valida primeiro dígito verificador
        soma = sum(int(cpf_limpo[i]) * (10 - i) for i in range(9))
        digito1 = (soma * 10 % 11) % 10
        if digito1 != int(cpf_limpo[9]):
            raise ValueError("CPF inválido")
        
        # Valida segundo dígito verificador
        soma = sum(int(cpf_limpo[i]) * (11 - i) for i in range(10))
        digito2 = (soma * 10 % 11) % 10
        if digito2 != int(cpf_limpo[10]):
            raise ValueError("CPF inválido")
        
        return v


class BarbeiroCreate(UsuarioBase):
    cpf: str  # Agora obrigatório
    endereco: Optional[str] = None
    latitude: Optional[float] = None  # Opcional - usado apenas na busca dinâmica
    longitude: Optional[float] = None  # Opcional - usado apenas na busca dinâmica

    @field_validator("cpf")
    @classmethod
    def validate_cpf(cls, v: str) -> str:
        # Remove pontuação
        cpf_limpo = v.replace(".", "").replace("-", "")
        if len(cpf_limpo) != 11 or not cpf_limpo.isdigit():
            raise ValueError("CPF deve ter 11 dígitos")
        
        # Validação do algoritmo do CPF
        if cpf_limpo == cpf_limpo[0] * 11:
            raise ValueError("CPF inválido")
        
        # Valida primeiro dígito verificador
        soma = sum(int(cpf_limpo[i]) * (10 - i) for i in range(9))
        digito1 = (soma * 10 % 11) % 10
        if digito1 != int(cpf_limpo[9]):
            raise ValueError("CPF inválido")
        
        # Valida segundo dígito verificador
        soma = sum(int(cpf_limpo[i]) * (11 - i) for i in range(10))
        digito2 = (soma * 10 % 11) % 10
        if digito2 != int(cpf_limpo[10]):
            raise ValueError("CPF inválido")
        
        return v


class BarbeariaCreate(UsuarioBase):
    endereco: str  # OBRIGATÓRIO - localização física fixa
    cep: Optional[str] = None
    cpf: str  # CPF do dono - agora obrigatório
    cnpj: Optional[str] = None  # CNPJ da empresa
    latitude: Optional[float] = None  # IMPORTANTE: Localização física da barbearia
    longitude: Optional[float] = None  # IMPORTANTE: Localização física da barbearia

    @field_validator("cpf")
    @classmethod
    def validate_cpf(cls, v: str) -> str:
        cpf_limpo = v.replace(".", "").replace("-", "")
        if len(cpf_limpo) != 11 or not cpf_limpo.isdigit():
            raise ValueError("CPF deve ter 11 dígitos")
        
        # Validação do algoritmo do CPF
        if cpf_limpo == cpf_limpo[0] * 11:
            raise ValueError("CPF inválido")
        
        # Valida primeiro dígito verificador
        soma = sum(int(cpf_limpo[i]) * (10 - i) for i in range(9))
        digito1 = (soma * 10 % 11) % 10
        if digito1 != int(cpf_limpo[9]):
            raise ValueError("CPF inválido")
        
        # Valida segundo dígito verificador
        soma = sum(int(cpf_limpo[i]) * (11 - i) for i in range(10))
        digito2 = (soma * 10 % 11) % 10
        if digito2 != int(cpf_limpo[10]):
            raise ValueError("CPF inválido")
        
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
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    cadeira_livre: bool
    presente_em_local: bool = False
    horario_chegada: Optional[datetime] = None


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
    barbeiro_selecionado_id: Optional[int] = None  # Confirmação defensiva de origem do frontend
    cadeira_id: Optional[int] = None  # BRB/cadeira (opcional)
    data_hora_inicio: Optional[datetime] = None  # Novo campo
    data_hora_fim: Optional[datetime] = None  # Novo campo
    cliente_latitude: float
    cliente_longitude: float


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
    email_verificado: bool
    perfil_aprovado: bool
    perfil_aprovado_em: Optional[datetime] = None
    disponivel: Optional[bool] = False  # Campo para barbeiros
    presente_em_local: Optional[bool] = False  # Se barbeiro está presente
    horario_chegada: Optional[datetime] = None  # Quando chegou


class DocumentoVerificar(BaseModel):
    usuario_id: int
    aprovado: bool
    motivo_rejeicao: Optional[str] = None

# ==========================================
# NOVOS SCHEMAS - BARBERMOVIE
# ==========================================

# --- Freelancer ---

class FreelancerCreate(BaseModel):
    """Dados para cadastro de freelancer"""
    tempo_experiencia_anos: int
    nivel_tecnico: str  # intermediario, avancado, expert
    especialidades: list[str]  # ["corte", "barba", "sobrancelha", "facial", "quimica"]
    
    @field_validator("nivel_tecnico")
    @classmethod
    def validate_nivel(cls, v: str) -> str:
        if v not in ["intermediario", "avancado", "expert"]:
            raise ValueError("N�vel t�cnico inv�lido. Use: intermediario, avancado ou expert")
        return v
    
    @field_validator("especialidades")
    @classmethod
    def validate_especialidades(cls, v: list[str]) -> list[str]:
        validos = ["corte", "barba", "sobrancelha", "facial", "quimica"]
        if not v:
            raise ValueError("Selecione pelo menos uma especialidade")
        for esp in v:
            if esp not in validos:
                raise ValueError(f"Especialidade inv�lida: {esp}")
        return v


class PortfolioUpload(BaseModel):
    """Upload de foto para portfolio"""
    tipo_servico: str  # corte, barba, facial
    url_imagem: str
    descricao: Optional[str] = None


class PortfolioResponse(BaseModel):
    """Resposta de foto do portfolio"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    tipo_servico: str
    url_imagem: str
    descricao: Optional[str]
    ordem: int
    criado_em: datetime


class FreelancerResponse(BaseModel):
    """Dados publicos do freelancer"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    usuario_id: int
    tempo_experiencia_anos: int
    nivel_tecnico: str
    status_pausado: bool
    latitude: Optional[float]
    longitude: Optional[float]
    distancia_km: Optional[float] = None
    
    # Dados do usu�rio
    nome: Optional[str] = None
    foto_perfil: Optional[str] = None
    
    # Avalia��o m�dia
    media_avaliacoes: Optional[float] = None
    total_avaliacoes: Optional[int] = None


class FreelancerDetalhes(FreelancerResponse):
    """Detalhes completos do freelancer (com portfolio)"""
    especialidades: list[str] = []
    portfolio: list[PortfolioResponse] = []
    avaliacoes_recentes: list = []


class SolicitarFreelancerRequest(BaseModel):
    """Payload para barbearia solicitar um freelancer"""
    freelancer_id: int
    servico_id: Optional[int] = None
    cadeira_id: Optional[int] = None
    data_hora_inicio: Optional[datetime] = None


# --- Cadeiras ---

class CadeiraCreate(BaseModel):
    """Criar cadeira na barbearia"""
    numero: int


class CadeiraUpdate(BaseModel):
    """Atualizar status da cadeira"""
    status: str  # disponivel, bloqueada, ocupada


class CadeiraResponse(BaseModel):
    """Resposta de cadeira"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    numero: int
    status: str
    criado_em: datetime
    freelancer_id: Optional[int] = None
    freelancer_nome: Optional[str] = None
    ocupada_em: Optional[datetime] = None


class CadeiraPresencaRequest(BaseModel):
    """Marcar freelancer como presente em uma cadeira"""
    freelancer_id: int
    cadeira_id: int


class CadeiraPresencaEncerrarRequest(BaseModel):
    """Encerrar presenca de freelancer em uma cadeira"""
    cadeira_id: int


# --- Assinaturas ---

class AssinaturaResponse(BaseModel):
    """Status da assinatura"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    barbearia_id: int
    plano: str
    valor: float
    status: str
    proximo_vencimento: datetime
    criado_em: datetime


# --- Comiss�es ---

class ComissaoResponse(BaseModel):
    """Dados de comissao"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    freelancer_id: int
    chamado_id: int
    valor_servico: float
    comissao_percentual: float
    valor_comissao: float
    status: str
    pago_em: Optional[datetime]
    criado_em: datetime


class RelatorioComissoes(BaseModel):
    """Relatorio de comissoes do freelancer"""
    total_atendimentos: int
    total_atendimentos_app: int
    total_atendimentos_proprios: int
    ganhos_brutos: float
    total_comissoes: float
    ganhos_liquidos: float
    comissoes_pendentes: float
    comissoes_pagas: float
    comissoes: list[ComissaoResponse]
    saldo_carteira: float = 0.0
    limite_negativo: float = -50.0
    bloqueado_financeiro: bool = False
    historico_movimentacoes: list[dict] = Field(default_factory=list)


# --- Avalia��es ---

class AvaliacaoCreate(BaseModel):
    """Criar avaliacao"""
    chamado_id: int
    avaliado_id: Optional[int] = None  # quando usar endpoint genérico
    nota: int  # 1-5
    comentario: Optional[str] = None
    foto_corte_url: Optional[str] = None  # URL da foto do corte (enviada antes via upload)
    tempo_real_servico_min: Optional[int] = None  # Tempo real em minutos
    
    @field_validator("nota")
    @classmethod
    def validate_nota(cls, v: int) -> int:
        if v < 1 or v > 5:
            raise ValueError("Nota deve ser entre 1 e 5")
        return v


class AvaliacaoFreelancerResponse(BaseModel):
    """Resposta de avaliacao do freelancer"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    nota: int
    comentario: Optional[str]
    tipo_avaliador: str
    foto_corte_url: Optional[str] = None  # Foto do corte realizado
    tempo_real_servico_min: Optional[int] = None  # Tempo real em minutos
    criado_em: datetime
    
    # Dados do avaliador
    avaliador_nome: Optional[str] = None
    avaliador_foto: Optional[str] = None


class AvaliacaoBarbeariaResponse(BaseModel):
    """Resposta de avaliacao da barbearia"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    nota: int
    comentario: Optional[str]
    tipo_avaliador: str
    criado_em: datetime
    
    # Dados do avaliador
    avaliador_nome: Optional[str] = None
    avaliador_foto: Optional[str] = None


# --- Solicita��es de Atendimento ---

class SolicitacaoAtendimento(BaseModel):
    """Cliente solicita atendimento com freelancer"""
    freelancer_id: int
    barbearia_id: int
    servico_id: int
    data_hora_inicio: str  # ISO format


class AceitarRecusarAtendimento(BaseModel):
    """Freelancer aceita ou recusa atendimento"""
    chamado_id: int
    aceitar: bool  # True = aceitar, False = recusar
    motivo: Optional[str] = None  # Motivo da recusa (opcional)

class AtualizarStatusFreelancer(BaseModel):
    """Atualizar status do freelancer"""
    status: str  # "offline", "online_region", "present_local"
    barbearia_id: Optional[int] = None  # Obrigatório se status = "present_local"
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "present_local",
                "barbearia_id": 1
            }
        }