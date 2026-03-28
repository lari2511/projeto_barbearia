# 🔗 INTEGRAÇÃO DE NOTIFICAÇÕES AOS FLUXOS EXISTENTES

## Objetivo
Conectar o sistema de notificações aos fluxos reais de negócio (criar chamados, aceitar chamados, etc)

---

## 1️⃣ NOTIFICAÇÃO: Novo Chamado Criado

### Onde integrar?
Quando cliente cria novo chamado → Barbeiro recebe notificação

### Arquivo: `app/routes.py` → `criar_chamado()`
```python
from app.routes_notificacoes import criar_notificacao_novo_chamado

@router.post("/api/v1/chamados")
def criar_chamado(
    dados: CriarChamadoRequest,
    db: Session = Depends(get_db),
    usuario = Depends(get_current_user),
    background_tasks  # 🔴 ADICIONAR
):
    # ... código existente ...
    
    # Criar chamado no BD
    novo_chamado = Chamado(...)
    db.add(novo_chamado)
    db.commit()
    
    # 🔴 NOVO: Criar notificação para barbeiro
    background_tasks.add_task(
        criar_notificacao_novo_chamado,
        barbeiro_id=dados.barbeiro_id,
        chamado_id=novo_chamado.id,
        cliente_nome=usuario.nome,
        servico_nome=novo_chamado.servico.nome if novo_chamado.servico else "Serviço",
        db=db
    )
    
    return {"id": novo_chamado.id, "status": "criado"}
```

---

## 2️⃣ NOTIFICAÇÃO: Barbeiro Aceita Chamado

### Onde integrar?
Quando barbeiro aceita um chamado → Cliente recebe notificação

### Arquivo: `app/routes_freelancer.py` → `aceitar_chamado()`
```python
from app.routes_notificacoes import criar_notificacao_chamado_aceito

@router.post("/api/v1/chamados/{chamado_id}/aceitar")
def aceitar_chamado(
    chamado_id: int,
    db: Session = Depends(get_db),
    usuario = Depends(get_current_user),
    background_tasks  # 🔴 ADICIONAR
):
    chamado = db.query(Chamado).filter(Chamado.id == chamado_id).first()
    
    if not chamado:
        raise HTTPException(status_code=404)
    
    # Aceitar chamado
    chamado.status = StatusChamado.CONFIRMADO
    db.commit()
    
    # 🔴 NOVO: Notificar cliente
    background_tasks.add_task(
        criar_notificacao_chamado_aceito,
        cliente_id=chamado.cliente_id,
        chamado_id=chamado.id,
        barbeiro_nome=usuario.nome,
        db=db
    )
    
    return {"status": "aceito"}
```

---

## 3️⃣ NOTIFICAÇÃO: Barbeiro Rejeita Chamado

### Onde integrar?
Quando barbeiro rejeita um chamado → Cliente recebe notificação

### Arquivo: `app/routes_freelancer.py` → `rejeitar_chamado()`
```python
from app.routes_notificacoes import criar_notificacao_chamado_rejeitado

@router.post("/api/v1/chamados/{chamado_id}/rejeitar")
def rejeitar_chamado(
    chamado_id: int,
    db: Session = Depends(get_db),
    usuario = Depends(get_current_user),
    background_tasks  # 🔴 ADICIONAR
):
    chamado = db.query(Chamado).filter(Chamado.id == chamado_id).first()
    
    if not chamado:
        raise HTTPException(status_code=404)
    
    # Rejeitar
    chamado.status = StatusChamado.CANCELADO
    db.commit()
    
    # 🔴 NOVO: Notificar cliente
    background_tasks.add_task(
        criar_notificacao_chamado_rejeitado,
        cliente_id=chamado.cliente_id,
        chamado_id=chamado.id,
        barbeiro_nome=usuario.nome,
        db=db
    )
    
    return {"status": "rejeitado"}
```

---

## 4️⃣ NOTIFICAÇÃO: Perfil Aprovado

### Já integrado ✅
- **Arquivo**: `app/admin_routes.py` → `aprovar_usuario()`
- **Status**: Email já está sendo enviado automaticamente
- **Próximo**: Adicionar também notificação push no dashboard

