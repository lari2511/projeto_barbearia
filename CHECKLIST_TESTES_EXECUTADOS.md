# Checklist de Testes Executados - BarberMove

Data: 2026-02-13

## Ambiente
- Workspace: c:\projeto_barbearia
- Frontend: barbermove
- Backend: FastAPI

## Execucoes Automatizadas
- [x] Build do frontend (Vite) - OK

## Testes Manuais (pendentes)
- [ ] Registro de cliente
- [ ] Registro de barbeiro (documentos + portfolio)
- [ ] Registro de barbearia (documentos)
- [ ] Login (cliente, barbeiro, barbearia)
- [ ] Upload de foto de perfil
- [ ] Upload de portfolio (barbeiro)
- [ ] Agendamento (cliente -> barbeiro)
- [ ] Aprovar/Rejeitar agendamento (barbeiro e barbearia)
- [ ] Pagamento PIX (geracao de QR)
- [ ] Notificacoes em tempo real
- [ ] Geolocalizacao
- [ ] PWA (instalacao e offline)
- [ ] Console limpo (sem logs em producao)

## Observacoes
- O build do frontend foi executado via `npm --prefix barbermove run build`.
- Para testes manuais, seguir o roteiro em GUIA_TESTES_FINAL.md.
