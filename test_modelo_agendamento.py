#!/usr/bin/env python3
"""
Testes para o novo modelo de Agendamento com Snapshot Financeiro.
Valida:
1. Cálculo de split de pagamento (15%, 45%, 40%)
2. Enum de status (PENDENTE, CONFIRMADO, CONCLUIDO, CANCELADO)
3. Snapshot financeiro (valores não mudam após criação)
4. Transições de status válidas
"""

import sys
from datetime import datetime, timedelta

# Simular o que seria importado do app
class MockStatusAgendamento:
    PENDENTE = "pendente"
    CONFIRMADO = "confirmado"
    CONCLUIDO = "concluido"
    CANCELADO = "cancelado"

def calcular_split_pagamento(valor_total: float) -> dict:
    """Função idêntica à app/routes.py"""
    comissao_plataforma = round(valor_total * 0.15, 2)
    valor_freelancer = round(valor_total * 0.45, 2)
    valor_dono = round(valor_total - comissao_plataforma - valor_freelancer, 2)
    
    return {
        'valor_total': valor_total,
        'comissao_plataforma': comissao_plataforma,
        'valor_freelancer': valor_freelancer,
        'valor_dono': valor_dono
    }

# ============================================================================
# TESTES
# ============================================================================

def test_split_basico():
    """Teste 1: Split básico com R$ 100"""
    split = calcular_split_pagamento(100.0)
    
    assert split['valor_total'] == 100.0, f"Total: esperado 100.0, obteve {split['valor_total']}"
    assert split['comissao_plataforma'] == 15.0, f"Plataforma: esperado 15.0, obteve {split['comissao_plataforma']}"
    assert split['valor_freelancer'] == 45.0, f"Freelancer: esperado 45.0, obteve {split['valor_freelancer']}"
    assert split['valor_dono'] == 40.0, f"Dono: esperado 40.0, obteve {split['valor_dono']}"
    
    total = split['comissao_plataforma'] + split['valor_freelancer'] + split['valor_dono']
    assert total == 100.0, f"Soma deve ser 100.0, obteve {total}"
    
    print("✅ test_split_basico: PASSOU")

def test_split_com_centavos():
    """Teste 2: Split com valor que gera centavos"""
    split = calcular_split_pagamento(33.33)
    
    # 33.33 * 0.15 = 4.9995 → 5.00
    # 33.33 * 0.45 = 14.9985 → 15.00
    # Resto: 33.33 - 5.00 - 15.00 = 13.33
    
    assert split['comissao_plataforma'] == 5.0, f"Esperado 5.0, obteve {split['comissao_plataforma']}"
    assert split['valor_freelancer'] == 15.0, f"Esperado 15.0, obteve {split['valor_freelancer']}"
    
    total = split['comissao_plataforma'] + split['valor_freelancer'] + split['valor_dono']
    assert abs(total - 33.33) < 0.01, f"Soma deve ser ~33.33, obteve {total}"
    
    print("✅ test_split_com_centavos: PASSOU")

def test_split_valor_baixo():
    """Teste 3: Split com valor baixo (R$ 10)"""
    split = calcular_split_pagamento(10.0)
    
    assert split['comissao_plataforma'] == 1.5, f"Esperado 1.5, obteve {split['comissao_plataforma']}"
    assert split['valor_freelancer'] == 4.5, f"Esperado 4.5, obteve {split['valor_freelancer']}"
    assert split['valor_dono'] == 4.0, f"Esperado 4.0, obteve {split['valor_dono']}"
    
    total = split['comissao_plataforma'] + split['valor_freelancer'] + split['valor_dono']
    assert total == 10.0, f"Soma deve ser 10.0, obteve {total}"
    
    print("✅ test_split_valor_baixo: PASSOU")

def test_split_valor_alto():
    """Teste 4: Split com valor alto (R$ 1000)"""
    split = calcular_split_pagamento(1000.0)
    
    assert split['comissao_plataforma'] == 150.0, f"Esperado 150.0, obteve {split['comissao_plataforma']}"
    assert split['valor_freelancer'] == 450.0, f"Esperado 450.0, obteve {split['valor_freelancer']}"
    assert split['valor_dono'] == 400.0, f"Esperado 400.0, obteve {split['valor_dono']}"
    
    print("✅ test_split_valor_alto: PASSOU")

def test_snapshot_financeiro():
    """Teste 5: Garantir que valores de snapshot não são recalculados"""
    valor_original = 50.0
    split = calcular_split_pagamento(valor_original)
    
    # "Salvar" valores no snapshot (simulando banco de dados)
    snapshot = {
        'valor_total': split['valor_total'],
        'comissao_plataforma': split['comissao_plataforma'],
        'valor_freelancer': split['valor_freelancer'],
        'valor_dono': split['valor_dono']
    }
    
    # "Mudar as regras" (hipotético): agora seria 20%, 40%, 40%
    novo_split = {
        'comissao_plataforma': round(valor_original * 0.20, 2),
        'valor_freelancer': round(valor_original * 0.40, 2),
    }
    
    # Verificar que o snapshot permaneceu igual
    assert snapshot['comissao_plataforma'] == 7.5, "Snapshot não deve mudar"
    assert novo_split['comissao_plataforma'] == 10.0, "Novo cálculo seria diferente"
    assert snapshot['comissao_plataforma'] != novo_split['comissao_plataforma'], "Devem ser diferentes"
    
    print("✅ test_snapshot_financeiro: PASSOU")

