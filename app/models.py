# --- ARQUIVO: app/models.py ---
# Modelos SQLAlchemy para o banco de dados

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean, Enum, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base
import enum

# --- ENUMS (Estados) ---
class StatusAgendamento(str, enum.Enum):
    """Status possíveis de um agendamento"""
    PENDENTE = "pendente"      # Cliente pediu, aguardando aceite do barbeiro/dono
    CONFIRMADO = "confirmado"  # Barbeiro/Dono aceitou
    EM_ATENDIMENTO = "em_atendimento"  # Corte em andamento
    CONCLUIDO = "concluido"    # Serviço foi realizado
    CANCELADO = "cancelado"    # Cliente ou barbeiro cancelou

class CategoriaServico(str, enum.Enum):
    """Categorias padrão de serviços (para organização, relatórios e filtros)"""
    CORTE = "corte"                    # Corte de Cabelo
    BARBA = "barba"                    # Barba e Bigode
    SOBRANCELHA = "sobrancelha"        # Sobrancelha
    QUIMICA = "quimica"                # Química (Luzes, Alisamento, Tintura)
    INFANTIL = "infantil"              # Infantil (Kids)
    TRATAMENTO = "tratamento"          # Tratamento (Hidratação, Limpeza de Pele)
    COMBO = "combo"                    # Combos (Ex: Corte + Barba)
    FACIAL = "facial"                  # Tratamento Facial
    OUTROS = "outros"                  # Outros serviços

class NivelTecnico(str, enum.Enum):
    """Nível técnico do freelancer"""
    INTERMEDIARIO = "intermediario"
    AVANCADO = "avancado"
    EXPERT = "expert"

class StatusFreelancer(str, enum.Enum):
    """Status do freelancer (barbeiro) para controle de conflito de agenda"""
    OFFLINE = "offline"                    # Não pode receber chamados
    ONLINE_REGION = "online_region"        # Disponível para qualquer barbearia da região
    PRESENT_LOCAL = "present_local"        # Presente em uma barbearia específica

class StatusCadeira(str, enum.Enum):
    """Status da cadeira na barbearia"""
    DISPONIVEL = "disponivel"
    BLOQUEADA = "bloqueada"
    OCUPADA = "ocupada"

class OrigemCliente(str, enum.Enum):
    """Origem do cliente para cálculo de comissão"""
    APP = "app"          # Cliente veio pelo BarberMovie (gera comissão)
    PROPRIO = "proprio"  # Cliente próprio do freelancer (sem comissão)

class BarbeariaFreelancer(Base):
    """Relacionamento entre barbearias e freelancers (para bloqueios)"""
    __tablename__ = "barbearia_freelancer"
    
    id = Column(Integer, primary_key=True, index=True)
    barbearia_id = Column(Integer, ForeignKey("barbearias.id"), nullable=False, index=True)
    freelancer_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False, index=True)
    bloqueado = Column(Boolean, default=False, index=True)
    motivo = Column(String, nullable=True)
    data_bloqueio = Column(DateTime, nullable=True)
    criado_em = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    barbearia = relationship("Barbearia")
    freelancer = relationship("Usuario")

