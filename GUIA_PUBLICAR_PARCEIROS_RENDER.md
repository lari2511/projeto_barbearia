# Guia rapido: publicar BarberMove para parceiros (rede publica)

Objetivo: deixar backend e APK acessiveis pela internet para quem esta em casa.

## 1) Preparar APK estavel

Na raiz do projeto:

```powershell
.\publicar_apk_publico.ps1 -ApiBaseUrl https://SEU-SERVICO.onrender.com
```

Isso garante um arquivo estavel em `APK_PRONTO/BarberMove.apk`.

## 2) Subir no Render (Blueprint)

1. Envie o projeto para o GitHub.
2. No Render, clique em New + > Blueprint.
3. Selecione o repositorio.
4. O Render vai ler `render.yaml` e criar os servicos automaticamente.

Observacoes importantes:
- `APK_DOWNLOAD_DIR=APK_PRONTO` ja esta configurado.
- CORS para app mobile ja esta configurado.

## 3) Variaveis obrigatorias no painel Render

Configure no servico `barbermove-api`:
- `SMTP_USER`
- `SMTP_PASSWORD`
- qualquer outra chave sensivel que voce use em producao

As demais ja estao no `render.yaml` e podem ser ajustadas depois.

## 4) Validar publicacao

Depois do deploy, teste no navegador:

- `https://SEU-SERVICO.onrender.com/health`
- `https://SEU-SERVICO.onrender.com/apk/info`
- `https://SEU-SERVICO.onrender.com/apk/latest`
- `https://SEU-SERVICO.onrender.com/apk/BarberMove.apk`
- `https://SEU-SERVICO.onrender.com/downloads/BarberMove.apk`

## 5) Link para compartilhar com parceiros

Use preferencialmente:

- `https://SEU-SERVICO.onrender.com/apk/latest`

Opcao com nome fixo:

- `https://SEU-SERVICO.onrender.com/apk/BarberMove.apk`

## 6) Checklist final de apresentacao

- Backend responde em `/health`
- APK baixa pelo link publico
- Frontend/web (se usar) aponta para API publica
- APK de release recompilado com URL de producao

## Problemas comuns

- 404 no APK: rode de novo `publicar_apk_publico.ps1` e faca commit do arquivo em `APK_PRONTO`.
- Erro CORS no app: confirme `ALLOWED_ORIGINS` no Render e redeploy.
- QR/PIX sem imagem: use codigo copia e cola (fallback ja implementado).
