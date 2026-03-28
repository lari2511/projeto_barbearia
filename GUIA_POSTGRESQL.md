# 🐘 GUIA: Como Conectar BarberMove ao PostgreSQL

## ❌ Problema Atual
O PostgreSQL não está rodando no seu computador.

---

## ✅ SOLUÇÃO 1: Iniciar o PostgreSQL

### Windows:
1. Aperte **Windows + R**
2. Digite: `services.msc` e aperte Enter
3. Procure por **"postgresql"** na lista
4. Clique com botão direito → **Iniciar**

**OU**

1. Abra o **pgAdmin 4**
2. Se pedir senha, digite a senha que você configurou na instalação
3. Se conectar, o PostgreSQL está rodando!

---

## ✅ SOLUÇÃO 2: Instalar PostgreSQL (se não tiver)

Se você não tem PostgreSQL instalado:

1. **Baixar:** https://www.postgresql.org/download/windows/
2. **Instalar:** 
   - Durante instalação, defina senha (anote ela!)
   - Port: 5432 (padrão)
   - Instalar Stack Builder: NÃO (não precisa)
3. **Depois de instalar:** 
   - O PostgreSQL inicia automaticamente
   - pgAdmin 4 é instalado junto

---

## 🔧 CONFIGURAR BARBERMOVE APÓS POSTGRESQL RODANDO

### 1. Atualize a senha no .env (se não for "postgres"):

```env
DATABASE_URL=postgresql://postgres:SUA_SENHA_AQUI@localhost:5432/barbermove
```

### 2. Execute o script de configuração:

```powershell
python setup_postgres.py
```

Isso vai:
- ✅ Criar o banco "barbermove"
- ✅ Criar todas as tabelas
- ✅ Mostrar as credenciais para pgAdmin

---

## 📊 CONECTAR NO PGADMIN

### Opção A: Se pgAdmin já está aberto

1. Clique com botão direito em **"Servers"**
2. **Register** → **Server**
3. Preencha:
   
   **Aba General:**
   - Name: `BarberMove`
   
   **Aba Connection:**
   - Host: `localhost`
   - Port: `5432`
   - Maintenance database: `barbermove` (depois que criar)
   - Username: `postgres`
   - Password: `sua senha do postgres`
   - ☑️ Save password
   
4. Clique **Save**

### Opção B: Conectar ao banco padrão primeiro

Se o banco `barbermove` ainda não existe:

1. Conecte ao banco **postgres** (banco padrão)
   - Host: `localhost`
   - Database: `postgres`
   - Username: `postgres`
   - Password: `sua senha`

2. Depois rode: `python setup_postgres.py`

3. Atualize a conexão para o banco `barbermove`

---

## 🎯 CREDENCIAIS PADRÃO

```
Host:     localhost
Port:     5432
Database: barbermove
Username: postgres
Password: postgres (ou a senha que você definiu)
```

---

## 🚀 DEPOIS DE CONECTAR

Você verá as tabelas:
- ✅ usuarios
- ✅ chamados
- ✅ servicos
- ✅ avaliacoes
- ✅ cupons
- ✅ pagamentos
- ✅ notificacoes
- E mais...

---

## 🔄 MIGRAR DADOS DO SQLITE (se tiver)

Se você já tem dados no SQLite e quer migrar:

```powershell
# 1. Exportar dados do SQLite
python exportar_sqlite.py

# 2. Importar no PostgreSQL
python importar_postgres.py
```

(Scripts podem ser criados se precisar)

---

## ❓ DÚVIDAS COMUNS

**Q: Esqueci a senha do postgres**
A: Reinstale o PostgreSQL ou redefina pelo pgAdmin

**Q: Port 5432 já está em uso**
A: Outro programa está usando. Mude a porta no PostgreSQL ou pare o outro programa

**Q: Não consigo conectar**
A: Verifique se o serviço está rodando em `services.msc`

**Q: Prefiro continuar com SQLite**
A: No .env, mude de volta:
```env
DATABASE_URL=sqlite:///./barbearia.db
```

---

## 📞 PRÓXIMOS PASSOS

1. ✅ Inicie o PostgreSQL
2. ✅ Execute: `python setup_postgres.py`
3. ✅ Abra o pgAdmin
4. ✅ Conecte ao banco "barbermove"
5. ✅ Visualize as tabelas!

---

**Status:** Aguardando você iniciar o PostgreSQL! 🐘
