# Runbook - Migracoes de Triggers BarberMove

## Objetivo
Aplicar triggers de integridade com seguranca no banco PostgreSQL do BarberMove.

## Arquivos
- Aplicacao atual (recomendado agora): `migration_triggers_fluxo_uber_v1_compat.sql`
- Rollback atual: `migration_triggers_fluxo_uber_v1_rollback.sql`
- Aplicacao futura (uber completo): `migration_triggers_fluxo_uber.sql`
- Rollback futuro: `migration_triggers_fluxo_uber_v2_rollback.sql`

## Pre-checks
1. Confirme backup recente do banco.
2. Execute em homologacao antes de producao.
3. Garanta permissao para `CREATE FUNCTION` e `CREATE TRIGGER`.

## Variaveis de ambiente (PowerShell)
```powershell
$env:PGHOST = "127.0.0.1"
$env:PGPORT = "5432"
$env:PGDATABASE = "barbermove"
$env:PGUSER = "postgres"
$env:PGPASSWORD = "SUA_SENHA"
```

## Aplicar v1 (agora)
```powershell
psql -v ON_ERROR_STOP=1 -f .\migration_triggers_fluxo_uber_v1_compat.sql
```

### Opcao 1 comando (recomendada)
```powershell
.\\deploy_triggers_v1.ps1 -DbHost 127.0.0.1 -DbPort 5432 -DbName barbermove -DbUser postgres -DbPassword "SUA_SENHA"
```

### Opcao 1 comando com rollback automatico
```powershell
.\\deploy_triggers_v1.ps1 -DbHost 127.0.0.1 -DbPort 5432 -DbName barbermove -DbUser postgres -DbPassword "SUA_SENHA" -AutoRollbackOnError
```

## Validar objetos criados
```powershell
psql -c "SELECT tgname FROM pg_trigger WHERE tgrelid = 'chamados'::regclass AND NOT tgisinternal ORDER BY tgname;"
```

## Teste rapido funcional
1. Crie/atualize chamado para `confirmado` em horario ja ocupado do mesmo barbeiro: deve bloquear por colisao.
2. Altere status para `confirmado`: deve criar notificacao para cliente.
3. Altere status para `concluido`: deve consolidar campos financeiros e liberar barbeiro.
4. Altere status para `cancelado`: deve liberar bloqueios operacionais do barbeiro.

## Rollback v1
```powershell
psql -v ON_ERROR_STOP=1 -f .\migration_triggers_fluxo_uber_v1_rollback.sql
```

### Opcao 1 comando de rollback
```powershell
.\\rollback_triggers_v1.ps1 -DbHost 127.0.0.1 -DbPort 5432 -DbName barbermove -DbUser postgres -DbPassword "SUA_SENHA"
```

## Aplicar v2 (quando estados intermediarios existirem)
```powershell
psql -v ON_ERROR_STOP=1 -f .\migration_triggers_fluxo_uber.sql
```

## Rollback v2
```powershell
psql -v ON_ERROR_STOP=1 -f .\migration_triggers_fluxo_uber_v2_rollback.sql
```

## Observacoes
- Se estiver usando outro nome de database/user, ajuste as variaveis.
- Para CI/CD, execute com `ON_ERROR_STOP=1` para falhar rapido em qualquer erro.