class Usuario(Base):
    __tablename__ = "usuarios"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    nome = Column(String)
    senha_hash = Column(String)
    tipo = Column(String)  # 'cliente', 'barbeiro', 'barbearia'
    endereco = Column(String, nullable=True)
    telefone = Column(String, nullable=True)
    cpf = Column(String, nullable=True, unique=True)  # Para clientes e barbeiros
    cnpj = Column(String, nullable=True, unique=True)  # Para barbearias
    rg = Column(String, nullable=True)  # RG ou CNH
    documento_frente_url = Column(String, nullable=True)  # URL da foto do documento frente
    documento_verso_url = Column(String, nullable=True)  # URL da foto do documento verso
    selfie_documento_url = Column(String, nullable=True)  # Selfie com documento
    documento_verificado = Column(Boolean, default=False)
    documento_verificado_em = Column(DateTime, nullable=True)
    documento_rejeitado_motivo = Column(String, nullable=True)
    email_verificado = Column(Boolean, default=False)
    token_verificacao = Column(String, nullable=True)
    twofa_ativo = Column(Boolean, default=False)
    twofa_secret = Column(String, nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    foto_perfil = Column(String, nullable=True)
    perfil_aprovado = Column(Boolean, default=False)  # Admin deve aprovar para ativar
    perfil_aprovado_em = Column(DateTime, nullable=True)
    disponivel = Column(Boolean, default=False)  # Barbeiro está disponível para chamados
    ocupado_ate = Column(DateTime, nullable=True, index=True)  # ✅ Timestamp de quando o barbeiro estará livre (liberação automática)
    em_atendimento = Column(Boolean, default=False)  # Barbeiro está atualmente em atendimento
    presente_em_local = Column(Boolean, default=False)  # Barbeiro está presente na barbearia
    online_regiao = Column(Boolean, default=False)  # Freelancer online no marketplace
    barbearia_atual_id = Column(Integer, ForeignKey("barbearias.id"), nullable=True)  # Barbearia onde está presente
    horario_chegada = Column(DateTime, nullable=True)  # Horário que chegou na barbearia
    criado_em = Column(DateTime, default=datetime.utcnow)
    
    # ✅ CONTROLE ADMIN - Flagging de usuários problemáticos
    bloqueado_por_admin = Column(Boolean, default=False)  # Admin bloqueou este usuário
    motivo_bloqueio = Column(String, nullable=True)  # Motivo do bloqueio
    bloqueado_em = Column(DateTime, nullable=True)  # Quando foi bloqueado
    media_avaliacoes_negativas = Column(Float, default=0)  # Contém avaliações ruim frequentemente
    total_avaliacoes_negativas = Column(Integer, default=0)  # Total de avaliações 1-2 estrelas
    
    # ✅ FIREBASE - Push Notifications
    device_token = Column(String, nullable=True)  # FCM token do React Native para notificações push
    device_token_atualizado_em = Column(DateTime, nullable=True)  # Última vez que o token foi atualizado
    
    # Relationships
    chamados_cliente = relationship("Chamado", foreign_keys="Chamado.cliente_id", back_populates="cliente")
    chamados_barbeiro = relationship("Chamado", foreign_keys="Chamado.barbeiro_id", back_populates="barbeiro")
    barbearias = relationship("Barbearia", back_populates="usuario", foreign_keys="Barbearia.usuario_id")
    barbearia_atual = relationship("Barbearia", foreign_keys=[barbearia_atual_id])

class Barbearia(Base):
    __tablename__ = "barbearias"
    
    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"))
    nome = Column(String)
    endereco = Column(String)
    telefone = Column(String, nullable=True)
    cep = Column(String, nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    cadeira_livre = Column(Boolean, default=True)  # LEGADO - manter compatibilidade
    status_online = Column(Boolean, default=True)  # Barbearia online/offline
    presente_em_local = Column(Boolean, default=False)  # Barbearia aberta no local
    horario_chegada = Column(DateTime, nullable=True)  # Horário que abriu
    bloqueada = Column(Boolean, default=False, index=True)  # Bloqueada por inadimplência
    motivo_bloqueio = Column(String, nullable=True)  # Motivo do bloqueio
    bloqueada_em = Column(DateTime, nullable=True)  # Quando foi bloqueada
    criado_em = Column(DateTime, default=datetime.utcnow)
    
    usuario = relationship("Usuario", back_populates="barbearias", foreign_keys=[usuario_id])
    servicos = relationship("Servico", back_populates="barbearia")
    chamados = relationship("Chamado", back_populates="barbearia")
    cadeiras = relationship("Cadeira", back_populates="barbearia")
    avaliacoes_recebidas = relationship("AvaliacaoBarbearia", back_populates="barbearia")

class Servico(Base):
    __tablename__ = "servicos"
    
    id = Column(Integer, primary_key=True, index=True)
    # O SEGREDO: Este serviço pertence EXCLUSIVAMENTE a esta barbearia
    barbearia_id = Column(Integer, ForeignKey("barbearias.id"), nullable=False, index=True)
    
    # ✅ LIBERDADE: O dono escreve o que quiser (nome criativo)
    nome = Column(String, nullable=False)  # Ex: "O Rei do Disfarce"
    descricao = Column(String, nullable=True)
    
    # ✅ ORGANIZAÇÃO: O sistema sabe o que é (para relatórios, filtros)
    categoria = Column(String, nullable=False, index=True)  # Ex: "corte", "barba", "combo"
    
    valor = Column(Float, nullable=False)  # Ex: 35.00
    duracao_minutos = Column(Integer, default=30)  # Ex: 40 minutos
    ativo = Column(Boolean, default=True)  # Para desativar serviço sem deletar
    criado_em = Column(DateTime, default=datetime.utcnow)
    
    barbearia = relationship("Barbearia", back_populates="servicos")
    chamados = relationship("Chamado", back_populates="servico")

class Chamado(Base):
    __tablename__ = "chamados"
    
    id = Column(Integer, primary_key=True, index=True)
    cliente_id = Column(Integer, ForeignKey("usuarios.id"))
    barbeiro_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    servico_id = Column(Integer, ForeignKey("servicos.id"))
    barbearia_id = Column(Integer, ForeignKey("barbearias.id"))
    cadeira_id = Column(Integer, ForeignKey("cadeiras.id"), nullable=True)
    
    # --- TEMPO (Quando vai ser) ---
    data_hora_inicio = Column(DateTime, nullable=True, index=True)  # Quando começa o serviço
    data_hora_fim = Column(DateTime, nullable=True)  # Quando termina (importante para liberar cadeira)
    data_agendamento = Column(DateTime, default=datetime.utcnow)  # Quando foi agendado
    horario_match = Column(DateTime, nullable=True)  # Quando freelancer aceitou (inicia contagem de 5 min)
    
    # --- STATUS (Máquina de estados) ---
    status = Column(String, default=StatusAgendamento.PENDENTE)  # pendente, confirmado, concluído, cancelado
    cliente_chegou = Column(Boolean, default=False)  # Cliente confirmou chegada no local
    barbeiro_chegou = Column(Boolean, default=False)  # Barbeiro confirmou chegada no local
    
    # --- APROVAÇÕES (Bidirecional) ---
    aprovado_barbeiro = Column(Boolean, default=False)  # Barbeiro aprovou
    aprovado_barbearia = Column(Boolean, default=False)  # Barbearia (dono) aprovou
    aprovado_barbeiro_em = Column(DateTime, nullable=True)
    aprovado_barbearia_em = Column(DateTime, nullable=True)
    
    # --- ORIGEM DO CLIENTE (Para cálculo de comissão) ---
    origem_cliente = Column(String, default=OrigemCliente.APP)  # app, proprio
    
    # --- SNAPSHOT FINANCEIRO (Valores no momento do agendamento) ---
    # IMPORTANTE: Esses valores são salvos para não mudar se as regras de comissão mudarem depois
    valor_total = Column(Float, nullable=True)  # Ex: 50.00 (valor completo do serviço)
    comissao_plataforma = Column(Float, nullable=True)  # Ex: 7.50 (15% para a plataforma)
    valor_freelancer = Column(Float, nullable=True)  # Ex: 22.50 (45% para o barbeiro)
    valor_dono = Column(Float, nullable=True)  # Ex: 20.00 (40% para o dono da barbearia)
    
    # --- LEGADO (Manter compatibilidade com código anterior) ---
    valor_original = Column(Float, nullable=True)
    valor_final = Column(Float, nullable=True)
    cupom_codigo = Column(String, nullable=True)
    observacao = Column(String, nullable=True)  # Ex: "Cliente pediu para não atrasar"
    
    # --- TIMESTAMPS ---
    criado_em = Column(DateTime, default=datetime.utcnow)
    atualizado_em = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    concluido_em = Column(DateTime, nullable=True)
    cancelado_em = Column(DateTime, nullable=True)
    tempo_cancelamento_minutos = Column(Integer, nullable=True)
    valor_taxa_cancelamento = Column(Float, nullable=True)
    motivo_cancelamento = Column(String, nullable=True)
    
    cliente = relationship("Usuario", foreign_keys=[cliente_id], back_populates="chamados_cliente")
    barbeiro = relationship("Usuario", foreign_keys=[barbeiro_id], back_populates="chamados_barbeiro")
    servico = relationship("Servico", back_populates="chamados")
    barbearia = relationship("Barbearia", back_populates="chamados")
    cadeira = relationship("Cadeira", foreign_keys=[cadeira_id])
    avaliacoes = relationship("Avaliacao", back_populates="chamado")
    historico = relationship("ChamadoHistorico", back_populates="chamado", order_by="ChamadoHistorico.criado_em")
    pagamento = relationship("Pagamento", back_populates="chamado", uselist=False)


class AgendamentoAtivo(Base):
    """
    Snapshot de rastreamento em tempo real para um chamado ativo.

    Armazena as coordenadas mais recentes do cliente e do barbeiro para
    cálculo de ETA e atualização em tempo real na interface.
    """
    __tablename__ = "agendamentos_ativos"

    id = Column(Integer, primary_key=True, index=True)
    chamado_id = Column(Integer, ForeignKey("chamados.id"), unique=True, nullable=False, index=True)
    cliente_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False, index=True)
    barbearia_id = Column(Integer, ForeignKey("barbearias.id"), nullable=False, index=True)
    barbeiro_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True, index=True)

    cliente_lat = Column(Float, nullable=True)
    cliente_lon = Column(Float, nullable=True)
    barbeiro_lat = Column(Float, nullable=True)
    barbeiro_lon = Column(Float, nullable=True)

    cliente_localizacao_em = Column(DateTime, nullable=True)
    barbeiro_localizacao_em = Column(DateTime, nullable=True)

    criado_em = Column(DateTime, default=datetime.utcnow, nullable=False)
    atualizado_em = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    chamado = relationship("Chamado", foreign_keys=[chamado_id])
    cliente = relationship("Usuario", foreign_keys=[cliente_id])
    barbeiro = relationship("Usuario", foreign_keys=[barbeiro_id])
    barbearia = relationship("Barbearia", foreign_keys=[barbearia_id])

