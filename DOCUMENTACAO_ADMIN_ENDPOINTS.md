# 📊 Endpoints Admin para Validação de Documentos

## Visão Geral
O painel de admin permite que gerentes de barbearias (tipo="barbearia") validem os documentos enviados por clientes e barbeiros.

---

## 🔌 Endpoints da API

### 1. GET `/api/v1/documentos/pendentes`
**Descripción:** Lista todos os documentos aguardando verificação

**Headers:**
```
Authorization: Bearer {token}
```

**Response (200):**
```json
[
  {
    "id": 5,
    "nome": "João Silva",
    "email": "joao@email.com",
    "rg": "12345678",
    "tipo": "cliente",
    "documento_frente_url": "/uploads/documentos/frente_123.jpg",
    "documento_verso_url": "/uploads/documentos/verso_123.jpg",
    "selfie_documento_url": "/uploads/documentos/selfie_123.jpg",
    "documento_verificado": false,
    "documento_verificado_em": null,
    "documento_rejeitado_motivo": null
  },
  ...
]
```

**Notas:**
- Retorna apenas documentos com `documento_verificado = false` e sem rejeição
- Usuário deve ter `tipo="barbearia"` para acessar
- Máximo 50 documentos por request

---

### 2. GET `/api/v1/documentos/status`
**Descripción:** Retorna status de documentos do usuário atual

**Headers:**
```
Authorization: Bearer {token}
```

**Response (200):**
```json
{
  "id": 3,
  "nome": "Maria",
  "email": "maria@email.com",
  "rg": "87654321",
  "documento_frente_url": "/uploads/documentos/frente_456.jpg",
  "documento_verso_url": "/uploads/documentos/verso_456.jpg",
  "selfie_documento_url": "/uploads/documentos/selfie_456.jpg",
  "documento_verificado": true,
  "documento_verificado_em": "2024-01-15T10:30:00",
  "documento_rejeitado_motivo": null,
  "email_verificado": true  ← Novo campo!
}
```

---

### 3. POST `/api/v1/documentos/verificar`
**Descripción:** Aprova ou rejeita documentos

**Headers:**
```
Authorization: Bearer {token}
Content-Type: application/json
```

**Request Body:**
```json
{
  "usuario_id": 5,
  "aprovado": true,
  "motivo_rejeicao": null  // Apenas se aprovado=false
}
```

**Exemplo - Aprovar:**
```json
{
  "usuario_id": 5,
  "aprovado": true
}
```

**Exemplo - Rejeitar:**
```json
{
  "usuario_id": 5,
  "aprovado": false,
  "motivo_rejeicao": "RG com números desfocados"
}
```

**Response (200):**
```json
{
  "message": "Documento aprovado com sucesso",
  "usuario_id": 5,
  "documento_verificado": true,
  "documento_verificado_em": "2024-01-15T14:45:00"
}
```

**Response (200) - Rejeição:**
```json
{
  "message": "Documento rejeitado com sucesso",
  "usuario_id": 5,
  "documento_verificado": false,
  "documento_rejeitado_motivo": "RG com números desfocados"
}
```

**Erros possíveis:**
- `400` - Dados incompletos
- `401` - Não autenticado
- `403` - Sem permissão (não é barbearia)
- `404` - Usuário não encontrado
- `409` - Documento já foi verificado

---

## 🎨 UI do AdminPanel

### Layout
```
┌─────────────────────────────────────────────────────────────────┐
│ 📊 Painel de Admin                                    [← Voltar] │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│  │📄 Documentos     │  │✅ Aprovados      │  │❌ Rejeitados     │
│  │  Pendentes       │  │  45              │  │  12              │
│  │  23              │  │                  │  │                  │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘
│
├─────────────────────────────────────────────────────────────────┤
│ Documentos Pendentes                                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│ ┌───────────────────────────────────────────────────────────┐  │
│ │ João Silva (joao@email.com)                         ⏳     │
│ │ RG: 12345678                                             │  │
│ │ 📷 [Frente] [Verso] [Selfie]                            │  │
│ │ ┌──────────────────┐ ┌──────────────────┐              │  │
│ │ │ ✅ Aprovar       │ │ ❌ Rejeitar       │              │  │
│ │ └──────────────────┘ └──────────────────┘              │  │
│ └───────────────────────────────────────────────────────────┘  │
│                                                                 │
│ ┌───────────────────────────────────────────────────────────┐  │
│ │ Maria Santos (maria@email.com)                       ⏳     │
│ │ RG: 87654321                                             │  │
│ │ 📷 [Frente] [Verso] [Selfie]                            │  │
│ │ ┌──────────────────┐ ┌──────────────────┐              │  │
│ │ │ ✅ Aprovar       │ │ ❌ Rejeitar       │              │  │
│ │ └──────────────────┘ └──────────────────┘              │  │
│ └───────────────────────────────────────────────────────────┘  │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│ [⏳ Pendentes] [✅ Aprovados] [❌ Rejeitados]                   │
└─────────────────────────────────────────────────────────────────┘
```

### Estados dos Documentos

