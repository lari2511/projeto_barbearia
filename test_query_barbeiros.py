"""Testar query de barbeiros"""
import sqlite3

conn = sqlite3.connect('barbearia.db')
cursor = conn.cursor()

print("=== Barbeiros no banco ===")
cursor.execute("""
    SELECT email, latitude, longitude, disponivel, ocupado_ate, perfil_aprovado
    FROM usuarios 
    WHERE tipo='barbeiro'
""")

for row in cursor.fetchall():
    print(f"Email: {row[0]}")
    print(f"  Lat: {row[1]}, Lon: {row[2]}")
    print(f"  Disponível: {row[3]}, Aprovado: {row[5]}")
    print(f"  Ocupado até: {row[4]}\n")

conn.close()
