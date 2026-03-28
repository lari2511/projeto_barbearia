/**
 * TELA DE PEDIDO DE BARBEIRO (CLIENTE)
 * Sistema On-Demand estilo Uber para buscar barbeiro agora
 * 
 * Funcionalidades:
 * 1. Mostra lista de barbeiros próximos em tempo real
 * 2. Permite que cliente veja distância e tempo estimado
 * 3. Cliente solicita barbeiro → Notificação push para barbeiro
 * 4. Sistema automaticamente escolhe barbeiro mais próximo
 * 5. Integração com geolocalização do cliente
 * 6. Rastreamento do barbeiro aceitando/recusando
 * 
 * Fluxo:
 * 1. Cliente abre tela "Solicitar Agora"
 * 2. Sistema obtém localização do cliente (GPS)
 * 3. Faz GET /api/v1/on-demand/barbeiros-proximos (raio 5km)
 * 4. Lista barbeiros ordenados por distância
 * 5. Cliente clica em barbeiro ou "Solicitar agora"
 * 6. POST /api/v1/on-demand/solicitar-barbeiro
 * 7. Backend envia notificação push para barbeiro
 * 8. Barbeiro recebe: "Nova solicitação a X km"
 * 9. Barbeiro clica para ver ou aceitar/recusar
 * 10. Se aceita: Cliente vê "Barbeiro a aceitar em X minutos"
 */

import React, { useEffect, useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ActivityIndicator,
  Alert,
  TouchableOpacity,
  SafeAreaView,
  StatusBar,
  FlatList,
  RefreshControl,
  Dimensions,
} from 'react-native';
import * as Location from 'expo-location';
import { MaterialCommunityIcons } from '@expo/vector-icons';

const { height: _height } = Dimensions.get('window');

