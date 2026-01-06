# 🏪 Serviços por Barbearia (Arquitetura Isolada)

## 📌 Conceito Principal

Cada **barbearia tem seus próprios serviços**, com nomes iguais mas preços diferentes.

```
Barbearia A (João)          Barbearia B (Carlos)
├── Corte - R$ 30           ├── Corte - R$ 50
├── Barba - R$ 20           ├── Barba - R$ 30
└── Combo - R$ 45           └── Combo - R$ 70
```

**São arquivos diferentes no banco!** Cada um é uma linha separate na tabela `servicos`.

## 🗂️ Arquitetura do Banco de Dados

```sql
-- Tabela de Serviços
CREATE TABLE servicos (
    id INTEGER PRIMARY KEY,
    barbearia_id INTEGER NOT NULL,  -- ← O SEGREDO!
    nome VARCHAR(100),              -- Ex: "Corte Masculino"
    descricao TEXT,
    valor FLOAT,                    -- Ex: 35.00
    duracao_minutos INTEGER,        -- Ex: 30
    ativo BOOLEAN DEFAULT TRUE,
    criado_em DATETIME,
    FOREIGN KEY (barbearia_id) REFERENCES barbearias(id)
);

-- Índice para buscar rápido por barbearia
CREATE INDEX idx_servico_barbearia ON servicos(barbearia_id);
```

**Por que `barbearia_id` é NOT NULL?**
- Garante que cada serviço pertence a UMA barbearia
- Impossível ter serviço "órfão" (sem dono)
- Queries são mais eficientes

## 🔄 Fluxos

### 1️⃣ Dono da Barbearia: Cadastro de Serviços (Onboarding)

```
┌─────────────────────────────────────┐
│ "Vamos configurar sua loja!"        │
│ Quais serviços você oferece?        │
└─────────────────────────────────────┘
         ↓
┌─────────────────────────────────────┐
│ [Corte] [Barba] [Combo] [...]       │ ← Templates sugeridos
└─────────────────────────────────────┘
         ↓ (clica em "Corte")
┌─────────────────────────────────────┐
│ ✏️ Personalizar serviço              │
│                                     │
│ Nome: Corte Masculino (pré-preench)│
│ Preço: 30.00 (padrão)     [Editar]  │
│ Duração: 30 min           [Editar]  │
│                                     │
│ [✅ Salvar] [Voltar]               │
└─────────────────────────────────────┘
         ↓
   ✅ Salvo no banco com barbearia_id do dono
```

**Componente:** `CadastroServicosOnboarding.jsx`

**API:**
```
GET /templates/servicos
→ Retorna lista de sugestões (hardcoded no backend)

POST /barbearias/{barbearia_id}/servicos
{
  "nome": "Corte Masculino",
  "descricao": "Com máquina e tesoura",
  "valor": 40.00,
  "duracao_minutos": 30
}
→ Backend adiciona automaticamente barbearia_id (from user context)
```

### 2️⃣ Cliente: Busca Barbearia e Vê Serviços

```
┌─────────────────────────────────────┐
│ Buscar Barbearia Próxima             │
└─────────────────────────────────────┘
         ↓
┌─────────────────────────────────────┐
│ Resultados:                         │
│ ✓ Barbearia João (3 km)             │
│ ✓ Barbearia Carlos (5 km)           │
│ ✓ Studio Abel (7 km)                │
└─────────────────────────────────────┘
         ↓ (clica em "Barbearia João")
┌─────────────────────────────────────┐
│ 💈 Barbearia João                   │
│                                     │
│ ✓ Corte Masculino        R$ 40     │
│   ⏱ 30 min                         │
│                                     │
│ ✓ Barba Completa         R$ 25     │
│   ⏱ 20 min                         │
│                                     │
│ ✓ Combo Corte + Barba    R$ 60     │
│   ⏱ 50 min                         │
└─────────────────────────────────────┘
         ↓ (clica em "Corte Masculino")
         ✓ Vê data/hora disponíveis
         ✓ Confirma agendamento
```

**Componente:** `SeletorServicoBarbearia.jsx`

**API:**
```
GET /barbearias/{barbearia_id}/servicos
→ SELECT * FROM servicos WHERE barbearia_id = ? AND ativo = TRUE

Retorna:
{
  "barbearia_nome": "Barbearia João",
  "servicos": [
    {
      "id": 5,
      "nome": "Corte Masculino",
      "valor": 40.00,
      "duracao_minutos": 30
    },
    ...
  ]
}
```

## 📊 Modelo SQLAlchemy

```python
# ✅ CORRETO: barbearia_id é obrigatório
class Servico(Base):
    __tablename__ = "servicos"
    
    id = Column(Integer, primary_key=True)
    barbearia_id = Column(Integer, ForeignKey("barbearias.id"), nullable=False, index=True)
    nome = Column(String, nullable=False)
    descricao = Column(String, nullable=True)
    valor = Column(Float, nullable=False)
    duracao_minutos = Column(Integer, default=30)
    ativo = Column(Boolean, default=True)  # Soft delete
    criado_em = Column(DateTime, default=datetime.utcnow)
    
    barbearia = relationship("Barbearia", back_populates="servicos")
```

