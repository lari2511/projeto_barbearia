# BarberMove - Apps Nativos Android e iOS

## ✅ Configuração Completa!

O projeto foi configurado com sucesso para gerar apps nativos Android e iOS usando **Capacitor**.

### 📱 Estrutura Criada

```
barbermove/
├── android/              # Projeto Android nativo
├── ios/                  # Projeto iOS nativo (requer macOS)
├── resources/            # Ícones e splash screens
│   ├── icon.png         # Ícone 1024x1024
│   └── splash.png       # Splash 2732x2732
├── capacitor.config.json # Configuração do Capacitor
└── GUIA_ANDROID_IOS.md  # Documentação completa
```

### 🚀 Comandos Principais

```bash
# Desenvolvimento
npm run build              # Build do projeto web
npm run cap:sync          # Sincronizar com apps nativos
npm run cap:open:android  # Abrir no Android Studio
npm run cap:open:ios      # Abrir no Xcode (macOS)

# Produção
npm run android:build:debug   # APK para testes
npm run android:build         # APK para publicação
```

### 📖 Documentação Completa

Consulte o arquivo [GUIA_ANDROID_IOS.md](./GUIA_ANDROID_IOS.md) para:
- Instalação de pré-requisitos
- Como gerar APK para Android
- Como gerar IPA para iOS
- Publicação nas lojas (Google Play e App Store)
- Solução de problemas
- Checklist de publicação

### 🎯 Próximos Passos

1. **Personalizar Ícones**
   ```bash
   # Gerar ícones temporários
   python generate_app_icons.py
   
   # Ou adicionar seus próprios em resources/
   # Depois execute:
   npx capacitor-assets generate
   ```

2. **Configurar Android Studio**
   - Download: https://developer.android.com/studio
   - Instalar Android SDK
   - Configurar variáveis de ambiente

3. **Gerar APK Debug (para testar)**
   ```bash
   npm run android:build:debug
   ```
   APK gerado em: `android/app/build/outputs/apk/debug/`

4. **Testar no Celular**
   - Ative "Depuração USB" no Android
   - Conecte via USB
   - Execute: `adb install android/app/build/outputs/apk/debug/app-debug.apk`

### 🔑 Para Publicação (Produção)

1. **Criar Keystore** (primeira vez)
   ```bash
   keytool -genkey -v -keystore barbermove-release.keystore \
     -alias barbermove -keyalg RSA -keysize 2048 -validity 10000
   ```

2. **Configurar assinatura** em `android/app/build.gradle`

3. **Gerar APK Release**
   ```bash
   npm run android:build
   ```

4. **Publicar na Google Play Store**
   - Criar conta: https://play.google.com/console
   - Fazer upload do APK/AAB
   - Preencher informações
   - Enviar para revisão

### 📱 Especificações do App

- **Nome**: BarberMove
- **ID do Pacote**: com.barbermove.app
- **Plataformas**: Android e iOS
- **Tecnologia**: React + Vite + Capacitor

### 🆘 Ajuda

- Documentação detalhada: [GUIA_ANDROID_IOS.md](./GUIA_ANDROID_IOS.md)
- Capacitor Docs: https://capacitorjs.com/docs
- Android Developers: https://developer.android.com

---

**Pronto para começar! 🎉**
