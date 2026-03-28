import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
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
    print("--- Banco de dados inicializado com sucesso ---")