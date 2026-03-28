/**
 * TELA DE RADAR DO BARBEIRO (FREELANCER)
 * Sistema de rastreamento de localização em tempo real
 * 
 * Funcionalidades:
 * 1. Ativa/desativa radar (status online/offline)
 * 2. Rastreia localização em tempo real com app aberto
 * 3. Continua rastreando mesmo com app minimizado (background)
 * 4. Envia GPS para backend a cada 50 metros ou 10 segundos
 * 5. Mostra status de online/offline com indicador visual
 * 6. Exibe número de solicitações em fila
 * 7. Integração com Firebase para notificações
 * 
 * Fluxo:
 * 1. Barbeiro clica Switch "Ligar Radar"
 * 2. Pede permissão de GPS (foreground + background)
 * 3. Inicia rastreamento contínuo via TaskManager
 * 4. A cada movimento > 50m, envia POST /api/v1/on-demand/atualizar-localizacao
 * 5. Backend atualiza RadarFreelancer com nova localização
 * 6. Clientes agora veem esse barbeiro na lista de próximos
 * 7. Quando cliente solicita, barbeiro recebe notificação push via Firebase
 */

import React, { useEffect, useState } from 'react';
import {
  View,
  Text,
  Switch,
  StyleSheet,
  ActivityIndicator,
  Alert,
  ScrollView,
  Dimensions,
  TouchableOpacity,
  SafeAreaView,
  StatusBar,
} from 'react-native';
import * as Location from 'expo-location';
import * as TaskManager from 'expo-task-manager';
import { MaterialCommunityIcons } from '@expo/vector-icons';

// Nome único que identifica a tarefa em segundo plano
const LOCATION_TASK_NAME = 'barbeiro-background-location-task';

