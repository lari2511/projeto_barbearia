#!/usr/bin/env python3
"""
Script para configurar o modelo de cobrança do BarberMove

Configurações:
- Taxa de 10% para barbeiros (freelancers)
- Assinatura PROGRESSIVA para barbearias:
  • 1ª cadeira: R$ 47,90
    • 2ª cadeira: R$ 37,90
    • 3ª cadeira: R$ 27,90
    • 4ª cadeira: R$ 20,90
    • 5ª cadeira: R$ 17,90
  • 6ª+ cadeiras: R$ 17,90 cada
"""

from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import sys
import os

# Importar modelos corretamente
from app.models import Base, Assinatura, Usuario
from app.database import SQLALCHEMY_DATABASE_URL

# Configurações
TAXA_BARBEIRO = 0.10  # 10%
VALOR_BASE_PRIMEIRA_CADEIRA = 47.90  # R$ 47,90 (1ª cadeira)
DIAS_RETENCAO = 7
SAQUE_MINIMO = 50.00

def configurar_modelo_cobranca():
    """Configura o modelo de cobrança no banco de dados"""
    
    # Conectar ao banco
    engine = create_engine('sqlite:///./barbearia.db')
    Session = sessionmaker(bind=engine)
    session = Session()
    
    print("=" * 60)
    print("CONFIGURAÇÃO DO MODELO DE COBRANÇA BARBERMOVE")
    print("=" * 60)
    print()
    
    print(f"📊 Configurações:")
    print(f"   • Taxa para barbeiros: {TAXA_BARBEIRO * 100}%")
    print(f"   • Mensalidade base (1ª cadeira): R$ {VALOR_BASE_PRIMEIRA_CADEIRA:.2f}")
    print(f"   • Dias de retenção: {DIAS_RETENCAO} dias")
    print(f"   • Saque mínimo: R$ {SAQUE_MINIMO:.2f}")
    print()
    
    # Buscar todas as barbearias
    barbearias = session.query(Usuario).filter(Usuario.tipo == 'barbearia').all()
    print(f"🏪 Barbearias encontradas: {len(barbearias)}")
    print()
    
    # Atualizar ou criar assinaturas para barbearias
    assinaturas_criadas = 0
    assinaturas_atualizadas = 0
    
    for barbearia in barbearias:
        # Verificar se já tem assinatura
        assinatura = session.query(Assinatura).filter(
            Assinatura.barbearia_id == barbearia.id
        ).first()
        
        if assinatura:
            # Atualizar assinatura existente (valor base para 1 cadeira)
            assinatura.valor_mensal = VALOR_BASE_PRIMEIRA_CADEIRA
            assinatura.status = 'ativa'
            if assinatura.proximo_vencimento < datetime.now():
                assinatura.proximo_vencimento = datetime.now() + timedelta(days=30)
            assinaturas_atualizadas += 1
            print(f"   ✓ Atualizada assinatura da barbearia: {barbearia.nome}")
        else:
            # Criar nova assinatura (valor base para 1 cadeira)
            nova_assinatura = Assinatura(
                barbearia_id=barbearia.id,
                status='ativa',
                proximo_vencimento=datetime.now() + timedelta(days=30),
                valor_mensal=VALOR_BASE_PRIMEIRA_CADEIRA
            )
            session.add(nova_assinatura)
            assinaturas_criadas += 1
            print(f"   + Criada assinatura para barbearia: {barbearia.nome}")
    
    # Salvar alterações
    try:
        session.commit()
        print()
        print("=" * 60)
        print("✅ CONFIGURAÇÃO CONCLUÍDA COM SUCESSO!")
        print("=" * 60)
        print()
        print(f"📈 Resumo:")
        print(f"   • Assinaturas criadas: {assinaturas_criadas}")
        print(f"   • Assinaturas atualizadas: {assinaturas_atualizadas}")
        print(f"   • Total de barbearias ativas: {len(barbearias)}")
        print()
        print("💡 Próximos passos:")
        print("   1. Verificar dashboard de pagamentos")
        print("   2. Testar fluxo de cobrança")
        print("   3. Validar cálculo de comissões")
        print()
        
    except Exception as e:
        session.rollback()
        print()
        print("❌ ERRO ao salvar configurações:")
        print(f"   {str(e)}")
        print()
        return False
    
    finally:
        session.close()
    
    # Exibir informações sobre barbeiros
    barbeiros = session.query(Usuario).filter(Usuario.tipo == 'barbeiro').all()
    print(f"💈 Barbeiros cadastrados: {len(barbeiros)}")
    print(f"   Taxa aplicada automaticamente: {TAXA_BARBEIRO * 100}%")
    print()
    
    return True


def exibir_exemplo_calculo():
    """Exibe exemplos de cálculo de comissão"""
    print("=" * 60)
    print("EXEMPLOS DE CÁLCULO DE COMISSÃO")
    print("=" * 60)
    print()
    
    valores_servico = [50.00, 80.00, 100.00, 150.00, 200.00]
    
    print(f"{'Serviço':<15} {'Comissão 10%':<15} {'Barbeiro Recebe':<20}")
    print("-" * 60)
    
    for valor in valores_servico:
        comissao = valor * TAXA_BARBEIRO
        valor_barbeiro = valor - comissao
        print(f"R$ {valor:>7.2f}      R$ {comissao:>7.2f}       R$ {valor_barbeiro:>7.2f}")
    
    print()
    print("💰 Exemplo mensal (20 serviços de R$ 100,00):")
    print(f"   Total bruto: R$ {20 * 100:.2f}")
    print(f"   Comissão BarberMove: R$ {20 * 100 * TAXA_BARBEIRO:.2f}")
    print(f"   Barbeiro recebe: R$ {20 * 100 * (1 - TAXA_BARBEIRO):.2f}")
    print()


if __name__ == "__main__":
    print()
    configurar_modelo_cobranca()
    print()
    exibir_exemplo_calculo()
    print()
    print("=" * 60)
    print("Script finalizado!")
    print("=" * 60)
    print()
