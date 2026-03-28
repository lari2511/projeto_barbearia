-- PostgreSQL - Triggers de integridade COMPATIVEIS com status atuais
-- Status atuais esperados: pendente, confirmado, concluido, cancelado
-- Esta versao evita depender de estados futuros (em_deslocamento, em_atendimento).

BEGIN;

-- 1) Anti-colisao de agenda (apenas confirmados bloqueiam slot)
CREATE OR REPLACE FUNCTION fn_chamado_validar_colisao_v1()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    v_conflict_id integer;
BEGIN
    IF NEW.barbeiro_id IS NULL THEN
        RETURN NEW;
    END IF;

    IF NEW.data_hora_inicio IS NULL OR NEW.data_hora_fim IS NULL THEN
        RETURN NEW;
    END IF;

    IF NEW.status <> 'confirmado' THEN
        RETURN NEW;
    END IF;

    SELECT c.id
      INTO v_conflict_id
      FROM chamados c
     WHERE c.barbeiro_id = NEW.barbeiro_id
       AND c.id <> COALESCE(NEW.id, -1)
       AND c.status = 'confirmado'
       AND tstzrange(c.data_hora_inicio, c.data_hora_fim, '[)')
           && tstzrange(NEW.data_hora_inicio, NEW.data_hora_fim, '[)')
     LIMIT 1;

    IF v_conflict_id IS NOT NULL THEN
        RAISE EXCEPTION 'Conflito de agenda para barbeiro % com chamado %', NEW.barbeiro_id, v_conflict_id
          USING ERRCODE = 'P0001';
    END IF;

    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_chamado_validar_colisao_v1 ON chamados;
CREATE TRIGGER trg_chamado_validar_colisao_v1
BEFORE INSERT OR UPDATE OF barbeiro_id, data_hora_inicio, data_hora_fim, status
ON chamados
FOR EACH ROW
EXECUTE FUNCTION fn_chamado_validar_colisao_v1();

-- 2) Historico automatico de status
CREATE OR REPLACE FUNCTION fn_chamado_historico_status_v1()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF TG_OP = 'UPDATE' AND OLD.status IS DISTINCT FROM NEW.status THEN
        INSERT INTO chamados_historico (chamado_id, status_anterior, status_novo, usuario_id, observacao, criado_em)
        VALUES (NEW.id, OLD.status, NEW.status, NEW.barbeiro_id, 'Transicao automatica por trigger v1', NOW());
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_chamado_historico_status_v1 ON chamados;
CREATE TRIGGER trg_chamado_historico_status_v1
AFTER UPDATE OF status ON chamados
FOR EACH ROW
EXECUTE FUNCTION fn_chamado_historico_status_v1();

-- 3) Notificacao em confirmacao
CREATE OR REPLACE FUNCTION fn_chamado_notificar_confirmacao_v1()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF TG_OP = 'UPDATE'
       AND OLD.status IS DISTINCT FROM NEW.status
       AND NEW.status = 'confirmado' THEN
        INSERT INTO notificacoes (usuario_id, titulo, mensagem, tipo, lido, referencia_id, criado_em)
        VALUES (
            NEW.cliente_id,
            'Agendamento confirmado',
            'Seu agendamento foi confirmado pelo barbeiro.',
            'chamado_confirmado',
            FALSE,
            NEW.id,
            NOW()
        );
    END IF;

    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_chamado_notificar_confirmacao_v1 ON chamados;
CREATE TRIGGER trg_chamado_notificar_confirmacao_v1
AFTER UPDATE OF status ON chamados
FOR EACH ROW
EXECUTE FUNCTION fn_chamado_notificar_confirmacao_v1();

-- 4) Consolidacao em finalizacao
CREATE OR REPLACE FUNCTION fn_chamado_finalizacao_consolidar_v1()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF TG_OP = 'UPDATE'
       AND OLD.status IS DISTINCT FROM NEW.status
       AND NEW.status = 'concluido' THEN

        UPDATE chamados
           SET concluido_em = COALESCE(concluido_em, NOW()),
               valor_total = COALESCE(valor_total, valor_original, valor_final),
               comissao_plataforma = COALESCE(comissao_plataforma, ROUND(COALESCE(valor_total, valor_original, valor_final) * 0.15, 2)),
               valor_freelancer = COALESCE(valor_freelancer, ROUND(COALESCE(valor_total, valor_original, valor_final) * 0.45, 2)),
               valor_dono = COALESCE(valor_dono, ROUND(COALESCE(valor_total, valor_original, valor_final) * 0.40, 2))
         WHERE id = NEW.id;

        IF NEW.barbeiro_id IS NOT NULL THEN
            UPDATE usuarios
               SET em_atendimento = FALSE,
                   ocupado_ate = NULL,
                   disponivel = TRUE
             WHERE id = NEW.barbeiro_id;
        END IF;
    END IF;

    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_chamado_finalizacao_consolidar_v1 ON chamados;
CREATE TRIGGER trg_chamado_finalizacao_consolidar_v1
AFTER UPDATE OF status ON chamados
FOR EACH ROW
EXECUTE FUNCTION fn_chamado_finalizacao_consolidar_v1();

-- 5) Reversao no cancelamento
CREATE OR REPLACE FUNCTION fn_chamado_cancelamento_reverter_v1()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF TG_OP = 'UPDATE'
       AND OLD.status IS DISTINCT FROM NEW.status
       AND NEW.status = 'cancelado' THEN
        IF NEW.barbeiro_id IS NOT NULL THEN
            UPDATE usuarios
               SET em_atendimento = FALSE,
                   ocupado_ate = NULL,
                   disponivel = TRUE
             WHERE id = NEW.barbeiro_id;
        END IF;
    END IF;

    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_chamado_cancelamento_reverter_v1 ON chamados;
CREATE TRIGGER trg_chamado_cancelamento_reverter_v1
AFTER UPDATE OF status ON chamados
FOR EACH ROW
EXECUTE FUNCTION fn_chamado_cancelamento_reverter_v1();

COMMIT;
