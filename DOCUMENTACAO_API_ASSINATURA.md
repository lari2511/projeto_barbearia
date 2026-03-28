# 💰 API de Assinatura - Documentação dos Endpoints

## 🎯 Overview

A API de Assinatura fornece endpoints para:
- ✅ Calcular mensalidade progressiva por cadeira (PÚBLICO)
- ✅ Consultar tabela de preços (PÚBLICO)
- ✅ Ativar/atualizar assinatura de barbearia (AUTENTICADO)
- ✅ Consultar detalhes da assinatura (AUTENTICADO)

---

## 📋 Endpoints

### 1. **POST** `/api/v1/assinatura/calcular`
**Calcula a mensalidade progressiva para uma quantidade de cadeiras.**

#### 🔓 Acesso
- **PÚBLICO** - Sem autenticação necessária (apenas cálculo simples)

#### Request
```json
{
    "quantidade_cadeiras": 3
}
```

#### Response (200 OK)
```json
{
    "quantidade_cadeiras": 3,
    "valor_mensal": 100.7,
    "valor_primeira_cadeira": 47.9,
    "valor_minimo_apos_quinta": 17.9,
    "breakdown": [
        {
            "posicao": 1,
            "valor_individual": 47.9,
            "acumulado": 47.9
        },
        {
            "posicao": 2,
            "valor_individual": 27.9,
            "acumulado": 75.8
        },
        {
            "posicao": 3,
            "valor_individual": 24.9,
            "acumulado": 100.7
        }
    ]
}
```

#### Exemplos de Cálculo
```
1 cadeira  → R$ 47.90
2 cadeiras → R$ 75.80
3 cadeiras → R$ 100.70
4 cadeiras → R$ 123.60
5 cadeiras → R$ 143.50
6 cadeiras → R$ 161.40  (a partir daqui: +17.90 cada)
7 cadeiras → R$ 179.30
8 cadeiras → R$ 197.20
10 cadeiras → R$ 233.00
```

---

### 2. **GET** `/api/v1/assinatura/tabela-precos`
**Retorna a tabela completa de preços progressivos.**

#### 🔓 Acesso
- **PÚBLICO** - Sem autenticação necessária

#### Query Parameters
| Parâmetro | Tipo | Default | Descrição |
|-----------|------|---------|-----------|
| `ate_cadeiras` | int | 10 | Até quais cadeiras mostrar na tabela (máx 50) |

#### Example Request
```
GET /api/v1/assinatura/tabela-precos?ate_cadeiras=10
```

#### Response (200 OK)
```json
{
    "tabela_precos": [
        {
            "cadeiras": 1,
            "valor_individual": 47.9,
            "valor_total_mensal": 47.9
        },
        {
            "cadeiras": 2,
            "valor_individual": 27.9,
            "valor_total_mensal": 75.8
        },
        {
            "cadeiras": 3,
            "valor_individual": 24.9,
            "valor_total_mensal": 100.7
        },
        {
            "cadeiras": 4,
            "valor_individual": 22.9,
            "valor_total_mensal": 123.6
        },
        {
            "cadeiras": 5,
            "valor_individual": 19.9,
            "valor_total_mensal": 143.5
        },
        {
            "cadeiras": 6,
            "valor_individual": 17.9,
            "valor_total_mensal": 161.4
        },
        {
            "cadeiras": 7,
            "valor_individual": 17.9,
            "valor_total_mensal": 179.3
        },
        {
            "cadeiras": 8,
            "valor_individual": 17.9,
            "valor_total_mensal": 197.2
        },
        {
            "cadeiras": 9,
            "valor_individual": 17.9,
            "valor_total_mensal": 215.1
        },
        {
            "cadeiras": 10,
            "valor_individual": 17.9,
            "valor_total_mensal": 233.0
        }
    ],
    "valor_primeira_cadeira": 47.9,
    "valor_minimo_apos_quinta": 17.9
}
```

---

### 3. **POST** `/api/v1/assinatura/ativar`
**Ativa ou atualiza a assinatura de uma barbearia.**

#### 🔐 Acesso
- **AUTENTICADO** - Require token JWT
- Apenas dono da barbearia ou admin pode ativar

#### Request Parameters
| Parâmetro | Tipo | Obrigatório | Descrição |
|-----------|------|-------------|-----------|
| `barbearia_id` | int | ✅ | ID da barbearia |
| `quantidade_cadeiras` | int | ✅ | Número de cadeiras (1-50) |

#### Example Request
```json
POST /api/v1/assinatura/ativar?barbearia_id=1&quantidade_cadeiras=3
```

#### Response (200 OK)
```json
{
    "message": "Assinatura ativada com sucesso",
    "barbearia_id": 1,
    "quantidade_cadeiras": 3,
    "valor_mensal": 100.7
}
```

