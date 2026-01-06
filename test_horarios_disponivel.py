#!/usr/bin/env python3
"""
Testes para a função is_horario_disponivel()
Valida a lógica de sobreposição de horários de agendamento.

Testes cobrem:
1. Horário disponível (sem conflitos)
2. Horário com conflito total
3. Horário com conflito parcial (overlapping)
4. Horário com agendamentos cancelados (deve ignorar)
5. Horários antes/depois (sem conflito)
"""

import sys
from datetime import datetime, timedelta

# Simular modelos
class MockStatus:
    CANCELADO = "cancelado"
    PENDENTE = "pendente"
    CONFIRMADO = "confirmado"
    CONCLUIDO = "concluido"

class MockChamado:
    def __init__(self, id, barbeiro_id, inicio, fim, status=None):
        self.id = id
        self.barbeiro_id = barbeiro_id
        self.data_hora_inicio = inicio
        self.data_hora_fim = fim
        self.status = status or MockStatus.CONFIRMADO

class MockDB:
    def __init__(self, chamados=None):
        self.chamados = chamados or []

    def query(self, model):
        return self

    def filter(self, condition):
        # Simples: já filtrado, retorna self
        return self

    def first(self):
        # Simular a busca (simplificado)
        return self.chamados[0] if self.chamados else None

# ============================================================================
# FUNÇÃO A SER TESTADA
# ============================================================================

def is_horario_disponivel(db, barbeiro_id, inicio, fim) -> bool:
    """
    Verifica se um barbeiro está disponível em um determinado horário.
    
    Procura por conflitos com agendamentos não-cancelados.
    Usa lógica de sobreposição de intervalos:
    - novo_inicio < agendamento_existente_fim AND
    - novo_fim > agendamento_existente_inicio
    """
    # Procura por conflitos com agendamentos do mesmo barbeiro
    conflito = None
    
    for chamado in db.chamados:
        # Verifica se é do mesmo barbeiro
        if chamado.barbeiro_id != barbeiro_id:
            continue
        
        # Ignora cancelados
        if chamado.status == MockStatus.CANCELADO:
            continue
        
        # Lógica mágica de sobreposição:
        # novo_inicio < agendamento_existente_fim AND novo_fim > agendamento_existente_inicio
        if chamado.data_hora_inicio < fim and chamado.data_hora_fim > inicio:
            conflito = chamado
            break
    
    # Se achou conflito, retorna False (não disponível)
    if conflito:
        return False
    return True  # Está livre!

# ============================================================================
# TESTES
# ============================================================================

def test_horario_completamente_livre():
    """Teste 1: Horário sem nenhum conflito"""
    base = datetime(2025, 1, 15, 10, 0)
    
    db = MockDB([
        MockChamado(1, 1, base + timedelta(hours=2), base + timedelta(hours=3))
    ])
    
    # Tentar agendar 1 hora antes
    disponivel = is_horario_disponivel(db, 1, base, base + timedelta(hours=1))
    assert disponivel == True, "Deveria estar disponível antes do agendamento"
    
    # Tentar agendar 1 hora depois
    disponivel = is_horario_disponivel(db, 1, base + timedelta(hours=3, minutes=1), base + timedelta(hours=4))
    assert disponivel == True, "Deveria estar disponível depois do agendamento"
    
    print("✅ test_horario_completamente_livre: PASSOU")

def test_horario_com_conflito_total():
    """Teste 2: Horário totalmente ocupado"""
    base = datetime(2025, 1, 15, 10, 0)
    agendamento_existente = base + timedelta(hours=1)
    
    db = MockDB([
        MockChamado(1, 1, agendamento_existente, agendamento_existente + timedelta(hours=1))
    ])
    
    # Tentar agendar exatamente no mesmo horário
    disponivel = is_horario_disponivel(
        db, 1, 
        agendamento_existente, 
        agendamento_existente + timedelta(hours=1)
    )
    assert disponivel == False, "Não deveria estar disponível (conflito total)"
    
    print("✅ test_horario_com_conflito_total: PASSOU")

