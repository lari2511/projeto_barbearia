# --- ARQUIVO: app/models.py ---
# Modelos SQLAlchemy para o banco de dados

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base
import enum

# --- ENUMS (Estados) ---
class StatusAgendamento(str, enum.Enum):
    """Status possíveis de um agendamento"""
    PENDENTE = "pendente"      # Cliente pediu, aguardando aceite do barbeiro/dono
    CONFIRMADO = "confirmado"  # Barbeiro/Dono aceitou
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
    OUTROS = "outros"                  # Outros serviços

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
    criado_em = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    chamados_cliente = relationship("Chamado", foreign_keys="Chamado.cliente_id", back_populates="cliente")
    chamados_barbeiro = relationship("Chamado", foreign_keys="Chamado.barbeiro_id", back_populates="barbeiro")
    barbearias = relationship("Barbearia", back_populates="usuario")

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
    cadeira_livre = Column(Boolean, default=True)
    criado_em = Column(DateTime, default=datetime.utcnow)
    
    usuario = relationship("Usuario", back_populates="barbearias")
    servicos = relationship("Servico", back_populates="barbearia")
    chamados = relationship("Chamado", back_populates="barbearia")

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
    
    # --- TEMPO (Quando vai ser) ---
    data_hora_inicio = Column(DateTime, nullable=True, index=True)  # Quando começa o serviço
    data_hora_fim = Column(DateTime, nullable=True)  # Quando termina (importante para liberar cadeira)
    data_agendamento = Column(DateTime, default=datetime.utcnow)  # Quando foi agendado
    
    # --- STATUS (Máquina de estados) ---
    status = Column(String, default=StatusAgendamento.PENDENTE)  # pendente, confirmado, concluído, cancelado
    
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
    
    cliente = relationship("Usuario", foreign_keys=[cliente_id], back_populates="chamados_cliente")
    barbeiro = relationship("Usuario", foreign_keys=[barbeiro_id], back_populates="chamados_barbeiro")
    servico = relationship("Servico", back_populates="chamados")
    barbearia = relationship("Barbearia", back_populates="chamados")
    avaliacoes = relationship("Avaliacao", back_populates="chamado")
    historico = relationship("ChamadoHistorico", back_populates="chamado", order_by="ChamadoHistorico.criado_em")
    pagamento = relationship("Pagamento", back_populates="chamado", uselist=False)

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

class Notificacao(Base):
    __tablename__ = "notificacoes"
    
    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"))
    titulo = Column(String)
    mensagem = Column(String)
    lida = Column(Boolean, default=False)
    tipo = Column(String)  # 'chamado', 'avaliacao', 'cupom', etc
    criado_em = Column(DateTime, default=datetime.utcnow)
    
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
