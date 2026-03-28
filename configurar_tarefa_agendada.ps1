# Configurar Tarefa Agendada - Verificacao de Inadimplentes
# Execute este script como Administrador

$nomeTarefa = "BarberMovie-VerificarInadimplentes"
$caminhoProjeto = "c:\projeto_barbearia"
$caminhoScript = "c:\projeto_barbearia\verificar_inadimplentes.py"
$caminhoPython = "c:\projeto_barbearia\.venv\Scripts\python.exe"

Write-Host "Configurando tarefa agendada: $nomeTarefa" -ForegroundColor Cyan

# Verificar se a tarefa ja existe
$tarefaExistente = Get-ScheduledTask -TaskName $nomeTarefa -ErrorAction SilentlyContinue

if ($tarefaExistente) {
    Write-Host "Tarefa ja existe. Removendo..." -ForegroundColor Yellow
    Unregister-ScheduledTask -TaskName $nomeTarefa -Confirm:$false
}

# Criar acao (executar script Python)
$acao = New-ScheduledTaskAction -Execute $caminhoPython -Argument $caminhoScript -WorkingDirectory $caminhoProjeto

# Criar gatilho (executar diariamente as 6h)
$gatilhoDiario = New-ScheduledTaskTrigger -Daily -At 6:00AM

# Tambem executar na inicializacao do sistema (com delay de 5 minutos)
$gatilhoInicializacao = New-ScheduledTaskTrigger -AtStartup
$gatilhoInicializacao.Delay = 'PT5M'

# Configuracoes adicionais
$configuracao = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -RunOnlyIfNetworkAvailable -MultipleInstances IgnoreNew

# Criar principal (executar com privilegios de sistema)
$principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest

# Registrar tarefa
Register-ScheduledTask -TaskName $nomeTarefa -Action $acao -Trigger @($gatilhoDiario, $gatilhoInicializacao) -Settings $configuracao -Principal $principal -Description "Verifica assinaturas vencidas e bloqueia barbearias inadimplentes automaticamente" -Force

Write-Host ""
Write-Host "Tarefa agendada criada com sucesso!" -ForegroundColor Green
Write-Host ""
Write-Host "Configuracao:" -ForegroundColor Cyan
Write-Host "  - Nome: $nomeTarefa"
Write-Host "  - Execucao: Diariamente as 6:00 AM"
Write-Host "  - Tambem executa: Na inicializacao do sistema (5min delay)"
Write-Host "  - Script: $caminhoScript"
Write-Host ""

# Mostrar informacoes da tarefa
Get-ScheduledTask -TaskName $nomeTarefa | Format-List

Write-Host ""
Write-Host "Para testar agora:" -ForegroundColor Yellow
Write-Host "  Start-ScheduledTask -TaskName $nomeTarefa"
Write-Host ""
Write-Host "Para ver historico:" -ForegroundColor Yellow
Write-Host "  Get-ScheduledTaskInfo -TaskName $nomeTarefa"
Write-Host ""
