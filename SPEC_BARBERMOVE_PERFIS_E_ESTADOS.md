# SPEC BarberMove - Perfis, Estados e Regras de Integridade

## Objetivo
Definir um fluxo operacional estilo Uber para o BarberMove, com estados claros por atendimento, responsabilidades por perfil e regras de integridade de dados no banco.

## Perfis e Responsabilidades

### Cliente
- Permitir geolocalizacao para busca por proximidade.
- Comparar barbeiros por portfolio, avaliacoes, preco e tempo estimado.
- Criar solicitacao de servico com horario.
- Acompanhar status em tempo real.
- Avaliar e concluir pagamento no fim do atendimento.

### Barbeiro
- Definir disponibilidade operacional (`offline`, `online_regiao`, `presente`).
- Gerenciar agenda e aceitar/recusar solicitacoes.
- Atualizar progresso da corrida de atendimento: deslocamento, inicio e fim.
- Gerenciar faturamento e performance no app.

### Administrador
- Aprovar perfis de barbeiros.
- Monitorar taxa de cancelamento, SLA de aceite e confiabilidade.
- Auditar conflitos, comportamentos recorrentes e saude da plataforma.

## Maquina de Estados do Atendimento

### Estados recomendados
- `solicitado`
- `confirmado`
- `em_deslocamento`
- `em_atendimento`
- `finalizado`
- `cancelado`

### Mapeamento com status atual da base
- `solicitado` -> `pendente`
- `confirmado` -> `confirmado`
- `finalizado` -> `concluido`
- `cancelado` -> `cancelado`

Observacao: os estados `em_deslocamento` e `em_atendimento` podem ser adicionados gradualmente no backend como novos valores de `chamados.status` (coluna string).

## Regras de Transicao
- `solicitado -> confirmado|cancelado`
- `confirmado -> em_deslocamento|cancelado`
- `em_deslocamento -> em_atendimento|cancelado`
- `em_atendimento -> finalizado`
- `finalizado` e `cancelado` sao terminais.

## Regras de Integridade (Banco)

### 1) Anti-colisao de agenda
- Ao inserir/atualizar chamado confirmado, negar sobreposicao para o mesmo barbeiro no intervalo (`data_hora_inicio`, `data_hora_fim`).

### 2) Historico automatico de status
- Qualquer mudanca de `chamados.status` gera linha em `chamados_historico`.

### 3) Notificacao automatica em confirmacao
- Quando transicionar para confirmado, registrar notificacao para cliente.

### 4) Finalizacao financeira automatica
- Ao transicionar para concluido/finalizado:
- preencher `concluido_em`;
- consolidar snapshot financeiro (`valor_total`, `comissao_plataforma`, `valor_freelancer`, `valor_dono`) se vazio;
- liberar agenda operacional do barbeiro (`em_atendimento=false`, `ocupado_ate=NULL`, `disponivel=true`).

### 5) Reversao em cancelamento
- Ao cancelar antes de iniciar atendimento, liberar bloqueios operacionais do barbeiro para novo slot.

## Endpoints de referencia no projeto
- `POST /api/v1/chamados`
- `GET /api/v1/chamados/abertos`
- `PUT /api/v1/chamados/{id}/aceitar`
- `PUT /api/v1/chamados/{id}/finalizar`
- `PUT /api/v1/freelancer/{freelancer_id}/alterar-status`
- `GET /api/v1/barbeiros/proximos`
- `WS /ws/notificacoes`

## Tempo Real
- Canal primario: WebSocket (`/ws/notificacoes`).
- Fallback: polling apenas quando WebSocket estiver desconectado.
- Eventos recomendados:
- `freelancer_status_changed`
- `chamado_status_changed`
- `agenda_slot_locked`
- `agenda_slot_released`

## Estrategia de rollout
1. Validar triggers em homologacao.
2. Ativar log de violacoes (anti-colisao) antes de bloquear em producao.
3. Liberar estados intermediarios (`em_deslocamento`, `em_atendimento`) com feature flag no frontend.
4. Monitorar SLA e taxa de cancelamento apos deploy.

## Arquivos de Migration Disponiveis
- `migration_triggers_fluxo_uber_v1_compat.sql`: use agora, compativel com status atuais (`pendente`, `confirmado`, `concluido`, `cancelado`).
- `migration_triggers_fluxo_uber.sql`: use quando os estados intermediarios (`em_deslocamento`, `em_atendimento`) ja estiverem ativos no backend.
