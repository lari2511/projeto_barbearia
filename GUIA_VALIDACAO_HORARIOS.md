# 📅 Validação de Horários Disponíveis para Agendamentos

## 🎯 Objetivo

Garantir que **dois agendamentos do mesmo barbeiro não se sobreponham**. Quando um cliente tenta agendar um horário já ocupado, o sistema retorna um erro amigável.

## 🔍 Como Funciona

### Lógica de Sobreposição (O Guardião)

```python
novo_inicio < agendamento_existente_fim AND novo_fim > agendamento_existente_inicio
```

Se **ambas** as condições forem verdadeiras, há sobreposição = **conflito!**

### Exemplos Visuais

```
✅ SEM CONFLITO (Agendamentos lado a lado):
   Agendamento 1: [10:00 ---- 11:00]
   Agendamento 2:                  [11:00 ---- 12:00]
   
   10:00 < 11:00 AND 12:00 > 10:00
   True AND True = TRUE? NÃO!
   Porque: novo_inicio (11:00) NÃO é < fim_existente (11:00)
   ✅ Resultado: DISPONÍVEL

❌ COM CONFLITO (Agendamentos sobrepostos):
   Agendamento 1: [10:00 ---- 11:00]
   Agendamento 2:      [10:30 ---- 11:30]
   
   10:30 < 11:00 AND 11:30 > 10:00
   True AND True = TRUE ✓
   ❌ Resultado: CONFLITO!

❌ COM CONFLITO (Um dentro do outro):
   Agendamento 1: [10:00 ---- 11:00]
   Agendamento 2:   [10:15 ---- 10:45]
   
   10:15 < 11:00 AND 10:45 > 10:00
   True AND True = TRUE ✓
   ❌ Resultado: CONFLITO!
```

## 🛠️ Implementação no Backend

### 1. Adicionar Função Helper

**Arquivo:** `app/routes.py`

```python
def is_horario_disponivel(db: Session, barbeiro_id: int, inicio: datetime, fim: datetime) -> bool:
    """
    Verifica se um barbeiro está disponível em um determinado horário.
    
    Ignora agendamentos CANCELADOS.
    """
    from sqlalchemy import and_
    
    conflito = db.query(models.Chamado).filter(
        and_(
            models.Chamado.barbeiro_id == barbeiro_id,
            models.Chamado.status != models.StatusAgendamento.CANCELADO.value,
            
            # Lógica mágica de sobreposição
            models.Chamado.data_hora_inicio < fim,
            models.Chamado.data_hora_fim > inicio
        )
    ).first()
    
    return conflito is None  # True se não há conflito
```

### 2. Usar no Endpoint de Criar Agendamento

**Arquivo:** `app/routes.py` → Endpoint `POST /chamados`

```python
@router.post("/chamados")
def criar_chamado(chamado: schemas.ChamadoCreate, ...):
    # ... validações anteriores ...
    
    # ✅ GUARDIÃO 1: Validar data/hora
    if not chamado.data_hora_inicio:
        raise HTTPException(status_code=400, detail="Data e hora obrigatórias")
    
    # Calcular hora de término
    duracao_minutos = servico.duracao_minutos or 30
    hora_fim = chamado.data_hora_inicio + timedelta(minutes=duracao_minutos)
    
    # ✅ GUARDIÃO 2: Verificar disponibilidade
    if chamado.barbeiro_id:
        disponivel = is_horario_disponivel(
            db,
            chamado.barbeiro_id,
            chamado.data_hora_inicio,
            hora_fim
        )
        
        if not disponivel:
            raise HTTPException(
                status_code=400,
                detail="Poxa! Esse horário já foi reservado. Que tal tentar outro?"
            )
    
    # ... resto do código ...
```

## 🎨 Tratamento de Erro no React

### Hook Customizado

**Arquivo:** `barbermove/src/hooks/useAgendamentoForm.js`