## 🛡️ Validações

### Backend: Isolamento Completo

```python
# Endpoint para criar serviço
@router.post("/barbearias/{barbearia_id}/servicos")
def criar_servico(barbearia_id, servico, token, db):
    user = get_current_user(token)
    
    # ✅ Validação 1: Barbearia existe?
    barbearia = db.query(Barbearia).filter(id=barbearia_id).first()
    if not barbearia:
        return 404  # Não existe
    
    # ✅ Validação 2: Usuário é dono dessa barbearia?
    if barbearia.usuario_id != user.id:
        return 403  # Não autorizado!
    
    # ✅ Validação 3: Gravar SEMPRE com barbearia_id correto
    novo = Servico(
        barbearia_id=barbearia_id,  # Do URL, não da request!
        nome=servico.nome,
        valor=servico.valor,
        duracao_minutos=servico.duracao_minutos
    )
    db.add(novo)
```

**Porque essas validações?**
- Usuário A não consegue criar serviço na barbearia B
- Serviço sempre pertence à barbearia certa (não confunde no banco)
- Dados isolados = segurança garantida

### Frontend: User Experience

```javascript
// Ao selecionar uma barbearia, buscar SEUS serviços
const buscarServicos = async (barbearia_id) => {
  const response = await fetch(
    `${apiUrl}/barbearias/${barbearia_id}/servicos`
  );
  
  // A API retorna APENAS serviços dessa barbearia
  const data = await response.json();
  setServicos(data.servicos);  // Lista já isolada
};
```

## 📝 Endpoints

### Templates (Sugestões)

```
GET /templates/servicos
→ Retorna lista de templates hardcoded
→ Sem autenticação (qualquer um vê)
→ Exemplo: "Corte Masculino - R$ 35, 30 min"
```

### Criar Serviço

```
POST /barbearias/{barbearia_id}/servicos
Header: Authorization: Bearer {token}

Body:
{
  "nome": "Corte Masculino",
  "descricao": "Com máquina e tesoura",
  "valor": 40.00,
  "duracao_minutos": 30
}

Response 201:
{
  "id": 5,
  "barbearia_id": 1,
  "nome": "Corte Masculino",
  "valor": 40.00,
  "mensagem": "✅ Serviço criado com sucesso!"
}
```

### Listar Serviços da Barbearia

```
GET /barbearias/{barbearia_id}/servicos
(sem autenticação obrigatória - cliente vê mesmo anônimo)

Response:
{
  "barbearia_id": 1,
  "barbearia_nome": "Barbearia João",
  "total": 3,
  "servicos": [
    {
      "id": 5,
      "nome": "Corte Masculino",
      "valor": 40.00,
      "duracao_minutos": 30
    },
    ...
  ]
}
```

### Atualizar Serviço

```
PUT /servicos/{servico_id}
Header: Authorization: Bearer {token}

Body (todos opcionais):
{
  "nome": "Corte Premium",
  "valor": 50.00,
  "duracao_minutos": 45,
  "ativo": true
}

Response:
{
  "id": 5,
  "nome": "Corte Premium",
  "valor": 50.00,
  "mensagem": "✅ Serviço atualizado!"
}
```

### Deletar Serviço (Soft Delete)

```
DELETE /servicos/{servico_id}
Header: Authorization: Bearer {token}

Response:
{
  "id": 5,
  "mensagem": "✅ Serviço desativado! (Agendamentos antigos não são afetados)"
}
```

### Meus Serviços (Dashboard do Dono)

```
GET /meus-servicos
Header: Authorization: Bearer {token}

Response:
{
  "total_barbearias": 2,
  "barbearias": [
    {
      "barbearia_id": 1,
      "barbearia_nome": "Barbearia João",
      "total_servicos": 3,
      "servicos": [...]
    },
    {
      "barbearia_id": 2,
      "barbearia_nome": "Studio Alves",
      "total_servicos": 5,
      "servicos": [...]
    }
  ]
}
```

## 🧪 Testes

### Teste 1: Criar Serviços com Nomes Iguais

```python
# Barbearia A cria "Corte" por R$ 30
response1 = POST /barbearias/1/servicos
{
  "nome": "Corte",
  "valor": 30.00,
  "duracao_minutos": 30
}
# Retorna: id=5, barbearia_id=1

# Barbearia B cria "Corte" por R$ 50
response2 = POST /barbearias/2/servicos
{
  "nome": "Corte",
  "valor": 50.00,
  "duracao_minutos": 30
}
# Retorna: id=6, barbearia_id=2

# Verificar isolamento
GET /barbearias/1/servicos
# Retorna apenas [{ id: 5, valor: 30 }]

GET /barbearias/2/servicos
# Retorna apenas [{ id: 6, valor: 50 }]
```

