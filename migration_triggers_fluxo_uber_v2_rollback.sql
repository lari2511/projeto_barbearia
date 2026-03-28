-- Rollback seguro dos triggers v2 (uber completo)

BEGIN;

DROP TRIGGER IF EXISTS trg_chamado_cancelamento_reverter ON chamados;
DROP FUNCTION IF EXISTS fn_chamado_cancelamento_reverter();

DROP TRIGGER IF EXISTS trg_chamado_finalizacao_consolidar ON chamados;
DROP FUNCTION IF EXISTS fn_chamado_finalizacao_consolidar();

DROP TRIGGER IF EXISTS trg_chamado_notificar_confirmacao ON chamados;
DROP FUNCTION IF EXISTS fn_chamado_notificar_confirmacao();

DROP TRIGGER IF EXISTS trg_chamado_historico_status ON chamados;
DROP FUNCTION IF EXISTS fn_chamado_historico_status();

DROP TRIGGER IF EXISTS trg_chamado_validar_colisao ON chamados;
DROP FUNCTION IF EXISTS fn_chamado_validar_colisao();

COMMIT;
