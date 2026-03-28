#!/usr/bin/env python
import sys
import time

print("Iniciando diagnóstico...")

# Teste 1: Models
print("\n1. Importando models...", flush=True)
start = time.time()
try:
    from app import models
    print(f"✅ Models OK ({time.time()-start:.2f}s)", flush=True)
except Exception as e:
    print(f"❌ Erro: {e}", flush=True)
    sys.exit(1)

# Teste 2: Database
print("\n2. Importando database...", flush=True)
start = time.time()
try:
    from app import database
    print(f"✅ Database OK ({time.time()-start:.2f}s)", flush=True)
except Exception as e:
    print(f"❌ Erro: {e}", flush=True)
    sys.exit(1)

# Teste 3: Schemas
print("\n3. Importando schemas...", flush=True)
start = time.time()
try:
    from app import schemas
    print(f"✅ Schemas OK ({time.time()-start:.2f}s)", flush=True)
except Exception as e:
    print(f"❌ Erro: {e}", flush=True)
    sys.exit(1)

# Teste 4: Routes (pode travar aqui)
print("\n4. Importando routes... (pode demorar)", flush=True)
start = time.time()
try:
    import app.routes
    elapsed = time.time()-start
    if elapsed > 5:
        print(f"⚠️ Routes LENTO ({elapsed:.2f}s) - pode ter problema!", flush=True)
    else:
        print(f"✅ Routes OK ({elapsed:.2f}s)", flush=True)
except Exception as e:
    print(f"❌ Erro: {e}", flush=True)
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Teste 5: Main
print("\n5. Importando app.main...", flush=True)
start = time.time()
try:
    from app.main import app
    print(f"✅ App.main OK ({time.time()-start:.2f}s)", flush=True)
except Exception as e:
    print(f"❌ Erro: {e}", flush=True)
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n✅ TODOS OS IMPORTS OK!")