### Teste 2: Segurança (Não Consegue Editar Serviço de Outra)

```python
# João (user_id=1) tenta editar serviço da Barbearia B (usuario_id=2)
user_token = get_token_for_joao()

PUT /servicos/6  # Serviço de Barbearia B
Header: Authorization Bearer {user_token}
Body: { "valor": 100.00 }

# Resposta: 403 Forbidden
# "Você só pode editar serviços da sua própria barbearia"
```

## 🎯 Fluxo Completo: Do Cadastro ao Agendamento

```
┌───────────────────────────────────────────────────────────┐
│ 1. CADASTRO (Dono da Barbearia)                           │
├───────────────────────────────────────────────────────────┤
│                                                           │
│ App mostra templates:                                    │
│ • Corte - R$ 35 (padrão)                                 │
│ • Barba - R$ 25 (padrão)                                 │
│ • Combo - R$ 55 (padrão)                                 │
│                                                           │
│ Dono clica em "Corte"                                    │
│ Form pré-preenchido: R$ 35 / 30 min                     │
│                                                           │
│ Dono edita: "Quero cobrar R$ 40"                        │
│ Clica em "Salvar"                                        │
│                                                           │
│ ✅ Salvo no banco:                                        │
│    id=5, barbearia_id=1, nome="Corte", valor=40.00     │
└───────────────────────────────────────────────────────────┘
         ↓
┌───────────────────────────────────────────────────────────┐
│ 2. AGENDAMENTO (Cliente)                                  │
├───────────────────────────────────────────────────────────┤
│                                                           │
│ Cliente busca barbearias próximas                        │
│ Clica em "Barbearia João"                               │
│                                                           │
│ App executa:                                             │
│ GET /barbearias/1/servicos                              │
│                                                           │
│ Retorna:                                                 │
│ • Corte - R$ 40 / 30 min                                │
│ • Barba - R$ 25 / 20 min                                │
│                                                           │
│ Cliente clica em "Corte R$ 40"                          │
│ ✓ Duração já vem salva: 30 minutos                      │
│                                                           │
│ Cliente seleciona: "20 de janeiro, 14:00"              │
│ ✓ Validação: Horário disponível?                       │
│                                                           │
│ Cliente confirma agendamento                            │
│ ✅ Agendamento criado com valores do snapshot           │
│    valor_total=40.00                                   │
│    duracao_minutos=30                                  │
│    comissao_plataforma=6.00 (15%)                      │
│    valor_freelancer=18.00 (45%)                        │
│    valor_dono=16.00 (40%)                              │
└───────────────────────────────────────────────────────────┘
```

## 🎨 Componentes React

| Componente | Arquivo | Uso |
|---|---|---|
| `CadastroServicosOnboarding` | `CadastroServicosOnboarding.jsx` | Dono cadastra serviços |
| `SeletorServicoBarbearia` | `SeletorServicoBarbearia.jsx` | Cliente seleciona serviço |
| `HorariosDisponiveis` | `useAgendamentoForm.js` | Mostra horários livres |

## ✨ Vantagens da Arquitetura

| Aspecto | Benefício |
|---------|-----------|
| **Isolamento** | Cada barbearia vê apenas seus serviços |
| **Preços Independentes** | "Corte" custa R$ 30 em A e R$ 50 em B |
| **Histórico Preciso** | Agendamentos salvam valores do snapshot |
| **Escalável** | Suporta N barbearias, cada uma com M serviços |
| **Segura** | Validações no backend impedem confusão |
| **UX Clara** | Cliente vê EXATAMENTE o que vai pagar |

## 🚀 Próximos Passos

1. ✅ Criar modelo `Servico` com `barbearia_id` NOT NULL
2. ✅ Criar endpoints CRUD para serviços
3. ✅ Criar componentes React (cadastro + seletor)
4. ✅ Integrar com validação de horários
5. ⏳ Adicionar fotos por serviço
6. ⏳ Permitir combos (ex: "Corte + Barba")
7. ⏳ Avaliar por serviço (não só por barbearia)

## 📚 Arquivos

- **Backend:** [app/routes_servicos.py](app/routes_servicos.py)
- **Models:** [app/models.py](app/models.py#L64-L77)
- **Schemas:** [app/schemas.py](app/schemas.py#L99-L135)
- **Frontend - Cadastro:** [CadastroServicosOnboarding.jsx](barbermove/src/components/CadastroServicosOnboarding.jsx)
- **Frontend - Seleção:** [SeletorServicoBarbearia.jsx](barbermove/src/components/SeletorServicoBarbearia.jsx)

---

**Status:** ✅ Completo e pronto para usar  
**Data:** 28 de dezembro de 2025
