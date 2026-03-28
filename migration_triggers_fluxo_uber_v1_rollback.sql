-- Rollback seguro dos triggers v1 (compat)

BEGIN;

DROP TRIGGER IF EXISTS trg_chamado_cancelamento_reverter_v1 ON chamados;
DROP FUNCTION IF EXISTS fn_chamado_cancelamento_reverter_v1();

DROP TRIGGER IF EXISTS trg_chamado_finalizacao_consolidar_v1 ON chamados;
DROP FUNCTION IF EXISTS fn_chamado_finalizacao_consolidar_v1();

DROP TRIGGER IF EXISTS trg_chamado_notificar_confirmacao_v1 ON chamados;
DROP FUNCTION IF EXISTS fn_chamado_notificar_confirmacao_v1();

DROP TRIGGER IF EXISTS trg_chamado_historico_status_v1 ON chamados;
DROP FUNCTION IF EXISTS fn_chamado_historico_status_v1();

DROP TRIGGER IF EXISTS trg_chamado_validar_colisao_v1 ON chamados;
DROP FUNCTION IF EXISTS fn_chamado_validar_colisao_v1();

COMMIT;
