# 💰 Modelo de Cobrança BarberMove

## Visão Geral
Sistema de monetização transparente e justo para todas as partes.

---

## 🎯 Modelo de Negócio

### 💈 Para Barbeiros (Freelancers)
**Taxa de 10% por serviço**

- ✅ Descontado automaticamente de cada atendimento
- ✅ Sem taxas de cadastro ou mensalidade
- ✅ Pagamento via PIX, cartão ou dinheiro
- ✅ Saque disponível com mínimo de R$ 50,00
- ✅ Processamento em 2-3 dias úteis

**Exemplo de cálculo:**
```
Serviço: R$ 100,00
Taxa BarberMove (10%): R$ 10,00
Valor recebido pelo barbeiro: R$ 90,00
```

**Retenção:**
- 7 dias de retenção para garantia de qualidade
- Após 7 dias, saldo liberado para saque

---

### 🏪 Para Barbearias
**Assinatura Mensal Progressiva por Cadeira**

📊 **Tabela de Preços:**
| Cadeiras | Valor por Cadeira | Valor Total Mensal |
|----------|-------------------|-------------------|
| 1        | R$ 47,90          | R$ 47,90          |
| 2        | +R$ 27,90         | R$ 75,80          |
| 3        | +R$ 24,90         | R$ 100,70         |
| 4        | +R$ 22,90         | R$ 123,60         |
| 5        | +R$ 19,90         | R$ 143,50         |
| 6        | +R$ 17,90         | R$ 161,40         |
| 7        | +R$ 17,90         | R$ 179,30         |
| 10       | +R$ 17,90         | R$ 233,00         |

**💡 Vantagens do Modelo Progressivo:**
- ✅ Cada nova cadeira fica mais barata
- ✅ Incentiva expansão constante da barbearia
- ✅ Valor forte na primeira cadeira (R$ 47,90)
- ✅ Estabiliza após 6ª cadeira em R$ 17,90/cadeira
- ✅ Cancelamento a qualquer momento

**Benefícios inclusos:**
- Dashboard de gestão completo
- Sistema de agendamentos
- Controle de cadeiras e barbeiros ilimitados
- Relatórios financeiros
- Suporte prioritário

---

### 👤 Para Clientes
**Grátis - Sem Taxas**

- ✅ Cadastro gratuito
- ✅ Busca ilimitada de profissionais
- ✅ Agendamentos sem custo adicional
- ✅ Pagamento direto ao barbeiro/barbearia
- ✅ Avaliações e histórico

---

## 💡 Diferenciais

### Transparência Total
- Sem taxas ocultas
- Valores claramente informados
- Cálculo automático e transparente

### Pagamento Seguro
- Processamento rápido (2-3 dias úteis)
- Múltiplas formas de pagamento
- Sistema de retenção para garantia

### Flexibilidade
- Barbeiros não pagam mensalidade
- Barbearias pagam valor fixo independente do volume
- Clientes não pagam nada

---

## 📊 Fluxo Financeiro

### Para Barbeiros:
1. Cliente paga pelo serviço (R$ 100,00)
2. Sistema calcula comissão de 10% (R$ 10,00)
3. Barbeiro recebe R$ 90,00
4. Valor fica 7 dias em retenção
5. Após 7 dias, saque disponível
6. Transferência em 2-3 dias úteis

### Para Barbearias:
1. Cobrança mensal de R$ 49,90
2. Renovação automática
3. Acesso ilimitado para todos os recursos
4. Sem custo adicional por volume ou serviços

---

## 🔧 Implementação Técnica

### Backend (Python/FastAPI)
- Cálculo automático de comissão no momento do pagamento
- Verificação de assinatura ativa para barbearias
- Sistema de retenção de 7 dias
- WebHooks para processar pagamentos

### Frontend (React)
- Exibição transparente de valores
- Cards informativos sobre taxas
- Dashboard financeiro completo
- Histórico de transações detalhado

### Banco de Dados
```sql
-- Tabela de comissões
comissao_barbeiro: 0.10 (10%)

-- Tabela de assinatura
valor_mensal: 49.90
periodo_retencao: 7 dias
saque_minimo: 50.00
```

---

## 📈 Métricas e Relatórios

### Para Barbeiros:
- Total bruto ganho
- Total líquido (após comissão)
- Comissão paga
- Média por serviço
- Serviços por mês
- Saldo disponível vs em retenção

### Para Barbearias:
- Total de serviços realizados
- Número de barbeiros ativos
- Taxa de ocupação de cadeiras
- Histórico de pagamentos da assinatura

---

## 🎯 Objetivos

1. **Sustentabilidade**: Taxa de 10% + assinatura garante manutenção da plataforma
2. **Justiça**: Barbeiros pagam proporcionalmente ao uso
3. **Previsibilidade**: Barbearias têm custo fixo mensal
4. **Crescimento**: Quanto mais serviços, mais receita para todos

---

## 📞 Suporte

Para dúvidas sobre cobrança:
- Email: financeiro@barbermove.com
- Telefone: (11) 9999-9999
- Chat: Disponível 24/7 no app

---

**Última atualização:** 28 de fevereiro de 2026
**Versão:** 1.0
