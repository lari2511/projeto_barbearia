# 🔧 GUIA RÁPIDO DE INTEGRAÇÃO

## 📦 Componentes Criados

✅ `src/components/RatingComponent.jsx` - Avaliação melhorada  
✅ `src/components/PaymentSection.jsx` - Pagamentos/Recebimentos  
✅ `src/components/ProfileCard.jsx` - Perfil visual  

## 📝 MUDANÇAS JÁ FEITAS

✅ Importações adicionadas em `App.jsx`  
✅ Função `enviarAvaliacao` atualizada  
✅ URLs de API corrigidas para `localhost:8000`  

---

## 🎯 PRÓXIMAS AÇÕES (EM ORDEM)

### PASSO 1: Substituir Avaliações Inline
**Localização**: `App.jsx` linhas ~1300-1330

**O que fazer**:
1. Procure por `{selectedOrder?.id === p.id && p.status === 'concluido' && (`
2. Substitua todo o bloco de avaliação inline por:

```jsx
{selectedOrder?.id === p.id && p.status === 'concluido' && (
  <div className="mt-3 grid grid-cols-1 sm:grid-cols-2 gap-3 animate-in fade-in">
    <RatingComponent
      onRate={(data) => enviarAvaliacao(p, 'freelancer', data.nota, data.comentario)}
      targetName={p.nome_barbeiro || 'Barbeiro'}
      color="yellow"
      showComment={true}
    />
    <RatingComponent
      onRate={(data) => enviarAvaliacao(p, 'barbearia', data.nota, data.comentario)}
      targetName={p.nome_barbearia || 'Barbearia'}
      color="orange"
      showComment={true}
    />
  </div>
)}
```

---

### PASSO 2: Adicionar Abas de Pagamento
**Localização**: `App.jsx` em `BarberDashboard` (~linha 1400)

**O que fazer**:
1. Procure por `{tab === 'perfil' && (`
2. Adicione ANTES dele:

```jsx
{tab === 'pagamentos' && (
  <div className="pb-24">
    <PaymentSection 
      userType="barbeiro" 
      token={token} 
      onNotify={notify} 
    />
  </div>
)}
```

3. Procure pelos botões de abas (bottom navigation)
4. Adicione o botão de pagamentos se não existir:

```jsx
<button 
  onClick={() => setTab('pagamentos')} 
  className={`flex flex-col items-center gap-1 p-2 w-16 ${tab === 'pagamentos' ? 'text-green-500' : 'text-zinc-600'}`}
>
  <CreditCard size={20} />
  <span className="text-[10px] font-bold">Ganhos</span>
</button>
```

---

### PASSO 3: Melhorar Layout de Barbeiros (Cliente)
**Localização**: `src/components/ClientDashboard.jsx` (~linha 200)

**Mudança simples**:
```jsx
// ANTES:
<div className="bg-zinc-900 p-4 rounded-2xl border border-zinc-800 cursor-pointer group">

// DEPOIS:
<div className="bg-zinc-900 p-6 rounded-2xl border border-zinc-800 cursor-pointer group hover:border-orange-500/50 transition-all h-full">
```

---

### PASSO 4: Backend - Criar Endpoints

**Arquivo**: `app/routes_extras.py` (ou novo arquivo)

