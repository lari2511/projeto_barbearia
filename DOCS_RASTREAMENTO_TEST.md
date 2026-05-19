Validação Rápida — Rastreamento (status-based gating)

Objetivo
- Confirmar que o mapa só aparece para cliente/barbeario após o barbeiro aceitar o chamado.

Ambiente (local)
- Backend: http://127.0.0.1:8000 (uvicorn)
- Frontend: http://localhost:5174 (Vite)
- Túnel público (ngrok): https://unpuritan-gastrocnemial-charlyn.ngrok-free.dev

Comandos úteis
- Iniciar backend:
```
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir C:/projeto_barbearia --host 127.0.0.1 --port 8000
```
- Iniciar frontend (pasta `barbermove`):
```
cd barbermove
npm run dev
```
- Iniciar ngrok (se necessário):
```
ngrok http 8000 --log stdout --pooling-enabled
```
- Rodar testes E2E locais:
```
$env:PYTHONPATH='C:\projeto_barbearia'; .\.venv\Scripts\python.exe test_e2e_status_gating.py
```
- Rodar testes E2E via ngrok (exemplo):
```
$env:PYTHONPATH='C:\projeto_barbearia'; .\.venv\Scripts\python.exe -c "import test_e2e_status_gating as t; t.BASE_URL='https://unpuritan-gastrocnemial-charlyn.ngrok-free.dev/api/v1'; t.main()"
```

Checklist de QA (rápido)
- [ ] Backend rodando em `127.0.0.1:8000`
- [ ] Frontend rodando em `localhost:5174`
- [ ] ngrok ativo e apontando para `127.0.0.1:8000`
- [ ] Criar/chamar um chamado PENDENTE (usar `test_e2e_status_gating.py` ou criar manualmente)
- [ ] Como cliente: acessar chamado → ver `mostrar_mapa: false` (UI mostra "Aguardando aceite")
- [ ] Como barbeiro: aceitar chamado → backend deve retornar `confirmado` e broadcast via WebSocket
- [ ] Como cliente: atualizar/abrir rastreamento → ver `mostrar_mapa: true` e coordenadas

Notas
- Se WebSocket falhar no navegador externo, verifique:
  - `VITE_WS_URL` em `barbermove/.env.local` (usar `ws://localhost:8000/ws/notificacoes` localmente)
  - Se usar ngrok, use `wss://<tunnel>/ws/notificacoes` (o projeto já tenta mapear)

Resultado do último teste automático
- `test_e2e_status_gating.py` executado contra o túnel ngrok público: 4/4 testes passaram.

Próximo passo manual recomendado
- Abrir `https://unpuritan-gastrocnemial-charlyn.ngrok-free.dev` em dispositivo externo (celular) e reproduzir o fluxo para validar WebSocket/HTTPS em redes externas.
