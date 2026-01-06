"""
Servidor HTTP com QR Code para compartilhar o APK
"""
import http.server
import socketserver
import socket
import os
import qrcode
from io import BytesIO

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

PORT = 8090

# Mudar para o diretório do APK
os.chdir('barbermove')

# Pegar IP local
ip = get_local_ip()
url = f"http://{ip}:{PORT}/BarberMove.apk"

# Gerar QR Code
print("\n" + "="*70)
print("📱 SERVIDOR APK - BarberMove")
print("="*70 + "\n")

print(f"🌐 Seu IP Local: {ip}")
print(f"📦 Link do APK: {url}\n")

# Criar QR Code
qr = qrcode.QRCode(
    version=1,
    error_correction=qrcode.constants.ERROR_CORRECT_L,
    box_size=10,
    border=4,
)
qr.add_data(url)
qr.make(fit=True)

# Exibir QR Code no terminal
print("📱 QR CODE - Escaneie com a câmera do celular:\n")
qr.print_ascii(invert=True)

print("\n" + "="*70)
print("📋 INSTRUÇÕES:")
print("1. Conecte seu celular na MESMA rede WiFi que este PC")
print("2. Escaneie o QR Code acima com a câmera do celular")
print("   OU")
print(f"   Digite no navegador: {url}")
print("3. Baixe e instale o APK")
print("\n⚠️  IMPORTANTE:")
print("   - Habilite 'Instalar apps de fontes desconhecidas' no Android")
print("   - Configurações > Segurança > Fontes desconhecidas")
print("="*70 + "\n")

print(f"🔴 Servidor rodando na porta {PORT}...")
print(f"📱 Escaneie o QR Code ou acesse: {url}")
print("\nPressione Ctrl+C para parar\n")
print("="*70 + "\n")

# Iniciar servidor
Handler = http.server.SimpleHTTPRequestHandler
with socketserver.TCPServer(("", PORT), Handler) as httpd:
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n\n✅ Servidor encerrado!")
