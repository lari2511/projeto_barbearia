import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

# Carrega variáveis do .env para garantir uso do DATABASE_URL correto
load_dotenv()

# DATABASE_URL pode ser PostgreSQL ou SQLite; default para SQLite local
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./barbearia.db")

# Se usar SQLite, habilitar check_same_thread
engine_kwargs = {"connect_args": {"check_same_thread": False}} if SQLALCHEMY_DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(SQLALCHEMY_DATABASE_URL, **engine_kwargs)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    """Dependency para obter sessão do banco de dados"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Inicialização do banco de dados
def init_db():
    """Cria as tabelas do banco de dados"""
    # Importa os modelos para registrar as tabelas no metadata
    try:
        from . import models  # noqa: F401
    except Exception:
        pass
    Base.metadata.create_all(bind=engine)

    inspector = inspect(engine)

    # ✅ Verificar e criar coluna email_verificado na tabela usuarios
    if "usuarios" in inspector.get_table_names():
        colunas_existentes = {coluna["name"] for coluna in inspector.get_columns("usuarios")}

        # Adicionar email_verificado se não existir
        if "email_verificado" not in colunas_existentes:
            with engine.begin() as connection:
                connection.execute(text("ALTER TABLE usuarios ADD COLUMN email_verificado BOOLEAN DEFAULT 0"))
                print("✅ Coluna email_verificado criada")

        # Adicionar token_verificacao se não existir
        if "token_verificacao" not in colunas_existentes:
            with engine.begin() as connection:
                connection.execute(text("ALTER TABLE usuarios ADD COLUMN token_verificacao VARCHAR(255)"))
                print("✅ Coluna token_verificacao criada")

    if "chamados" in inspector.get_table_names():
        colunas_existentes = {coluna["name"] for coluna in inspector.get_columns("chamados")}
        colunas_esperadas = {
            "cancelado_em": "DATETIME",
            "tempo_cancelamento_minutos": "INTEGER",
            "valor_taxa_cancelamento": "FLOAT",
            "motivo_cancelamento": "VARCHAR(255)",
            "horario_match": "DATETIME",  # ✅ Novo: timestamp quando freelancer aceita (inicia 5 min)
            "cliente_chegou": "BOOLEAN DEFAULT 0",
            "barbeiro_chegou": "BOOLEAN DEFAULT 0",
        }

        with engine.begin() as connection:
            for nome_coluna, definicao in colunas_esperadas.items():
                if nome_coluna not in colunas_existentes:
                    connection.execute(text(f"ALTER TABLE chamados ADD COLUMN {nome_coluna} {definicao}"))

    if "radar_freelancer" in inspector.get_table_names():
        colunas_existentes = {coluna["name"] for coluna in inspector.get_columns("radar_freelancer")}
        colunas_esperadas = {
            "ocupado_ate": "DATETIME",
            "localizacao_atualizada_em": "DATETIME",
            "barbearia_atendimento_id": "INTEGER",
            "cliente_atendimento_id": "INTEGER",
        }

        with engine.begin() as connection:
            for nome_coluna, definicao in colunas_esperadas.items():
                if nome_coluna not in colunas_existentes:
                    connection.execute(text(f"ALTER TABLE radar_freelancer ADD COLUMN {nome_coluna} {definicao}"))

    print("--- Banco de dados inicializado com sucesso ---")