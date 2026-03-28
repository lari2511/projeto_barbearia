"""
Módulo de Cálculo de Mensalidade Progressiva BarberMovie

📌 REGRA DE NEGÓCIO – MENSALIDADE PROGRESSIVA POR CADEIRA

🔹 Estrutura de Preços:
- 1ª cadeira (obrigatória): R$ 47,90
- 2ª cadeira: R$ 37,90
- 3ª cadeira: R$ 27,90
- 4ª cadeira: R$ 20,90
- 5ª cadeira: R$ 17,90
- 6ª cadeira em diante: R$ 17,90 (valor mínimo estabilizado)

📌 Objetivo Estratégico:
- Cada nova cadeira sempre fica mais barata
- Incentiva expansão constante
- Cria percepção de vantagem progressiva
- Mantém valor forte na primeira cadeira
- Estabiliza margem após 6ª cadeira
"""

# 💰 TABELA DE PREÇOS PROGRESSIVOS
PRECOS_CADEIRAS = [
    47.90,  # 1ª cadeira
    37.90,  # 2ª cadeira
    27.90,  # 3ª cadeira
    20.90,  # 4ª cadeira
    17.90   # 5ª cadeira
]

VALOR_MINIMO_APOS_QUINTA = 17.90  # 6ª cadeira em diante (PISO FIXO: nunca menor que isso)


def calcular_mensalidade_progressiva(quantidade_cadeiras):
    """
    Calcula mensalidade com preços progressivos (decrescentes) por cadeira.
    
    Regra: Cada nova cadeira fica mais barata, incentivando expansão.
    - 1ª a 5ª cadeira: valores fixos da tabela PRECOS_CADEIRAS
    - 6ª em diante: valor mínimo de R$ 17,90
    
    Args:
        quantidade_cadeiras (int): Número de cadeiras da barbearia (mínimo 1)
    
    Returns:
        float: Valor total da mensalidade
    
    Exemplos:
        >>> calcular_mensalidade_progressiva(1)
        47.90
        >>> calcular_mensalidade_progressiva(2)
        85.80
        >>> calcular_mensalidade_progressiva(3)
        113.70
        >>> calcular_mensalidade_progressiva(10)
        242.00
    """
    if quantidade_cadeiras < 1:
        return 0.0
    
    total = 0.0
    for i in range(1, quantidade_cadeiras + 1):
        if i <= 5:
            valor_cadeira = PRECOS_CADEIRAS[i - 1]
        else:
            valor_cadeira = VALOR_MINIMO_APOS_QUINTA

        valor_cadeira = max(valor_cadeira, VALOR_MINIMO_APOS_QUINTA)
        total += valor_cadeira
    
    return round(total, 2)


def obter_valor_cadeira(posicao):
    """
    Retorna o valor de uma cadeira específica pela sua posição.
    
    Args:
        posicao (int): Posição da cadeira (1 = primeira, 2 = segunda, etc.)
    
    Returns:
        float: Valor individual da cadeira naquela posição
    
    Exemplos:
        >>> obter_valor_cadeira(1)
        47.90
        >>> obter_valor_cadeira(6)
        17.90
    """
    if posicao < 1:
        return 0.0
    
    if posicao <= 5:
        return max(PRECOS_CADEIRAS[posicao - 1], VALOR_MINIMO_APOS_QUINTA)
    else:
        return VALOR_MINIMO_APOS_QUINTA


def gerar_tabela_precos(ate_cadeiras=10):
    """
    Gera tabela de preços para visualização.
    
    Args:
        ate_cadeiras (int): Até quantas cadeiras mostrar na tabela (padrão: 10)
    
    Returns:
        list: Lista de tuplas (quantidade, valor_individual, valor_total)
    
    Exemplo:
        >>> tabela = gerar_tabela_precos(5)
        >>> tabela[0]
        (1, 47.90, 47.90)
    """
    tabela = []
    for qtd in range(1, ate_cadeiras + 1):
        valor_individual = obter_valor_cadeira(qtd)
        valor_total = calcular_mensalidade_progressiva(qtd)
        tabela.append((qtd, valor_individual, valor_total))
    
    return tabela


def exibir_tabela_precos(ate_cadeiras=10):
    """
    Exibe tabela de preços formatada no console.
    
    Args:
        ate_cadeiras (int): Até quantas cadeiras mostrar (padrão: 10)
    """
    print("\n📊 TABELA DE MENSALIDADE PROGRESSIVA\n")
    print(f"{'Cadeiras':<10} | {'Valor Cadeira':<15} | {'Total Mensal':<15}")
    print("-" * 45)
    
    tabela = gerar_tabela_precos(ate_cadeiras)
    for qtd, valor_ind, valor_total in tabela:
        if qtd == 1:
            print(f"{qtd:<10} | R$ {valor_ind:>8.2f}       | R$ {valor_total:>8.2f}")
        else:
            print(f"{qtd:<10} | +R$ {valor_ind:>7.2f}       | R$ {valor_total:>8.2f}")
    
    print()
    print("💡 A partir da 6ª cadeira: R$ 17,90/cadeira")
    print()


if __name__ == "__main__":
    # Testes e demonstração
    print("🚀 Módulo de Cálculo de Mensalidade Progressiva")
    print("=" * 60)
    
    # Exibir tabela padrão
    exibir_tabela_precos(10)
    
    # Validar casos específicos do usuário
    print("✅ VALIDAÇÃO DOS EXEMPLOS FORNECIDOS:")
    casos_teste = [
        (1, 47.90),
        (2, 85.80),
        (3, 113.70),
        (4, 134.60),
        (5, 152.50),
        (6, 170.40),
        (7, 188.30),
        (8, 206.20),
        (10, 242.00)
    ]
    
    todos_ok = True
    for qtd, esperado in casos_teste:
        calculado = calcular_mensalidade_progressiva(qtd)
        status = "✓" if abs(calculado - esperado) < 0.01 else "✗"
        print(f"  {status} {qtd} cadeiras: R$ {calculado:.2f} (esperado: R$ {esperado:.2f})")
        if abs(calculado - esperado) >= 0.01:
            todos_ok = False
    
    print()
    if todos_ok:
        print("🎉 TODOS OS TESTES PASSARAM!")
    else:
        print("⚠️  ALGUNS TESTES FALHARAM!")
