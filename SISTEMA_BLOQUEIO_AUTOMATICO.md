"""
Guia de Implementação do Sistema de Bloqueio Automático
========================================================

OBJETIVO:
- Bloquear barbearias que não pagarem mensalidade
- Desbloquear automaticamente ao pagar
- Cliente sempre pode pagar
- Barbeiro sempre pode receber

COMPONENTES IMPLEMENTADOS:
==========================

1. ✅ Modelo de Dados (app/models.py)
   - Barbearia: campos bloqueada, motivo_bloqueio, bloqueada_em
   - AssinaturaBarbearia: campos status, proximo_vencimento

2. ✅ Dependency de Verificação (app/dependencies.py)
   - verificar_barbearia_ativa(): Valida se barbearia está ativa
   - Retorna HTTP 402/403 se bloqueada ou vencida
   - Bloqueia automaticamente se vencida

3. ✅ Endpoints de Assinatura (app/routes_assinaturas.py)
   - POST /api/v1/assinaturas/pagar-mensalidade: Paga e desbloqueia
   - GET /api/v1/assinaturas/status: Verifica status atual
   - POST /api/v1/assinaturas/criar: Cria assinatura
   - POST /api/v1/assinaturas/renovar: Renova assinatura

4. ✅ Script Automático (verificar_inadimplentes.py)
   - Verifica assinaturas vencidas
   - Bloqueia barbearias inadimplentes
   - Envia alertas de vencimento próximo

5. ✅ Migração de Banco (adicionar_campos_bloqueio_barbearia.py)
   - Adiciona campos bloqueada, motivo_bloqueio, bloqueada_em
   - Execute: python adicionar_campos_bloqueio_barbearia.py

COMO APLICAR A VERIFICAÇÃO EM ROTAS:
====================================

Para rotas que devem ser bloqueadas se a barbearia estiver inadimplente,
adicione a dependency verificar_barbearia_ativa:

```python
from app.dependencies import verificar_barbearia_ativa

@router.post("/alguma-rota")
def funcao_protegida(
    db: Session = Depends(get_db),
    usuario_atual = Depends(verificar_barbearia_ativa)  # <- ADICIONE AQUI
):
    # Esta rota só funciona se a barbearia estiver ativa
    pass
```

ROTAS QUE DEVEM SER PROTEGIDAS:
================================

✅ BLOQUEAR (adicionar verificar_barbearia_ativa):
- POST /api/v1/aprovacoes/chamados/{id}/aprovacao-barbearia
- POST /api/v1/cadeiras/criar
- PUT /api/v1/cadeiras/{id}
- POST /api/v1/servicos/barbearias/{id}/servicos
- PUT /api/v1/servicos/{id}
- POST /api/v1/freelancer-status/barbearia/{id}/bloquear-freelancer
- GET /api/v1/analytics/barbearia/resumo
- Qualquer rota que modifique dados da barbearia

❌ NÃO BLOQUEAR:
- GET /api/v1/assinaturas/status (precisa funcionar para mostrar status)
- POST /api/v1/assinaturas/pagar-mensalidade (precisa funcionar para pagar)
- GET /api/v1/assinaturas/minha (precisa ver para pagar)
- Rotas de cliente (pagamentos de serviços)
- Rotas de barbeiro (receber pagamentos)

FLUXO DE BLOQUEIO AUTOMÁTICO:
==============================

1. Barbearia contrata assinatura (30 dias)
2. Sistema monitora data de vencimento
3. Ao vencer:
   - verificar_inadimplentes.py marca como inadimplente
   - Barbearia.bloqueada = True
   - AssinaturaBarbearia.status = "inadimplente"
4. Ao tentar usar features:
   - Dependency intercepta a requisição
   - Retorna HTTP 402 com detalhes do bloqueio
5. Ao pagar:
   - POST /pagar-mensalidade
   - Barbearia.bloqueada = False
   - AssinaturaBarbearia.status = "ativa"
   - proximo_vencimento += 30 dias

SCHEDULE DO VERIFICADOR:
=========================

Execute verificar_inadimplentes.py automaticamente:

Windows (Task Scheduler):
```powershell
# Executar todo dia às 6h
schtasks /create /tn "BarberMovie-Verificar-Inadimplentes" /tr "python c:\projeto_barbearia\verificar_inadimplentes.py" /sc daily /st 06:00
```

Linux (crontab):
```bash
# Executar todo dia às 6h
0 6 * * * cd /path/to/projeto && python verificar_inadimplentes.py
```

MENSAGENS DE ERRO PARA O FRONTEND:
===================================

HTTP 402 - Payment Required (Vencida):
```json
{
  "detail": {
    "erro": "assinatura_vencida",
    "mensagem": "Sua assinatura venceu em 15/02/2026. Complete o pagamento para continuar.",
    "valor_devido": 47.90,
    "vencimento": "2026-02-15T00:00:00"
  }
}
```

HTTP 403 - Forbidden (Bloqueada):
```json
{
  "detail": {
    "erro": "assinatura_bloqueada",
    "mensagem": "Barbearia bloqueada. Complete o pagamento da mensalidade para continuar usando o app.",
    "bloqueada_em": "2026-02-16T10:30:00"
  }
}
```

HTTP 402 - Payment Required (Sem assinatura):
```json
{
  "detail": {
    "erro": "sem_assinatura",
    "mensagem": "Você precisa contratar uma assinatura para usar o app."
  }
}
```

PRÓXIMOS PASSOS:
================

1. Execute a migração:
   ```
   python adicionar_campos_bloqueio_barbearia.py
   ```

2. Configure o verificador automático (cron/task scheduler)

3. Adicione verificar_barbearia_ativa nas rotas críticas

4. Implemente notificações:
   - Email de vencimento próximo (3 dias antes)
   - Email de bloqueio
   - Notificação push no app

5. Frontend:
   - Tela de pagamento de mensalidade
   - Banner de alerta de vencimento próximo
   - Modal de bloqueio com botão "Pagar agora"
"""