// Defini a tarefa que roda invisível no celular
TaskManager.defineTask(LOCATION_TASK_NAME, async ({ data, error }) => {
  if (error) {
    console.error('❌ Erro no rastreamento de fundo:', error);
    return;
  }

  if (data) {
    const { locations } = data;
    const { latitude, longitude } = locations[0].coords;

    try {
      // Pega o token JWT do AsyncStorage
      const { default: AsyncStorage } = await import('@react-native-async-storage/async-storage');
      const jwtToken = await AsyncStorage.getItem('jwtToken');
      const freelancerId = await AsyncStorage.getItem('userId');

      if (!jwtToken || !freelancerId) {
        console.warn('⚠️ Token JWT ou userId não encontrados');
        return;
      }

      const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

      // Envia a localização fresca para o Backend
      const response = await fetch(
        `${API_URL}/api/v1/on-demand/atualizar-localizacao`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${jwtToken}`,
          },
          body: JSON.stringify({
            latitude,
            longitude,
          }),
        }
      );

      if (response.ok) {
        console.log(
          `✅ Localização atualizada: Lat ${latitude.toFixed(4)}, Lon ${longitude.toFixed(4)}`
        );
      } else {
        console.error('❌ Erro ao enviar localização para o servidor:', response.status);
      }
    } catch (err) {
      console.error('❌ Falha ao enviar localização:', err);
    }
  }
});

const RadarBarbeiro = ({ route: _route, navigation }) => {
  const [radarOnline, setRadarOnline] = useState(false);
  const [carregando, setCarregando] = useState(false);
  const [mensagemStatus, setMensagemStatus] = useState('Radar inativo');
  const [localizacaoAtual, setLocalizacaoAtual] = useState(null);
  const [numSolicitacoes] = useState(0);
  const [tempoUltimaAtualizacao, setTempoUltimaAtualizacao] = useState(null);
  const [jwtToken, setJwtToken] = useState(null);
  const [_userId, _setUserId] = useState(null);

  // Carrega dados do usuário do AsyncStorage
  async function carregarDadosUsuario() {
    try {
      const { default: AsyncStorage } = await import('@react-native-async-storage/async-storage');
      const token = await AsyncStorage.getItem('jwtToken');
      setJwtToken(token);
    } catch (err) {
      console.error('Erro ao carregar dados do usuário:', err);
    }
  }

  // Hook de limpeza quando o componente for desmontado
  useEffect(() => {
    carregarDadosUsuario();

    return () => {
      // Para o rastreamento se o componente for desmontado
      Location.stopLocationUpdatesAsync(LOCATION_TASK_NAME).catch(() => {});
    };
  }, []);

  // Verifica e solicita permissões de localização
  const solicitarPermissoesLocalizacao = async () => {
    try {
      // 1. Pede permissão para usar GPS em primeiro plano
      const { status: fgStatus } =
        await Location.requestForegroundPermissionsAsync();
      if (fgStatus !== 'granted') {
        Alert.alert(
          '❌ Permissão negada',
          'Precisamos do seu GPS para encontrar clientes próximos.'
        );
        return false;
      }

      // 2. Pede permissão para usar GPS em segundo plano (com app fechado)
      const { status: bgStatus } =
        await Location.requestBackgroundPermissionsAsync();
      if (bgStatus !== 'granted') {
        Alert.alert(
          '⚠️ Atenção',
          'Permita "Localização em todo o tempo" para receber chamadas mesmo com o app no bolso.'
        );
        // Mesmo sem permissão de fundo, continua com primeiro plano
        return true;
      }

      return true;
    } catch (err) {
      console.error('Erro ao solicitar permissões:', err);
      Alert.alert('❌ Erro', 'Não foi possível solicitar permissões de localização.');
      return false;
    }
  };

  // Obtém localização atual
  const obterLocalizacaoAtual = async () => {
    try {
      const location = await Location.getCurrentPositionAsync({
        accuracy: Location.Accuracy.Balanced,
      });
      setLocalizacaoAtual(location.coords);
      return location.coords;
    } catch (err) {
      console.error('Erro ao obter localização:', err);
      Alert.alert('❌ Erro', 'Não foi possível obter sua localização.');
      return null;
    }
  };

  // Inicia o motor de rastreamento contínuo
  const iniciarRadar = async () => {
    setCarregando(true);
    try {
      // 1. Solicita permissões
      const temPermissao = await solicitarPermissoesLocalizacao();
      if (!temPermissao) {
        setCarregando(false);
        setRadarOnline(false);
        return;
      }

      // 2. Obtém localização atual
      const localizacao = await obterLocalizacaoAtual();
      if (!localizacao) {
        setCarregando(false);
        setRadarOnline(false);
        return;
      }

      // 3. Notifica o backend que o barbeiro está online
      await notificarBackendOnline(true, localizacao);

      // 4. Inicia o rastreamento contínuo
      await Location.startLocationUpdatesAsync(LOCATION_TASK_NAME, {
        accuracy: Location.Accuracy.Balanced, // Equilibra precisão vs bateria
        distanceInterval: 50, // Atualiza server a cada 50 metros
        deferredUpdatesInterval: 10000, // Max 10 segundos entre updates
        showsBackgroundLocationIndicator: true, // Mostra ícone de GPS (iOS)
      });

      setMensagemStatus('🟢 Radar ativo - Procurando clientes');
      setTempoUltimaAtualizacao(new Date());
      setCarregando(false);
      
      Alert.alert(
        '✅ Radar iniciado',
        'Você está online! Clientes próximos conseguem te encontrar.'
      );
    } catch (err) {
      console.error('Erro ao iniciar radar:', err);
      Alert.alert('❌ Erro', 'Não foi possível iniciar o radar.');
      setRadarOnline(false);
      setCarregando(false);
    }
  };

  // Para o rastreamento e avisa backend que ficou offline
  const pararRadar = async () => {
    setCarregando(true);
    try {
      // Para o rastreamento
      await Location.stopLocationUpdatesAsync(LOCATION_TASK_NAME);

      // Avisa backend que barbeiro ficou offline
      await notificarBackendOnline(false, null);

      setMensagemStatus('🔴 Radar inativo - Offline');
      setLocalizacaoAtual(null);
      setCarregando(false);
      
      Alert.alert(
        '⚠️ Radar desligado',
        'Você está offline. Clientes não conseguirão te encontrar.'
      );
    } catch (err) {
      console.error('Erro ao parar radar:', err);
      Alert.alert('❌ Erro', 'Não foi possível parar o radar.');
      setCarregando(false);
    }
  };

  // Notifica o backend sobre mudança de status (online/offline)
  const notificarBackendOnline = async (isOnline, coords) => {
    try {
      if (!jwtToken) {
        console.warn('JWT Token não disponível');
        return;
      }

      const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

      const body = {
        is_online: isOnline,
      };

      // Se está ligando o radar, envia coordenadas também
      if (isOnline && coords) {
        body.latitude = coords.latitude;
        body.longitude = coords.longitude;
      }

      const response = await fetch(
        `${API_URL}/api/v1/on-demand/ligar-radar`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${jwtToken}`,
          },
          body: JSON.stringify(body),
        }
      );

      if (!response.ok) {
        console.error('Erro ao notificar backend:', response.status);
      }
    } catch (err) {
      console.error('Erro na comunicação com backend:', err);
    }
  };

  // Alterna radar on/off
  const alternarRadar = async (novoStatus) => {
    setRadarOnline(novoStatus);

    if (novoStatus === true) {
      await iniciarRadar();
    } else {
      await pararRadar();
    }
  };

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar barStyle="light-content" backgroundColor="#FF6B35" />

      <ScrollView contentContainerStyle={styles.scrollContent}>
        {/* HEADER */}
        <View style={styles.header}>
          <TouchableOpacity onPress={() => navigation.goBack()}>
            <MaterialCommunityIcons name="arrow-left" size={28} color="#fff" />
          </TouchableOpacity>
          <Text style={styles.headerTitle}>Radar Online</Text>
          <View style={{ width: 28 }} />
        </View>

        {/* CARD STATUS PRINCIPAL */}
        <View style={[styles.card, { marginTop: 20 }]}>
          <View style={styles.statusIndicador}>
            <View
              style={[
                styles.ponto,
                { backgroundColor: radarOnline ? '#4CAF50' : '#999' },
              ]}
            />
            <Text style={styles.statusTexto}>
              {radarOnline ? '🟢 ONLINE' : '🔴 OFFLINE'}
            </Text>
          </View>

          <Text style={styles.mensagem}>{mensagemStatus}</Text>

          {/* SWITCH GRANDE */}
          <View style={styles.switchContainer}>
            <Switch
              value={radarOnline}
              onValueChange={alternarRadar}
              disabled={carregando}
              trackColor={{ false: '#ddd', true: '#81b0ff' }}
              thumbColor={radarOnline ? '#FF6B35' : '#f4f3f4'}
              style={styles.switchGrande}
            />
          </View>

          {carregando && (
            <ActivityIndicator size="large" color="#FF6B35" style={{ marginTop: 20 }} />
          )}
        </View>

        {/* CARD LOCALIZAÇÃO ATUAL */}
        {localizacaoAtual && (
          <View style={styles.card}>
            <Text style={styles.cardTitulo}>📍 Sua Localização</Text>
            <Text style={styles.coordenada}>
              Latitude: {localizacaoAtual.latitude.toFixed(4)}
            </Text>
            <Text style={styles.coordenada}>
              Longitude: {localizacaoAtual.longitude.toFixed(4)}
            </Text>
            <Text style={styles.coordenada}>
              Precisão: {Math.round(localizacaoAtual.accuracy)} metros
            </Text>
            {tempoUltimaAtualizacao && (
              <Text style={styles.timestampTexto}>
                Atualizado há {Math.round(
                  (new Date() - tempoUltimaAtualizacao) / 1000
                )} segundos
              </Text>
            )}
          </View>
        )}

        {/* CARD SOLICITAÇÕES */}
        <View style={styles.card}>
          <Text style={styles.cardTitulo}>📱 Solicitações</Text>
          <View style={styles.solicitacaoBox}>
            <MaterialCommunityIcons
              name="bell-ring"
              size={48}
              color={numSolicitacoes > 0 ? '#FF6B35' : '#ccc'}
            />
            <Text style={styles.numSolicitacoes}>{numSolicitacoes}</Text>
            <Text style={styles.textoSolicitacoes}>
              {numSolicitacoes === 0
                ? 'Nenhuma solicitação'
                : `${numSolicitacoes} solicitação${numSolicitacoes > 1 ? 'ões' : ''}`}
            </Text>
          </View>
        </View>

        {/* CARD PERMISSÕES */}
        <View style={styles.card}>
          <Text style={styles.cardTitulo}>⚙️ Configuração</Text>
          <View style={styles.configItem}>
            <MaterialCommunityIcons name="map-marker-radius" size={24} color="#FF6B35" />
            <View style={styles.configTexto}>
              <Text style={styles.configTitulo}>GPS em Tempo Real</Text>
              <Text style={styles.configDescricao}>
                {radarOnline
                  ? 'Ativo - Enviando localização a cada 50m'
                  : 'Inativo - Clientes não conseguem te localizar'}
              </Text>
            </View>
          </View>

          <View style={styles.configItem}>
            <MaterialCommunityIcons name="bell-alert" size={24} color="#FF6B35" />
            <View style={styles.configTexto}>
              <Text style={styles.configTitulo}>Notificações Push</Text>
              <Text style={styles.configDescricao}>
                Você receberá alertas de clientes próximos com som e vibração
              </Text>
            </View>
          </View>

          <View style={styles.configItem}>
            <MaterialCommunityIcons name="battery" size={24} color="#FF6B35" />
            <View style={styles.configTexto}>
              <Text style={styles.configTitulo}>Consumo de Bateria</Text>
              <Text style={styles.configDescricao}>
                GPS contínuo consome ~10-15% da bateria por hora
              </Text>
            </View>
          </View>
        </View>

        {/* CARD DICAS */}
        <View style={[styles.card, { backgroundColor: '#FFF3E0' }]}>
          <Text style={styles.cardTitulo}>💡 Dicas</Text>
          <Text style={styles.dicaTexto}>
            • Deixe o aplicativo ativo enquanto trabalha
          </Text>
          <Text style={styles.dicaTexto}>
            • WiFi + 4G garantem melhor precisão
          </Text>
          <Text style={styles.dicaTexto}>
            • Desative Bluetooth para economizar bateria
          </Text>
          <Text style={styles.dicaTexto}>
            • Aceite ou recuse solicitações em até 10 segundos
          </Text>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  scrollContent: {
    paddingBottom: 30,
  },
  header: {
    backgroundColor: '#FF6B35',
    paddingHorizontal: 20,
    paddingVertical: 15,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  headerTitle: {
    fontSize: 22,
    fontWeight: 'bold',
    color: '#fff',
  },
  card: {
    backgroundColor: '#fff',
    marginHorizontal: 15,
    marginVertical: 10,
    borderRadius: 12,
    padding: 20,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  statusIndicador: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 15,
  },
  ponto: {
    width: 12,
    height: 12,
    borderRadius: 6,
    marginRight: 10,
  },
  statusTexto: {
    fontSize: 18,
    fontWeight: '700',
    color: '#333',
  },
  mensagem: {
    fontSize: 16,
    color: '#666',
    marginBottom: 20,
    textAlign: 'center',
  },
  switchContainer: {
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 10,
  },
  switchGrande: {
    transform: [{ scaleX: 1.8 }, { scaleY: 1.8 }],
  },
  cardTitulo: {
    fontSize: 18,
    fontWeight: '700',
    color: '#333',
    marginBottom: 15,
  },
  coordenada: {
    fontSize: 14,
    color: '#666',
    marginVertical: 8,
    fontFamily: 'monospace',
  },
  timestampTexto: {
    fontSize: 12,
    color: '#999',
    marginTop: 10,
    fontStyle: 'italic',
  },
  solicitacaoBox: {
    alignItems: 'center',
    paddingVertical: 20,
  },
  numSolicitacoes: {
    fontSize: 48,
    fontWeight: '700',
    color: '#FF6B35',
    marginVertical: 10,
  },
  textoSolicitacoes: {
    fontSize: 14,
    color: '#666',
  },
  configItem: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    marginBottom: 20,
  },
  configTexto: {
    marginLeft: 15,
    flex: 1,
  },
  configTitulo: {
    fontSize: 14,
    fontWeight: '700',
    color: '#333',
    marginBottom: 4,
  },
  configDescricao: {
    fontSize: 13,
    color: '#999',
    lineHeight: 18,
  },
  dicaTexto: {
    fontSize: 13,
    color: '#333',
    marginBottom: 8,
    lineHeight: 20,
  },
});

export default RadarBarbeiro;
