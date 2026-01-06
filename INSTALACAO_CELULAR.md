# 📱 GUIA: Como Instalar o BarberMove no Celular

## 🚀 3 Formas de Instalar

---

### ✅ **OPÇÃO 1: Servidor Local (Recomendado)**

**Passo a passo:**

1. **No PC, execute:**
```powershell
cd C:\projeto_barbearia
python servir_apk.py
```

2. **Conecte o celular na MESMA rede WiFi do PC**

3. **Vai aparecer um link como:**
```
http://192.168.1.100:8080/BarberMove.apk
```

4. **No celular:**
   - Abra o navegador (Chrome/Safari)
   - Digite o link mostrado
   - Baixe o APK
   - Instale

5. **Se pedir permissão:**
   - Vá em: `Configurações > Segurança`
   - Habilite: `Instalar apps de fontes desconhecidas`
   - Volte e instale o APK

---

### 🌐 **OPÇÃO 2: Upload para Servidor Online**

#### **A. Google Drive**
1. Faça upload do `BarberMove.apk` para o Google Drive
2. Clique com botão direito > Compartilhar
3. Altere para "Qualquer pessoa com o link"
4. Copie o link e envie para o celular
5. Baixe e instale

#### **B. WeTransfer (Até 2GB grátis)**
1. Acesse: https://wetransfer.com
2. Faça upload do APK
3. Pegue o link gerado
4. Envie para o celular

#### **C. File.io (Upload temporário)**
```powershell
# No PowerShell:
cd C:\projeto_barbearia\barbermove
curl -F "file=@BarberMove.apk" https://file.io
```
Vai retornar um link para download.

---

### 📧 **OPÇÃO 3: Enviar por Email/WhatsApp**

1. **Comprimir o APK (opcional):**
```powershell
Compress-Archive -Path "C:\projeto_barbearia\barbermove\BarberMove.apk" -DestinationPath "BarberMove.zip"
```

2. **Enviar:**
   - Email: anexar o arquivo
   - WhatsApp Web: enviar como documento
   - Telegram: enviar como arquivo

3. **No celular:**
   - Baixe o arquivo
   - Instale

---

## ⚙️ **Configurações Importantes**

### **1. Habilitar Instalação de Apps**

**Android 8.0+:**
- `Configurações > Apps > Acesso especial > Instalar apps desconhecidos`
- Selecione o navegador/gerenciador de arquivos
- Habilite a opção

**Android 7.0 e anterior:**
- `Configurações > Segurança`
- Habilite `Fontes desconhecidas`

### **2. Conectar ao Backend**

⚠️ **IMPORTANTE:** O app precisa se conectar ao servidor backend!

**Se você estiver na mesma rede WiFi:**

O app deve estar configurado para:
```
http://SEU_IP_LOCAL:8000
```

**Para descobrir seu IP:**
```powershell
ipconfig
# Procure por "IPv4" na sua rede WiFi
```

**Editar URL no app:**
- Abra: `barbermove/src/App.jsx`
- Procure por: `const API_URL`
- Altere para: `http://192.168.1.X:8000/api/v1`
- Recompile: `npm run build && npx cap sync`

---

## 🔧 **Recompilar APK (Se Necessário)**

Se você fez mudanças no código:

```powershell
cd C:\projeto_barbearia\barbermove

# 1. Build do React
npm run build

# 2. Sync com Capacitor
npx cap sync

# 3. Compilar APK
cd android
.\gradlew assembleDebug

# APK estará em:
# android/app/build/outputs/apk/debug/app-debug.apk
```

---

## 📱 **Testando o App**

### **Backend deve estar rodando:**
```powershell
cd C:\projeto_barbearia
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

**`--host 0.0.0.0`** permite acesso de outros dispositivos na rede!

### **Testar conexão:**
No celular, abra o navegador e acesse:
```
http://SEU_IP:8000/docs
```

Se abrir a documentação da API, está funcionando! ✅

---

## 🐛 **Troubleshooting**

### **"Não consigo baixar o APK"**
- Verifique se está na mesma rede WiFi
- Desative VPN no PC e celular
- Tente outro navegador

### **"App não conecta ao backend"**
- Backend está rodando? (`uvicorn ... --host 0.0.0.0`)
- Firewall bloqueando? (desabilite temporariamente)
- IP correto no app?

### **"Erro ao instalar APK"**
- Habilite "Fontes desconhecidas"
- Espaço insuficiente? Libere espaço
- APK corrompido? Baixe novamente

---

## 🚀 **Método Mais Rápido (AGORA)**

Execute no PC:
```powershell
cd C:\projeto_barbearia
python servir_apk.py
```

Escaneie o QR Code que aparece ou digite o link no celular! 📱
