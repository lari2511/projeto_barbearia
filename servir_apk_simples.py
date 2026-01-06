"""
Servidor HTTP simples para compartilhar o APK via rede local
"""
import http.server
import socketserver
import socket
import os

def get_local_ip():
    """Pega o IP local da máquina"""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
    except:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip

PORT = 8090  # Mudado de 8080 para 8090

# Mudar para o diretório do APK
os.chdir('barbermove')

# Pegar IP local
ip = get_local_ip()
url = f"http://{ip}:{PORT}/BarberMove.apk"

print("\n" + "="*70)
print("📱 SERVIDOR APK - BarberMove")
print("="*70)
print(f"\n🌐 Seu IP Local: {ip}")
print(f"📦 Link do APK: {url}")
print(f"\n📋 INSTRUÇÕES:")
print(f"1. Conecte seu celular na MESMA rede WiFi que este PC")
print(f"2. Abra o navegador no celular (Chrome/Safari)")
print(f"3. Digite na barra de endereço: {url}")
print(f"4. Baixe e instale o APK")
print(f"\n⚠️  IMPORTANTE:")
print(f"   - Habilite 'Instalar apps de fontes desconhecidas' no Android")
print(f"   - Configurações > Segurança > Fontes desconhecidas")
print(f"\n🔴 Servidor rodando na porta {PORT}...")
print(f"📱 Acesse no celular: {url}")
print(f"\nPressione Ctrl+C para parar\n")
print("="*70 + "\n")

# Iniciar servidor HTTP
Handler = http.server.SimpleHTTPRequestHandler
with socketserver.TCPServer(("", PORT), Handler) as httpd:
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n\n✅ Servidor encerrado!")