```python
# Endpoint 1: Saldo do Barbeiro
@router.get("/pagamentos/saldo-barbeiro")
def saldo_barbeiro(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    user = get_current_user(token, db)
    if user.tipo != "barbeiro":
        raise HTTPException(status_code=403, detail="Apenas barbeiros")
    
    # Lógica para calcular saldo
    saldo_disponivel = db.query(func.sum(models.Transacao.valor)).filter(
        models.Transacao.usuario_id == user.id,
        models.Transacao.tipo == "credito",
        models.Transacao.status == "disponivel"
    ).scalar() or 0
    
    saldo_retencao = db.query(func.sum(models.Transacao.valor)).filter(
        models.Transacao.usuario_id == user.id,
        models.Transacao.tipo == "credito",
        models.Transacao.status == "retencao"
    ).scalar() or 0
    
    return {
        "saldo_disponivel": saldo_disponivel,
        "saldo_em_retencao": saldo_retencao,
        "comissao_paga": 0,
        "proximo_saque": "2025-02-12"
    }

# Endpoint 2: Saldo da Barbearia
@router.get("/pagamentos/saldo-barbearia")
def saldo_barbearia(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    user = get_current_user(token, db)
    if user.tipo != "barbearia":
        raise HTTPException(status_code=403, detail="Apenas barbearias")
    
    # Similar ao barbeiro
    return {...}

# Endpoint 3: Transações
@router.get("/pagamentos/transacoes")
def listar_transacoes(
    limite: int = 10,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    user = get_current_user(token, db)
    transacoes = db.query(models.Transacao).filter(
        models.Transacao.usuario_id == user.id
    ).order_by(models.Transacao.data.desc()).limit(limite).all()
    
    return transacoes

# Endpoint 4: Solicitar Saque
@router.post("/pagamentos/solicitar-saque")
def solicitar_saque(
    data: dict,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    user = get_current_user(token, db)
    valor = data.get("valor")
    
    # Validar saldo
    # Criar registro de saque
    # Enviar notificação
    
    return {"sucesso": True, "mensagem": "Saque solicitado"}
```

---

### PASSO 5: Backend - Criar Modelo Transacao

**Arquivo**: `app/models.py`

```python
class Transacao(Base):
    __tablename__ = "transacoes"
    
    id = Column(Integer, primary_key=True)
    usuario_id = Column(Integer, ForeignKey("usuario.id"))
    tipo = Column(String)  # "credito" ou "debito"
    valor = Column(Float)
    descricao = Column(String)
    status = Column(String)  # "disponivel" ou "retencao"
    data = Column(DateTime, default=datetime.utcnow)
    
    usuario = relationship("Usuario", back_populates="transacoes")
```

---

### PASSO 6: Backend - Adicionar Média de Avaliações

**Arquivo**: `app/models.py`

```python
# Em Usuario, adicione:
@property
def media_avaliacoes(self):
    avaliacoes = self.avaliacoes_recebidas  # relationship
    if not avaliacoes:
        return 0
    return sum(a.nota for a in avaliacoes) / len(avaliacoes)
```

**Endpoint**:
```python
@router.get("/usuario/{usuario_id}/avaliacoes")
def listar_avaliacoes_usuario(usuario_id: int, db: Session = Depends(get_db)):
    usuario = db.query(models.Usuario).get(usuario_id)
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    
    avaliacoes = db.query(models.Avaliacao).filter(
        models.Avaliacao.avaliado_id == usuario_id
    ).order_by(models.Avaliacao.criado_em.desc()).all()
    
    media = sum(a.nota for a in avaliacoes) / len(avaliacoes) if avaliacoes else 0
    
    return {
        "media": media,
        "total": len(avaliacoes),
        "ultimas": avaliacoes[:5]
    }
```

---

## ✅ CHECKLIST

- [ ] Imports verificados em App.jsx
- [ ] Avaliações substituídas por RatingComponent
- [ ] Abas de pagamento adicionadas
- [ ] Layout de barbeiros melhorado
- [ ] Endpoints de pagamento criados
- [ ] Modelo Transacao criado
- [ ] Média de avaliações calculada
- [ ] Testado em navegador (F12)
- [ ] Testado no celular
- [ ] Deploy realizado

---

## 🆘 ERROS COMUNS

### "RatingComponent não encontrado"
→ Verifique o import em App.jsx: `import RatingComponent from './components/RatingComponent';`

### "PaymentSection não funciona"
→ Certifique-se que os endpoints estão criados no backend

### Avaliação não aparece depois de enviar
→ Recarregue a página ou chame `carregarPedidos()` novamente

---

## 🎉 PRONTO!

Após seguir todos os passos, você terá:
✅ Avaliações que não fecham ao clicar  
✅ Seção de pagamentos/recebimentos  
✅ Perfil visual melhorado  
✅ Sistema de notas na plataforma  
✅ Média de avaliações visível  

Bom trabalho! 🚀
