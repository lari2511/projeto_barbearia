# 🚀 SISTEMA DE APROVAÇÃO DE PERFIS - BARBERMOVIE v2

## ✨ Implementações Novas

### 1. **Aprovação Obrigatória** ✅
- **Cliente**, **Barbeiro** e **Barbearia** agora precisam de aprovação do admin
- Perfil não aprovado = **SEM ACESSO** ao app
- Tela de espera: "Perfil em Análise" com estimativa de 24h

### 2. **CLI Admin Separado** ✅
- Admin agora é **SEPARADO DO APP**
- Ferramenta CLI (`admin_cli.py`) gerencia aprovações
- Sem interface web (segurança)

### 3. **Geolocalização de Barbearias** ✅
- Barbearias aparecem **SOMENTE** para usuários próximos (até 10km)
- **Zona Norte** ≠ **Zona Leste** (filtro por distância)
- Mesma lógica das cadeiras (Haversine)

### 4. **Novo Endpoint Backend** ✅
- `GET /api/v1/barbearias/proximas?raio_km=10`
  - Retorna barbearias aprovadas e próximas
  - Filtro de distância automático
  - Incluindo distância em km

### 5. **Nova Aba no Cliente** ✅
- ClientDashboard agora tem 3 abas:
  1. **Barbeiros** - Barbeiros freelancers próximos
  2. **Lojas** - Barbearias próximas e aprovadas ✨ NOVO
  3. **Agenda** - Seus agendamentos

---

## 🔧 COMO USAR

### **PASSO 1: Marcar Usuários Existentes Como Aprovados**

```bash
cd c:\projeto_barbearia
python marcar_como_aprovados.py
```

**Output esperado:**
```
╔════════════════════════════════════════════════════════════════════╗
║ 🚀 MARCANDO USUÁRIOS EXISTENTES COMO APROVADOS                   ║
╚════════════════════════════════════════════════════════════════════╝

📋 Encontrados 5 usuários para aprovar

✅   1 | João Silva              | barbeiro   | joao@email.com
✅   2 | Maria Santos            | cliente    | maria@email.com
✅   3 | BarberShop XYZ          | barbearia  | shop@email.com
... (mais usuários)

✅ SUCESSO! 5 usuários marcados como aprovados!

📊 ESTATÍSTICAS:
   Total de usuários: 5
   Aprovados: 5
   Pendentes: 0
```

---

### **PASSO 2: Usar a CLI Admin**

```bash
cd c:\projeto_barbearia
python admin_cli.py
```

**Menu Principal:**
```
╔════════════════════════════════════════════════════════════════════╗
║ 🔧 ADMIN CLI - BarberMovie                                        ║
╚════════════════════════════════════════════════════════════════════╝

1. 📋 Listar perfis pendentes
2. ✅ Listar perfis aprovados
3. ✨ Aprovar um perfil
4. ❌ Rejeitar um perfil
5. 🚪 Sair

Escolha uma opção (1-5): _
```

**Opção 1: Listar Pendentes**
```
📋 PERFIS PENDENTES DE APROVAÇÃO (2)

1. 👤 Carlos Silva
   📧 Email: carlos@email.com
   🏷️  Tipo: BARBEIRO
   📞 Telefone: (11) 99999-8888
   🆔 RG: 12345678900
   📅 Cadastrado em: 17/01/2026 14:30:45
   
   📄 DOCUMENTOS:
      • Frente: ✅
      • Verso: ✅
      • Selfie: ✅
      • Email Verificado: ✅

2. 👤 Ana Costa
   📧 Email: ana@email.com
   🏷️  Tipo: CLIENTE
   📞 Telefone: Não informado
   🆔 RG: Não informado
   📅 Cadastrado em: 17/01/2026 15:10:20
   
   📄 DOCUMENTOS:
      • Frente: ❌
      • Verso: ❌
      • Selfie: ❌
      • Email Verificado: ✅
```

**Opção 3: Aprovar Perfil**
```
1. 📋 Listar perfis pendentes
...
[menu apareça]

Digite o número do perfil para aprovar (0 para cancelar): 1

✅ PERFIL APROVADO!
   👤 Carlos Silva
   📧 carlos@email.com
   🏷️  Tipo: BARBEIRO
   ✨ Agora pode usar o app!
```

**Opção 4: Rejeitar Perfil**
```
Digite o número do perfil para rejeitar (0 para cancelar): 2
Digite o motivo da rejeição (ou deixe em branco): Documentos incompletos, falta selfie

⚠️  REJEITANDO PERFIL
   👤 Ana Costa
   📧 ana@email.com
   Motivo: Documentos incompletos, falta selfie

✅ Perfil deletado com sucesso!
```

---

## 🎯 FLUXO DO USUÁRIO

### **1️⃣ Cadastro**
```
Usuário preenche:
├─ Nome, Email, Senha
├─ Telefone, Localização (lat/long)
└─ (Futuramente) Documentos (frente, verso, selfie)

Status: perfil_aprovado = FALSE
```