class Avaliacao(Base):
    __tablename__ = "avaliacoes"
    
    id = Column(Integer, primary_key=True, index=True)
    chamado_id = Column(Integer, ForeignKey("chamados.id"))
    avaliador_id = Column(Integer, ForeignKey("usuarios.id"))  # quem avaliou
    avaliado_id = Column(Integer, ForeignKey("usuarios.id"))  # quem foi avaliado
    nota = Column(Integer)  # 1 a 5
    comentario = Column(String, nullable=True)
    criado_em = Column(DateTime, default=datetime.utcnow)
    
    chamado = relationship("Chamado", back_populates="avaliacoes")
    avaliador = relationship("Usuario", foreign_keys=[avaliador_id])
    avaliado = relationship("Usuario", foreign_keys=[avaliado_id])

class Favorito(Base):
    __tablename__ = "favoritos"
    
    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"))  # cliente
    favorito_id = Column(Integer, ForeignKey("usuarios.id"))  # barbeiro ou barbearia
    criado_em = Column(DateTime, default=datetime.utcnow)
    
    usuario = relationship("Usuario", foreign_keys=[usuario_id])
    favorito = relationship("Usuario", foreign_keys=[favorito_id])

class Foto(Base):
    __tablename__ = "fotos"
    
    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"))
    servico_id = Column(Integer, ForeignKey("servicos.id"), nullable=True)
    url = Column(String)
    descricao = Column(String, nullable=True)
    criado_em = Column(DateTime, default=datetime.utcnow)
    
    usuario = relationship("Usuario")
    servico = relationship("Servico")

class Cupom(Base):
    __tablename__ = "cupons"
    
    id = Column(Integer, primary_key=True, index=True)
    codigo = Column(String, unique=True, index=True)
    desconto_percentual = Column(Float, nullable=True)  # ex: 10.0 para 10%
    desconto_fixo = Column(Float, nullable=True)  # ex: 5.0 para R$5
    valido_ate = Column(DateTime, nullable=True)
    uso_maximo = Column(Integer, nullable=True)
    uso_atual = Column(Integer, default=0)
    ativo = Column(Boolean, default=True)
    criado_em = Column(DateTime, default=datetime.utcnow)

class PontosFidelidade(Base):
    __tablename__ = "pontos_fidelidade"
    
    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"))
    pontos = Column(Integer, default=0)
    nivel = Column(String, default="BRONZE")  # BRONZE, PRATA, OURO, PLATINA
    atualizado_em = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    usuario = relationship("Usuario")

class ChamadoHistorico(Base):
    __tablename__ = "chamados_historico"
    
    id = Column(Integer, primary_key=True, index=True)
    chamado_id = Column(Integer, ForeignKey("chamados.id"))
    status_anterior = Column(String, nullable=True)
    status_novo = Column(String)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"))  # quem fez a ação
    observacao = Column(String, nullable=True)
    criado_em = Column(DateTime, default=datetime.utcnow)
    
    chamado = relationship("Chamado", back_populates="historico")
    usuario = relationship("Usuario")

class TokenRecuperacao(Base):
    __tablename__ = "tokens_recuperacao"
    
    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"))
    token = Column(String, unique=True, index=True)
    usado = Column(Boolean, default=False)
    expira_em = Column(DateTime)
    criado_em = Column(DateTime, default=datetime.utcnow)
    
    usuario = relationship("Usuario")

    
    usuario = relationship("Usuario")

class MensagemChat(Base):
    __tablename__ = "mensagens_chat"
    
    id = Column(Integer, primary_key=True, index=True)
    chamado_id = Column(Integer, ForeignKey("chamados.id"))
    remetente_id = Column(Integer, ForeignKey("usuarios.id"))
    mensagem = Column(String)
    lida = Column(Boolean, default=False)
    criado_em = Column(DateTime, default=datetime.utcnow)
    
    chamado = relationship("Chamado")
    remetente = relationship("Usuario")

class Pagamento(Base):
    """
    Registro simplificado de valores para auditoria.
    App NÃO processa pagamentos - apenas registra valores.
    Barbeiro/Barbearia cobram presencialmente e repassam os 15% da plataforma depois.
    """
    __tablename__ = "pagamentos"

    id = Column(Integer, primary_key=True, index=True)
    chamado_id = Column(Integer, ForeignKey("chamados.id"), unique=True)
    valor_total = Column(Float)  # Valor total do serviço
    taxa_plataforma = Column(Float)  # 15% para a plataforma (calculado automaticamente)
    valor_barbeiro = Column(Float)  # O quanto o barbeiro/barbearia pode negociar (85%)
    pago_em = Column(DateTime, nullable=True)  # Quando foi marcado como pago/concluído
    criado_em = Column(DateTime, default=datetime.utcnow)

    chamado = relationship("Chamado", back_populates="pagamento")