def test_horario_com_conflito_parcial_inicio():
    """Teste 3: Novo agendamento começa antes mas termina no meio do existente"""
    base = datetime(2025, 1, 15, 10, 0)
    agendamento_existente = base + timedelta(hours=2)
    
    db = MockDB([
        MockChamado(1, 1, agendamento_existente, agendamento_existente + timedelta(hours=1))
    ])
    
    # Tentar agendar começando 30 min antes e terminando 30 min após o início
    disponivel = is_horario_disponivel(
        db, 1,
        agendamento_existente - timedelta(minutes=30),
        agendamento_existente + timedelta(minutes=30)
    )
    assert disponivel == False, "Não deveria estar disponível (overlapping no início)"
    
    print("✅ test_horario_com_conflito_parcial_inicio: PASSOU")

def test_horario_com_conflito_parcial_fim():
    """Teste 4: Novo agendamento começa no meio e termina depois do existente"""
    base = datetime(2025, 1, 15, 10, 0)
    agendamento_existente = base + timedelta(hours=2)
    
    db = MockDB([
        MockChamado(1, 1, agendamento_existente, agendamento_existente + timedelta(hours=1))
    ])
    
    # Tentar agendar começando 30 min após o início e terminando 30 min depois do fim
    disponivel = is_horario_disponivel(
        db, 1,
        agendamento_existente + timedelta(minutes=30),
        agendamento_existente + timedelta(hours=1, minutes=30)
    )
    assert disponivel == False, "Não deveria estar disponível (overlapping no fim)"
    
    print("✅ test_horario_com_conflito_parcial_fim: PASSOU")

def test_ignora_agendamentos_cancelados():
    """Teste 5: Agendamentos cancelados devem ser ignorados"""
    base = datetime(2025, 1, 15, 10, 0)
    agendamento_cancelado = base + timedelta(hours=1)
    
    db = MockDB([
        MockChamado(1, 1, agendamento_cancelado, agendamento_cancelado + timedelta(hours=1), status=MockStatus.CANCELADO)
    ])
    
    # Tentar agendar no mesmo horário de um agendamento CANCELADO
    disponivel = is_horario_disponivel(
        db, 1,
        agendamento_cancelado,
        agendamento_cancelado + timedelta(hours=1)
    )
    assert disponivel == True, "Deveria estar disponível (agendamento foi cancelado)"
    
    print("✅ test_ignora_agendamentos_cancelados: PASSOU")

def test_apenas_mesmo_barbeiro():
    """Teste 6: Agendamentos de outros barbeiros não afetam disponibilidade"""
    base = datetime(2025, 1, 15, 10, 0)
    agendamento_outro_barbeiro = base + timedelta(hours=1)
    
    db = MockDB([
        MockChamado(1, 2, agendamento_outro_barbeiro, agendamento_outro_barbeiro + timedelta(hours=1))
    ])
    
    # Tentar agendar para o barbeiro 1 no mesmo horário de um agendamento do barbeiro 2
    disponivel = is_horario_disponivel(
        db, 1,  # Barbeiro diferente
        agendamento_outro_barbeiro,
        agendamento_outro_barbeiro + timedelta(hours=1)
    )
    assert disponivel == True, "Deveria estar disponível (agendamento é de outro barbeiro)"
    
    print("✅ test_apenas_mesmo_barbeiro: PASSOU")

def test_horario_logo_depois():
    """Teste 7: Agendamento que começa exatamente quando o outro termina"""
    base = datetime(2025, 1, 15, 10, 0)
    agendamento_existente = base + timedelta(hours=1)
    fim_existente = agendamento_existente + timedelta(hours=1)
    
    db = MockDB([
        MockChamado(1, 1, agendamento_existente, fim_existente)
    ])
    
    # Tentar agendar começando EXATAMENTE quando o outro termina
    disponivel = is_horario_disponivel(
        db, 1,
        fim_existente,  # Começa exatamente no fim do anterior
        fim_existente + timedelta(hours=1)
    )
    assert disponivel == True, "Deveria estar disponível (sem sobreposição: A.fim == B.inicio)"
    
    print("✅ test_horario_logo_depois: PASSOU")

def test_multiplos_agendamentos():
    """Teste 8: Múltiplos agendamentos, um gera conflito"""
    base = datetime(2025, 1, 15, 10, 0)
    
    db = MockDB([
        MockChamado(1, 1, base, base + timedelta(hours=1)),
        MockChamado(2, 1, base + timedelta(hours=2), base + timedelta(hours=3)),
        MockChamado(3, 1, base + timedelta(hours=4), base + timedelta(hours=5)),
    ])
    
    # Tentar agendar entre o 1º e 2º (disponível)
    disponivel = is_horario_disponivel(
        db, 1,
        base + timedelta(hours=1, minutes=1),
        base + timedelta(hours=1, minutes=59)
    )
    assert disponivel == True, "Deveria estar disponível no gap"
    
    # Tentar agendar no 2º (não disponível)
    disponivel = is_horario_disponivel(
        db, 1,
        base + timedelta(hours=2, minutes=30),
        base + timedelta(hours=2, minutes=45)
    )
    assert disponivel == False, "Não deveria estar disponível (conflito com 2º agendamento)"
    
    print("✅ test_multiplos_agendamentos: PASSOU")