```javascript
export const useAgendamentoForm = (token, apiUrl) => {
  const [loading, setLoading] = useState(false);
  const [erro, setErro] = useState(null);

  const criar = async (dados) => {
    try {
      const response = await fetch(`${apiUrl}/chamados`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify(dados),
      });

      const data = await response.json();

      if (!response.ok) {
        const novoErro = {
          status: response.status,
          mensagem: data.detail,
          horarioIndisponivel: false,
          tipo: null,
        };

        // Detectar erro específico
        if (response.status === 400 && data.detail.includes('horário')) {
          novoErro.horarioIndisponivel = true;
          novoErro.tipo = 'horario_ocupado';
        }

        setErro(novoErro);
        return null;
      }

      // Sucesso!
      return data;
    } finally {
      setLoading(false);
    }
  };

  return { criar, loading, erro };
};
```

### Componente com Mensagem Amigável

```jsx
import { useAgendamentoForm } from '@/hooks/useAgendamentoForm';

export function AgendamentoForm() {
  const { criar, loading, erro } = useAgendamentoForm(token, apiUrl);

  const handleSubmit = async (e) => {
    e.preventDefault();
    const resultado = await criar(dados);
  };

  return (
    <form onSubmit={handleSubmit}>
      {/* Formulário ... */}

      {/* ✅ Tratamento de erro amigável */}
      {erro?.horarioIndisponivel && (
        <div className="bg-yellow-100 border border-yellow-400 p-4 rounded">
          <h3 className="font-bold mb-2">⏳ Horário Indisponível</h3>
          <p className="mb-3">{erro.mensagem}</p>
          <div className="text-sm">
            <p className="font-semibold">💡 Dicas:</p>
            <ul className="list-disc list-inside">
              <li>Experimente horários próximos (14:00, 15:30, etc)</li>
              <li>Escolha outro dia da semana</li>
              <li>Veja a agenda do barbeiro</li>
            </ul>
          </div>
        </div>
      )}
    </form>
  );
}
```

## 📋 Checklist de Implementação

- [x] Adicionar função `is_horario_disponivel()` em `app/routes.py`
- [x] Adicionar validação no endpoint `POST /chamados`
- [x] Adicionar campos `data_hora_inicio` e `data_hora_fim` ao modelo `Chamado`
- [x] Calcular hora de término baseado na duração do serviço
- [x] Criar hook React `useAgendamentoForm.js`
- [x] Implementar tratamento de erro amigável no formulário
- [x] Criar testes em `test_horarios_disponivel.py`
- [ ] Testar com 2+ agendamentos do mesmo barbeiro
- [ ] Adicionar botão "Ver Horários Disponíveis" no formulário
- [ ] Implementar endpoint GET `/barbeiro/{id}/horarios-disponiveis?data=YYYY-MM-DD`

## 🧪 Testes

Executar os testes de sobreposição:

```bash
python test_horarios_disponivel.py
```

Inclui 10 testes para validar:
- ✅ Horário livre
- ❌ Conflito total
- ❌ Conflito parcial (início e fim)
- ✅ Agendamentos cancelados ignorados
- ✅ Apenas mesmo barbeiro
- ✅ Horários adjacentes (sem conflito)

## 🚀 Próximos Passos

### 1. Endpoint: Listar Horários Disponíveis