### **2️⃣ Email Verificado**
```
Admin vê perfil pendente na CLI:
├─ Verifica documentos
├─ Aprova se OK ✅ ou Rejeita ❌
│
└─ Se Aprovado:
   ├─ perfil_aprovado = TRUE
   ├─ perfil_aprovado_em = datetime.now()
   └─ Email enviado ao usuário ✨ (futuro)
```

### **3️⃣ Acesso ao App**
```
Frontend verifica:
├─ Se perfil_aprovado = FALSE → Mostra "Perfil em Análise"
├─ Se perfil_aprovado = TRUE → Acesso liberado
│  ├─ Cliente pode ver barbearias próximas
│  ├─ Barbeiro pode oferecer cadeiras
│  └─ Barbearia aparece somente para zona próxima
└─ Botão "Verificar Novamente" recarrega status
```

---

## 📍 LÓGICA DE GEOLOCALIZAÇÃO

### **Cliente na Zona Leste**
```
Cliente lat/long: -23.5505, -46.6333 (São Paulo - Zona Leste)

Sistema busca barbearias com raio 10km:
├─ Barbearia A: -23.5510, -46.6340 → DISTÂNCIA 0.1km ✅ MOSTRA
├─ Barbearia B: -23.5450, -46.6350 → DISTÂNCIA 0.7km ✅ MOSTRA
├─ Barbearia C: -23.4500, -46.5000 → DISTÂNCIA 120km ❌ NÃO MOSTRA (Zona Norte)
└─ Barbearia D: não aprovada ❌ NÃO MOSTRA (filtro perfil_aprovado=True)
```

### **Cálculo (Fórmula de Haversine)**
```python
def calcular_distancia(lat1, lon1, lat2, lon2):
    R = 6371  # Raio da Terra em km
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    return R * c
```

---

## 📊 ENDPOINTS NOVOS

### **Frontend**
```
GET /api/v1/barbearias/proximas?raio_km=10
  Headers: Authorization: Bearer {token}
  
  Resposta:
  {
    "total": 3,
    "raio_km": 10.0,
    "localizacao": {
      "latitude": -23.5505,
      "longitude": -46.6333
    },
    "barbearias": [
      {
        "id": 1,
        "nome": "BarberShop Centro",
        "endereco": "Rua A, 123",
        "telefone": "(11) 99999-8888",
        "distancia_km": 0.5,
        "aprovado_em": "2026-01-16T14:30:00"
      },
      ...
    ]
  }

GET /api/v1/barbearias/todas-aprovadas
  Headers: Authorization: Bearer {token}
  
  Resposta: Lista TODAS as barbearias aprovadas (sem filtro de distância)

GET /api/v1/barbearias/{id}
  Headers: Authorization: Bearer {token}
  
  Resposta: Detalhes de uma barbearia específica
```

---

## ✅ CHECKLIST DE TESTE

- [ ] Executar `python marcar_como_aprovados.py` - todos os usuários marcados
- [ ] Abrir app - usuários antigos conseguem acessar
- [ ] Executar `python admin_cli.py` - CLI abre corretamente
- [ ] Listar pendentes - CLI mostra usuários corretamente
- [ ] Listar aprovados - CLI mostra usuários corretamente
- [ ] Criar novo usuário - aparece como pendente
- [ ] Aprovar novo usuário na CLI - status muda
- [ ] Novo usuário entra no app - vê "Perfil em Análise" até ser aprovado
- [ ] Cliente na Zona Leste vê apenas barbearias próximas
- [ ] Cliente sem localização vê todas as barbearias aprovadas
- [ ] Barbearia não aprovada NÃO aparece para ninguém
- [ ] Botão "Verificar Novamente" atualiza status em tempo real

---

## 🔐 SEGURANÇA

✅ Admin CLI não acessa internet (local-only)
✅ Admin CLI requer acesso ao banco PostgreSQL
✅ Barbearias não aprovadas são filtradas em todo lugar
✅ Usuários sem localização recebem aviso no app
✅ Distância é sempre verificada servidor-side

---

## 🚀 PRÓXIMAS FASES

**Fase 2: Documentos na Signup**
- [ ] Adicionar upload de documentos ao cadastro
- [ ] Frente, Verso, Selfie obrigatórios
- [ ] Validação de imagem (tamanho, formato)

**Fase 3: Notificações por Email**
- [ ] Email ao ser aprovado
- [ ] Email ao ser rejeitado (com motivo)
- [ ] Relembrete diário se pendente > 24h

**Fase 4: Analytics**
- [ ] Dashboard admin: tempo médio de aprovação
- [ ] Motivos de rejeição mais comuns
- [ ] Taxa de aprovação por tipo de usuário

---

**Versão: 2.0 - Aprovação de Perfis**
**Data: 17 de Janeiro de 2026**
**Status: ✅ PRONTO PARA TESTES**