const TelaPedirBarbeiro = ({ route: _route, navigation }) => {
  const [localizacaoCliente, setLocalizacaoCliente] = useState(null);
  const [barbeirosProximos, setBarbeirosProximos] = useState([]);
  const [carregando, setCarregando] = useState(false);
  const [atualizando, setAtualizando] = useState(false);
  const [raioKm] = useState(5.0);
  const [jwtToken, setJwtToken] = useState(null);
  const [_barbeariaSelecionada, _setBarbeariaSelecionada] = useState(null);
  const [solicitacaoEmAndamento, setSolicitacaoEmAndamento] = useState(false);

  const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

  // Carrega dados ao montar
  useEffect(() => {
    carregarToken();
    obterLocalizacaoInicial();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Carrega JWT do AsyncStorage
  const carregarToken = async () => {
    try {
      const { default: AsyncStorage } = await import('@react-native-async-storage/async-storage');
      const token = await AsyncStorage.getItem('jwtToken');
      setJwtToken(token);
    } catch (err) {
      console.error('Erro ao carregar token:', err);
    }
  };

  // Obtém localização inicial do cliente
  const obterLocalizacaoInicial = async () => {
    try {
      setCarregando(true);

      // Solicita permissão
      const { status } = await Location.requestForegroundPermissionsAsync();
      if (status !== 'granted') {
        Alert.alert(
          'Permissão negada',
          'Precisamos do seu GPS para encontrar barbeiros próximos.'
        );
        setCarregando(false);
        return;
      }

      // Obtém localização
      const location = await Location.getCurrentPositionAsync({
        accuracy: Location.Accuracy.Balanced,
      });

      setLocalizacaoCliente(location.coords);
      await buscarBarbeirosProximos(location.coords);
    } catch (err) {
      console.error('Erro ao obter localização:', err);
      Alert.alert('Erro', 'Não foi possível obter sua localização.');
    } finally {
      setCarregando(false);
    }
  };

  // GET /api/v1/on-demand/barbeiros-proximos
  const buscarBarbeirosProximos = async (coords) => {
    try {
      if (!coords) return;

      const params = new URLSearchParams({
        latitude: coords.latitude,
        longitude: coords.longitude,
        raio_km: raioKm,
      });

      const response = await fetch(
        `${API_URL}/api/v1/on-demand/barbeiros-proximos?${params}`,
        {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${jwtToken}`,
          },
        }
      );

      const data = await response.json();

      if (response.ok) {
        console.log(`✅ Encontrados ${data.total_encontrados} barbeiros`);
        setBarbeirosProximos(data.barbeiros);
      } else {
        console.error('Erro na busca:', data);
        Alert.alert('Erro', 'Não foi possível buscar barbeiros próximos.');
      }
    } catch (err) {
      console.error('Erro ao buscar barbeiros:', err);
      Alert.alert('Erro', 'Erro ao conectar com servidor.');
    } finally {
      setAtualizando(false);
    }
  };

  // Recarrega lista de barbeiros
  const aoPuxarParaAtualizarTela = async () => {
    setAtualizando(true);
    if (localizacaoCliente) {
      await buscarBarbeirosProximos(localizacaoCliente);
    }
  };

  // POST /api/v1/on-demand/solicitar-barbeiro
  const solicitarBarbeiro = async (barbeiro) => {
    try {
      if (!localizacaoCliente || !jwtToken) {
        Alert.alert('Erro', 'Localização ou autenticação indisponíveis.');
        return;
      }

      setSolicitacaoEmAndamento(true);

      const payload = {
        latitude: localizacaoCliente.latitude,
        longitude: localizacaoCliente.longitude,
        endereco: 'Seu endereço aqui', // TODO: Implementar endereço real
        raio_km: raioKm,
        tipo_servico: 'corte', // TODO: Permitir seleção
        observacoes: '',
        valor_oferta: 120.0, // TODO: Cálculo dinâmico
      };

      const response = await fetch(
        `${API_URL}/api/v1/on-demand/solicitar-barbeiro`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${jwtToken}`,
          },
          body: JSON.stringify(payload),
        }
      );

      const data = await response.json();

      if (response.ok) {
        console.log('✅ Solicitação enviada para barbeiros próximos');
        Alert.alert(
          '✅ Pedido enviado!',
          `Aguardando resposta de barbeiros a ${barbeiro.distancia_km} km...`
        );
        navigation.goBack();
      } else {
        Alert.alert('Erro', data.detail || 'Não foi possível fazer a solicitação.');
      }
    } catch (err) {
      console.error('Erro ao solicitar barbeiro:', err);
      Alert.alert('Erro', 'Erro na comunicação com servidor.');
    } finally {
      setSolicitacaoEmAndamento(false);
    }
  };

  // Renderiza item de barbeiro
  const renderizarBarbeiro = ({ item, index }) => {
    const minutos = Math.round((item.distancia_km / 10) * 60); // Estimativa 10 km/h

    return (
      <TouchableOpacity
        style={[
          styles.barbeirCard,
          { opacity: solicitacaoEmAndamento ? 0.5 : 1 },
        ]}
        onPress={() => solicitarBarbeiro(item)}
        disabled={solicitacaoEmAndamento}
      >
        {/* Posição no ranking */}
        <View style={styles.posiçãoBadge}>
          <Text style={styles.posiçãoTexto}>{index + 1}</Text>
        </View>

        {/* Informações básicas */}
        <View style={styles.infoBasica}>
          <View>
            <Text style={styles.nomeFreelancer}>Barbeiro #{item.freelancer_id}</Text>
            <Text style={styles.distancia}>
              📍 {item.distancia_km} km de distância
            </Text>
            <Text style={styles.tempoEstimado}>
              ⏱️ ~{minutos} minutos para chegar
            </Text>
          </View>

          {/* Avaliação (placeholder) */}
          <View style={styles.avaliacaoBox}>
            <MaterialCommunityIcons name="star" size={16} color="#FFB800" />
            <Text style={styles.avaliacaoTexto}>4.8</Text>
          </View>
        </View>

        {/* Botão de solicitar */}
        <TouchableOpacity
          style={styles.botaoSolicitar}
          onPress={() => solicitarBarbeiro(item)}
          disabled={solicitacaoEmAndamento}
        >
          <MaterialCommunityIcons name="phone-forward" size={20} color="#fff" />
          <Text style={styles.botaoTexto}>
            {solicitacaoEmAndamento ? 'Enviando...' : 'Chamar agora'}
          </Text>
        </TouchableOpacity>
      </TouchableOpacity>
    );
  };

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar barStyle="light-content" backgroundColor="#FF6B35" />

      {/* HEADER */}
      <View style={styles.header}>
        <TouchableOpacity onPress={() => navigation.goBack()}>
          <MaterialCommunityIcons name="arrow-left" size={28} color="#fff" />
        </TouchableOpacity>
        <Text style={styles.headerTitle}>Barbeiros Próximos</Text>
        <TouchableOpacity onPress={aoPuxarParaAtualizarTela}>
          <MaterialCommunityIcons
            name={atualizando ? 'loading' : 'refresh'}
            size={24}
            color="#fff"
          />
        </TouchableOpacity>
      </View>

      {carregando ? (
        <View style={styles.carregandoContainer}>
          <ActivityIndicator size="large" color="#FF6B35" />
          <Text style={styles.carregandoTexto}>Buscando barbeiros próximos...</Text>
        </View>
      ) : barbeirosProximos.length === 0 ? (
        <View style={styles.nenhumBarbeiro}>
          <MaterialCommunityIcons
            name="emoticon-sad-outline"
            size={80}
            color="#ccc"
          />
          <Text style={styles.nenhumTitulo}>Nenhum barbeiro disponível</Text>
          <Text style={styles.nenhumDescricao}>
            No momento não há barbeiros online no raio de {raioKm} km.
          </Text>
          <Text style={styles.nenhumDica}>
            Tente aumentar o raio de busca ou tente novamente em alguns minutos.
          </Text>
          <TouchableOpacity
            style={styles.botaoTentarNovamente}
            onPress={aoPuxarParaAtualizarTela}
          >
            <Text style={styles.botaoTentarTexto}>Tentar novamente</Text>
          </TouchableOpacity>
        </View>
      ) : (
        <FlatList
          data={barbeirosProximos}
          renderItem={renderizarBarbeiro}
          keyExtractor={(item, index) => `${item.freelancer_id}-${index}`}
          contentContainerStyle={styles.listaContent}
          refreshControl={
            <RefreshControl
              refreshing={atualizando}
              onRefresh={aoPuxarParaAtualizarTela}
              colors={['#FF6B35']}
            />
          }
        />
      )}

      {/* CARD DE LOCALIZAÇÃO DO CLIENTE */}
      {localizacaoCliente && (
        <View style={styles.footerLocalizacao}>
          <MaterialCommunityIcons name="map-marker" size={20} color="#FF6B35" />
          <Text style={styles.footerTexto}>
            Seu local: ({localizacaoCliente.latitude.toFixed(4)}, 
            {localizacaoCliente.longitude.toFixed(4)})
          </Text>
        </View>
      )}
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
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
    fontSize: 20,
    fontWeight: 'bold',
    color: '#fff',
  },
  carregandoContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  carregandoTexto: {
    marginTop: 15,
    fontSize: 16,
    color: '#666',
  },
  listaContent: {
    paddingHorizontal: 12,
    paddingVertical: 10,
  },
  barbeirCard: {
    backgroundColor: '#fff',
    borderRadius: 12,
    marginVertical: 8,
    padding: 15,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
    borderLeftWidth: 4,
    borderLeftColor: '#FF6B35',
  },
  posiçãoBadge: {
    position: 'absolute',
    top: 10,
    right: 10,
    backgroundColor: '#FF6B35',
    width: 32,
    height: 32,
    borderRadius: 16,
    justifyContent: 'center',
    alignItems: 'center',
  },
  posiçãoTexto: {
    fontSize: 16,
    fontWeight: '700',
    color: '#fff',
  },
  infoBasica: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 12,
    marginRight: 30,
  },
  nomeFreelancer: {
    fontSize: 16,
    fontWeight: '700',
    color: '#333',
    marginBottom: 6,
  },
  distancia: {
    fontSize: 14,
    color: '#666',
    marginBottom: 4,
  },
  tempoEstimado: {
    fontSize: 14,
    color: '#FF6B35',
    fontWeight: '600',
  },
  avaliacaoBox: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#FFF3E0',
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: 8,
  },
  avaliacaoTexto: {
    marginLeft: 6,
    fontSize: 14,
    fontWeight: '700',
    color: '#FF6B35',
  },
  botaoSolicitar: {
    backgroundColor: '#FF6B35',
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 12,
    borderRadius: 8,
  },
  botaoTexto: {
    marginLeft: 8,
    fontSize: 15,
    fontWeight: '700',
    color: '#fff',
  },
  nenhumBarbeiro: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: 30,
  },
  nenhumTitulo: {
    fontSize: 18,
    fontWeight: '700',
    color: '#333',
    marginTop: 20,
  },
  nenhumDescricao: {
    fontSize: 14,
    color: '#666',
    marginTop: 10,
    textAlign: 'center',
  },
  nenhumDica: {
    fontSize: 13,
    color: '#999',
    marginTop: 10,
    textAlign: 'center',
    fontStyle: 'italic',
  },
  botaoTentarNovamente: {
    backgroundColor: '#FF6B35',
    paddingHorizontal: 30,
    paddingVertical: 12,
    borderRadius: 8,
    marginTop: 20,
  },
  botaoTentarTexto: {
    color: '#fff',
    fontWeight: '700',
    fontSize: 15,
  },
  footerLocalizacao: {
    backgroundColor: '#fff',
    borderTopWidth: 1,
    borderTopColor: '#eee',
    paddingHorizontal: 15,
    paddingVertical: 12,
    flexDirection: 'row',
    alignItems: 'center',
  },
  footerTexto: {
    marginLeft: 10,
    fontSize: 12,
    color: '#666',
  },
});

export default TelaPedirBarbeiro;
