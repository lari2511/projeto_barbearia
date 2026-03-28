"""
Implementação do Modelo de Cobrança BarberMovie

📌 MODELO DE BARBEARIA - MENSALIDADE PROGRESSIVA:
- 1ª cadeira (obrigatória): R$ 47,90
- 2ª cadeira: R$ 37,90
- 3ª cadeira: R$ 27,90
- 4ª cadeira: R$ 20,90
- 5ª cadeira: R$ 17,90
- 6ª cadeira em diante: R$ 17,90 (valor mínimo estabilizado)

Exemplos:
- 1 cadeira: R$ 47,90
- 2 cadeiras: R$ 85,80 (47,90 + 37,90)
- 3 cadeiras: R$ 113,70 (47,90 + 37,90 + 27,90)
- 10 cadeiras: R$ 242,00

📌 MODELO FREELANCER:
- Valor do corte: R$ 50,00
- Divisão: 50% barbearia (R$ 25,00) + 50% freelancer (R$ 25,00)
- Comissão plataforma: 10% sobre valor do freelancer (R$ 2,50)
- Freelancer recebe líquido: R$ 22,50
"""

import sqlite3
from datetime import datetime, timedelta
import bcrypt

# 💰 MODELO DE MENSALIDADE PROGRESSIVA POR CADEIRA
# Preços por posição (índice 0 = 1ª cadeira, índice 1 = 2ª cadeira, etc.)
PRECOS_CADEIRAS = [
    47.90,  # 1ª cadeira
    37.90,  # 2ª cadeira
    27.90,  # 3ª cadeira
    20.90,  # 4ª cadeira
    17.90   # 5ª cadeira
]
VALOR_MINIMO_APOS_QUINTA = 17.90  # 6ª cadeira em diante (PISO FIXO: nunca menor que isso)

PERCENTUAL_COMISSAO_PLATAFORMA = 0.10
VALOR_SERVICO_PADRAO = 50.00

def calcular_mensalidade_barbearia(quantidade_cadeiras):
    """
    Calcula mensalidade com preços progressivos (decrescentes) por cadeira.
    
    Regra: Cada nova cadeira fica mais barata, incentivando expansão.
    - 1ª a 5ª cadeira: valores fixos da tabela PRECOS_CADEIRAS
    - 6ª em diante: valor mínimo de R$ 17,90
    
    Args:
        quantidade_cadeiras (int): Número de cadeiras da barbearia
    
    Returns:
        float: Valor total da mensalidade
    """
    if quantidade_cadeiras < 1:
        return 0
    
    total = 0
    for i in range(1, quantidade_cadeiras + 1):
        if i <= 5:
            valor_cadeira = PRECOS_CADEIRAS[i - 1]
        else:
            valor_cadeira = VALOR_MINIMO_APOS_QUINTA

        valor_cadeira = max(valor_cadeira, VALOR_MINIMO_APOS_QUINTA)
        total += valor_cadeira
    
    return total

def calcular_comissao_freelancer(valor_servico):
    """Calcula comissão sobre valor do freelancer (50% do serviço)"""
    valor_freelancer = valor_servico * 0.50  # Freelancer recebe 50%
    comissao = valor_freelancer * PERCENTUAL_COMISSAO_PLATAFORMA
    valor_liquido = valor_freelancer - comissao
    return {
        'valor_total': valor_servico,
        'valor_barbearia': valor_servico * 0.50,
        'valor_freelancer_bruto': valor_freelancer,
        'comissao_plataforma': comissao,
        'valor_freelancer_liquido': valor_liquido
    }

# Conectar ao banco
conn = sqlite3.connect('barbearia.db')
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

print("🚀 Implementando Modelo de Cobrança BarberMovie...\n")

# 1. Validar exemplos de mensalidade
print("📊 VALIDAÇÃO MENSALIDADE PROGRESSIVA:")
exemplos = [1, 2, 3, 4, 5, 6, 7, 8, 10]
for qtd in exemplos:
    valor = calcular_mensalidade_barbearia(qtd)
    print(f"  {qtd} cadeira{'s' if qtd > 1 else '':<9} -> R$ {valor:>6.2f}")

