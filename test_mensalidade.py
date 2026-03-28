#!/usr/bin/env python3
# Script para testar a lógica de mensalidade progressiva

from app.routes_mensalidade import calcular_mensalidade_total, calcular_preco_cadeira

print("=" * 60)
print("TESTE DE MENSALIDADE PROGRESSIVA")
print("=" * 60)

# Teste 1: Verificar preços individuais
print("\n1️⃣  PRECOS INDIVIDUAIS POR CADEIRA:")
print("-" * 60)
for i in range(1, 11):
    preco = calcular_preco_cadeira(i)
    print(f"   Cadeira {i:2d}: R$ {preco:7.2f}")

# Teste 2: Verificar totais progressivos
print("\n2️⃣  TOTAIS PROGRESSIVOS (TABELA COMPLETA):")
print("-" * 60)
print(f"{'Cadeiras':<10} | {'Total Mensal':<15} | {'Economia':<15}")
print("-" * 60)
for qtd in range(1, 11):
    total, _, economia = calcular_mensalidade_total(qtd)
    print(f"{qtd:<10} | R$ {total:>13.2f} | R$ {economia:>13.2f}")

# Teste 3: Validar exemplos da documentação
print("\n3️⃣  VALIDACAO DOS EXEMPLOS DA DOCUMENTACAO:")
print("-" * 60)
exemplos = {
    1: 47.90,
    2: 85.80,
    3: 113.70,
    4: 134.60,
    5: 152.50,
    6: 170.40,
    7: 188.30,
    8: 206.20,
    10: 242.00
}

todos_ok = True
for qtd, esperado in exemplos.items():
    total, _, _ = calcular_mensalidade_total(qtd)
    total = round(total, 2)
    esperado = round(esperado, 2)
    status = "✅" if total == esperado else "❌"
    todos_ok = todos_ok and (total == esperado)
    print(f"{status} {qtd} cadeira(s): R$ {total:7.2f} (esperado R$ {esperado:7.2f})")

if todos_ok:
    print("\n✅ TODOS OS TESTES PASSARAM!")
else:
    print("\n❌ ALGUNS TESTES FALHARAM!")

# Teste 4: Simulação de expansão
print("\n4️⃣  SIMULACAO DE EXPANSAO (3 → 6 CADEIRAS):")
print("-" * 60)
atual_total, _, _ = calcular_mensalidade_total(3)
nova_total, _, nova_economia = calcular_mensalidade_total(6)
incremento = nova_total - atual_total

print(f"   Situação Atual (3 cadeiras): R$ {atual_total:.2f}")
print(f"   Nova Situação (6 cadeiras): R$ {nova_total:.2f}")
print(f"   Incremento Mensal: R$ {incremento:.2f}")
print(f"   Incremento Anual: R$ {incremento * 12:.2f}")
print(f"   Economia Total (vs uniforme): R$ {nova_economia:.2f}")

print("\n" + "=" * 60)
