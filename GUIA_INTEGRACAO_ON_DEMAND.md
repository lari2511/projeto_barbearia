# 🚀 GUIA DE INTEGRAÇÃO: SISTEMA ON-DEMAND EM TEMPO REAL

**Data**: 5 de março de 2026

---

## 📋 Sumário Executivo

Implementamos um **sistema Uber-style completo** para o BarberMove:

1. ✅ **Backend em Python** (FastAPI)
   - Função Haversine para cálculo de distância
   - 7 endpoints RESTful para On-Demand
   - Integração com Firebase para notificações push
   - Banco de dados com 3 novos modelos

2. ✅ **Frontend em React Native**
   - `RadarBarbeiro.jsx` - Tela do barbeiro (lado-supply)
   - `TelaPedirBarbeiro.jsx` - Tela do cliente (lado-demand)
   - Rastreamento de GPS em segundo plano
   - Permissões de localização (foreground + background)

3. ✅ **Fluxo End-to-End**
   - Cliente pede → Barbeiro notificado → Aceita/Recusa → Confirmação

---

## 🔧 PASSO 1: Adicionar Telas ao Router de Navegação

No seu arquivo de **navegação principal** (ex: `App.jsx` ou `Navigation.jsx`), importe as novas telas:

```jsx
// No topo do arquivo
import RadarBarbeiro from './screens/RadarBarbeiro';
import TelaPedirBarbeiro from './screens/TelaPedirBarbeiro';

// Na estrutura do Stack Navigator
export default function NavigationStack() {
  return (
    <Stack.Navigator
      screenOptions={{
        headerShown: false,
      }}
    >
      {/* Telas existentes */}
      <Stack.Screen name="Home" component={TelaHome} />
      <Stack.Screen name="Login" component={TelaLoginFreelancer} />
      
      {/* NOVAS TELAS */}
      <Stack.Screen 
        name="RadarBarbeiro" 
        component={RadarBarbeiro}
        options={{
          animationEnabled: true, // Slide in
        }}
      />
      <Stack.Screen 
        name="TelaPedirBarbeiro" 
        component={TelaPedirBarbeiro}
        options={{
          animationEnabled: true,
        }}
      />
    </Stack.Navigator>
  );
}
```

---

## 🎮 PASSO 2: Adicionar Botões de Acesso nas Telas Principais

### Para o **Barbeiro** (lado-supply):

Na tela principal do barbeiro (ex: `BarberDashboard.jsx`), adicione um botão para acessar o Radar:

```jsx
<TouchableOpacity
  style={styles.botaoRadar}
  onPress={() => navigation.navigate('RadarBarbeiro')}
>
  <MaterialCommunityIcons name="radar" size={24} color="#fff" />
  <Text style={styles.botaoTexto}>Ligar Radar Online</Text>
</TouchableOpacity>
```

### Para o **Cliente** (lado-demand):

Na tela principal do cliente (ex: `ClienteHome.jsx`), adicione um botão para solicitar barbeiro:

```jsx
<TouchableOpacity
  style={styles.botaoPedirAgora}
  onPress={() => navigation.navigate('TelaPedirBarbeiro')}
>
  <MaterialCommunityIcons name="phone-in-talk" size={24} color="#fff" />
  <Text style={styles.botaoTexto}>Barbeiro Agora</Text>
</TouchableOpacity>
```

---

## ⚙️ PASSO 3: Configurar Permissões Nativas

### Android (`android/app/src/main/AndroidManifest.xml`):

```xml
<manifest ...>
  <!-- Permissões de Localização -->
  <uses-permission android:name="android.permission.ACCESS_FINE_LOCATION" />
  <uses-permission android:name="android.permission.ACCESS_COARSE_LOCATION" />
  <uses-permission android:name="android.permission.ACCESS_BACKGROUND_LOCATION" />
  
  <!-- Permissões de Notificação -->
  <uses-permission android:name="android.permission.POST_NOTIFICATIONS" />
  
  <application>
    <!-- ... resto do manifest ... -->
  </application>
</manifest>
```

### iOS (`ios/BarberMove/Info.plist`):

