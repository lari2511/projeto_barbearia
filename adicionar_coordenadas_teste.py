"""
Adiciona coordenadas aos usuários de teste
"""
import sqlite3

def atualizar_coordenadas():
    conn = sqlite3.connect('barbearia.db')
    cursor = conn.cursor()
    
    try:
        # Atualizar barbeiro com coordenadas de São Paulo
        cursor.execute("""
            UPDATE usuarios 
            SET latitude = -23.5505,
                longitude = -46.6333,
                disponivel = 1,
                perfil_aprovado = 1
            WHERE email = 'larissavideos2018@gmail.com'
        """)
        
        # Atualizar cliente com coordenadas próximas
        cursor.execute("""
            UPDATE usuarios 
            SET latitude = -23.5515,
                longitude = -46.6343
            WHERE email = 'lari.nascimento20148@gmail.com'
        """)
        
        # Atualizar barbearia com coordenadas
        cursor.execute("""
            UPDATE usuarios 
            SET latitude = -23.5525,
                longitude = -46.6353,
                perfil_aprovado = 1
            WHERE email = 'allansiqueira06@gmail.com'
        """)
        
        conn.commit()
        
        print("✅ Coordenadas atualizadas!")
        
        # Verificar
        cursor.execute("SELECT email, latitude, longitude, disponivel, perfil_aprovado FROM usuarios WHERE tipo = 'barbeiro'")
        barbeiros = cursor.fetchall()
        print("\n📍 Barbeiros:")
        for b in barbeiros:
            print(f"  {b[0]}: lat={b[1]}, lon={b[2]}, disponível={b[3]}, aprovado={b[4]}")
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    atualizar_coordenadas()
