# 🚀 GUIA DE DEPLOY - BarberMove

## 📋 Pré-requisitos Completos

### Para ir ao público você precisa:
- [ ] Domínio próprio (ex: barbermove.com.br)
- [ ] Conta em serviço de hospedagem (recomendado: Railway, Heroku, AWS, ou VPS)
- [ ] Conta Google/Gmail para SMTP (emails)
- [ ] Chave API MercadoPago ou Stripe (pagamentos - opcional no início)
- [ ] Conta Google Play Console ($25 taxa única) - para Android
- [ ] Conta Apple Developer ($99/ano) - para iOS

---

## 🔧 PASSO 1: Configurar Variáveis de Ambiente

### Backend (.env na raiz do projeto)

```bash
# Gere uma chave forte (32+ caracteres aleatórios)
SECRET_KEY=SuaChaveSecretaForteAqui123456789AbcDefGhIjKl

# URLs permitidas (seu domínio em produção)
ALLOWED_ORIGINS=https://barbermove.com.br,https://www.barbermove.com.br

# Database (PostgreSQL recomendado em produção)
DATABASE_URL=postgresql://usuario:senha@host:5432/barbermove_db

# Email (Gmail - crie senha de app em https://myaccount.google.com/apppasswords)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=seuemail@gmail.com
SMTP_PASSWORD=sua_senha_app_16_digitos
SMTP_FROM=noreply@barbermove.com.br

# Verificação
REQUIRE_EMAIL_VERIFIED=1
VERIFICATION_LINK_BASE=https://barbermove.com.br/verificar

# URLs
FRONTEND_URL=https://barbermove.com.br
API_URL=https://api.barbermove.com.br
```

### Frontend (.env na pasta barbermove/)

```bash
VITE_API_URL=https://api.barbermove.com.br
VITE_WS_URL=wss://api.barbermove.com.br/ws/notificacoes
VITE_DEV_MODE=false
```

---

## 🌐 PASSO 2: Deploy do Backend (API)

### Opção A: Railway (Recomendado - Fácil)