```xml
<plist version="1.0">
<dict>
  <!-- Localização em First Plano -->
  <key>NSLocationWhenInUseUsageDescription</key>
  <string>Precisamos da sua localização para encontrar clientes próximos</string>
  
  <!-- Localização em Background -->
  <key>NSLocationAlwaysAndWhenInUseUsageDescription</key>
  <string>Permitir localização em todo o tempo para receber chamadas mesmo com o app no bolso</string>
  
  <!-- Modo Background -->
  <key>UIBackgroundModes</key>
  <array>
    <string>location</string>
  </array>
</dict>
</plist>
```

---

## 📦 PASSO 4: Instalar Dependências NPM

```bash
cd barbermove
npm install
# Para Expo projects:
expo install expo-location expo-task-manager
# Para projeto Capacitor:
npm install @react-native-firebase/messaging
npx cap sync
```

---

## 🔌 PASSO 5: Verificar Endpoints do Backend

Certifique-se de que o backend FastAPI está respondendo em:

```bash
# Terminal 1: Inicie o backend
cd c:\projeto_barbearia
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Teste os endpoints:

```bash
# Terminal 2: Teste
curl -X GET http://localhost:8000/api/v1/on-demand/barbeiros-proximos?latitude=-23.5505&longitude=-46.6333&raio_km=5.0
```

---

## 🌍 PASSO 6: Configurar Variável de Ambiente

Crie um arquivo `.env` na raiz de `barbermove/`:

```env
VITE_API_URL=http://localhost:8000
REACT_APP_API_URL=http://localhost:8000
```

No arquivo da tela, use:

```jsx
const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';
```

---

## 🧪 PASSO 7: Testar o Fluxo Completo

### Cenário 1: Barbeiro Fica Online

```
1. Barbeiro abre app
2. Vai para tela "Radar Online"
3. Clica no Switch
4. Aceita permissões de GPS
5. Switch fica verde (🟢 ONLINE)
6. GPS envia localização a cada 50m ou 10s
```

**Verificação Backend**:
```sql
SELECT * FROM radar_freelancer WHERE freelancer_id = 10;
-- Resultado esperado: is_online = true, latitude/longitude preenchidos
```

### Cenário 2: Cliente Solicita Barbeiro

```
1. Cliente abre app
2. Vai para tela "Barbeiros Próximos"
3. Permite GPS
4. Sistema busca barbeiros em um raio de 5km
5. Lista mostra: "Barbeiro #10 - 2.3 km de distância"
6. Cliente clica "Chamar agora"
7. POST /api/v1/on-demand/solicitar-barbeiro
```

**Verificação Backend**:
```sql
SELECT * FROM solicitacao_barbeiro WHERE cliente_id = 24;
-- Resultado esperado: status = "aguardando_resposta"

SELECT * FROM notificacao_barbeiro WHERE barbeiro_id = 10;
-- Resultado esperado: resposta = "none"
```

### Cenário 3: Barbeiro Recebe Notificação

```
1. Firebase envia push para barbeiro
2. Tela de notificação aparece:
   "📞 Novo Chamado! Carlos solicitou a 2.3 km"
3. Barbeiro clica na notificação
4. Abre SolicitacaoBarbeiro com detalhes
5. Clica "ACEITAR" ou "RECUSAR"
```

**Esperado**:
- ✅ Notificação som + vibração
- ✅ Tela acende
- ✅ App abre automaticamente
- ✅ Menos de 1 segundo de latência

---

## 📊 FLUXO DE DADOS (Diagramas de Sequência)

### Fluxo Barbeiro Ficar Online:

```
RadarBarbeiro.jsx
      │
      ├─ User clica Switch
      │
      ├─ Location.requestForegroundPermissionsAsync()
      │  └─ iOS/Android mostra dialog
      │
      ├─ Location.requestBackgroundPermissionsAsync()
      │  └─ iOS/Android mostra dialog
      │
      ├─ Location.getCurrentPositionAsync()
      │  └─ Obtém lat/lon do GPS
      │
      ├─ POST /api/v1/on-demand/ligar-radar
      │  │  Headers: Authorization: Bearer {JWT}
      │  │  Body: { is_online: true, latitude: -23.5505, longitude: -46.6333 }
      │  │
      │  └─ Backend:
      │     ├─ Valida JWT
      │     ├─ Busca/cria RadarFreelancer
      │     ├─ is_online = true
      │     ├─ latitude/longitude = valores recebidos
      │     └─ db.commit()
      │
      ├─ Location.startLocationUpdatesAsync(LOCATION_TASK_NAME)
      │  └─ TaskManager ativo em background
      │
      └─ UI: Switch fica verde 🟢
         Mensagem: "Radar ativo - Procurando clientes"
