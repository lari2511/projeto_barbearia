import psycopg2
import sys

try:
    conn = psycopg2.connect(
        host='localhost',
        database='barbermovie',
        user='postgres',
        password='postgres'
    )
    cur = conn.cursor()
    
    cur.execute("ALTER TABLE cadeiras ADD COLUMN acionada_em TIMESTAMP")
    print("Added acionada_em")
except Exception as e:
    print("acionada_em error: " + str(type(e).__name__))

try:
    cur.execute("ALTER TABLE cadeiras ADD COLUMN acionada_por_id INTEGER REFERENCES usuarios(id)")
    print("Added acionada_por_id")
except Exception as e:
    print("acionada_por_id error: " + str(type(e).__name__))

try:
    conn.commit()
    print("Committed")
except:
    pass

try:
    conn.close()
except:
    pass