class Saque(Base):
    """Registro de saques solicitados por barbeiros"""
    __tablename__ = "saques"

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), index=True)
    valor = Column(Float, nullable=False)  # Valor bruto solicitado
    valor_liquido = Column(Float, nullable=False)  # Depois de deduzir taxa
    taxa = Column(Float, default=0.0)  # 10% de taxa
    status = Column(String, default="pendente")  # pendente, processando, concluído, cancelado
    banco = Column(String, nullable=False)
    agencia = Column(String, nullable=False)
    conta = Column(String, nullable=False)
    tipo_conta = Column(String, default="corrente")  # corrente ou poupanca
    criado_em = Column(DateTime, default=datetime.utcnow)
    processado_em = Column(DateTime, nullable=True)
    cancelado_em = Column(DateTime, nullable=True)
    motivo_cancelamento = Column(String, nullable=True)

    usuario = relationship("Usuario")


class Disponibilidade(Base):
    __tablename__ = "disponibilidades"

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"))
    inicio = Column(DateTime, default=datetime.utcnow)
    fim = Column(DateTime, nullable=False)
    raio_km = Column(Float, default=3.0)
    ativo = Column(Boolean, default=True)
    criado_em = Column(DateTime, default=datetime.utcnow)

    usuario = relationship("Usuario")


# ==========================================
# NOVOS MODELOS - BARBERMOVIE
# ==========================================

class Freelancer(Base):
    """Modelo para freelancers (barbeiros independentes)"""
    __tablename__ = "freelancers"
    
    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), unique=True)
    tempo_experiencia_anos = Column(Integer, nullable=False)  # Anos de experiência
    nivel_tecnico = Column(String, nullable=False, default=NivelTecnico.INTERMEDIARIO)
    comissao_ativa = Column(Boolean, default=False)  # True após 1º mês grátis
    data_cadastro = Column(DateTime, default=datetime.utcnow)
    status_pausado = Column(Boolean, default=False)  # Pausar atendimentos (ex: almoço)
    latitude = Column(Float, nullable=True)  # Localização atual
    longitude = Column(Float, nullable=True)
    criado_em = Column(DateTime, default=datetime.utcnow)
    
    usuario = relationship("Usuario")
    especialidades = relationship("EspecialidadeFreelancer", back_populates="freelancer")
    portfolio = relationship("PortfolioFreelancer", back_populates="freelancer")
    avaliacoes_recebidas = relationship("AvaliacaoFreelancer", back_populates="freelancer")


class EspecialidadeFreelancer(Base):
    """Especialidades do freelancer (corte, barba, sobrancelha, facial, química)"""
    __tablename__ = "especialidades_freelancer"
    
    id = Column(Integer, primary_key=True, index=True)
    freelancer_id = Column(Integer, ForeignKey("freelancers.id"))
    tipo = Column(String, nullable=False)  # corte, barba, sobrancelha, facial, quimica
    criado_em = Column(DateTime, default=datetime.utcnow)
    
    freelancer = relationship("Freelancer", back_populates="especialidades")


class PortfolioFreelancer(Base):
    """Portfólio de fotos do freelancer (obrigatório)"""
    __tablename__ = "portfolio_freelancer"
    
    id = Column(Integer, primary_key=True, index=True)
    freelancer_id = Column(Integer, ForeignKey("freelancers.id"))
    tipo_servico = Column(String, nullable=False)  # corte, barba, facial
    url_imagem = Column(String, nullable=False)
    descricao = Column(String, nullable=True)
    ordem = Column(Integer, default=0)  # Para ordenação
    criado_em = Column(DateTime, default=datetime.utcnow)
    
    freelancer = relationship("Freelancer", back_populates="portfolio")


class Cadeira(Base):
    """Cadeiras da barbearia (disponíveis para freelancers)"""
    __tablename__ = "cadeiras"
    
    id = Column(Integer, primary_key=True, index=True)
    barbearia_id = Column(Integer, ForeignKey("barbearias.id"))
    chamado_id = Column(Integer, ForeignKey("chamados.id"), nullable=True)  # Qual chamado está usando essa cadeira
    freelancer_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    numero = Column(Integer, nullable=False)  # Número/nome da cadeira
    status = Column(String, default=StatusCadeira.DISPONIVEL)  # disponivel, bloqueada, ocupada
    acionada_em = Column(DateTime, nullable=True)  # Quando foi acionada para barbeiros
    ocupada_em = Column(DateTime, nullable=True)
    liberada_em = Column(DateTime, nullable=True)
    criado_em = Column(DateTime, default=datetime.utcnow)
    
    barbearia = relationship("Barbearia", back_populates="cadeiras")
    freelancer = relationship("Usuario", foreign_keys=[freelancer_id])
    chamado = relationship("Chamado", foreign_keys=[chamado_id])
    chamado = relationship("Chamado", foreign_keys=[chamado_id])


class Assinatura(Base):
    """Assinatura mensal da barbearia com cálculo progressivo por cadeira"""
    __tablename__ = "assinaturas"
    
    id = Column(Integer, primary_key=True, index=True)
    barbearia_id = Column(Integer, ForeignKey("barbearias.id"), unique=True)
    quantidade_cadeiras = Column(Integer, default=1)  # Número de cadeiras
    valor_mensal = Column(Float, nullable=False)  # Valor calculado e fixado
    plano = Column(String, default="basico")  # Futuro: planos diferentes
    valor = Column(Float, default=49.90)  # Deprecated: usar valor_mensal
    status = Column(String, default="ativa")  # ativa, cancelada, vencida
    ativa = Column(Boolean, default=True)  # Status simplificado
    proximo_vencimento = Column(DateTime, nullable=False)
    criado_em = Column(DateTime, default=datetime.utcnow)
    atualizada_em = Column(DateTime, default=datetime.utcnow)  # Atualizado manualmente via API
    cancelado_em = Column(DateTime, nullable=True)
    
    barbearia = relationship("Barbearia")


class Comissao(Base):
    """Comissões do freelancer (4% sobre atendimentos via app)"""
    __tablename__ = "comissoes"
    
    id = Column(Integer, primary_key=True, index=True)
    freelancer_id = Column(Integer, ForeignKey("freelancers.id"))
    chamado_id = Column(Integer, ForeignKey("chamados.id"))
    valor_servico = Column(Float, nullable=False)
    comissao_percentual = Column(Float, default=4.0)  # 4%
    valor_comissao = Column(Float, nullable=False)
    status = Column(String, default="pendente")  # pendente, pago
    pago_em = Column(DateTime, nullable=True)
    criado_em = Column(DateTime, default=datetime.utcnow)
    
    freelancer = relationship("Freelancer")
    chamado = relationship("Chamado")