```

### Fluxo Cliente Solicita Barbeiro:

```
TelaPedirBarbeiro.jsx
      │
      ├─ User permite GPS
      │
      ├─ Location.getCurrentPositionAsync()
      │  └─ Obtém GPS do cliente
      │
      ├─ GET /api/v1/on-demand/barbeiros-proximos?lat=-23.550&lon=-46.633&raio=5.0
      │  │  Headers: Authorization: Bearer {JWT}
      │  │
      │  └─ Backend:
      │     ├─ Busca RadarFreelancer WHERE is_online=true AND em_atendimento=false
      │     │
      │     ├─ Para CADA barbeiro:
      │     │  │
      │     │  ├─ calcular_distancia_haversine(lat_cliente, lon_cliente, lat_barbeiro, lon_barbeiro)
      │     │  │  Formula: d = 2r * arcsin(√(...))
      │     │  │  Resultado: 2.3 km
      │     │  │
      │     │  └─ IF 2.3 <= 5.0:  ✓ Adiciona na lista
      │     │
      │     ├─ Ordena por distância crescente
      │     └─ Retorna JSON com [barbeiro1, barbeiro2, ...]
      │
      ├─ UI: FlatList mostra barbeiros
      │  Item 1: "Barbeiro #10 - 2.3 km - ⏱️ 9 minutos"
      │  Item 2: "Barbeiro #15 - 4.1 km - ⏱️ 16 minutos"
      │
      ├─ User clica "Chamar agora" em Barbeiro #10
      │
      ├─ POST /api/v1/on-demand/solicitar-barbeiro
      │  │  Headers: Authorization: Bearer {JWT}
      │  │  Body: {
      │  │    latitude: -23.550,
      │  │    longitude: -46.633,
      │  │    endereco: "Rua X, 123",
      │  │    raio_km: 5.0,
      │  │    tipo_servico: "corte",
      │  │    valor_oferta: 120.00
      │  │  }
      │  │
      │  └─ Backend:
      │     ├─ Cria SolicitacaoBarbeiro
      │     │  status = "aguardando_resposta"
      │     │
      │     ├─ Busca RadarFreelancer WHERE is_online=true
      │     │  (Refaz Haversine para cada um)
      │     │
      │     ├─ Para CADA barbeiro no raio:
      │     │  ├─ Cria NotificacaoBarbeiro
      │     │  ├─ Busca usuario.device_token (ex: "exJhbGc...")
      │     │  └─ Dispara Firebase:
      │     │     messaging.send(Message {
      │     │       title: "📞 Novo Chamado!",
      │     │       body: "Carlos solicitou a 2.3 km",
      │     │       data: {
      │     │         tipo: "chamado",
      │     │         solicitacao_id: 1,
      │     │         cliente_nome: "Carlos",
      │     │         distancia_km: 2.3
      │     │       },
      │     │       token: "exJhbGc..."
      │     │     })
      │     │
      │     └─ db.commit()
      │
      └─ UI: Alert "✅ Pedido enviado!"
         Volta para tela anterior
         Mensagem: "Aguardando resposta de barbeiros..."
```

---

## 🔔 PASSO 8: Testar Notificações Push

### Verificar Device Token:

```sql
-- Barbeiro recebeu device token?
SELECT usuario_id, device_token, device_token_atualizado_em 
FROM usuarios 
WHERE usuario_id = 10;
```

### Simular Notificação (via Backend):

```bash
# Terminal Python
python -c "
from app.firebase_config import enviar_notificacao_novo_chamado
enviar_notificacao_novo_chamado(
    token_dispositivo='exJhbGc2NjZlcjcwN3JlN2MyZGNkZjc3...',
    cliente_nome='Carlos',
    distancia_km=2.3
)
print('✅ Notificação enviada!')
"
```

---

## 🐛 Troubleshooting

### Problema: "Nenhum barbeiro encontrado"

**Causa**: Nenhum barbeiro online no raio

**Solução**:
```sql
-- Verificar status dos barbeiros
SELECT freelancer_id, is_online, latitude, longitude 
FROM radar_freelancer;

