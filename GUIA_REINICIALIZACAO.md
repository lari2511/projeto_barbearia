# 🚀 GUIA DE REINICIALIZAÇÃO DO BARBERMOVE

## ✅ CORREÇÕES JÁ APLICADAS

1. **Erro JSX corrigido:** Frontend agora compila sem erros
2. **Banco resetado:** Novo banco SQLite criado (barbearia.db)
3. **Backup criado:** barbearia_backup_20260226_202855.db (300 KB)

## ⚠️ PROBLEMA DETECTADO

Processos Python órfãos estão impedindo o import de SQLAlchemy.
Requer reinicialização do sistema para resolver completamente.

## 📋 PASSOS APÓS REINICIAR O COMPUTADOR

### 1. Criar Contas de Teste
```powershell
python criar_contas_teste.py
```

### 2. Criar Serviços de Teste  
```powershell
python criar_servicos_teste.py
```

### 3. Iniciar Backend
```powershell
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Aguarde ver:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete.
```

### 4. Iniciar Frontend (em outro terminal)
```powershell
cd barbermove
npm run dev
```

Aguarde ver:
```
VITE v7.2.6  ready in XXX ms
➜  Local:   http://localhost:5173/
```

### 5. Verificar Sistema

Abra no navegador: http://localhost:5173

**Login Teste:**
- Admin: barbermove2024@gmail.com / senha123
- Barbeiro: LARISSA (criar conta nova)
- Cliente: criar conta nova

## 🎯 FEATURES IMPLEMENTADAS (PRONTAS PARA TESTAR)

### 1. Modo Uber - Agendamento Instantâneo
- Quando barbeiro está PRESENTE na barbearia
- Cliente vê botão "Agendar AGORA" ao invés de selecionar data/hora
- Sistema agenda automaticamente para o momento atual

### 2. Filtro de 10km
- Barbearias próximas são filtradas automaticamente
- Cliente só vê barbeiros/barbearias num raio de 10km

### 3. Tempo Estimado (tipo Uber)
- Cards de barbeiros mostram:
  - 📍 Distância em km
  - ⏱ Tempo estimado em minutos
- Cálculo baseado em velocidade média de 40 km/h

### 4. Barbeiros Presentes Aparecem
- Barbeiros com `presente_em_local=True` agora são listados
- Filtro que os excluía foi removido

## 🧪 COMO TESTAR O MODO UBER

1. Criar conta de barbeiro (LARISSA ou outro)
2. No dashboard do barbeiro, fazer check-in em uma barbearia:
   - Clicar em "Check-in Barbearia"
   - Selecionar barbearia
   - Status muda para "PRESENTE"
3. Criar conta de cliente
4. No dashboard do cliente:
   - Permitir geolocalização
   - Selecionar a barbearia onde o barbeiro está presente
   - Escolher o barbeiro
   - Selecionar serviço
   - **Botão deve mostrar "Agendar AGORA"** ao invés de pedir data/hora
5. Confirmar agendamento
6. Verificar no dashboard do barbeiro que apareceu o agendamento imediato

## 📦 ARQUIVOS CRIADOS

- `resetar_banco.py` - Script para resetar banco quando bloqueado
- `criar_sqlite_simples.py` - Criar banco SQLite sem imports complexos
- `test_sqlalchemy_direto.py` - Testar SQLAlchemy standalone
- `test_models.py` - Testar import de models
- `teste_detalhado.py` - Diagnóstico completo de imports

## 🔍 DIAGNÓSTICO SE BACKEND NÃO SUBIR

```powershell
# 1. Verificar se porta está livre
netstat -ano | Select-String ":8000"

# 2. Verificar processos Python
Get-Process python -ErrorAction SilentlyContinue

# 3. Matar processos órfãos (se necessário)
Get-Process python -ErrorAction SilentlyContinue | Stop-Process -Force

# 4. Testar conexão com banco
python test_sqlalchemy_direto.py > test_log.txt 2>&1
Get-Content test_log.txt
```

## 🎨 CÓDIGO DO MODO UBER

### Backend (routes.py linha ~1499)
```python
# Calcular tempo estimado: velocidade média 40 km/h em zona urbana
tempo_minutos = int((distancia / 40) * 60)

barbeiros_proximos.append({
    "distancia_km": round(distancia, 2),
    "tempo_estimado_minutos": tempo_minutos,
    # ... outros campos ...
})
```

### Frontend (ClientDashboard.jsx linha ~200)
```javascript
// Detectar se barbeiro está PRESENTE (modo Uber)
const ehAgendamentoAgora = selectedBarber?.presente_em_local && 
                           selectedBarber?.barbearia_atual_id === selectedBarbearia?.id;

const mensagemAgendamento = ehAgendamentoAgora ? "Agendar AGORA" : "Agendar";
const horarioAgendamento = ehAgendamentoAgora 
    ? new Date().toISOString()  // AGORA instantâneo
    : (dataHoraInicio ? new Date(dataHoraInicio).toISOString() : null);
```

### UI Distância/Tempo (ClientDashboard.jsx linha ~397)
```jsx
{barber.distancia_km !== undefined && (
    <div className="px-2 pb-2 flex items-center justify-between text-xs text-zinc-400 border-t border-zinc-800 pt-2">
        <div className="flex items-center gap-1">
            <MapPin size={12} />
            <span>{barber.distancia_km} km</span>
        </div>
        {barber.tempo_estimado_minutos !== undefined && (
            <div className="text-orange-400 font-bold">
                ⏱ {barber.tempo_estimado_minutos} min
            </div>
        )}
    </div>
)}
```

## 💡 PRÓXIMOS PASSOS (OPCIONAL)

1. Descomentar endpoint `/barbearias/proximas` em routes.py (linha 587)
2. Implementar notificações push quando barbeiro aceitar agendamento
3. Adicionar tracking em tempo real da posição do barbeiro
4. Sistema de fila quando barbeiro está ocupado

## 📞 SUPORTE

Se backend continuar travando após reiniciar:
1. Deletar `barbearia.db` e executar `python criar_sqlite_simples.py`
2. Verificar se há antivírus bloqueando processos Python
3. Reinstalar dependências: `pip install -r requirements.txt --force-reinstall`
4. Verificar logs de erro no VS Code

---
**Última atualização:** 26/02/2026 20:30
**Status:** Sistema pronto para testes após reinicialização
