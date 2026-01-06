import sys

print("1. Importando database...")
from app.database import Base, engine, init_db, SessionLocal
print("   ✅ OK")

print("2. Importando models...")
from app import models
print("   ✅ OK")

print("3. Importando schemas...")
from app import schemas
print("   ✅ OK")

print("4. Importando routes...")
from app.routes import router
print("   ✅ OK")

print("5. Importando main...")
from app.main import app
print("   ✅ OK")

print("\n✅ Todos os imports funcionando!")
sys.exit(0)
