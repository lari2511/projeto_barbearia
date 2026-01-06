#!/usr/bin/env python3
"""
Script para criar as tabelas do banco de dados
"""

from app.database import engine, Base
from app import models

# Criar todas as tabelas
Base.metadata.create_all(bind=engine)
print("✅ Tabelas criadas com sucesso!")
