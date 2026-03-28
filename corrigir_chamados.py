"""
Corrigir chamados - remover barbeiro_id para aparecerem como "abertos"
"""

import sqlite3
from datetime import datetime, timedelta

conn = sqlite3.connect('barbearia.db')
cursor = conn.cursor()

print("🔧 CORRIGINDO CHAMADOS...\n")

# 1. Limpar chamados existentes
cursor.execute("DELETE FROM chamados")
print("✓ Chamados antigos removidos")

# 2. Buscar IDs necessários
cursor.execute("SELECT id FROM usuarios WHERE tipo = 'cliente' LIMIT 1")
cliente = cursor.fetchone()

cursor.execute("SELECT id FROM barbearias LIMIT 1")
barbearia = cursor.fetchone()

cursor.execute("SELECT id, nome, valor FROM servicos LIMIT 5")
servicos = cursor.fetchall()

if cliente and barbearia and servicos:
    cliente_id = cliente[0]
    barbearia_id = barbearia[0]
    
    print(f"\n📋 Criando chamados para:")
    print(f"  Cliente ID: {cliente_id}")
    print(f"  Barbearia ID: {barbearia_id}\n")
    
    # 3. Criar 10 chamados PENDENTES sem barbeiro
    chamados_novos = []
    for i, servico in enumerate(servicos):
        # Criar 2 chamados de cada serviço
        for j in range(2):
            servico_id = servico[0]
            servico_nome = servico[1]
            servico_valor = servico[2]
            data_hora = datetime.now() + timedelta(hours=i*2 + j)
            
            cursor.execute("""
                INSERT INTO chamados (
                    cliente_id, 
                    barbeiro_id,
                    barbearia_id, 
                    servico_id,
                    status, 
                    data_hora_inicio, 
                    observacao, 
                    data_agendamento,
                    valor_total
                ) VALUES (?, NULL, ?, ?, 'pendente', ?, ?, ?, ?)
            """, (
                cliente_id,
                barbearia_id, 
                servico_id,
                data_hora.isoformat(), 
                f"Chamado novo {i*2 + j + 1}",
                datetime.now().isoformat(),
                servico_valor
            ))
            chamados_novos.append((servico_nome, servico_valor))
    
    conn.commit()
    print(f"✅ {len(chamados_novos)} chamados PENDENTES criados:\n")
    for idx, (nome, valor) in enumerate(chamados_novos, 1):
        print(f"  {idx}. {nome} - R$ {valor:.2f}")
    
    # Verificar
    cursor.execute("SELECT COUNT(*) FROM chamados WHERE barbeiro_id IS NULL")
    count = cursor.fetchone()[0]
    print(f"\n📊 Total de chamados sem barbeiro: {count}")

else:
    print("❌ Erro: Faltam dados necessários (cliente, barbearia ou serviços)")

conn.close()
