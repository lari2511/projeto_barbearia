#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script simplificado para criar banco SQLite sem travar
"""
import sqlite3
import os

print("=" * 60)
print("🏗️ CRIANDO BANCO SQLite MANUALMENTE")
print("=" * 60)

# Nome do banco
banco = "barbearia.db"

# Conectar (cria o arquivo se não existir)
print(f"\n📝 Criando arquivo {banco}...")
conn = sqlite3.connect(banco)
cursor = conn.cursor()

# SQL para criar tabelas (baseado nos models)
print("\n📊 Criando tabelas...")

# Tabela usuarios
cursor.execute("""
CREATE TABLE IF NOT EXISTS usuarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    senha_hash TEXT NOT NULL,
    tipo TEXT NOT NULL,
    telefone TEXT,
    cpf TEXT,
    data_nascimento TEXT,
    barbearia_id INTEGER,
    aprovado BOOLEAN DEFAULT 0,
    perfil_aprovado BOOLEAN DEFAULT 0,
    email_verificado BOOLEAN DEFAULT 0,
    foto_perfil TEXT,
    rua TEXT,
    numero TEXT,
    bairro TEXT,
    cidade TEXT,
    estado TEXT,
    cep TEXT,
    latitude REAL,
    longitude REAL,
    disponivel BOOLEAN DEFAULT 1,
    online_regiao BOOLEAN DEFAULT 0,
    presente_em_local BOOLEAN DEFAULT 0,
    barbearia_atual_id INTEGER,
    cadeira_numero INTEGER,
    acionada_em TEXT,
    avaliacao REAL DEFAULT 5.0,
    total_avaliacoes INTEGER DEFAULT 0,
    criado_em TEXT DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (barbearia_id) REFERENCES usuarios(id),
    FOREIGN KEY (barbearia_atual_id) REFERENCES usuarios(id)
)
""")
print("   ✅ Tabela 'usuarios' criada")

# Tabela servicos
cursor.execute("""
CREATE TABLE IF NOT EXISTS servicos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    barbearia_id INTEGER NOT NULL,
    nome TEXT NOT NULL,
    descricao TEXT,
    preco REAL NOT NULL,
    duracao INTEGER NOT NULL,
    ativo BOOLEAN DEFAULT 1,
    criado_em TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (barbearia_id) REFERENCES usuarios(id)
)
""")
print("   ✅ Tabela 'servicos' criada")

# Tabela agendamentos
cursor.execute("""
CREATE TABLE IF NOT EXISTS agendamentos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cliente_id INTEGER NOT NULL,
    barbeiro_id INTEGER NOT NULL,
    servico_id INTEGER NOT NULL,
    barbearia_id INTEGER NOT NULL,
    data_hora_inicio TEXT NOT NULL,
    data_hora_fim TEXT,
    status TEXT DEFAULT 'pendente',
    observacoes TEXT,
    avaliacao INTEGER,
    comentario TEXT,
    imediato BOOLEAN DEFAULT 0,
    criado_em TEXT DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (cliente_id) REFERENCES usuarios(id),
    FOREIGN KEY (barbeiro_id) REFERENCES usuarios(id),
    FOREIGN KEY (servico_id) REFERENCES servicos(id),
    FOREIGN KEY (barbearia_id) REFERENCES usuarios(id)
)
""")
print("   ✅ Tabela 'agendamentos' criada")

# Tabela tokens_verificacao
cursor.execute("""
CREATE TABLE IF NOT EXISTS tokens_verificacao (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id INTEGER NOT NULL,
    token TEXT UNIQUE NOT NULL,
    tipo TEXT NOT NULL,
    usado BOOLEAN DEFAULT 0,
    expira_em TEXT NOT NULL,
    criado_em TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
)
""")
print("   ✅ Tabela 'tokens_verificacao' criada")

# Commit
conn.commit()
conn.close()

# Verificar
if os.path.exists(banco):
    tamanho = os.path.getsize(banco) / 1024
    print(f"\n✅ BANCO CRIADO COM SUCESSO!")
    print(f"📦 Arquivo: {banco} ({tamanho:.2f} KB)")
else:
    print(f"\n❌ ERRO: Banco não foi criado!")

print("\n🚀 Próximos passos:")
print("   python criar_contas_teste.py")
print("   python criar_servicos_teste.py")
print()