**⏳ Pendente**
- Cor: Amarelo (yellow-600/20)
- Botões: Aprovar | Rejeitar
- Descrição: Aguardando análise do admin

**✅ Aprovado**
- Cor: Verde (green-600/20)
- Botões: Nenhum (apenas exibição)
- Descrição: Documento validado

**❌ Rejeitado**
- Cor: Vermelho (red-600/20)
- Exibe: Motivo da rejeição
- Botões: Nenhum (apenas exibição)

---

## 🔐 Segurança

### Verificações Implementadas:
1. ✅ Usuario deve estar autenticado (Bearer token)
2. ✅ Usuario deve ter `tipo="barbearia"`
3. ✅ Documentos de clientes/barbeiros não podem ser alterados por outros admins
4. ✅ Histórico de aprovação/rejeição é registrado

### Campos Sensíveis:
- URLs de documentos apontam para `/uploads/documentos/`
- Apenas usuários autenticados podem acessar
- Cache disabled para documentos

---

## 📱 Acesso via AdminPanel (Frontend)

### Passo 1: Login
```
Login como usuário tipo="barbearia"
```

### Passo 2: Navegação
```
Clique no botão "📊 Admin" no header
```

### Passo 3: Ações
```
Ver documentos pendentes → Aprovar/Rejeitar → Lista atualiza
```

---

## 🛠️ Integração com AdminPanel

### Fetch de Documentos Pendentes:
```javascript
const carregarDocumentos = async () => {
  const r = await fetch(`${API_URL}/api/v1/documentos/pendentes`, {
    headers: { 'Authorization': `Bearer ${token}` }
  });
  const data = await r.json();
  setDocumentos(data);
};
```

### Aprovar Documento:
```javascript
const aprovarDocumento = async (usuarioId) => {
  const r = await fetch(`${API_URL}/api/v1/documentos/verificar`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
    body: JSON.stringify({ usuario_id: usuarioId, aprovado: true })
  });
  // Recarrega lista
  carregarDocumentos();
};
```

### Rejeitar Documento:
```javascript
const rejeitarDocumento = async (usuarioId, motivo) => {
  const r = await fetch(`${API_URL}/api/v1/documentos/verificar`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
    body: JSON.stringify({ 
      usuario_id: usuarioId, 
      aprovado: false, 
      motivo_rejeicao: motivo 
    })
  });
  // Recarrega lista
  carregarDocumentos();
};
```

---

## 📊 Exemplo de Fluxo Completo

```
1. Admin (barbearia) clica "📊 Admin"
   ↓
2. AdminPanel carrega e faz fetch de /documentos/pendentes
   ↓
3. Recebe lista com 3 documentos pendentes
   ↓
4. Mostra cards com informações
   ↓
5. Admin clica "✅ Aprovar" para João
   ↓
6. Envia POST para /documentos/verificar com {usuario_id: 5, aprovado: true}
   ↓
7. API atualiza documento_verificado=true no BD
   ↓
8. AdminPanel recarrega lista automaticamente
   ↓
9. João some da lista de pendentes
   ↓
10. Contadores atualizam (Pendentes: 3→2, Aprovados: 45→46)
```

---

## 🚨 Tratamento de Erros

### Erro 401 - Não autenticado
```javascript
if (r.status === 401) {
  notify('Sessão expirada', 'error');
  // Redireciona para login
}
```

### Erro 403 - Sem permissão
```javascript
if (r.status === 403) {
  notify('Apenas barbearias podem validar documentos', 'error');
}
```

### Erro 404 - Usuário não encontrado
```javascript
if (r.status === 404) {
  notify('Usuário não encontrado', 'error');
}
```

### Erro 409 - Já verificado
```javascript
if (r.status === 409) {
  notify('Este documento já foi verificado', 'error');
}
```

---

## 📈 Métricas & Monitoramento

### O que rastrear:
- ✅ Total de documentos pendentes
- ✅ Taxa de aprovação vs rejeição
- ✅ Tempo médio de análise
- ✅ Motivos mais comuns de rejeição

### Consultas SQL úteis:
```sql
-- Total pendentes
SELECT COUNT(*) FROM usuarios WHERE documento_verificado = false AND documento_rejeitado_motivo IS NULL;

-- Taxa de aprovação
SELECT 
  SUM(CASE WHEN documento_verificado=true THEN 1 ELSE 0 END) as aprovados,
  SUM(CASE WHEN documento_rejeitado_motivo IS NOT NULL THEN 1 ELSE 0 END) as rejeitados;

-- Motivos de rejeição
SELECT documento_rejeitado_motivo, COUNT(*) as total 
FROM usuarios 
GROUP BY documento_rejeitado_motivo;
```

---

## ✨ Funcionalidades Futuras

- [ ] Notificação por email quando documento é aprovado/rejeitado
- [ ] Busca por nome/email no admin panel
- [ ] Paginação para muitos documentos
- [ ] Export de relatório em PDF
- [ ] Dashboard com gráficos
- [ ] Foto em alta resolução no modal
- [ ] Histórico de ações administrativas
- [ ] Aprovação em lote

