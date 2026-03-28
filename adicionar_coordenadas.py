"""
Adicionar coordenadas para barbearias
"""

import sqlite3

conn = sqlite3.connect('barbearia.db')
cursor = conn.cursor()

print("🗺️  ADICIONANDO COORDENADAS PARA BARBEARIAS...\n")

# Coordenadas para São Paulo (região central)
# Caso não tenha coordenadas específicas, usa centro de SP
lat_sp = -23.5505
lon_sp = -46.6333

# Atualizar todas as barbearias sem coordenadas
cursor.execute("""
    UPDATE barbearias 
    SET latitude = ?, longitude = ?
    WHERE latitude IS NULL OR longitude IS NULL
""", (lat_sp, lon_sp))

rows_updated = cursor.rowcount
conn.commit()

print(f"✅ {rows_updated} barbearia(s) atualizada(s) com coordenadas de São Paulo")
print(f"   Latitude: {lat_sp}")
print(f"   Longitude: {lon_sp}\n")

# Verificar resultado
barbearias = cursor.execute("""
    SELECT id, nome, endereco, latitude, longitude
    FROM barbearias
""").fetchall()

print("📍 BARBEARIAS NO SISTEMA:\n")
for b in barbearias:
    print(f"ID: {b[0]}")
    print(f"  Nome: {b[1]}")
    print(f"  Endereço: {b[2]}")
    print(f"  Coordenadas: {b[3]}, {b[4]}")
    print()

conn.close()
