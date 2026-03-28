"""Verificar e criar chamados de teste"""
import sqlite3
from datetime import datetime, timedelta

conn = sqlite3.connect('barbearia.db')
cursor = conn.cursor()

try:
    # 1. Verificar chamados existentes
    print("=== Verificando chamados existentes ===")
    cursor.execute("SELECT COUNT(*) FROM chamados")
    total = cursor.fetchone()[0]
    print(f"Total de chamados: {total}\n")
    
    if total > 0:
        cursor.execute("""
            SELECT id, cliente_id, barbeiro_id, servico_id, status, 
                   data_hora_inicio, data_hora_fim
            FROM chamados 
            LIMIT 5
        """)
        print("Últimos chamados:")
        for row in cursor.fetchall():
            print(f"  ID: {row[0]}, Cliente: {row[1]}, Barbeiro: {row[2]}, "
                  f"Serviço: {row[3]}, Status: {row[4]}")
    
    # 2. Buscar IDs dos usuários de teste
    print("\n=== Buscando usuários ===")
    cursor.execute("SELECT id, email, tipo FROM usuarios WHERE tipo IN ('cliente', 'barbeiro', 'barbearia')")
    usuarios = {}
    for row in cursor.fetchall():
        usuarios[row[2]] = usuarios.get(row[2], [])
        usuarios[row[2]].append({'id': row[0], 'email': row[1]})
        print(f"  {row[2]}: ID {row[0]} - {row[1]}")
    
    # 3. Buscar serviços disponíveis
    print("\n=== Buscando serviços ===")
    cursor.execute("SELECT id, nome, valor, barbearia_id FROM servicos WHERE ativo = 1 LIMIT 3")
    servicos = cursor.fetchall()
    print(f"Total de serviços ativos: {len(servicos)}")
    for s in servicos:
        print(f"  ID: {s[0]}, Nome: {s[1]}, Valor: R$ {s[2]}, Barbearia: {s[3]}")
    
    # 4. Criar serviço de teste se não existir
    if len(servicos) == 0:
        print("\n⚠️  Nenhum serviço encontrado. Criando serviço de teste...")
        
        # Buscar ou criar barbearia
        barbearia_id = None
        if 'barbearia' in usuarios and len(usuarios['barbearia']) > 0:
            barbearia_id = usuarios['barbearia'][0]['id']
        else:
            print("❌ Nenhuma barbearia encontrada!")
        
        if barbearia_id:
            cursor.execute("""
                INSERT INTO servicos (barbearia_id, nome, descricao, categoria, valor, duracao_minutos, ativo)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (barbearia_id, "Corte Masculino", "Corte tradicional", "corte", 35.0, 40, 1))
            
            cursor.execute("""
                INSERT INTO servicos (barbearia_id, nome, descricao, categoria, valor, duracao_minutos, ativo)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (barbearia_id, "Barba Completa", "Barba com navalha", "barba", 25.0, 30, 1))
            
            conn.commit()
            print("✅ Serviços de teste criados!")
            
            # Buscar novamente
            cursor.execute("SELECT id, nome, valor FROM servicos WHERE ativo = 1")
            servicos = cursor.fetchall()
    
    # 5. Criar chamados de teste
    if 'cliente' in usuarios and 'barbearia' in usuarios and len(servicos) > 0:
        print("\n=== Criando chamados de teste ===")
        
        cliente_id = usuarios['cliente'][0]['id']
        barbearia_id = usuarios['barbearia'][0]['id']
        servico_id = servicos[0][0]
        
        # Verificar se já existem chamados pendentes
        cursor.execute("""
            SELECT COUNT(*) FROM chamados 
            WHERE cliente_id = ? AND status = 'pendente'
        """, (cliente_id,))
        
        chamados_pendentes = cursor.fetchone()[0]
        
        if chamados_pendentes == 0:
            # Criar 3 chamados de teste
            agora = datetime.now()
            
            for i in range(3):
                inicio = agora + timedelta(hours=i+1)
                fim = inicio + timedelta(minutes=40)
                
                cursor.execute("""
                    INSERT INTO chamados 
                    (cliente_id, servico_id, barbearia_id, status, 
                     data_hora_inicio, data_hora_fim, data_agendamento)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (cliente_id, servico_id, barbearia_id, 'pendente',
                      inicio.strftime('%Y-%m-%d %H:%M:%S'),
                      fim.strftime('%Y-%m-%d %H:%M:%S'),
                      agora.strftime('%Y-%m-%d %H:%M:%S')))
            
            conn.commit()
            print(f"✅ Criados 3 chamados de teste para cliente ID {cliente_id}")
        else:
            print(f"ℹ️  Já existem {chamados_pendentes} chamados pendentes")
    
    # 6. Listar chamados finais
    print("\n=== Chamados cadastrados ===")
    cursor.execute("""
        SELECT c.id, u.nome, s.nome, c.status, c.data_hora_inicio
        FROM chamados c
        LEFT JOIN usuarios u ON u.id = c.cliente_id
        LEFT JOIN servicos s ON s.id = c.servico_id
        ORDER BY c.data_agendamento DESC
        LIMIT 5
    """)
    
    for row in cursor.fetchall():
        print(f"  ID: {row[0]} | Cliente: {row[1]} | Serviço: {row[2]} | "
              f"Status: {row[3]} | Horário: {row[4]}")
    
except Exception as e:
    print(f"❌ Erro: {e}")
    import traceback
    traceback.print_exc()
finally:
    conn.close()
