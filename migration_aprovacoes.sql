-- Migration: Adicionar colunas de aprovação bidirecional
-- Data: 2026-02-05

-- Adicionar colunas de aprovação na tabela chamados
ALTER TABLE chamados 
ADD COLUMN IF NOT EXISTS aprovado_barbeiro BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS aprovado_barbearia BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS aprovado_barbeiro_em TIMESTAMP,
ADD COLUMN IF NOT EXISTS aprovado_barbearia_em TIMESTAMP;

-- Adicionar colunas de vinculação de chamado na tabela cadeiras
ALTER TABLE cadeiras
ADD COLUMN IF NOT EXISTS chamado_id INTEGER REFERENCES chamados(id) ON DELETE SET NULL;

-- Criar índices para melhorar performance
CREATE INDEX IF NOT EXISTS idx_chamados_aprovado_barbeiro ON chamados(aprovado_barbeiro);
CREATE INDEX IF NOT EXISTS idx_chamados_aprovado_barbearia ON chamados(aprovado_barbearia);
CREATE INDEX IF NOT EXISTS idx_cadeiras_chamado_id ON cadeiras(chamado_id);

-- Verificar as colunas adicionadas
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_name = 'chamados' 
AND column_name IN ('aprovado_barbeiro', 'aprovado_barbearia', 'aprovado_barbeiro_em', 'aprovado_barbearia_em')
ORDER BY column_name;

SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_name = 'cadeiras' 
AND column_name = 'chamado_id'
ORDER BY column_name;
