# 📱 Guia Completo - Apps Nativos Android e iOS

Este guia explica como compilar e gerar os aplicativos nativos **BarberMove** para Android (APK) e iOS (IPA).

---

## 📋 Pré-requisitos

### Para Android:
- ✅ **Node.js** (já instalado)
- ✅ **Java JDK 17+** ([Download](https://adoptium.net/))
- ✅ **Android Studio** ([Download](https://developer.android.com/studio))
- ✅ **Android SDK** (instalado via Android Studio)
- ✅ **Gradle** (incluído no Android Studio)

### Para iOS (apenas macOS):
- ✅ **Xcode 14+** (Mac App Store)
- ✅ **CocoaPods** (`sudo gem install cocoapods`)
- ✅ **Conta Apple Developer** (para distribuição)

---

## 🚀 Comandos Disponíveis

### Desenvolvimento
```bash
# Build do projeto web
npm run build

# Sincronizar código web com apps nativos
npm run cap:sync

# Abrir projeto Android no Android Studio
npm run cap:open:android

# Abrir projeto iOS no Xcode (macOS)
npm run cap:open:ios

# Rodar app em dispositivo/emulador Android
npm run cap:run:android

# Rodar app em dispositivo/simulador iOS (macOS)
npm run cap:run:ios
```

### Produção
```bash
# Gerar APK Debug (para testes)
npm run android:build:debug

# Gerar APK Release (para publicação)
npm run android:build
```

---

## 🤖 Como Gerar APK para Android

### Passo 1: Configurar Ambiente Android

1. **Instalar Android Studio**
   - Download: https://developer.android.com/studio
   - Durante instalação, marque "Android SDK" e "Android Virtual Device"

2. **Configurar Variáveis de Ambiente**
   ```powershell
   # Adicionar ao PATH do Windows:
   C:\Users\[SeuUsuario]\AppData\Local\Android\Sdk\platform-tools
   C:\Users\[SeuUsuario]\AppData\Local\Android\Sdk\tools
   ```

3. **Instalar Java JDK 17**
   - Download: https://adoptium.net/
   - Configurar JAVA_HOME no Windows

### Passo 2: Gerar Keystore (apenas primeira vez)

```bash
# Criar keystore para assinar o app
keytool -genkey -v -keystore barbermove-release.keystore -alias barbermove -keyalg RSA -keysize 2048 -validity 10000

# Responda as perguntas e GUARDE A SENHA!
```

Mova o arquivo `barbermove-release.keystore` para `c:\projeto_barbearia\barbermove\android\`

### Passo 3: Configurar Assinatura

Edite o arquivo `android/app/build.gradle` e adicione (substitua pelas suas senhas):

```gradle
android {
    ...
    signingConfigs {
        release {
            storeFile file('../../barbermove-release.keystore')
            storePassword 'SUA_SENHA_AQUI'
            keyAlias 'barbermove'
            keyPassword 'SUA_SENHA_AQUI'
        }
    }
    buildTypes {
        release {
            signingConfig signingConfigs.release
            minifyEnabled false
            proguardFiles getDefaultProguardFile('proguard-android.txt'), 'proguard-rules.pro'
        }
    }
}
```

### Passo 4: Build do APK

```bash
# APK Debug (não precisa keystore)
npm run android:build:debug

# APK Release (assinado, pronto para Google Play)
npm run android:build
```

**APK gerado em:**
- Debug: `barbermove/android/app/build/outputs/apk/debug/app-debug.apk`
- Release: `barbermove/android/app/build/outputs/apk/release/app-release.apk`

### Passo 5: Testar APK

```bash
# Instalar no dispositivo conectado via USB
adb install android/app/build/outputs/apk/release/app-release.apk

# Ou transfira o arquivo .apk para o celular e instale manualmente
```

---

## 🍎 Como Gerar IPA para iOS (macOS)

### Passo 1: Configurar Ambiente iOS

1. **Instalar Xcode**
   ```bash
   # Via Mac App Store ou:
   xcode-select --install
   ```

2. **Instalar CocoaPods**
   ```bash
   sudo gem install cocoapods
   ```

3. **Instalar dependências nativas**
   ```bash
   cd ios/App
   pod install
   ```

### Passo 2: Configurar Certificados

1. Entre em https://developer.apple.com/account
2. Crie um **App ID** para `com.barbermove.app`
3. Gere **Certificados** e **Provisioning Profiles**
4. Importe no Xcode via Preferences → Accounts

### Passo 3: Build do IPA

```bash
# Abrir no Xcode
npm run cap:open:ios

# No Xcode:
# 1. Selecione "Any iOS Device" como destino
# 2. Product → Archive
# 3. Após o build, clique "Distribute App"
# 4. Escolha "Ad Hoc" ou "App Store"
# 5. Siga o assistente e exporte o .ipa
```

**IPA gerado em:**
`~/Library/Developer/Xcode/Archives/`

### Passo 4: Testar IPA

```bash
# Instalar via Xcode em dispositivo conectado
# Ou usar ferramentas como TestFlight
```

---

## 🎨 Customizar Ícones e Splash Screens

### Opção 1: Automática (Recomendada)

1. **Adicione suas imagens:**
   - Ícone: `resources/icon.png` (1024x1024px, PNG)
   - Splash: `resources/splash.png` (2732x2732px, PNG)

2. **Gere os assets:**
   ```bash
   npm install @capacitor/assets --save-dev
   npx capacitor-assets generate
   ```

### Opção 2: Manual

- Android: Substitua os arquivos em `android/app/src/main/res/`
- iOS: Substitua em `ios/App/App/Assets.xcassets/`

---

## 📦 Publicar nas Lojas

### Google Play Store (Android)

1. **Criar conta**: https://play.google.com/console
2. **Gerar App Bundle** (recomendado):
   ```bash
   cd android
   ./gradlew bundleRelease
   ```
   Arquivo gerado: `android/app/build/outputs/bundle/release/app-release.aab`

3. **Upload**: Play Console → Criar App → Upload do .aab
4. **Preencher**: Screenshots, descrição, categoria, etc.
5. **Publicar**: Enviar para revisão

### Apple App Store (iOS)

1. **Criar conta**: https://developer.apple.com ($99/ano)
2. **App Store Connect**: Criar novo app
3. **Xcode**: Product → Archive → Distribute → App Store
4. **Upload**: Através do Xcode ou Application Loader
5. **Preencher**: Metadados no App Store Connect
6. **Enviar para revisão**

---

## 🔧 Solução de Problemas

### Android

**Erro: "SDK location not found"**
```bash
# Criar arquivo android/local.properties:
sdk.dir=C:\\Users\\[SeuUsuario]\\AppData\\Local\\Android\\Sdk
```

**Erro: "Gradle build failed"**
```bash
cd android
./gradlew clean
./gradlew build
```

**Erro: "JAVA_HOME not set"**
```powershell
# Configurar variável de ambiente:
setx JAVA_HOME "C:\Program Files\Eclipse Adoptium\jdk-17.0.x"
```

### iOS

**Erro: "pod install failed"**
```bash
cd ios/App
pod repo update
pod install
```

**Erro: "Code signing error"**
- Configure certificados no Xcode (Preferences → Accounts)
- Ou desabilite assinatura automática temporariamente

---

## 📱 Testar em Dispositivos Reais

### Android
```bash
# Habilitar "Depuração USB" no celular
# Conectar via USB
adb devices
npm run cap:run:android
```

### iOS
```bash
# Conectar iPhone via USB
# Confiar no computador no iPhone
npm run cap:run:ios
```

---

## 🔄 Workflow de Atualização

Sempre que fizer mudanças no código:

```bash
# 1. Build do projeto web
npm run build

# 2. Sincronizar com apps nativos
npx cap sync

# 3. Abrir IDE para testar
npm run cap:open:android  # ou cap:open:ios

# 4. Gerar nova versão
npm run android:build  # ou build via Xcode
```

---

## 📝 Checklist de Publicação

- [ ] Testar app em dispositivos reais
- [ ] Atualizar versão em `package.json`
- [ ] Atualizar `versionCode` e `versionName` (Android)
- [ ] Atualizar `CFBundleVersion` (iOS)
- [ ] Gerar ícones e splash screens
- [ ] Assinar app com certificados de produção
- [ ] Criar screenshots para lojas
- [ ] Preparar descrição e palavras-chave
- [ ] Definir política de privacidade
- [ ] Gerar APK/AAB ou IPA assinado
- [ ] Upload nas lojas
- [ ] Aguardar aprovação (1-7 dias)

---

## 🆘 Recursos Adicionais

- **Documentação Capacitor**: https://capacitorjs.com/docs
- **Android Developers**: https://developer.android.com
- **Apple Developer**: https://developer.apple.com
- **Guia PWA**: Ver arquivo `GUIA_PWA.md`

---

## 🎯 Próximos Passos

1. **Instalar Android Studio** e configurar SDK
2. **Adicionar ícones** em `resources/icon.png`
3. **Gerar APK debug** para testar: `npm run android:build:debug`
4. **Testar em dispositivo** físico
5. **Criar keystore** e gerar APK release
6. **Publicar na Google Play Store**

Para iOS, repita os passos com Xcode em um macOS.

---

**Dúvidas?** Consulte a documentação ou entre em contato!
