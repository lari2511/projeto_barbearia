import psycopg2
import os
os.environ['PYTHONIOENCODING'] = 'utf-8'

DB_CONFIG = {
    'host': 'localhost',
    'database': 'barbermovie',
    'user': 'postgres',
    'password': 'postgres',
    'port': 5432
}

try:
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    print("OK - Connected to database")
    
    try:
        cur.execute("""
            ALTER TABLE cadeiras 
            ADD COLUMN acionada_em TIMESTAMP NULL DEFAULT NULL;
        """)
        print("OK - Column 'acionada_em' added")
    except psycopg2.Error as e:
        if "already exists" in str(e):
            print("WARN - Column 'acionada_em' already exists")
        else:
            print("ERROR - " + str(e))
    
    try:
        cur.execute("""
            ALTER TABLE cadeiras 
            ADD COLUMN acionada_por_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL;
        """)
        print("OK - Column 'acionada_por_id' added")
    except psycopg2.Error as e:
        if "already exists" in str(e):
            print("WARN - Column 'acionada_por_id' already exists")
        else:
            print("ERROR - " + str(e))
    
    conn.commit()
    print("OK - Database schema updated!")
    
    cur.execute("""
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_name = 'cadeiras' 
        AND column_name IN ('acionada_em', 'acionada_por_id');
    """)
    
    colunas = cur.fetchall()
    print("OK - Columns verified:")
    for col_name, data_type in colunas:
        print("   - " + col_name + ": " + data_type)
    
    cur.close()
    conn.close()
    
except psycopg2.Error as e:
    print("ERROR - " + str(e))
except Exception as e:
    print("ERROR - " + str(e))