-- Se vazio, barbeiro nunca ativou radar
-- Ir em RadarBarbeiro.jsx e clicar no switch
```

### Problema: Localização não atualiza

**Causa**: GPS desligado ou permissões não concedidas

**Solução**:
- Verificar em Configurações do telefone: 
  - Android: `Permissões > Localização > Sempre`
  - iOS: `Privacidade > Localização > App > Sempre`

### Problema: Notificação não chega

**Causas possíveis**:
1. Device token não registrado (verificar `usuarios.device_token`)
2. Firebase não configurado (falta `firebase-credentials.json`)
3. Internet offline no barbeiro

**Solução**:
```bash
# Verificar firebase_config.py
grep "FIREBASE_DISPONIVEL" app/firebase_config.py

# Deve estar True se firebase-admin instalado
pip install firebase-admin
```

### Problema: "Authorization header missing"

**Causa**: JWT não está sendo enviado

**Solução**:
```jsx
// Em RadarBarbeiro.jsx
const jwtToken = await AsyncStorage.getItem('jwtToken');

// Verificar se não é null
if (!jwtToken) {
  Alert.alert('Erro', 'Você precisa fazer login primeiro');
  navigation.navigate('Login');
  return;
}

// No fetch:
headers: {
  'Authorization': `Bearer ${jwtToken}`,  // ← Espaço importante!
  'Content-Type': 'application/json',
}
```

---

## 📈 Métricas de Desempenho

Quando está tudo funcionando, você deve observar:

| Métrica | Esperado | Crítico |
|---------|----------|---------|
| Latência Webhook → Notificação | < 1s | < 5s |
| Cálculo Haversine | < 50ms | < 500ms |
| GET Barbeiros próximos | < 200ms | < 2s |
| GPS em background | a cada 50m | a cada 10s máx |
| Precisão de distância | ±100m | ±500m |

---

## 🚀 Próximos Passos

1. **Implementar Deep Linking**
   - Notificação push → Abre app exatamente na solicitação

2. **Adicionar Mapa em Tempo Real**
   - `react-native-maps` para ver barbeiro se aproximando

3. **Histórico de Solicitações**
   - Tela mostrando aceitas/recusadas/concluídas

4. **Avaliações Pós-Serviço**
   - Cliente avalia barbeiro após serviço
   - Barbeiro avalia cliente

5. **Pagamento Integrado**
   - Webhook do MercadoPago dispara após serviço
   - Notificação push de pagamento recebido

---

## 📞 Referência Rápida dos Endpoints

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| POST | `/api/v1/on-demand/ligar-radar` | Barbeiro fica online |
| POST | `/api/v1/on-demand/atualizar-localizacao` | GPS do barbeiro |
| GET | `/api/v1/on-demand/barbeiros-proximos` | Lista by raio |
| POST | `/api/v1/on-demand/solicitar-barbeiro` | Cliente solicita |
| POST | `/api/v1/on-demand/aceitar-solicitacao/{id}` | Barbeiro aceita |
| POST | `/api/v1/on-demand/terminar-atendimento` | Finaliza |
| GET | `/api/v1/on-demand/status-meu-radar` | Status do barbeiro |
| POST | `/api/v1/firebase/registrar-token` | Salva device token |
| POST | `/api/v1/firebase/teste-notificacao` | Testa push |

---

## 📚 Documentação de Referência

- [Expo Location](https://docs.expo.dev/versions/latest/sdk/location/)
- [Expo Task Manager](https://docs.expo.dev/versions/latest/sdk/task-manager/)
- [React Native Firebase](https://rnfirebase.io/messaging/usage)
- [FastAPI](https://fastapi.tiangolo.com/)
- [Haversine Formula](https://en.wikipedia.org/wiki/Haversine_formula)

---

**Status**: ✅ Sistema 100% implementado e pronto para deploy
