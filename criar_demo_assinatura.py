"""Criar dados de demonstração para assinatura"""
import sqlite3
from datetime import datetime, timedelta

conn = sqlite3.connect('barbearia.db')
cursor = conn.cursor()

try:
    print("=== Criando dados de demo para assinatura ===\n")
    
    # 1. Buscar barbearia de teste
    cursor.execute("SELECT id, nome FROM usuarios WHERE email = 'allansiqueira06@gmail.com'")
    barbearia = cursor.fetchone()
    
    if not barbearia:
        print("❌ Barbearia não encontrada!")
    else:
        barbearia_id = barbearia[0]
        print(f"✅ Barbearia encontrada: ID {barbearia_id} - {barbearia[1]}")
        
        # 2. Criar assinatura ativa
        agora = datetime.now()
        vencimento = agora + timedelta(days=30)
        dia_venc = vencimento.day
        
        cursor.execute("""
            INSERT OR REPLACE INTO assinaturas_barbearia 
            (barbearia_id, cadeiras_ativas, quantidade_cadeiras, status, valor_mensalidade, 
             dia_vencimento, proximo_vencimento)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (barbearia_id, 2, 2, 'ativa', 54.00, dia_venc, vencimento.strftime('%Y-%m-%d %H:%M:%S')))
        
        print(f"✅ Assinatura criada: 2 cadeiras por R$ 54,00/mês")
        print(f"   Vencimento: {vencimento.strftime('%d/%m/%Y')}")
        
        # 3. Criar cadeiras vinculadas
        cursor.execute("DELETE FROM cadeiras WHERE barbearia_id = ?", (barbearia_id,))
        
        for i in range(1, 3):  # 2 cadeiras
            cursor.execute("""
                INSERT INTO cadeiras 
                (barbearia_id, numero, status, acionada_em, ocupada_em)
                VALUES (?, ?, ?, ?, ?)
            """, (barbearia_id, f"Cadeira {i}", "disponivel", None, None))
        
        print(f"✅ 2 cadeiras criadas e vinculadas à barbearia")
        
        conn.commit()
        print("\n=== Demo configurado com sucesso! ===")
        print("\n📋 Faça login como barbearia e vá na aba 'Assinatura'")
        
except Exception as e:
    print(f"❌ Erro: {e}")
    import traceback
    traceback.print_exc()
finally:
    conn.close()
