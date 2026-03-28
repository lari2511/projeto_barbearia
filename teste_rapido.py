#!/usr/bin/env python
print("1. Importando database...", flush=True)
from app.database import SessionLocal
print("OK", flush=True)

print("2. Importando models...", flush=True)
from app import models
print("OK", flush=True)

print("3. Importando schemas...", flush=True)
from app import schemas
print("OK", flush=True)

print("4. Testando query simples...", flush=True)
db = SessionLocal()
count = db.query(models.Usuario).count()
print(f"OK - {count} usuários", flush=True)
db.close()

print("\n✅ Tudo OK! Backend deve funcionar.")
