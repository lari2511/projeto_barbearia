# 🎓 GUIA PASSO A PASSO: USAR O NOVO SISTEMA

## 👨‍💼 PARA O BARBEIRO

### 1️⃣ Fazer Upload de Portfólio

**Passo 1:** Fazer login no app
```
Email: lari.nascimento20148@gmail.com
Senha: [sua senha]
```

**Passo 2:** Encontrar seção "Portfólio"
```
Dashboard do Barbeiro → Portfólio
```

**Passo 3:** Preencher formulário
```
Tipo de Serviço: [Corte ▼]
URL da imagem: [deixar em branco ou colar URL]
Arquivo: [Selecionar arquivo local]
Descrição: [ex: "Corte degradado moderno"]
```

**Passo 4:** Clicar em "Adicionar ao portfólio"
```
✅ "Foto adicionada ao portfólio!"
```

**Resultado:**
- Foto salva no banco de dados
- Aparece na lista de portfólio
- Pode deletar depois se quiser

---

### 2️⃣ Fazer Upload de Documentos

**Passo 1:** Rolar até "Verificação de Documentos"
```
Dashboard do Barbeiro → Verificação de Documentos
```

**Passo 2:** Preencher número do documento
```
RG/CNH: [ex: 123456789]
```

**Passo 3:** Selecionar 3 imagens
```
1. Frente do documento: [foto da frente]
2. Verso do documento: [foto do verso]
3. Selfie com documento: [sua foto segurando o doc]
```

**Passo 4:** Clicar em "Enviar Documentos"
```
✅ "Documentos enviados para verificação!"
```

**Resultado:**
- Documentos salvos no banco
- Admin vai validar
- Você será notificado quando aprovado

---

## 👔 PARA O ADMIN/BARBEARIA

### 1️⃣ Listar Documentos Pendentes

**Abrir terminal:**
```powershell
cd C:\projeto_barbearia
```

**Executar comando:**
```bash
python admin_documentos.py pendentes
```

**Resultado:**
```
📄 DOCUMENTOS PENDENTES DE VERIFICAÇÃO

1. Larissa Rocha (lari.nascimento20148@gmail.com)
   ID: 2
   RG/CNH: 123456789
   Frente: http://localhost:8000/uploads/documentos/abc123.jpg
   Verso: http://localhost:8000/uploads/documentos/def456.jpg
   Selfie: http://localhost:8000/uploads/documentos/ghi789.jpg
   Status: ⏳ AGUARDANDO VERIFICAÇÃO
```

---

### 2️⃣ Aprovar Documento

**Executar comando:**
```bash
python admin_documentos.py aprovar 2
```

**Resultado:**
```
✅ APROVANDO DOCUMENTO DE: Larissa Rocha
   Email: lari.nascimento20148@gmail.com
   ✅ Documento APROVADO com sucesso!
```

**O que muda no banco:**
```sql
UPDATE usuarios SET 
  documento_verificado = TRUE,
  documento_verificado_em = '2025-01-16 10:30:00'
WHERE id = 2;
```

---

### 3️⃣ Rejeitar Documento

**Executar comando:**
```bash
python admin_documentos.py rejeitar 2 "Foto desfocada, envie novamente"
```

**Resultado:**
```
❌ REJEITANDO DOCUMENTO DE: Larissa Rocha
   Email: lari.nascimento20148@gmail.com
   Motivo: Foto desfocada, envie novamente
   ❌ Documento REJEITADO com sucesso!
```

**O que muda no banco:**
```sql
UPDATE usuarios SET 
  documento_verificado = FALSE,
  documento_rejeitado_motivo = 'Foto desfocada, envie novamente'
WHERE id = 2;
```

---

### 4️⃣ Listar Documentos Verificados

**Executar comando:**
```bash
python admin_documentos.py verificados
```

**Resultado:**
```
✅ DOCUMENTOS VERIFICADOS

✓ Larissa Rocha (lari.nascimento20148@gmail.com)
  Verificado em: 16/01/2025 10:30:00
```

---

### 5️⃣ Listar Documentos Rejeitados

**Executar comando:**
```bash
python admin_documentos.py rejeitados
```