class AvaliacaoFreelancer(Base):
    """Avaliações recebidas pelo freelancer (de clientes e barbearias)"""
    __tablename__ = "avaliacoes_freelancer"
    
    id = Column(Integer, primary_key=True, index=True)
    freelancer_id = Column(Integer, ForeignKey("freelancers.id"))
    avaliador_id = Column(Integer, ForeignKey("usuarios.id"))
    chamado_id = Column(Integer, ForeignKey("chamados.id"))
    nota = Column(Integer, nullable=False)  # 1-5
    comentario = Column(String, nullable=True)
    tipo_avaliador = Column(String, nullable=False)  # cliente, barbearia
    # Campos específicos para avaliação de barbeiro
    foto_corte_url = Column(String, nullable=True)  # URL da foto do corte realizado
    tempo_real_servico_min = Column(Integer, nullable=True)  # Tempo em minutos
    criado_em = Column(DateTime, default=datetime.utcnow)
    
    # ✅ CONTROLE ADMIN - Avaliações problemáticas
    bloqueada_por_admin = Column(Boolean, default=False)  # Admin bloqueou esta avaliação
    motivo_bloqueio = Column(String, nullable=True)  # Motivo do bloqueio
    bloqueada_em = Column(DateTime, nullable=True)  # Quando foi bloqueada
    revisada_por_admin_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)  # Qual admin revisou
    
    freelancer = relationship("Freelancer", back_populates="avaliacoes_recebidas")
    avaliador = relationship("Usuario", foreign_keys=[avaliador_id])
    chamado = relationship("Chamado")
    admin_revisor = relationship("Usuario", foreign_keys=[revisada_por_admin_id])


class AvaliacaoBarbearia(Base):
    """Avaliações recebidas pela barbearia (de clientes e freelancers)"""
    __tablename__ = "avaliacoes_barbearia"
    
    id = Column(Integer, primary_key=True, index=True)
    barbearia_id = Column(Integer, ForeignKey("barbearias.id"))
    avaliador_id = Column(Integer, ForeignKey("usuarios.id"))
    chamado_id = Column(Integer, ForeignKey("chamados.id"))
    nota = Column(Integer, nullable=False)  # 1-5
    comentario = Column(String, nullable=True)
    tipo_avaliador = Column(String, nullable=False)  # cliente, freelancer
    criado_em = Column(DateTime, default=datetime.utcnow)
    
    # ✅ CONTROLE ADMIN - Avaliações problemáticas
    bloqueada_por_admin = Column(Boolean, default=False)  # Admin bloqueou esta avaliação
    motivo_bloqueio = Column(String, nullable=True)  # Motivo do bloqueio
    bloqueada_em = Column(DateTime, nullable=True)  # Quando foi bloqueada
    revisada_por_admin_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)  # Qual admin revisou
    
    barbearia = relationship("Barbearia", back_populates="avaliacoes_recebidas")
    avaliador = relationship("Usuario", foreign_keys=[avaliador_id])
    chamado = relationship("Chamado")
    admin_revisor = relationship("Usuario", foreign_keys=[revisada_por_admin_id])
class Notificacao(Base):
    """Notificações do sistema para usuários"""
    __tablename__ = "notificacoes"
    
    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False, index=True)
    titulo = Column(String, nullable=False)
    mensagem = Column(String, nullable=False)
    tipo = Column(String, nullable=False)  # novo_chamado, chamado_aceito, perfil_aprovado, etc
    lido = Column(Boolean, default=False, index=True)
    referencia_id = Column(Integer, nullable=True)  # ID do chamado, agendamento, etc
    criado_em = Column(DateTime, default=datetime.utcnow, index=True)
    
    usuario = relationship("Usuario", foreign_keys=[usuario_id])

class PrecoCustomizado(Base):
    """Preços customizados de barbeiros para serviços"""
    __tablename__ = "precos_customizados"
    
    id = Column(Integer, primary_key=True, index=True)
    barbeiro_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False, index=True)
    servico_id = Column(Integer, ForeignKey("servicos.id"), nullable=False, index=True)
    preco_original = Column(Float, nullable=False)
    preco_customizado = Column(Float, nullable=False)
    desconto_percentual = Column(Float, default=0)  # Desconto em %
    ativo = Column(Boolean, default=True, index=True)
    criado_em = Column(DateTime, default=datetime.utcnow)
    atualizado_em = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    barbeiro = relationship("Usuario", foreign_keys=[barbeiro_id])
    servico = relationship("Servico")


# ==========================================
# MODELOS DE RASTREAMENTO FINANCEIRO
# ==========================================

class TipoTransacao(str, enum.Enum):
    """Tipos de transações financeiras no sistema"""
    COMISSAO_FREELANCER = "comissao_freelancer"  # 40% para o barbeiro
    COMISSAO_BARBEARIA = "comissao_barbearia"    # 50% para o dono da barbearia
    TAXA_PLATAFORMA = "taxa_plataforma"          # 10% para a BarberMovie
    PAGAMENTO_ASSINATURA = "pagamento_assinatura"  # Mensalidade das cadeiras
    SAQUE_PROCESSADO = "saque_processado"        # Quando um saque é concluído
    DEVOLUCAO = "devolucao"                      # Devolução por cancelamento


class CarteiraBarbeiro(Base):
    """Saldo virtual do barbeiro para controle de ganhos e débito de comissão."""
    __tablename__ = "carteiras"

    id = Column(Integer, primary_key=True, index=True)
    barbeiro_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False, unique=True, index=True)
    saldo = Column(Float, default=0.0, nullable=False)
    limite_negativo = Column(Float, default=-50.0, nullable=False)
    criado_em = Column(DateTime, default=datetime.utcnow)
    atualizado_em = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    barbeiro = relationship("Usuario", foreign_keys=[barbeiro_id])
    movimentacoes = relationship("HistoricoMovimentacaoFinanceira", back_populates="carteira")