```python
# Já está fazendo isso:
background_tasks.add_task(
    send_perfil_approved_email,
    usuario.email,
    usuario.nome,
    usuario.tipo
)

# 🔴 ADICIONAR: Notificação também
background_tasks.add_task(
    criar_notificacao_perfil_aprovado,
    usuario_id=usuario.id,
    db=db
)
```

---

## 📊 PADRÃO DE INTEGRAÇÃO

Sempre seguir este padrão em qualquer endpoint que deba enviar notificação:

```python
@router.post("/seu_endpoint")
def seu_endpoint(
    dados: SeuSchema,
    db: Session = Depends(get_db),
    usuario = Depends(get_current_user),
    background_tasks  # 🔴 Sempre adicionar
):
    # ... lógica principal ...
    
    db.commit()  # Salvar antes de notificar
    
    # 🔴 Notificar em background
    background_tasks.add_task(
        criar_notificacao_X,
        usuario_id=recipient_id,
        titulo="Seu título",
        mensagem="Sua mensagem",
        db=db
    )
    
    return {"status": "ok"}
```

---

## 🎯 IMPORTS NECESSÁRIOS

Em qualquer arquivo que use notificações:

```python
from fastapi import BackgroundTasks
from app.routes_notificacoes import (
    criar_notificacao_novo_chamado,
    criar_notificacao_chamado_aceito,
    criar_notificacao_chamado_rejeitado,
    criar_notificacao_perfil_aprovado
)
```

---

## 🧪 TESTE DE INTEGRAÇÃO

### 1. Verificar se notificação foi criada
```bash
# Após criar um chamado:
curl http://localhost:8000/api/v1/notificacoes/ \
  -H "Authorization: Bearer {token_do_barbeiro}"
```

### 2. Verificar contador de não-lidas
```bash
curl http://localhost:8000/api/v1/notificacoes/nao-lidas/count \
  -H "Authorization: Bearer {token}"
```

### 3. Marcar como lida
```bash
curl -X POST http://localhost:8000/api/v1/notificacoes/1/marcar-lida \
  -H "Authorization: Bearer {token}"
```

---

## 📋 CHECKLIST DE INTEGRAÇÃO

- [ ] Adicionar `BackgroundTasks` ao parâmetro de `criar_chamado()`
- [ ] Importar `criar_notificacao_novo_chamado`
- [ ] Chamar `background_tasks.add_task()` após salvar chamado
- [ ] Testar criando novo chamado
- [ ] Verificar se barbeiro recebe notificação
- [ ] Repetir para `aceitar_chamado()`
- [ ] Repetir para `rejeitar_chamado()`
- [ ] Testar marcar como lida
- [ ] Testar contar não-lidas

---

## 🔄 FLUXO COMPLETO (Com Notificações)

```
1. Cliente cria chamado
   ↓
   🔔 Barbeiro recebe: "Novo Chamado! 📞"
   
2. Barbeiro aceita chamado
   ↓
   🔔 Cliente recebe: "Chamado Aceito! ✅"
   
3. Barbeiro completa serviço
   ↓
   Cliente pode avaliar
   
4. Admin aprova perfil de novo barbeiro
   ↓
   🔔 Barbeiro recebe: "Perfil Aprovado! 🎉"
   + 📧 Email de aprovação
```

---

## 💾 DADOS DA NOTIFICAÇÃO

Cada notificação armazena:

```json
{
  "id": 1,
  "usuario_id": 5,
  "titulo": "Novo Chamado! 📞",
  "mensagem": "João pediu Corte de Cabelo",
  "tipo": "novo_chamado",
  "lido": false,
  "referencia_id": 123,  // ID do chamado
  "criado_em": "2025-01-15T10:30:00"
}
```

---

## 🚀 PRÓXIMA ETAPA

Após integrar as notificações backend, criar UI frontend:

```jsx
// No header: Mostrar badge
<button>
  🔔 Notificações 
  <span className="badge">{naoLidas}</span>
</button>

// Em drawer/modal:
{notificacoes.map(n => (
  <div onClick={() => marcarComoLida(n.id)}>
    <h4>{n.titulo}</h4>
    <p>{n.mensagem}</p>
    <small>{formatData(n.criado_em)}</small>
  </div>
))}
```

---

**Status**: 🟡 Em Desenvolvimento  
**Versão**: 1.1.0  
**Próxima revisão**: Após integração
