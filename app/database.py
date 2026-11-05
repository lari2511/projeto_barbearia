import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

# Carrega variáveis do .env para garantir uso do DATABASE_URL correto
load_dotenv()

# DATABASE_URL pode ser PostgreSQL ou SQLite; default para SQLite local
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./barbearia.db")

# Sem driver explícito, versões recentes do SQLAlchemy tentam importar o
# psycopg (v3) para "postgresql://", que não está instalado (só temos
# psycopg2-binary no requirements.txt) e derruba o app no boot. Fixa o
# driver pra não depender da resolução automática do SQLAlchemy.
if SQLALCHEMY_DATABASE_URL.startswith("postgresql://"):
    SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace(
        "postgresql://", "postgresql+psycopg2://", 1
    )

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

        # Etapa 7: saída pendente do freelancer presente (aguardando concluir atendimentos)
        if "saida_pendente" not in colunas_existentes:
            with engine.begin() as connection:
                connection.execute(text("ALTER TABLE usuarios ADD COLUMN saida_pendente VARCHAR(20)"))
                print("[migracao] Coluna saida_pendente criada")

        # Cadeado do proprietário: libera freelancer PRESENTE para clientes do app
        if "clientes_app_liberado_barbearia_id" not in colunas_existentes:
            with engine.begin() as connection:
                connection.execute(text("ALTER TABLE usuarios ADD COLUMN clientes_app_liberado_barbearia_id INTEGER"))
                print("[migracao] Coluna clientes_app_liberado_barbearia_id criada")

        # Tempo de experiência do freelancer, informado no cadastro
        if "tempo_experiencia" not in colunas_existentes:
            with engine.begin() as connection:
                connection.execute(text("ALTER TABLE usuarios ADD COLUMN tempo_experiencia VARCHAR(30)"))
                print("[migracao] Coluna tempo_experiencia criada")

        # Cadastro rápido (só e-mail + senha): dados do perfil completados depois, dentro do app
        if "cadastro_pendente" not in colunas_existentes:
            with engine.begin() as connection:
                connection.execute(text("ALTER TABLE usuarios ADD COLUMN cadastro_pendente BOOLEAN DEFAULT FALSE"))
                print("[migracao] Coluna cadastro_pendente criada")

        # Freelancer: data de nascimento declarada (18 anos completos)
        if "data_nascimento" not in colunas_existentes:
            with engine.begin() as connection:
                connection.execute(text("ALTER TABLE usuarios ADD COLUMN data_nascimento DATE"))
                print("[migracao] Coluna data_nascimento criada")

        # Atendimento a domicílio: opt-in do freelancer (nasce desligado)
        if "atende_domicilio" not in colunas_existentes:
            with engine.begin() as connection:
                connection.execute(text("ALTER TABLE usuarios ADD COLUMN atende_domicilio BOOLEAN DEFAULT FALSE"))
                print("[migracao] Coluna atende_domicilio criada")

    postgres = engine.dialect.name == "postgresql"

    # Atendimento a domicílio: serviço do freelancer (sem barbearia).
    # SQLite não suporta DROP NOT NULL; o banco de teste nasce do models (já nullable).
    if "servicos" in inspector.get_table_names():
        colunas_servicos = {coluna["name"]: coluna for coluna in inspector.get_columns("servicos")}
        if "freelancer_id" not in colunas_servicos:
            with engine.begin() as connection:
                connection.execute(text("ALTER TABLE servicos ADD COLUMN freelancer_id INTEGER"))
                print("[migracao] Coluna servicos.freelancer_id criada")
        if postgres and not colunas_servicos.get("barbearia_id", {}).get("nullable", True):
            with engine.begin() as connection:
                connection.execute(text("ALTER TABLE servicos ALTER COLUMN barbearia_id DROP NOT NULL"))
                print("[migracao] servicos.barbearia_id agora aceita NULL")

    if postgres and "agendamentos_ativos" in inspector.get_table_names():
        colunas_ativos = {coluna["name"]: coluna for coluna in inspector.get_columns("agendamentos_ativos")}
        if not colunas_ativos.get("barbearia_id", {}).get("nullable", True):
            with engine.begin() as connection:
                connection.execute(text("ALTER TABLE agendamentos_ativos ALTER COLUMN barbearia_id DROP NOT NULL"))
                print("[migracao] agendamentos_ativos.barbearia_id agora aceita NULL")

    if "condicoes_estrutura_barbearia" in inspector.get_table_names():
        colunas_existentes = {coluna["name"] for coluna in inspector.get_columns("condicoes_estrutura_barbearia")}
        # Estrutura oferecida ao freelancer: equipamentos e textos livres do dono
        colunas_esperadas = {
            "secador_disponivel": "BOOLEAN",
            "cadeira_disponivel": "BOOLEAN",
            "bancada_disponivel": "BOOLEAN",
            "espelho_disponivel": "BOOLEAN",
            "outros_recursos": "VARCHAR(500)",
            "observacoes": "VARCHAR(1000)",
        }

        with engine.begin() as connection:
            for nome_coluna, definicao in colunas_esperadas.items():
                if nome_coluna not in colunas_existentes:
                    connection.execute(text(f"ALTER TABLE condicoes_estrutura_barbearia ADD COLUMN {nome_coluna} {definicao}"))

    if "chamados" in inspector.get_table_names():
        colunas_existentes = {coluna["name"] for coluna in inspector.get_columns("chamados")}
        colunas_esperadas = {
            "cancelado_em": "TIMESTAMP",
            "tempo_cancelamento_minutos": "INTEGER",
            "valor_taxa_cancelamento": "FLOAT",
            "motivo_cancelamento": "VARCHAR(255)",
            "horario_match": "TIMESTAMP",  # ✅ Novo: timestamp quando freelancer aceita (inicia 5 min)
            "cliente_chegou": "BOOLEAN DEFAULT 0",
            "barbeiro_chegou": "BOOLEAN DEFAULT 0",
            "pausado_em": "TIMESTAMP",  # ✅ Novo: timestamp de quando o atendimento foi pausado
            "pausa_acumulada_segundos": "INTEGER DEFAULT 0",  # ✅ Novo: soma das pausas deste atendimento
            "grupo_id": "INTEGER",  # ✅ Novo: liga chamados de uma mesma selecao de multiplos servicos
            # Modalidade: chamados existentes ficam como atendimento na barbearia
            "modalidade": "VARCHAR(30) DEFAULT 'ATENDIMENTO_BARBEARIA'",
            "endereco_atendimento": "VARCHAR(255)",
            "latitude_atendimento": "FLOAT",
            "longitude_atendimento": "FLOAT",
        }

        with engine.begin() as connection:
            for nome_coluna, definicao in colunas_esperadas.items():
                if nome_coluna not in colunas_existentes:
                    connection.execute(text(f"ALTER TABLE chamados ADD COLUMN {nome_coluna} {definicao}"))

    if "barbearias" in inspector.get_table_names():
        colunas_existentes = {coluna["name"] for coluna in inspector.get_columns("barbearias")}
        # Horário de funcionamento (texto livre, só exibição no perfil)
        if "horario_funcionamento" not in colunas_existentes:
            with engine.begin() as connection:
                connection.execute(text("ALTER TABLE barbearias ADD COLUMN horario_funcionamento VARCHAR(200)"))
                print("[migracao] Coluna horario_funcionamento criada")

    if "historico_movimentacoes" in inspector.get_table_names():
        colunas_existentes = {coluna["name"] for coluna in inspector.get_columns("historico_movimentacoes")}
        # Fechamento diário (21:00) que considerou a movimentação
        if "fechamento_id" not in colunas_existentes:
            with engine.begin() as connection:
                connection.execute(text("ALTER TABLE historico_movimentacoes ADD COLUMN fechamento_id INTEGER"))
                print("[migracao] Coluna historico_movimentacoes.fechamento_id criada")

    if "radar_freelancer" in inspector.get_table_names():
        colunas_existentes = {coluna["name"] for coluna in inspector.get_columns("radar_freelancer")}
        colunas_esperadas = {
            "ocupado_ate": "TIMESTAMP",
            "localizacao_atualizada_em": "TIMESTAMP",
            "barbearia_atendimento_id": "INTEGER",
            "cliente_atendimento_id": "INTEGER",
        }

        with engine.begin() as connection:
            for nome_coluna, definicao in colunas_esperadas.items():
                if nome_coluna not in colunas_existentes:
                    connection.execute(text(f"ALTER TABLE radar_freelancer ADD COLUMN {nome_coluna} {definicao}"))

    print("--- Banco de dados inicializado com sucesso ---")