class HistoricoMovimentacaoFinanceira(Base):
    """Auditoria linha a linha de cada crédito/débito aplicado na carteira do barbeiro."""
    __tablename__ = "historico_movimentacoes"

    id = Column(Integer, primary_key=True, index=True)
    carteira_id = Column(Integer, ForeignKey("carteiras.id"), nullable=False, index=True)
    barbeiro_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False, index=True)
    chamado_id = Column(Integer, ForeignKey("chamados.id"), nullable=True, index=True)
    tipo = Column(String, nullable=False, index=True)
    descricao = Column(String, nullable=False)
    valor = Column(Float, nullable=False)
    saldo_antes = Column(Float, nullable=False)
    saldo_depois = Column(Float, nullable=False)
    criado_em = Column(DateTime, default=datetime.utcnow, index=True)

    carteira = relationship("CarteiraBarbeiro", back_populates="movimentacoes")
    barbeiro = relationship("Usuario", foreign_keys=[barbeiro_id])
    chamado = relationship("Chamado", foreign_keys=[chamado_id])


class Corte(Base):
    """
    Registro de cada serviço realizado na plataforma.
    
    PROPÓSITO: Tabela central que conecta cliente, barbeiro, barbearia e pagamento.
    Quando um cliente finaliza o pagamento no checkout, cria-se um registro aqui.
    
    SEGURANÇA: Snapshot dos valores no momento do serviço (não mudam se regras mudarem depois)
    """
    __tablename__ = "cortes"
    
    id = Column(Integer, primary_key=True, index=True)
    cliente_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False, index=True)
    freelancer_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False, index=True)
    barbearia_id = Column(Integer, ForeignKey("barbearias.id"), nullable=False, index=True)
    servico_id = Column(Integer, ForeignKey("servicos.id"), nullable=True)
    chamado_id = Column(Integer, ForeignKey("chamados.id"), nullable=True)
    
    # --- VALORES (Snapshot do momento do serviço) ---
    valor_total = Column(Float, nullable=False)  # Valor total cobrado do cliente
    metodo_pagamento = Column(String, nullable=False)  # PIX, CARTAO, DINHEIRO
    status_pagamento = Column(String, default="aprovado")  # aprovado, pendente, falhou
    
    # --- TIMESTAMPS ---
    data_criacao = Column(DateTime, default=datetime.utcnow, index=True)
    data_conclusao = Column(DateTime, nullable=True)
    criado_em = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    cliente = relationship("Usuario", foreign_keys=[cliente_id])
    freelancer = relationship("Usuario", foreign_keys=[freelancer_id])
    barbearia = relationship("Barbearia")
    servico = relationship("Servico")
    chamado = relationship("Chamado")
    transacoes = relationship("TransacaoFinanceira", back_populates="corte")


class TransacaoFinanceira(Base):
    """
    Registro de CADA movimentação de dinheiro no sistema.
    
    PROPÓSITO: Para cada "Corte" realizado, o sistema gera AUTOMATICAMENTE 3 transações:
    - 40% para o freelancer (comissão)
    - 50% para o dono da barbearia
    - 10% para a plataforma BarberMovie
    
    AUDITORIA: Se um barbeiro reclamar que não recebeu, você consegue:
    1. Ver qual foi o valor destinado a ele
    2. Ver o status do repasse (concluído, pendente, falhou)
    3. Rastrear problemas no gateway de pagamento
    """
    __tablename__ = "transacoes_financeiras"
    
    id = Column(Integer, primary_key=True, index=True)
    corte_id = Column(Integer, ForeignKey("cortes.id"), nullable=True, index=True)
    
    # --- DESTINATÁRIO ---
    recebedor_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False, index=True)  # Quem recebe o dinheiro
    tipo = Column(String, nullable=False, index=True)  # comissao_freelancer, comissao_barbearia, taxa_plataforma, etc
    
    # --- VALORES ---
    valor = Column(Float, nullable=False)  # Valor da transação
    percentual = Column(Float, nullable=False)  # Percentual aplicado (70%, 20%, 10%, etc)
    
    # --- STATUS DO REPASSE ---
    status_repasse = Column(String, default="concluido", index=True)  # concluido, pendente, falhou, revertido
    data_repasse = Column(DateTime, nullable=True)  # Quando foi repassado efetivamente
    motivo_falha = Column(String, nullable=True)  # Descrição se falhou
    
    # --- TIMESTAMPS ---
    data_transacao = Column(DateTime, default=datetime.utcnow, index=True)
    criado_em = Column(DateTime, default=datetime.utcnow)
    atualizado_em = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    corte = relationship("Corte", back_populates="transacoes")
    recebedor = relationship("Usuario", foreign_keys=[recebedor_id])


class ContaPagamentoUsuario(Base):
    """Conta de recebimento usada no repasse por usuario."""
    __tablename__ = "contas_pagamento_usuarios"

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False, unique=True, index=True)
    chave_pix = Column(String, nullable=True)
    banco = Column(String, nullable=True)
    agencia = Column(String, nullable=True)
    conta = Column(String, nullable=True)
    tipo_conta = Column(String, default="corrente")
    titular_nome = Column(String, nullable=True)
    titular_documento = Column(String, nullable=True)
    ativo = Column(Boolean, default=True)
    criado_em = Column(DateTime, default=datetime.utcnow)
    atualizado_em = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    usuario = relationship("Usuario", foreign_keys=[usuario_id])


class ConfiguracaoRepasseUsuario(Base):
    """Preferencia de periodicidade de repasse para cada usuario."""
    __tablename__ = "configuracoes_repasse_usuarios"

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False, unique=True, index=True)
    frequencia_repasse = Column(String, default="semanal")  # diario | semanal | mensal
    dia_semana_repasse = Column(Integer, default=1)  # 0=segunda ... 6=domingo
    dia_mes_repasse = Column(Integer, default=5)  # 1..28
    ativo = Column(Boolean, default=True)
    criado_em = Column(DateTime, default=datetime.utcnow)
    atualizado_em = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    usuario = relationship("Usuario", foreign_keys=[usuario_id])


class ConfiguracaoSplitPagamento(Base):
    """Configuracao de percentuais e conta de deposito da plataforma."""
    __tablename__ = "configuracoes_split_pagamento"

    id = Column(Integer, primary_key=True, index=True)
    percentual_barbeiro = Column(Float, default=40.0)
    percentual_barbearia = Column(Float, default=50.0)
    percentual_barbermove = Column(Float, default=10.0)

    recebedor_plataforma_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True, index=True)
    deposito_nome = Column(String, nullable=True)
    deposito_chave_pix = Column(String, nullable=True)
    deposito_banco = Column(String, nullable=True)
    deposito_agencia = Column(String, nullable=True)
    deposito_conta = Column(String, nullable=True)

    atualizado_por_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    criado_em = Column(DateTime, default=datetime.utcnow)
    atualizado_em = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    atualizado_por = relationship("Usuario", foreign_keys=[atualizado_por_id])
    recebedor_plataforma = relationship("Usuario", foreign_keys=[recebedor_plataforma_id])


