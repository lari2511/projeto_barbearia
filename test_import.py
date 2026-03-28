import sys
print("Testando imports...")

try:
    print("1. Importando models...")
    from app import models
    print("✅ Models OK")
except Exception as e:
    print(f"❌ Models: {e}")
    sys.exit(1)

try:
    print("2. Importando database...")
    from app import database
    print("✅ Database OK")
except Exception as e:
    print(f"❌ Database: {e}")
    sys.exit(1)

try:
    print("3. Importando schemas...")
    from app import schemas
    print("✅ Schemas OK")
except Exception as e:
    print(f"❌ Schemas: {e}")
    sys.exit(1)

try:
    print("4. Importando routes (pode demorar)...")
    import signal
    
    def timeout_handler(signum, frame):
        raise TimeoutError("Import travou!")
    
    # Timeout de 5 segundos
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(5)
    
    from app import routes
    signal.alarm(0)  # Cancelar alarm
    print("✅ Routes OK")
except TimeoutError as e:
    print(f"❌ Routes travou: {e}")
    sys.exit(1)
except Exception as e:
    print(f"❌ Routes: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n✅ Todos os imports OK!")
