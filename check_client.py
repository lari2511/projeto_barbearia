import sqlite3

# Conectar ao banco
conn = sqlite3.connect('barbearia.db')
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# Verificar cliente
cursor.execute("""
    SELECT id, nome, tipo, latitude, longitude, email 
    FROM usuarios 
    WHERE email = 'lari.nascimento20148@gmail.com'
""")

result = cursor.fetchone()
if result:
    print(f"\n✅ CLIENTE ENCONTRADO:")
    print(f"   ID: {result['id']}")
    print(f"   Nome: {result['nome']}")
    print(f"   Tipo: {result['tipo']}")
    print(f"   Latitude: {result['latitude']}")
    print(f"   Longitude: {result['longitude']}")
    print(f"   Email: {result['email']}")
    
    # Se não tem coordenadas, adicionar as mesmas da barbearia
    if not result['latitude'] or not result['longitude']:
        print(f"\n⚠️  Sem coordenadas GPS! Adicionando coordenadas da barbearia...")
        cursor.execute("""
            UPDATE usuarios 
            SET latitude = -23.5525, longitude = -46.6353
            WHERE id = ?
        """, (result['id'],))
        conn.commit()
        print(f"✅ Coordenadas adicionadas: -23.5525, -46.6353")
else:
    print(f"❌ Cliente 'lari.nascimento20148@gmail.com' não encontrado")

conn.close()
