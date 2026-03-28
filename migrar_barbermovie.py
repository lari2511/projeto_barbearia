#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script de migração para adicionar novos modelos do BarberMovie
Executa as alterações no banco de dados existente
"""

from app.database import SessionLocal, engine
from app.models import Base
import sys

def migrar_banco():
    """Cria as novas tabelas do BarberMovie"""
    try:
        print("🔧 Iniciando migração do banco de dados...")
        
        # Criar todas as tabelas (as que já existem serão ignoradas)
        Base.metadata.create_all(bind=engine)
        
        print("✅ Migração concluída com sucesso!")
        print("\nNovas tabelas criadas:")
        print("  - freelancers")
        print("  - especialidades_freelancer")
        print("  - portfolio_freelancer")
        print("  - cadeiras")
        print("  - assinaturas")
        print("  - comissoes")
        print("  - avaliacoes_freelancer")
        print("  - avaliacoes_barbearia")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro durante a migração: {str(e)}")
        return False


def verificar_migracao():
    """Verifica se as novas tabelas foram criadas"""
    from sqlalchemy import inspect
    
    try:
        inspector = inspect(engine)
        tabelas_esperadas = [
            'freelancers',
            'especialidades_freelancer',
            'portfolio_freelancer',
            'cadeiras',
            'assinaturas',
            'comissoes',
            'avaliacoes_freelancer',
            'avaliacoes_barbearia'
        ]
        
        tabelas_existentes = inspector.get_table_names()
        
        print("\n🔍 Verificando tabelas criadas:")
        for tabela in tabelas_esperadas:
            if tabela in tabelas_existentes:
                print(f"  ✅ {tabela}")
            else:
                print(f"  ❌ {tabela} - NÃO ENCONTRADA")
        
        # Verificar coluna origem_cliente na tabela chamados
        print("\n🔍 Verificando colunas adicionadas:")
        colunas_chamados = [col['name'] for col in inspector.get_columns('chamados')]
        if 'origem_cliente' in colunas_chamados:
            print("  ✅ chamados.origem_cliente")
        else:
            print("  ⚠️  chamados.origem_cliente - NÃO ENCONTRADA (pode precisar adicionar manualmente)")
        
        colunas_barbearias = [col['name'] for col in inspector.get_columns('barbearias')]
        if 'status_online' in colunas_barbearias:
            print("  ✅ barbearias.status_online")
        else:
            print("  ⚠️  barbearias.status_online - NÃO ENCONTRADA (pode precisar adicionar manualmente)")
            
    except Exception as e:
        print(f"❌ Erro ao verificar migração: {str(e)}")


if __name__ == "__main__":
    print("=" * 60)
    print("MIGRAÇÃO BARBERMOVIE")
    print("=" * 60)
    print()
    
    resposta = input("Deseja continuar com a migração? (s/n): ")
    if resposta.lower() != 's':
        print("Migração cancelada.")
        sys.exit(0)
    
    if migrar_banco():
        verificar_migracao()
        print("\n✨ Processo finalizado!")
    else:
        print("\n❌ Migração falhou!")
        sys.exit(1)