```python
@router.get("/barbeiro/{barbeiro_id}/horarios-disponiveis")
def horarios_disponiveis(
    barbeiro_id: int,
    data: str,  # "2025-01-15"
    db: Session = Depends(get_db)
):
    """
    Retorna lista de horários disponíveis para um barbeiro em um dia específico.
    
    Exemplo resposta:
    {
        "data": "2025-01-15",
        "barbeiro_id": 1,
        "horarios": ["10:00", "10:30", "11:00", "14:00", "15:00"]
    }
    """
    # Buscar todos os agendamentos do dia
    data_inicio = datetime.strptime(data, "%Y-%m-%d")
    data_fim = data_inicio + timedelta(days=1)
    
    agendamentos = db.query(models.Chamado).filter(
        and_(
            models.Chamado.barbeiro_id == barbeiro_id,
            models.Chamado.data_hora_inicio >= data_inicio,
            models.Chamado.data_hora_inicio < data_fim,
            models.Chamado.status != models.StatusAgendamento.CANCELADO.value
        )
    ).all()
    
    # Gerar slots de 30 minutos (9:00 - 18:00)
    horarios_disponiveis = []
    hora_atual = data_inicio.replace(hour=9, minute=0)
    hora_fim_dia = data_inicio.replace(hour=18, minute=0)
    
    while hora_atual < hora_fim_dia:
        hora_fim_slot = hora_atual + timedelta(minutes=30)
        
        # Verificar se está livre
        if is_horario_disponivel(db, barbeiro_id, hora_atual, hora_fim_slot):
            horarios_disponiveis.append(hora_atual.strftime("%H:%M"))
        
        hora_atual = hora_fim_slot
    
    return {
        "data": data,
        "barbeiro_id": barbeiro_id,
        "horarios": horarios_disponiveis
    }
```

### 2. Componente React: Selector de Horários

```jsx
import { useState, useEffect } from 'react';

export function HorarioSelector({ barbeiro_id, token, apiUrl }) {
  const [data, setData] = useState('');
  const [horarios, setHorarios] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!data || !barbeiro_id) return;

    setLoading(true);
    fetch(
      `${apiUrl}/barbeiro/${barbeiro_id}/horarios-disponiveis?data=${data}`,
      { headers: { 'Authorization': `Bearer ${token}` } }
    )
      .then(r => r.json())
      .then(d => setHorarios(d.horarios))
      .finally(() => setLoading(false));
  }, [data, barbeiro_id]);

  return (
    <div>
      <input
        type="date"
        value={data}
        onChange={(e) => setData(e.target.value)}
        min={new Date().toISOString().split('T')[0]}
      />

      {loading && <p>Carregando horários...</p>}

      {horarios.length > 0 && (
        <div className="grid grid-cols-3 gap-2 mt-3">
          {horarios.map(h => (
            <button
              key={h}
              className="p-2 bg-green-100 hover:bg-green-200 rounded"
              onClick={() => console.log(`Selecionou ${h}`)}
            >
              {h}
            </button>
          ))}
        </div>
      )}

      {!loading && horarios.length === 0 && data && (
        <p className="text-red-500">Nenhum horário disponível</p>
      )}
    </div>
  );
}
```

## 📚 Referências

- **Arquivo com Lógica:** [app/routes.py](app/routes.py#L37-L65)
- **Hook React:** [barbermove/src/hooks/useAgendamentoForm.js](barbermove/src/hooks/useAgendamentoForm.js)
- **Testes:** [test_horarios_disponivel.py](test_horarios_disponivel.py)
- **Status Colors:** [barbermove/src/utils/statusColors.js](barbermove/src/utils/statusColors.js)

## 💡 Dicas

1. **Validar no Cliente:** Antes de enviar, verifica data/hora no React
2. **Validar no Servidor:** Backend faz a verificação final (defesa em profundidade)
3. **Mensagens Amigáveis:** Não mostrar "400 Bad Request", mostrar "Poxa! Alguém pegou esse horário"
4. **Sugestões:** Oferecer horários próximos ou outro dia
5. **Feedback em Tempo Real:** Quando usuário seleciona data, já mostra horários disponíveis

## ⚠️ Casos Especiais

- **Barbeiro não especificado:** Validação não acontece (qualquer horário é aceito, barbeiro a ser definido depois)
- **Agendamentos cancelados:** Ignorados na validação (espaço fica vazio)
- **Múltiplos barbeiros:** Cada um tem agenda independente
- **Duração do serviço:** Calcula automaticamente ou usa 30 min como padrão