**Resultado:**
```
❌ DOCUMENTOS REJEITADOS

✗ Larissa Rocha (lari.nascimento20148@gmail.com)
  Motivo: Foto desfocada, envie novamente
```

---

## 🔍 VERIFICAR NO BANCO DIRETAMENTE

### Ver Portfólio do Barbeiro
```sql
SELECT id, url, descricao, criado_em 
FROM fotos 
WHERE usuario_id = 2
ORDER BY criado_em DESC;
```

### Ver Documentos do Barbeiro
```sql
SELECT id, email, rg, documento_frente_url, documento_verificado, documento_rejeitado_motivo
FROM usuarios 
WHERE id = 2;
```

### Ver Todas as Fotos
```sql
SELECT u.nome, f.url, f.descricao, f.criado_em
FROM fotos f
JOIN usuarios u ON f.usuario_id = u.id
ORDER BY f.criado_em DESC;
```

---

## 📞 TROUBLESHOOTING

### Problema: Upload de portfólio falha com "URL não informada"
**Solução:** Selecione um arquivo OU preencha uma URL
```
Arquivo: [Selecionar arquivo]  ← OU
URL: http://exemplo.com/foto.jpg
```

### Problema: Upload de documentos falha com "3 documentos obrigatórios"
**Solução:** Selecione EXATAMENTE 3 imagens
```
✅ Frente: [arquivo selecionado]
✅ Verso: [arquivo selecionado]  
✅ Selfie: [arquivo selecionado]
```

### Problema: Comando "python admin_documentos.py" não funciona
**Solução:** Certifique-se que você está no diretório correto
```powershell
# Correto:
cd C:\projeto_barbearia
python admin_documentos.py pendentes

# Errado:
cd C:\
python admin_documentos.py pendentes  # ❌ Arquivo não encontrado
```

### Problema: Documentos não aparecem após upload
**Solução:** Aguarde 2-3 segundos e recarregue a página
```
Frontend faz polling a cada 10 segundos
Se não aparecer, recarregue manualmente: F5
```

---

## ✅ CHECKLIST DE USO

### Barbeiro
- [ ] Fiz upload de pelo menos 1 foto de portfólio
- [ ] Enviei meus documentos (RG frente, verso e selfie)
- [ ] Aguardei a validação do admin
- [ ] Vi a mensagem de "Documentos verificados ✅"

### Admin
- [ ] Executei `python admin_documentos.py pendentes`
- [ ] Vi os documentos pendentes
- [ ] Aprovei ou rejeitei cada um
- [ ] Notifiquei o barbeiro do resultado

---

## 🎉 PRÓXIMOS PASSOS

1. **Barbeiro:**
   - [ ] Adicionar mais fotos ao portfólio
   - [ ] Enviar documentos para validação
   - [ ] Aguardar aprovação

2. **Admin:**
   - [ ] Validar documentos periodicamente
   - [ ] Comunicar com barbeiro sobre rejeitados
   - [ ] Monitorar novos uploads

3. **Sistema:**
   - [ ] Barbeiro aprovado pode receber chamados
   - [ ] Portfólio aparece no perfil público
   - [ ] Histórico de documentos armazenado

---

## 📊 RESUMO RÁPIDO

| Ação | Comando |
|------|---------|
| Ver pendentes | `python admin_documentos.py pendentes` |
| Ver aprovados | `python admin_documentos.py verificados` |
| Ver rejeitados | `python admin_documentos.py rejeitados` |
| Aprovar ID 2 | `python admin_documentos.py aprovar 2` |
| Rejeitar ID 2 | `python admin_documentos.py rejeitar 2 "motivo"` |

---

## 📱 URLS ÚTEIS

| Funcionalidade | URL |
|----------------|-----|
| Login | http://localhost:5173/login |
| Dashboard Barbeiro | http://localhost:5173/ (após login) |
| API - Status Doc | GET http://localhost:8000/api/v1/documentos/status |
| API - Upload Doc | POST http://localhost:8000/api/v1/documentos/upload |
| API - Portfólio | POST http://localhost:8000/api/v1/barbeiro/portfolio |

---

**Pronto! Você está usando o novo sistema de portfólio e documentos! 🎉**
