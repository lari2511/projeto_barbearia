# BarberMove - Especificacao de Fluxo (Implementacao)

## 1. Fluxo do Cliente

Ordem obrigatoria:
1. Selecionar Barbearia
2. Selecionar Freelancer

Regras:
- Se existir freelancer na barbearia:
  - Listar apenas freelancers com status: PRESENTE_NA_BARBEARIA
- Se NAO existir:
  - Exibir opcao: SOLICITAR_FREELANCER
  - Buscar freelancers com status: ATIVO_REGIAO
  - Enviar solicitacao
  - Ao aceitar e chegar:
    - Atualizar status para PRESENTE_NA_BARBEARIA

## 2. Status do Freelancer

- ATIVO_REGIAO
- PRESENTE_NA_BARBEARIA
- EM_ATENDIMENTO
- AGUARDANDO_PROXIMO
- INDISPONIVEL (quando atingir limite de fila)

## 3. Logica de Fila

Regra:
- Maximo de 1 cliente em atendimento
- Maximo de 1 cliente aguardando

Comportamento:
- Se clientes = 0: disponivel
- Se clientes = 1: disponivel com status EM_ATENDIMENTO
- Se clientes = 2: indisponivel (nao aparece para novos clientes)

Transicao:
- FINALIZAR_ATENDIMENTO:
  - cliente_em_espera vira EM_ATENDIMENTO
  - libera vaga para novo cliente

## 4. Inicio do Atendimento

Acao:
- Botao INICIAR_CORTE

Sistema deve registrar:
- horario_inicio
- barbearia_id
- tipo_servico

Sistema deve:
- Buscar tempo do servico com base na barbearia
- Iniciar cronometro
- Calcular previsao_termino = horario_inicio + tempo_servico

## 5. Tempo do Servico

Fonte:
- Configuracao da barbearia

Exemplo:

```json
{
  "corte": 30,
  "barba": 60,
  "corte_barba": 80
}
```

Aplicacao:
- Aplicar automaticamente ao iniciar atendimento

## 6. Exibicao para Cliente em Espera

Mostrar:
- status = EM_ATENDIMENTO
- horario_inicio
- previsao_termino

## 7. Finalizacao do Atendimento

Acao:
- Botao FINALIZAR_CORTE

Sistema deve:
- Encerrar cronometro
- Finalizar atendimento
- Liberar pagamento
- Atualizar fila:
  - proximo cliente vira EM_ATENDIMENTO

## 8. Chat

Regra:
- Ativar apos criacao de vinculo (match)

Permitir:
- Cliente <-> Freelancer

## 9. Regra de Atraso

Tolerancia:
- 15 minutos

Fluxo:
- Cliente deve acionar CHEGUEI
- Se nao acionar:
  - Apos 15 minutos, liberar opcao CANCELAR_CLIENTE_AUSENTE
  - Remover da fila
  - Chamar proximo automaticamente

## 10. Cancelamentos (Flexivel com Controle)

Permissoes:
- Cliente pode cancelar a qualquer momento
- Freelancer pode cancelar a qualquer momento

## 11. Controle de Cancelamentos

Sistema deve registrar:
- cancelamentos_cliente
- cancelamentos_freelancer

## 12. Regras de Penalidade

Se excesso de cancelamentos, aplicar automaticamente:
- reduzir visibilidade
- reduzir prioridade
- bloqueio temporario

## 13. Regras Gerais

- Nunca permitir mais de 1 cliente em espera
- Cronometro depende de INICIAR_CORTE
- Tempo sempre baseado na barbearia atual
- Fluxo deve ser continuo (sem acumulo)

## Resumo Tecnico

- Fluxo: BARBEARIA -> FREELANCER
- Fila: 1 atendimento + 1 espera
- Cronometro: obrigatorio
- Tempo: por barbearia
- Cancelamento: livre com controle
- Sistema: orientado a fluxo continuo