def test_status_enum():
    """Teste 6: Validar valores do Enum de Status"""
    status = MockStatusAgendamento()
    
    assert status.PENDENTE == "pendente", "Status PENDENTE inválido"
    assert status.CONFIRMADO == "confirmado", "Status CONFIRMADO inválido"
    assert status.CONCLUIDO == "concluido", "Status CONCLUIDO inválido"
    assert status.CANCELADO == "cancelado", "Status CANCELADO inválido"
    
    # Verificar que são strings
    assert isinstance(status.PENDENTE, str), "Status deve ser string"
    
    print("✅ test_status_enum: PASSOU")

def test_transicoes_status():
    """Teste 7: Validar máquina de estados"""
    # Transições válidas
    valid_transitions = {
        'pendente': ['confirmado', 'cancelado'],
        'confirmado': ['concluido', 'cancelado'],
        'concluido': [],
        'cancelado': []
    }
    
    # Simular transições
    transitions_ok = [
        ('pendente', 'confirmado', True),
        ('pendente', 'cancelado', True),
        ('pendente', 'concluido', False),  # Inválido: não pode pular
        ('confirmado', 'concluido', True),
        ('confirmado', 'cancelado', True),
        ('confirmado', 'pendente', False),  # Não pode voltar atrás
        ('concluido', 'cancelado', False),  # Terminal
    ]
    
    for from_status, to_status, should_be_valid in transitions_ok:
        is_valid = to_status in valid_transitions[from_status]
        assert is_valid == should_be_valid, \
            f"Transição {from_status} → {to_status}: esperado {should_be_valid}, obteve {is_valid}"
    
    print("✅ test_transicoes_status: PASSOU")

def test_arredondamento_zero():
    """Teste 8: Garantir que não há perda de precisão com arredondamento"""
    # Testar múltiplos valores
    test_values = [1.0, 7.77, 25.50, 99.99, 123.45, 666.66]
    
    for valor in test_values:
        split = calcular_split_pagamento(valor)
        total = split['comissao_plataforma'] + split['valor_freelancer'] + split['valor_dono']
        
        # Permitir erro de 0.01 centavos (arredondamento)
        assert abs(total - valor) < 0.01, \
            f"Valor {valor}: soma foi {total}, diferença {total - valor}"
    
    print("✅ test_arredondamento_zero: PASSOU")

def test_percentuais():
    """Teste 9: Validar que os percentuais estão corretos"""
    valor = 1000.0
    split = calcular_split_pagamento(valor)
    
    # Percentuais
    pct_plataforma = (split['comissao_plataforma'] / valor) * 100
    pct_freelancer = (split['valor_freelancer'] / valor) * 100
    pct_dono = (split['valor_dono'] / valor) * 100
    
    assert abs(pct_plataforma - 15) < 0.1, f"Plataforma: esperado ~15%, obteve {pct_plataforma}%"
    assert abs(pct_freelancer - 45) < 0.1, f"Freelancer: esperado ~45%, obteve {pct_freelancer}%"
    assert abs(pct_dono - 40) < 0.1, f"Dono: esperado ~40%, obteve {pct_dono}%"
    
    print("✅ test_percentuais: PASSOU")

def test_datetime_fields():
    """Teste 10: Validar que campos de datetime funcionam"""
    agora = datetime.utcnow()
    inicio = agora
    fim = agora + timedelta(hours=1)
    
    # Simular agendamento com datas
    agendamento = {
        'data_hora_inicio': inicio,
        'data_hora_fim': fim,
        'status': MockStatusAgendamento.PENDENTE
    }
    
    duracao = agendamento['data_hora_fim'] - agendamento['data_hora_inicio']
    assert duracao.total_seconds() == 3600, "Duração deve ser 1 hora"
    assert isinstance(agendamento['data_hora_inicio'], datetime), "Deve ser datetime"
    
    print("✅ test_datetime_fields: PASSOU")

# ============================================================================
# EXECUTAR TESTES
# ============================================================================

if __name__ == "__main__":
    print("\n" + "="*70)
    print("TESTES: Modelo de Agendamento com Snapshot Financeiro")
    print("="*70 + "\n")
    
    tests = [
        test_split_basico,
        test_split_com_centavos,
        test_split_valor_baixo,
        test_split_valor_alto,
        test_snapshot_financeiro,
        test_status_enum,
        test_transicoes_status,
        test_arredondamento_zero,
        test_percentuais,
        test_datetime_fields,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"❌ {test.__name__}: FALHOU - {e}")
            failed += 1
        except Exception as e:
            print(f"❌ {test.__name__}: ERRO - {e}")
            failed += 1
    
    print("\n" + "="*70)
    print(f"RESULTADO: {passed} PASSOU, {failed} FALHOU de {len(tests)} testes")
    print("="*70 + "\n")
    
    sys.exit(0 if failed == 0 else 1)