class AssinaturaBarbearia(Base):
    """
    Registro mensal da assinatura da barbearia com cálculo progressivo por cadeira.
    
    PROPÓSITO: Armazenar o número de cadeiras ativas (1-20).
    Todo mês, o sistema:
    1. Lê o número de cadeiras
    2. Calcula quanto custa cada cadeira (com desconto progressivo)
    3. Gera a cobrança mensal
    
    TABELA DE PREÇOS (Fixed):
    - 1ª cadeira: R$ 47,90
    - 2ª cadeira: R$ 37,90
    - 3ª cadeira: R$ 27,90
    - 4ª cadeira: R$ 20,90
    - 5ª cadeira: R$ 17,90
    - 6ª em diante: R$ 17,90 (piso mínimo)
    
    Exemplos:
    - 1 cadeira: R$ 47,90/mês
    - 2 cadeiras: R$ 85,80/mês
    - 3 cadeiras: R$ 113,70/mês
    - 5 cadeiras: R$ 152,50/mês
    - 10 cadeiras: R$ 242,00/mês
    """
    __tablename__ = "assinaturas_barbearia"
    
    id = Column(Integer, primary_key=True, index=True)
    barbearia_id = Column(Integer, ForeignKey("barbearias.id"), unique=True, nullable=False, index=True)
    
    # --- CADEIRAS (Número ativo) ---
    quantidade_cadeiras = Column(Integer, default=1, nullable=False)  # 1-20
    
    # --- VALORES (Calculado mediante tabela progressiva) ---
    valor_mensalidade = Column(Float, nullable=False)  # Valor total mensal (soma de todas as cadeiras)
    valor_por_cadeira = Column(String, nullable=True)  # JSON com breakdown: [47.90, 37.90, 27.90, ...]
    economia_mensal = Column(Float, default=0.0)  # Quanto economiza vs 1ª cadeira (incentivo)
    
    # --- VENCIMENTO ---
    dia_vencimento = Column(Integer, default=10, nullable=False)  # Dia do mês para cobrar
    proximo_vencimento = Column(DateTime, nullable=False)  # Data exata do próximo vencimento
    
    # --- STATUS ---
    status = Column(String, default="ativa", index=True)  # ativa, inadimplente, cancelada, suspensa
    motivo_suspensao = Column(String, nullable=True)  # Motivo se suspenso
    metodo_pagamento_preferido = Column(String, nullable=True)  # pix, cartao, cartao_credito, cartao_debito, boleto, dinheiro
    
    # --- TIMESTAMPS ---
    ultima_atualizacao = Column(DateTime, default=datetime.utcnow)  # Quando quantidade_cadeiras foi alterado
    criado_em = Column(DateTime, default=datetime.utcnow)
    cancelado_em = Column(DateTime, nullable=True)  # Quando foi cancelado (se foi)
    
    # Relationships
    barbearia = relationship("Barbearia")
    faturas = relationship("FaturaAssinatura", back_populates="assinatura")


class FaturaAssinatura(Base):
    """
    Registro de cada fatura mensal gerada para a barbearia.
    
    PROPÓSITO: Histórico de cobranças.
    Todo mês, o sistema gera uma fatura baseado na AssinaturaBarbearia.
    Registra se foi pago, quando vence, se está vencida, etc.
    """
    __tablename__ = "faturas_assinatura"
    
    id = Column(Integer, primary_key=True, index=True)
    assinatura_id = Column(Integer, ForeignKey("assinaturas_barbearia.id"), nullable=False, index=True)
    
    # --- PERÍODO DA FATURA ---
    mes_referencia = Column(String, nullable=False)  # YYYY-MM (ex: 2026-03)
    data_inicio_periodo = Column(DateTime, nullable=False)
    data_fim_periodo = Column(DateTime, nullable=False)
    
    # --- VALORES ---
    valor_fatura = Column(Float, nullable=False)  # Valor cobrado
    quantidade_cadeiras = Column(Integer, nullable=False)  # Snapshot de cadeiras no mês
    descricao_cobrada = Column(String, nullable=True)  # Descrição do que foi cobrado
    
    # --- PAGAMENTO ---
    data_vencimento = Column(DateTime, nullable=False)  # Quando vence a fatura
    data_pagamento = Column(DateTime, nullable=True)  # Quando foi pago
    status = Column(String, default="pendente", index=True)  # pendente, pago, vencido, cancelado
    metodo_pagamento = Column(String, nullable=True)  # Como foi pago (se já foi)
    
    # --- TIMESTAMPS ---
    criada_em = Column(DateTime, default=datetime.utcnow)
    atualizada_em = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    assinatura = relationship("AssinaturaBarbearia", back_populates="faturas")


# ============================================================================
# 📍 MODELO ON-DEMAND: RADAR EM TEMPO REAL PARA BARBEIROS (ESTILO UBER)
# ============================================================================

class RadarFreelancer(Base):
    """
    Rastreamento em tempo real da localização e disponibilidade de barbeiros.
    
    Funciona como um "radar" - o barbeiro abre o app, clica "Ficar Online"
    e a localização dele é constantemente atualizada via GPS.
    
    O sistema usa isso para fazer matches instantâneos com clientes próximos.
    
    Arquitetura: On-Demand (sob demanda), exatamente como Uber.
    """
    __tablename__ = "radar_freelancer"
    
    id = Column(Integer, primary_key=True, index=True)
    freelancer_id = Column(Integer, ForeignKey("usuarios.id"), unique=True, nullable=False, index=True)
    
    # Status: Barbeiro clicou o botão "Ficar Online"?
    is_online = Column(Boolean, default=False, index=True)
    
    # Status: Barbeiro está em atendimento neste momento?
    em_atendimento = Column(Boolean, default=False, index=True)
    
    # ✅ NOVO: Timestamp de quando o barbeiro estará livre (liberação automática)
    ocupado_ate = Column(DateTime, nullable=True, index=True)
    
    # Localização atual (GPS do celular)
    latitude = Column(Float, nullable=True)  # Precisão: até 8 casas decimais
    longitude = Column(Float, nullable=True)  # Precisão: até 8 casas decimais
    
    # Quando a localização foi atualizada pela última vez
    localizacao_atualizada_em = Column(DateTime, nullable=True)
    
    # Qual barbearia ele está atendendo no momento (se em_atendimento = True)
    barbearia_atendimento_id = Column(Integer, ForeignKey("barbearias.id"), nullable=True)
    
    # Cliente que está sendo atendido
    cliente_atendimento_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    
    # Timestamps de controle
    criado_em = Column(DateTime, default=datetime.utcnow)
    atualizado_em = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relacionamentos
    freelancer = relationship("Usuario", foreign_keys=[freelancer_id], backref="radar")