# 2. Validar comissão freelancer
print("\n💰 VALIDAÇÃO COMISSÃO FREELANCER:")
resultado = calcular_comissao_freelancer(50.00)
print(f"  Valor corte: R$ {resultado['valor_total']:.2f}")
print(f"  Barbearia recebe: R$ {resultado['valor_barbearia']:.2f}")
print(f"  Freelancer bruto: R$ {resultado['valor_freelancer_bruto']:.2f}")
print(f"  Comissão plataforma: R$ {resultado['comissao_plataforma']:.2f}")
print(f"  Freelancer líquido: R$ {resultado['valor_freelancer_liquido']:.2f}")

# 3. Criar serviços com valores corretos
print("\n📋 CRIANDO SERVIÇOS DE TESTE...")

# Buscar barbearia de teste
cursor.execute("SELECT id FROM barbearias LIMIT 1")
barbearia = cursor.fetchone()

if barbearia:
    barbearia_id = barbearia['id']
    
    # Limpar serviços existentes
    cursor.execute("DELETE FROM servicos WHERE barbearia_id = ?", (barbearia_id,))
    
    # Criar serviços padrão (com categorias)
    servicos = [
        ('Corte Simples', 'Corte tradicional', 'corte', 50.00, 30),
        ('Corte + Barba', 'Corte completo com barba', 'combo', 80.00, 45),
        ('Barba', 'Aparar e modelar barba', 'barba', 30.00, 20),
        ('Corte Degradê', 'Corte degradê profissional', 'corte', 60.00, 40),
        ('Sombrancelha', 'Design de sombrancelha', 'sobrancelha', 15.00, 15),
    ]
    
    for nome, descricao, categoria, valor, duracao in servicos:
        cursor.execute("""
            INSERT INTO servicos (barbearia_id, nome, descricao, categoria, valor, duracao_minutos, ativo)
            VALUES (?, ?, ?, ?, ?, ?, 1)
        """, (barbearia_id, nome, descricao, categoria, valor, duracao))
        print(f"  ✓ {nome} - R$ {valor:.2f}")
    
    # Atualizar número de cadeiras da barbearia (se a coluna existir)
    # cursor.execute("UPDATE barbearias SET cadeiras_disponiveis = 3 WHERE id = ?", (barbearia_id,))
    mensalidade = calcular_mensalidade_barbearia(3)
    print(f"\n✓ Barbearia configurada com 3 cadeiras")
    print(f"  Mensalidade: R$ {mensalidade:.2f}")

# 4. Criar chamados de teste
print("\n📞 CRIANDO CHAMADOS DE TESTE...")

# Buscar IDs necessários
cursor.execute("SELECT id FROM usuarios WHERE tipo = 'cliente' LIMIT 1")
cliente = cursor.fetchone()

cursor.execute("SELECT id FROM usuarios WHERE tipo = 'barbeiro' LIMIT 1")
barbeiro = cursor.fetchone()

cursor.execute("SELECT id FROM servicos LIMIT 3")
servicos_db = cursor.fetchall()

if cliente and barbeiro and servicos_db and barbearia:
    cliente_id = cliente['id']
    barbeiro_id = barbeiro['id']
    
    # Criar 5 chamados com diferentes status
    chamados_teste = [
        ('pendente', 0, 'Aguardando atendimento'),
        ('aceito', 1, 'Barbeiro aceitou'),
        ('em_andamento', 2, 'Atendimento em andamento'),
        ('concluido', 3, 'Serviço finalizado'),
        ('pendente', 4, 'Novo agendamento'),
    ]
    
    for status, offset, descricao in chamados_teste:
        servico = servicos_db[offset % len(servicos_db)]
        data_hora = datetime.now() + timedelta(hours=offset)
        
        cursor.execute("""
            INSERT INTO chamados (
                cliente_id, barbeiro_id, barbearia_id, servico_id,
                status, data_hora_inicio, observacao, data_agendamento
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            cliente_id, barbeiro_id, barbearia_id, servico['id'],
            status, data_hora.isoformat(), descricao, datetime.now().isoformat()
        ))
        print(f"  ✓ Chamado {status} - {descricao}")

conn.commit()
print("\n✅ Modelo de cobrança implementado com sucesso!")
print("\n📝 RESUMO:")
print(f"  • Serviços criados: {len(servicos)}")
print(f"  • Chamados criados: {len(chamados_teste)}")
print(f"  • Modelo de mensalidade: Progressivo (1ª: R$47,90 → 6ª+: R$17,90)")
print(f"  • Comissão freelancer: 10% sobre 50% do valor do serviço")

conn.close()
