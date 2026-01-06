"""
Gera QR Code em imagem PNG para download do APK
"""
import qrcode
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

# Pegar IP local
ip = get_local_ip()
PORT = 8090
url = f"http://{ip}:{PORT}/BarberMove.apk"

print("\n" + "="*70)
print("📱 GERANDO QR CODE - BarberMove")
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

# Gerar imagem
img = qr.make_image(fill_color="black", back_color="white")

# Salvar imagem
img_path = "qrcode_barbermove.png"
img.save(img_path)

print(f"✅ QR Code salvo em: {os.path.abspath(img_path)}\n")
print("📋 INSTRUÇÕES:")
print("1. Conecte seu celular na MESMA rede WiFi que este PC")
print("2. Abra a câmera do celular")
print("3. Aponte para o QR Code que vai abrir")
print("4. Baixe e instale o APK\n")
print("="*70 + "\n")

# Abrir a imagem
import subprocess
if os.name == 'nt':  # Windows
    os.startfile(img_path)
else:  # Linux/Mac
    subprocess.call(['xdg-open', img_path])

print("🖼️  QR Code aberto! Escaneie com a câmera do celular.\n")
