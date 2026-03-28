"""Verificar dados do barbeiro"""
import sqlite3

conn = sqlite3.connect('barbearia.db')
cursor = conn.cursor()

try:
    # Buscar barbeiro
    cursor.execute("""
        SELECT id, nome, email, tipo, disponivel, em_atendimento, ocupado_ate, offline
        FROM usuarios 
        WHERE email = 'larissavideos2018@gmail.com'
    """)
    barbeiro = cursor.fetchone()
    
    if barbeiro:
        print("=== Dados do Barbeiro ===")
        print(f"ID: {barbeiro[0]}")
        print(f"Nome: {barbeiro[1]}")
        print(f"Email: {barbeiro[2]}")
        print(f"Tipo: {barbeiro[3]}")
        print(f"Disponível: {barbeiro[4]}")
        print(f"Em atendimento: {barbeiro[5]}")
        print(f"Ocupado até: {barbeiro[6]}")
        print(f"Offline: {barbeiro[7]}")
        
        # Verificar freelancer perfil
        cursor.execute("""
            SELECT id FROM freelancers WHERE usuario_id = ?
        """, (barbeiro[0],))
        freelancer = cursor.fetchone()
        print(f"\nFreelancer perfil: {'Sim (ID: ' + str(freelancer[0]) + ')' if freelancer else 'NÃO ENCONTRADO'}")
        
        # Verificar especialidades
        if freelancer:
            cursor.execute("""
                SELECT tipo FROM especialidades_freelancer 
                WHERE freelancer_id = ?
            """, (freelancer[0],))
            especialidades = cursor.fetchall()
            print(f"Especialidades: {', '.join([e[0] for e in especialidades]) if especialidades else 'Nenhuma'}")
        
        # Verificar chamado 1
        cursor.execute("""
            SELECT c.id, c.cliente_id, c.servico_id, c.status, s.nome, s.categoria, s.duracao_minutos
            FROM chamados c
            LEFT JOIN servicos s ON c.servico_id = s.id
            WHERE c.id = 1
        """)
        chamado = cursor.fetchone()
        if chamado:
            print(f"\n=== Chamado #1 ===")
            print(f"Status: {chamado[3]}")
            print(f"Serviço: {chamado[4]} (categoria: {chamado[5]}, duração: {chamado[6]}min)")
        else:
            print("\n❌ Chamado #1 não encontrado!")
    else:
        print("❌ Barbeiro não encontrado!")
        
except Exception as e:
    print(f"❌ Erro: {e}")
    import traceback
    traceback.print_exc()
finally:
    conn.close()