def test_horario_logo_antes():
    """Teste 9: Agendamento que termina exatamente quando o outro começa"""
    base = datetime(2025, 1, 15, 10, 0)
    agendamento_existente = base + timedelta(hours=2)
    inicio_existente = agendamento_existente
    
    db = MockDB([
        MockChamado(1, 1, inicio_existente, inicio_existente + timedelta(hours=1))
    ])
    
    # Tentar agendar terminando EXATAMENTE quando o outro começa
    disponivel = is_horario_disponivel(
        db, 1,
        base,
        inicio_existente  # Termina exatamente no início do próximo
    )
    assert disponivel == True, "Deveria estar disponível (sem sobreposição: A.fim == B.inicio)"
    
    print("✅ test_horario_logo_antes: PASSOU")

def test_agendar_dentro_de_agendamento():
    """Teste 10: Tentar agendar completamente dentro de outro agendamento"""
    base = datetime(2025, 1, 15, 10, 0)
    agendamento_existente = base + timedelta(hours=1)
    
    db = MockDB([
        MockChamado(1, 1, agendamento_existente, agendamento_existente + timedelta(hours=2))
    ])
    
    # Tentar agendar bem no meio
    disponivel = is_horario_disponivel(
        db, 1,
        agendamento_existente + timedelta(minutes=30),
        agendamento_existente + timedelta(minutes=45)
    )
    assert disponivel == False, "Não deveria estar disponível (está dentro do agendamento)"
    
    print("✅ test_agendar_dentro_de_agendamento: PASSOU")

# ============================================================================
# EXECUTAR TESTES
# ============================================================================

if __name__ == "__main__":
    print("\n" + "="*70)
    print("TESTES: Validação de Disponibilidade de Horário")
    print("Função: is_horario_disponivel()")
    print("="*70 + "\n")
    
    tests = [
        test_horario_completamente_livre,
        test_horario_com_conflito_total,
        test_horario_com_conflito_parcial_inicio,
        test_horario_com_conflito_parcial_fim,
        test_ignora_agendamentos_cancelados,
        test_apenas_mesmo_barbeiro,
        test_horario_logo_depois,
        test_multiplos_agendamentos,
        test_horario_logo_antes,
        test_agendar_dentro_de_agendamento,
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
    print("="*70)
    
    # Explicar a lógica mágica
    print("\n" + "="*70)
    print("EXPLICAÇÃO DA LÓGICA DE SOBREPOSIÇÃO:")
    print("="*70)
    print("""
A LÓGICA MÁGICA:
  novo_inicio < agendamento_fim AND novo_fim > agendamento_inicio

EXEMPLOS:
  
  ✅ SEM CONFLITO:
    Agendamento Existente: [10:00 ---- 11:00]
    Novo Agendamento:                        [11:00 ---- 12:00]
    Teste: 11:00 < 11:00 AND 12:00 > 10:00
    Resultado: False AND True = FALSE ✅ (disponível)
  
  ❌ COM CONFLITO (overlapping):
    Agendamento Existente: [10:00 ---- 11:00]
    Novo Agendamento:           [10:30 ---- 11:30]
    Teste: 10:30 < 11:00 AND 11:30 > 10:00
    Resultado: True AND True = TRUE ❌ (conflito!)
  
  ❌ COM CONFLITO (totalmente dentro):
    Agendamento Existente: [10:00 ---- 11:00]
    Novo Agendamento:        [10:15 ---- 10:45]
    Teste: 10:15 < 11:00 AND 10:45 > 10:00
    Resultado: True AND True = TRUE ❌ (conflito!)
  
  ✅ SEM CONFLITO (bem depois):
    Agendamento Existente: [10:00 ---- 11:00]
    Novo Agendamento:                        [11:01 ---- 12:00]
    Teste: 11:01 < 11:00 AND 12:00 > 10:00
    Resultado: False AND True = FALSE ✅ (disponível)
""")
    
    sys.exit(0 if failed == 0 else 1)
