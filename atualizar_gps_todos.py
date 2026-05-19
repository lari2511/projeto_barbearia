import sqlite3

conn = sqlite3.connect('barbearia.db')
cursor = conn.cursor()

# Adicionar GPS a todos os clientes/freelancers que não têm
cursor.execute('''UPDATE usuarios SET latitude = -23.5505, longitude = -46.6333 
                 WHERE (tipo = "cliente" OR tipo = "barbeiro") 
                 AND (latitude IS NULL OR longitude IS NULL)''')

conn.commit()
print('✅ GPS adicionado aos usuários que estavam sem localização')
print(f'Atualizados: {cursor.rowcount} perfis')

# Verificar
cursor.execute('SELECT COUNT(*) FROM usuarios WHERE latitude IS NOT NULL AND longitude IS NOT NULL')
total_com_gps = cursor.fetchone()[0]
print(f'✅ Total de usuários com GPS: {total_com_gps}')

# Listar todos para confirmar
print('\n=== Perfis de Teste Atualizados ===')
cursor.execute('SELECT id, nome, email, tipo, latitude, longitude FROM usuarios WHERE tipo IN ("cliente", "barbeiro") ORDER BY tipo, nome')
for row in cursor.fetchall():
    print(f'{row[2]:30} ({row[3]:8}) - Lat: {row[4]}, Lon: {row[5]}')

conn.close()
