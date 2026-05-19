import sqlite3

conn = sqlite3.connect('barbearia.db')
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

print('=== FREELANCER larissavideos2018@gmail.com ===')
cursor.execute('SELECT id, nome, email, tipo, latitude, longitude FROM usuarios WHERE email = ?', ('larissavideos2018@gmail.com',))
for row in cursor.fetchall():
    print(f'ID: {row["id"]}, Nome: {row["nome"]}, Tipo: {row["tipo"]}')
    print(f'Lat: {row["latitude"]}, Lon: {row["longitude"]}')

print('\n=== CLIENTES ativos ===')
cursor.execute('SELECT id, nome, email, tipo, latitude, longitude FROM usuarios WHERE tipo = ? LIMIT 5', ('cliente',))
for row in cursor.fetchall():
    print(f'ID: {row["id"]}, Nome: {row["nome"]}, Email: {row["email"]}')
    print(f'Lat: {row["latitude"]}, Lon: {row["longitude"]}')

print('\n=== Todos os FREELANCERS ===')
cursor.execute('SELECT id, nome, email, tipo, latitude, longitude FROM usuarios WHERE tipo = ? LIMIT 10', ('barbeiro',))
for row in cursor.fetchall():
    print(f'ID: {row["id"]}, Nome: {row["nome"]}, Email: {row["email"]}')
    print(f'Lat: {row["latitude"]}, Lon: {row["longitude"]}')

conn.close()
