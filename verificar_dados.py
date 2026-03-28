import sqlite3

conn = sqlite3.connect('barbearia.db')
cursor = conn.cursor()

# Verificar chamados
chamados = cursor.execute("""
    SELECT c.id, c.status, s.nome as servico, u.nome as cliente, c.observacao
    FROM chamados c
    JOIN servicos s ON c.servico_id = s.id
    JOIN usuarios u ON c.cliente_id = u.id
    ORDER BY c.id DESC
    LIMIT 10
""").fetchall()

print("📞 CHAMADOS NO BANCO DE DADOS:\n")
if chamados:
    for chamado in chamados:
        print(f"  #{chamado[0]} - {chamado[1].upper()}")
        print(f"    Serviço: {chamado[2]}")
        print(f"    Cliente: {chamado[3]}")
        print(f"    Obs: {chamado[4]}")
        print()
    print(f"✅ Total: {len(chamados)} chamados encontrados")
else:
    print("  ❌ NENHUM CHAMADO ENCONTRADO!")

# Verificar serviços
servicos = cursor.execute("SELECT nome, categoria, valor FROM servicos").fetchall()
print(f"\n📋 SERVIÇOS NO BANCO: {len(servicos)}")
for s in servicos:
    print(f"  - {s[0]} ({s[1]}) - R$ {s[2]:.2f}")

conn.close()