1. Acesse [railway.app](https://railway.app) e faça login com GitHub
2. Clique "New Project" → "Deploy from GitHub repo"
3. Selecione seu repositório `projeto_barbearia`
4. Configure as variáveis de ambiente no painel Railway
5. Railway detecta Python automaticamente e faz deploy

**Comandos que o Railway executa:**
```bash
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

6. Railway fornece URL: `https://seu-projeto.up.railway.app`

### Opção B: Heroku

```bash
# Instale Heroku CLI
# Crie Procfile na raiz:
echo "web: uvicorn app.main:app --host 0.0.0.0 --port $PORT" > Procfile

# Deploy
heroku login
heroku create barbermove-api
heroku addons:create heroku-postgresql:mini
heroku config:set SECRET_KEY=sua_chave_aqui
heroku config:set ALLOWED_ORIGINS=https://barbermove.com.br
# ... configure todas as variáveis

git push heroku main
```

### Opção C: VPS (DigitalOcean, AWS EC2)

```bash
# No servidor
sudo apt update
sudo apt install python3-pip python3-venv nginx

# Clone projeto
git clone seu-repo
cd projeto_barbearia
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Crie arquivo .env com suas configurações

# Instale supervisor para manter rodando
sudo apt install supervisor

# Configure nginx como proxy reverso
# /etc/nginx/sites-available/barbermove
server {
    listen 80;
    server_name api.barbermove.com.br;
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}

# SSL com Let's Encrypt
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d api.barbermove.com.br
```

---

## 🎨 PASSO 3: Deploy do Frontend

### Opção A: Vercel (Recomendado - Grátis)

1. Acesse [vercel.com](https://vercel.com)
2. Importe repositório GitHub
3. Configure:
   - **Root Directory**: `barbermove`
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`
4. Configure variáveis de ambiente
5. Deploy automático!

### Opção B: Netlify

```bash
cd barbermove
npm run build

# Instale Netlify CLI
npm install -g netlify-cli
netlify login
netlify deploy --prod --dir=dist
```

### Opção C: Junto com backend (Nginx)

```bash
# Build do frontend
cd barbermove
npm install
npm run build

# Copie dist/ para /var/www/barbermove
sudo cp -r dist/* /var/www/barbermove/

# Configure nginx
server {
    listen 80;
    server_name barbermove.com.br;
    root /var/www/barbermove;
    index index.html;
    
    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

---

## 📱 PASSO 4: Gerar APK Final de Produção

```bash
cd barbermove

# 1. Configure API_URL de produção no .env
echo "VITE_API_URL=https://api.barbermove.com.br" > .env
echo "VITE_WS_URL=wss://api.barbermove.com.br/ws/notificacoes" >> .env

# 2. Build do frontend
npm run build

# 3. Sincronize com Capacitor
npx cap sync android

# 4. Abra Android Studio
npx cap open android

# 5. No Android Studio:
# - Build > Generate Signed Bundle / APK
# - Escolha APK
# - Crie keystore (guarde senha!) ou use existente
# - Build: release
# - APK estará em: android/app/release/app-release.apk
```

---

## 🏪 PASSO 5: Publicar na Google Play

1. **Crie conta**: [play.google.com/console](https://play.google.com/console) ($25 taxa única)

2. **Prepare assets**:
   - Ícone 512x512px
   - Screenshots (mínimo 2)
   - Feature graphic 1024x500px
   - Descrição curta (80 caracteres)
   - Descrição completa
   - Política de privacidade (URL)

3. **Classificação**:
   - Preencha questionário de conteúdo
   - Classificação etária

4. **Upload APK**:
   - Production > Create new release
   - Upload app-release.apk
   - Preencha changelog
   - Review e publicar

5. **Aguarde aprovação** (1-3 dias)

---

## 🍎 PASSO 6: Publicar na App Store (iOS)

```bash
# 1. No Mac, abra projeto iOS
npx cap open ios

# 2. No Xcode:
# - Configure Bundle ID único
# - Configure provisioning profile
# - Product > Archive
# - Distribute App > App Store Connect
```

1. **Crie conta**: [developer.apple.com](https://developer.apple.com) ($99/ano)
2. **App Store Connect**: Crie novo app
3. **Preencha informações** (similar ao Google Play)
4. **Upload build** via Xcode
5. **Submit for review**
6. **Aguarde aprovação** (2-7 dias)

---

## ✅ CHECKLIST PRÉ-LANÇAMENTO

### Segurança
- [ ] SECRET_KEY forte e única
- [ ] CORS configurado (sem *)
- [ ] HTTPS habilitado (SSL)
- [ ] Senhas hasheadas (bcrypt ✅)
- [ ] Rate limiting ativado
- [ ] Variáveis sensíveis em .env (não no código)

### Funcionalidades
- [ ] Todos testes passando
- [ ] Sistema de pagamento testado
- [ ] Emails sendo enviados
- [ ] Push notifications funcionando
- [ ] Geolocalização precisa
- [ ] Chat em tempo real estável

### Legal
- [ ] Termos de Uso redigidos
- [ ] Política de Privacidade (LGPD)
- [ ] Página "Sobre" e "Contato"
- [ ] CNPJ da empresa (se aplicável)

### Performance
- [ ] Imagens otimizadas
- [ ] Frontend minificado
- [ ] Banco de dados indexado
- [ ] Logs de erro configurados (Sentry)
- [ ] Monitoramento ativo

### Marketing
- [ ] Google Analytics configurado
- [ ] Meta tags SEO
- [ ] Landing page
- [ ] Redes sociais criadas
- [ ] Vídeo demonstração

---

## 📊 Pós-Deploy: Monitoramento

### Logs e Erros
```bash
# Instale Sentry para rastreamento de erros
pip install sentry-sdk[fastapi]
```

### Analytics
- Google Analytics no frontend
- Mixpanel ou Amplitude para eventos

### Backups
```bash
# PostgreSQL - backup diário
pg_dump $DATABASE_URL > backup_$(date +%Y%m%d).sql
```

---

## 🆘 Troubleshooting Comum

### Erro: CORS blocked
- Verifique ALLOWED_ORIGINS no .env
- Certifique-se que frontend usa HTTPS se backend usa

### Erro: Database connection
- Confirme DATABASE_URL correto
- Verifique se PostgreSQL permite conexões externas

### Erro: Email não envia
- Verifique SMTP_PASSWORD (senha de app, não senha normal)
- Teste com: [https://www.gmass.co/smtp-test](https://www.gmass.co/smtp-test)

### APK não instala
- Verifique se é build release (não debug)
- Confirme assinatura digital

---

## 💰 Custos Estimados

| Serviço | Custo Mensal | Notas |
|---------|--------------|-------|
| Railway/Heroku | $5-20 | Backend |
| Vercel | Grátis | Frontend |
| PostgreSQL | $5-15 | Database |
| Domínio | $10/ano | .com.br |
| SSL | Grátis | Let's Encrypt |
| Google Play | $25 (único) | Publicação Android |
| Apple Dev | $99/ano | Publicação iOS |
| **TOTAL INICIAL** | **~$20-40/mês** | + $124 inicial |

---

## 🚀 Próximos Passos AGORA

1. **Teste local completo** - garanta que tudo funciona
2. **Escolha hospedagem** - Railway para começar
3. **Configure .env produção** - chaves fortes
4. **Deploy backend** - Railway/Heroku
5. **Deploy frontend** - Vercel
6. **Teste em produção** - crie conta, faça agendamento
7. **Gere APK release** - Android Studio
8. **Crie conta Google Play** - $25
9. **Upload APK** - primeira versão
10. **Marketing** - divulgue!

---

**Quer que eu ajude com algum passo específico?** 🎯
