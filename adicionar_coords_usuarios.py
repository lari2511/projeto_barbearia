import sqlite3

conn = sqlite3.connect('barbearia.db')
cursor = conn.cursor()

# Ver barbeiros e barbearias com coordenadas
usuarios = cursor.execute("""
    SELECT id, nome, tipo, latitude, longitude
    FROM usuarios
    WHERE tipo IN ('barbeiro', 'barbearia')
""").fetchall()

print("👥 BARBEIROS E BARBEARIAS:\n")
for u in usuarios:
    print(f"ID: {u[0]}")
    print(f"  Nome: {u[1]}")
    print(f"  Tipo: {u[2]}")
    print(f"  Coordenadas: {u[3]}, {u[4]}")
    print()

# Atualizar todos sem coordenadas
print("\n🗺️  ADICIONANDO COORDENADAS...\n")

lat_sp = -23.5505
lon_sp = -46.6333

cursor.execute("""
    UPDATE usuarios
    SET latitude = ?, longitude = ?
    WHERE tipo IN ('barbeiro', 'barbearia')
    AND (latitude IS NULL OR longitude IS NULL)
""", (lat_sp, lon_sp))

rows_updated = cursor.rowcount
conn.commit()

print(f"✅ {rows_updated} usuário(s) atualizado(s)")

# Verificar resultado
usuarios = cursor.execute("""
    SELECT id, nome, tipo, latitude, longitude
    FROM usuarios
    WHERE tipo IN ('barbeiro', 'barbearia')
""").fetchall()

print("\n📍 RESULTADO:\n")
for u in usuarios:
    print(f"{u[0]}: {u[1]} ({u[2]}) → {u[3]}, {u[4]}")

conn.close()
