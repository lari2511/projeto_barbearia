#!/usr/bin/env python3
from app.database import SessionLocal
from app import models

db = SessionLocal()
users = db.query(models.Usuario).all()

print(f'\n📊 Total usuários no banco: {len(users)}\n')

if len(users) == 0:
    print("❌ BANCO VAZIO!")
else:
    for u in users:
        print(f"  ✓ {u.email} ({u.tipo}) - ID: {u.id}")

db.close()