class SolicitacaoBarbeiro(Base):
    """
    Pedido On-Demand de um cliente buscando barbeiro próximo.
    
    Fluxo:
    1. Cliente ou barbearia clica "Solicitar Barbeiro Agora"
    2. Sistema envia notificações para todos os barbeiros próximos
    3. Primeiro a aceitar ganha o serviço
    4. Status muda de 'aguardando_resposta' para 'aceito' ou 'recusado'
    """
    __tablename__ = "solicitacoes_barbeiro"
    
    id = Column(Integer, primary_key=True, index=True)
    cliente_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False, index=True)
    barbearia_id = Column(Integer, ForeignKey("barbearias.id"), nullable=True, index=True)
    
    # Localização onde o serviço será realizado
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    endereco = Column(String, nullable=True)  # Descrição do local (ex: "Rua das Flores, 123")
    
    # Raio de busca em km (quanto mais longe, menos urgente)
    raio_km = Column(Float, default=5.0)  # Padrão: 5 km
    
    # Qual barbeiro aceitou (se houver)
    barbeiro_aceito_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True, index=True)
    
    # Status do pedido
    status = Column(String, default="aguardando_resposta", index=True)
    # Valores: aguardando_resposta, aceito, recusado_por_todos, cancelado, concluido
    
    # Valor ofertado/acordado
    valor_oferta = Column(Float, nullable=True)
    
    # Detalhes do serviço
    tipo_servico = Column(String, nullable=True)  # "corte", "barba", "combo", etc
    observacoes = Column(String, nullable=True)  # Notas especiais do cliente
    
    # Timestamps
    criado_em = Column(DateTime, default=datetime.utcnow, index=True)
    aceito_em = Column(DateTime, nullable=True)
    concluido_em = Column(DateTime, nullable=True)
    
    # Relacionamentos
    cliente = relationship("Usuario", foreign_keys=[cliente_id], backref="solicitacoes_como_cliente")
    barbearia = relationship("Barbearia", foreign_keys=[barbearia_id])
    barbeiro_aceito = relationship("Usuario", foreign_keys=[barbeiro_aceito_id], backref="solicitacoes_aceitas")
    visualizacoes = relationship("RequestView", back_populates="solicitacao", cascade="all, delete-orphan")


class CadeiraAcionada(Base):
    """
    Evento de vaga relampago acionada pela barbearia para aceite em tempo real.

    Fluxo principal:
    - status='disponivel': vaga aberta para barbeiros/clientes elegiveis.
    - status='ocupada_por_barbeiro': barbeiro assumiu a cadeira.
    - status='reservada_por_cliente': cliente reservou atendimento imediato.
    - status='expirada': tempo limite encerrado sem aceite valido.
    """

    __tablename__ = "cadeiras_acionadas"

    id = Column(Integer, primary_key=True, index=True)
    barbearia_id = Column(Integer, ForeignKey("barbearias.id"), nullable=False, index=True)
    cadeira_id = Column(Integer, ForeignKey("cadeiras.id"), nullable=True, index=True)

    status = Column(String, default="disponivel", index=True)
    barbeiro_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True, index=True)
    cliente_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True, index=True)

    raio_km = Column(Float, default=5.0)
    tipo_servico = Column(String, nullable=True)
    valor_oferta = Column(Float, nullable=True)
    observacoes = Column(String, nullable=True)

    criado_em = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    atualizado_em = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    limite_chegada = Column(DateTime, nullable=True, index=True)
    expira_em = Column(DateTime, nullable=True, index=True)

    barbearia = relationship("Barbearia", foreign_keys=[barbearia_id])
    cadeira = relationship("Cadeira", foreign_keys=[cadeira_id])
    barbeiro = relationship("Usuario", foreign_keys=[barbeiro_id])
    cliente = relationship("Usuario", foreign_keys=[cliente_id])


class NotificacaoBarbeiro(Base):
    """
    Log de notificações enviadas aos barbeiros.
    
    Cada vez que um cliente solicita um barbeiro próximo, cria registros
    nessa tabela para rastrear quem foi notificado, quem respondeu, etc.
    """
    __tablename__ = "notificacoes_barbeiro"
    
    id = Column(Integer, primary_key=True, index=True)
    barbeiro_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False, index=True)
    solicitacao_id = Column(Integer, ForeignKey("solicitacoes_barbeiro.id"), nullable=False)
    
    # Distância entre barbeiro e cliente (em km)
    distancia_km = Column(Float, nullable=True)
    
    # A notificação foi aceitá ou recusada?
    resposta = Column(String, nullable=True)  # None, "aceito", "recusado"
    
    # Timestamps
    enviada_em = Column(DateTime, default=datetime.utcnow)
    respondida_em = Column(DateTime, nullable=True)
    
    # Relacionamentos
    barbeiro = relationship("Usuario", foreign_keys=[barbeiro_id])
    solicitacao = relationship("SolicitacaoBarbeiro")


class RequestView(Base):
    """Registro de visualização/recebimento de uma solicitação on-demand."""

    __tablename__ = "request_views"
    __table_args__ = (
        UniqueConstraint("request_id", "freelancer_id", name="uq_request_views_request_freelancer"),
    )

    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(Integer, ForeignKey("solicitacoes_barbeiro.id"), nullable=False, index=True)
    freelancer_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False, index=True)
    viewed_at = Column(DateTime, default=datetime.utcnow, index=True)

    solicitacao = relationship("SolicitacaoBarbeiro", back_populates="visualizacoes")
    freelancer = relationship("Usuario", foreign_keys=[freelancer_id])