#### Error Responses
| Status | Caso |
|--------|------|
| 401 | Não autenticado |
| 403 | Não é dono da barbearia |
| 404 | Barbearia não encontrada |
| 400 | Quantidade inválida |

---

### 4. **GET** `/api/v1/assinatura/barbearia/{barbearia_id}`
**Obtém detalhes da assinatura de uma barbearia.**

#### 🔐 Acesso
- **AUTENTICADO** - Require token JWT

#### Path Parameters
| Parâmetro | Tipo | Descrição |
|-----------|------|-----------|
| `barbearia_id` | int | ID da barbearia |

#### Example Request
```
GET /api/v1/assinatura/barbearia/1
Authorization: Bearer <token>
```

#### Response (200 OK)
```json
{
    "barbearia_id": 1,
    "quantidade_cadeiras": 3,
    "valor_mensal": 100.7,
    "ativa": true,
    "criada_em": "2026-03-03T12:00:00",
    "breakdown": [
        {
            "posicao": 1,
            "valor_individual": 47.9,
            "acumulado": 47.9
        },
        {
            "posicao": 2,
            "valor_individual": 27.9,
            "acumulado": 75.8
        },
        {
            "posicao": 3,
            "valor_individual": 24.9,
            "acumulado": 100.7
        }
    ]
}
```

---

## 🧮 Lógica de Cálculo

### Preços Progressivos
A mensalidade é calculada de forma **progressiva decrescente** por cadeira:

| Posição | Valor Individual | Motivo |
|---------|------------------|--------|
| 1ª | R$ 47,90 | Cadeira obrigatória, preço alto |
| 2ª | R$ 27,90 | Incentiva expansão |
| 3ª | R$ 24,90 | Continua descendo |
| 4ª | R$ 22,90 | Motiva mais crescimento |
| 5ª | R$ 19,90 | Penúltima antes do piso |
| 6ª+ | R$ 17,90 | **PISO FIXO** - Nunca menor |

### Safeguard
Para garantir a integridade, aplicamos sempre:
```python
valor_cadeira = max(valor_cadeira, VALOR_MINIMO_APOS_QUINTA)
```

Isso assegura que nenhuma cadeira custe menos de R$ 17,90 após a 6ª.

---

## 🔧 Implementação Técnica

### Imports
```python
from .routes_assinatura import router as router_assinatura
```

### No main.py
```python
app.include_router(router_assinatura)  # 💰 Assinatura e cálculo de mensalidades
```

### Exemplo de Uso (Python)
```python
import requests

# Calcular mensalidade
response = requests.post(
    "http://localhost:8000/api/v1/assinatura/calcular",
    json={"quantidade_cadeiras": 3}
)
resultado = response.json()
print(f"R$ {resultado['valor_mensal']}")  # R$ 100.7
```

### Exemplo de Uso (JavaScript/React)
```javascript
// Calcular mensalidade
const response = await fetch("/api/v1/assinatura/calcular", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ quantidade_cadeiras: 3 })
});
const resultado = await response.json();
console.log(`R$ ${resultado.valor_mensal}`);  // R$ 100.7
```

---

## 📊 Status dos Testes

✅ **Todos os endpoints testados e funcionando:**
- POST /calcular (1 cadeira) → **200 OK** ⏱️ Retorna 47.90
- POST /calcular (3 cadeiras) → **200 OK** ⏱️ Retorna 100.70
- POST /calcular (6 cadeiras) → **200 OK** ⏱️ Retorna 161.40
- POST /calcular (10 cadeiras) → **200 OK** ⏱️ Retorna 233.00
- GET /tabela-precos → **200 OK** ⏱️ Retorna 10 linhas

---

## 🚀 Próximos Passos

1. **Integração com Frontend**
   - Usar endpoint `/calcular` em componentes de configuração
   - Exibir `/tabela-precos` em guias de preços

2. **Integração com Fluxo de Assinatura**
   - Chamar `/ativar` ao criar barbearia
   - Usar valores para calcular cobranças

3. **Dashboard Admin**
   - Exibir assinaturas ativas por barbearia
   - Permitir modificação de quantidade de cadeiras
   - Mostrar relatório de receita por assinatura

4. **Notificações**
   - Alertar sobre renovação de assinatura
   - Alertar sobre próximo vencimento

---

## 📝 Notas

- Os valores em JSON são retornados com até 1 casa decimal (47.9 = R$ 47,90)
- Para display em UI, formatar com 2 casas: `valor.toFixed(2)`
- O endpoint `/calcular` é proposital **público** para permitir que clientes vejam preços antes de criar conta
- Os endpoints que modificam dados requerem **autenticação JWT**

