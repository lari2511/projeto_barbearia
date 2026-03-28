-- PostgreSQL - Triggers de integridade para fluxo estilo Uber no BarberMove
-- Execute primeiro em homologacao.

BEGIN;

-- 1) Funcao de anti-colisao de agenda para barbeiro
CREATE OR REPLACE FUNCTION fn_chamado_validar_colisao()
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

    IF NEW.status NOT IN ('confirmado', 'em_deslocamento', 'em_atendimento') THEN
        RETURN NEW;
    END IF;

    SELECT c.id
      INTO v_conflict_id
      FROM chamados c
     WHERE c.barbeiro_id = NEW.barbeiro_id
       AND c.id <> COALESCE(NEW.id, -1)
       AND c.status IN ('confirmado', 'em_deslocamento', 'em_atendimento')
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

DROP TRIGGER IF EXISTS trg_chamado_validar_colisao ON chamados;
CREATE TRIGGER trg_chamado_validar_colisao
BEFORE INSERT OR UPDATE OF barbeiro_id, data_hora_inicio, data_hora_fim, status
ON chamados
FOR EACH ROW
EXECUTE FUNCTION fn_chamado_validar_colisao();

-- 2) Historico automatico de status
CREATE OR REPLACE FUNCTION fn_chamado_historico_status()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF TG_OP = 'UPDATE' AND OLD.status IS DISTINCT FROM NEW.status THEN
        INSERT INTO chamados_historico (chamado_id, status_anterior, status_novo, usuario_id, observacao, criado_em)
        VALUES (NEW.id, OLD.status, NEW.status, NEW.barbeiro_id, 'Transicao automatica por trigger', NOW());
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_chamado_historico_status ON chamados;
CREATE TRIGGER trg_chamado_historico_status
AFTER UPDATE OF status ON chamados
FOR EACH ROW
EXECUTE FUNCTION fn_chamado_historico_status();

-- 3) Notificacao em confirmacao
CREATE OR REPLACE FUNCTION fn_chamado_notificar_confirmacao()
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

DROP TRIGGER IF EXISTS trg_chamado_notificar_confirmacao ON chamados;
CREATE TRIGGER trg_chamado_notificar_confirmacao
AFTER UPDATE OF status ON chamados
FOR EACH ROW
EXECUTE FUNCTION fn_chamado_notificar_confirmacao();

-- 4) Consolidacao de finalizacao e liberacao operacional
CREATE OR REPLACE FUNCTION fn_chamado_finalizacao_consolidar()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF TG_OP = 'UPDATE'
       AND OLD.status IS DISTINCT FROM NEW.status
       AND NEW.status IN ('concluido', 'finalizado') THEN

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

DROP TRIGGER IF EXISTS trg_chamado_finalizacao_consolidar ON chamados;
CREATE TRIGGER trg_chamado_finalizacao_consolidar
AFTER UPDATE OF status ON chamados
FOR EACH ROW
EXECUTE FUNCTION fn_chamado_finalizacao_consolidar();

-- 5) Reversao operacional no cancelamento
CREATE OR REPLACE FUNCTION fn_chamado_cancelamento_reverter()
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

DROP TRIGGER IF EXISTS trg_chamado_cancelamento_reverter ON chamados;
CREATE TRIGGER trg_chamado_cancelamento_reverter
AFTER UPDATE OF status ON chamados
FOR EACH ROW
EXECUTE FUNCTION fn_chamado_cancelamento_reverter();

COMMIT;
