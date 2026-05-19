import sqlite3

# Conectar ao banco
conn = sqlite3.connect('barbearia.db')
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# Verificar usuário barbearia
cursor.execute("""
    SELECT id, nome, tipo, perfil_aprovado, latitude, longitude, email 
    FROM usuarios 
    WHERE nome = 'allansiqueira06' OR email LIKE '%allansiqueira%'
""")

result = cursor.fetchall()
if result:
    for row in result:
        print(f"\n✅ USUÁRIO ENCONTRADO:")
        print(f"   ID: {row['id']}")
        print(f"   Nome: {row['nome']}")
        print(f"   Tipo: {row['tipo']}")
        print(f"   Perfil Aprovado: {row['perfil_aprovado']}")
        print(f"   Latitude: {row['latitude']}")
        print(f"   Longitude: {row['longitude']}")
        print(f"   Email: {row['email']}")
        
        user_id = row['id']
        
        # Se é barbearia, verificar detalhes
        if row['tipo'] == 'barbearia':
            cursor.execute("""
                SELECT id, usuario_id, nome, endereco
                FROM barbearias
                WHERE usuario_id = ?
            """, (user_id,))
            
            barb = cursor.fetchone()
            if barb:
                print(f"\n📍 BARBEARIA:")
                print(f"   ID Barbearia: {barb['id']}")
                print(f"   Nome: {barb['nome']}")
                print(f"   Endereço: {barb['endereco']}")
                
                # Verificar cadeiras
                cursor.execute("""
                    SELECT COUNT(*) as total, 
                           SUM(CASE WHEN status = 'disponivel' THEN 1 ELSE 0 END) as livres
                    FROM cadeiras
                    WHERE barbearia_id = ?
                """, (barb['id'],))
                
                cadeiras = cursor.fetchone()
                print(f"\n🪑 CADEIRAS:")
                print(f"   Total: {cadeiras['total']}")
                print(f"   Livres (disponível): {cadeiras['livres']}")
else:
    print("❌ Barbearia 'allansiqueira06' não encontrada no banco")

conn.close()
