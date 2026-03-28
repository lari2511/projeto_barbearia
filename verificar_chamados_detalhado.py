import sqlite3

conn = sqlite3.connect('barbearia.db')
cursor = conn.cursor()

# Verificar chamados detalhados
chamados = cursor.execute("""
    SELECT c.id, c.status, c.barbeiro_id, c.barbearia_id, s.nome as servico, u.nome as cliente
    FROM chamados c
    JOIN servicos s ON c.servico_id = s.id
    JOIN usuarios u ON c.cliente_id = u.id
    ORDER BY c.id
""").fetchall()

print("📞 CHAMADOS NO BANCO:\n")
for ch in chamados:
    print(f"ID: {ch[0]}")
    print(f"  Status: {ch[1]}")
    print(f"  Barbeiro ID: {ch[2]}")
    print(f"  Barbearia ID: {ch[3]}")
    print(f"  Serviço: {ch[4]}")
    print(f"  Cliente: {ch[5]}")
    print()

# Ver barbeiros
barbeiros = cursor.execute("""
    SELECT id, nome, email, tipo, presente_em_local, barbearia_atual_id
    FROM usuarios
    WHERE tipo = 'barbeiro'
""").fetchall()

print("\n💈 BARBEIROS:\n")
for b in barbeiros:
    print(f"ID: {b[0]}")
    print(f"  Nome: {b[1]}")
    print(f"  Email: {b[2]}")
    print(f"  Presente em local: {b[4]}")
    print(f"  Barbearia atual ID: {b[5]}")
    print()

conn.close()
