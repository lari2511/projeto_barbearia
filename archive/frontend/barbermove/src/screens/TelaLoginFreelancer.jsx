/**
 * TELA DE LOGIN - BARBEIRO (FREELANCER)
 * Integrada com Firebase Cloud Messaging para notificações push
 * 
 * Fluxo:
 * 1. Barbeiro digita email e senha
 * 2. Backend faz login e retorna token JWT
 * 3. React Native pede permissão para notificações
 * 4. Gera device token (FCM) único do celular
 * 5. Envia device token para backend via POST /api/v1/firebase/registrar-token
 * 6. Backend salva no campo device_token do Usuario
 * 7. Barbeiro recebe notificações: pagamentos, chamados, saques, etc
 */

import React, { useState } from 'react';
import {
  View,
  TextInput,
  Text,
  TouchableOpacity,
  Alert,
  ActivityIndicator,
  KeyboardAvoidingView,
  ScrollView,
  Platform,
  StyleSheet
} from 'react-native';
import messaging from '@react-native-firebase/messaging';
import { MaterialCommunityIcons } from '@expo/vector-icons';

const TelaLoginFreelancer = ({ navigation, onLoginSuccess }) => {
  const [email, setEmail] = useState('barbeiro@teste.com');
  const [senha, setSenha] = useState('123456');
  const [loading, setLoading] = useState(false);
  const [mostraSenha, setMostraSenha] = useState(false);

  const defaultHost = typeof window !== 'undefined' ? window.location.hostname : 'localhost';
  const defaultProtocol = typeof window !== 'undefined' && window.location.protocol === 'https:' ? 'https' : 'http';
  const API_URL = import.meta.env.VITE_API_URL || `${defaultProtocol}://${defaultHost}:8000`;

  /**
   * Registra o device token no backend
   * Esse token permite que o servidor envie notificações push para esse aparelho específico
   */
  const registrarTokenNoBackend = async (jwtToken, userId, deviceToken) => {
    try {
      const response = await fetch(`${API_URL}/api/v1/firebase/registrar-token`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${jwtToken}`
        },
        body: JSON.stringify({
          device_token: deviceToken,
          tipo_dispositivo: Platform.OS // 'ios' ou 'android'
        })
      });

      if (!response.ok) {
        const error = await response.json();
        console.warn('⚠️ Erro ao registrar token:', error);
        // Não falha o login se o token não for registrado
        return;
      }

      const data = await response.json();
      console.log('✅ Device token registrado com sucesso:', data);

      return data;
    } catch (erro) {
      console.error('❌ Erro de conexão ao registrar token:', erro);
      // Não falha o login se houver erro de rede
    }
  };

  /**
   * Configura as notificações push:
   * 1. Pede permissão ao iOS/Android 13+
   * 2. Gera o device token único
   * 3. Envia para o backend
   */
  const configurarNotificacoes = async (jwtToken, userId) => {
    try {
      // 1. Pede permissão ao usuário
      const statusAutorizacao = await messaging().requestPermission();
      
      const permissaoConcedida = 
        statusAutorizacao === messaging.AuthorizationStatus.AUTHORIZED ||
        statusAutorizacao === messaging.AuthorizationStatus.PROVISIONAL;

      if (!permissaoConcedida) {
        // Usuário negou permissão, mas login segue funcionando
        console.warn('⚠️ Permissão de notificações negada pelo usuário');
        Alert.alert(
          "Notificações Desativadas",
          "Você não receberá avisos quando um cliente pagar pelo corte. Você pode ativar isto mais tarde nas configurações.",
          [{ text: "OK" }]
        );
        return;
      }

      // 2. Gera o device token (identificador único do aparelho)
      const deviceToken = await messaging().getToken();
      console.log('📱 Device Token gerado:', deviceToken);

      // 3. Envia para o backend registrar
      if (deviceToken) {
        await registrarTokenNoBackend(jwtToken, userId, deviceToken);
      }
    } catch (erro) {
      console.error('❌ Erro ao configurar notificações:', erro);
      // Não interrompe o login se houver erro com Firebase
    }
  };

  /**
   * Fazer login:
   * 1. Valida email/senha contra backend
   * 2. Recebe JWT token
   * 3. Configura notificações push
   * 4. Navega para dashboard
   */
  const fazerLogin = async () => {
    if (!email || !senha) {
      Alert.alert("Atenção", "Digite seu e-mail e senha");
      return;
    }

    setLoading(true);

    try {
      // 1. Backend: validar credenciais (form-urlencoded, endpoint por tipo)
      const form = new URLSearchParams({
        username: email,
        password: senha,
      });
      const responseLogin = await fetch(`${API_URL}/api/v1/login/barbeiro/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded'
        },
        body: form.toString()
      });

      if (!responseLogin.ok) {
        const erro = await responseLogin.json();
        Alert.alert(
          "Erro de Login",
          erro.detail || "E-mail ou senha incorretos"
        );
        setLoading(false);
        return;
      }

      const dadosLogin = await responseLogin.json();
      const jwtToken = dadosLogin.access_token;
      const userId = dadosLogin.user_id;

      console.log('✅ Login bem-sucedido! Token:', jwtToken.substring(0, 20) + '...');

      // 2. Configurar notificações push
      await configurarNotificacoes(jwtToken, userId);

      // 3. Salvar token localmente (AsyncStorage ou similar)
      // await AsyncStorage.setItem('jwt_token', jwtToken);
      // await AsyncStorage.setItem('user_id', userId.toString());

      // 4. Chamar callback de sucesso
      if (onLoginSuccess) {
        onLoginSuccess({
          token: jwtToken,
          userId: userId,
          email: email,
          tipo: dadosLogin.tipo || 'barbeiro'
        });
      }

      // 5. Navegar para dashboard
      if (navigation) {
        navigation.replace('BarberDashboard', { userId });
      }

      Alert.alert("Sucesso", "Login realizado! Você receberá notificações de pagamentos.");

    } catch (erro) {
      console.error('❌ Erro ao fazer login:', erro);
      Alert.alert(
        "Erro de Conexão",
        "Não foi possível conectar ao servidor. Verifique sua internet."
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <KeyboardAvoidingView
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
      style={styles.container}
    >
      <ScrollView contentContainerStyle={styles.scrollViewContent}>
        {/* Header com logo/título */}
        <View style={styles.headerContainer}>
          <MaterialCommunityIcons
            name="scissors-cutting"
            size={60}
            color="#FF6B35"
            style={styles.icon}
          />
          <Text style={styles.titulo}>Barber Move</Text>
          <Text style={styles.subtitulo}>Login Barbeiro</Text>
        </View>

        {/* Formulário */}
        <View style={styles.form}>
          {/* Email */}
          <View style={styles.inputGroup}>
            <MaterialCommunityIcons
              name="email"
              size={20}
              color="#FF6B35"
              style={styles.inputIcon}
            />
            <TextInput
              placeholder="E-mail"
              value={email}
              onChangeText={setEmail}
              keyboardType="email-address"
              autoCapitalize="none"
              editable={!loading}
              style={styles.input}
              placeholderTextColor="#999"
            />
          </View>

          {/* Senha */}
          <View style={styles.inputGroup}>
            <MaterialCommunityIcons
              name="lock"
              size={20}
              color="#FF6B35"
              style={styles.inputIcon}
            />
            <TextInput
              placeholder="Senha"
              value={senha}
              onChangeText={setSenha}
              secureTextEntry={!mostraSenha}
              editable={!loading}
              style={styles.input}
              placeholderTextColor="#999"
            />
            <TouchableOpacity
              onPress={() => setMostraSenha(!mostraSenha)}
              style={styles.eyeIcon}
            >
              <MaterialCommunityIcons
                name={mostraSenha ? 'eye-off' : 'eye'}
                size={20}
                color="#FF6B35"
              />
            </TouchableOpacity>
          </View>

          {/* Botão de login */}
          <TouchableOpacity
            style={[styles.botaoLogin, loading && styles.botaoDisabled]}
            onPress={fazerLogin}
            disabled={loading}
          >
            {loading ? (
              <ActivityIndicator color="#fff" size="small" />
            ) : (
              <>
                <MaterialCommunityIcons
                  name="login"
                  size={20}
                  color="#fff"
                  style={{ marginRight: 8 }}
                />
                <Text style={styles.botaoTexto}>Entrar</Text>
              </>
            )}
          </TouchableOpacity>

          {/* Informações sobre notificações */}
          <View style={styles.infoBox}>
            <MaterialCommunityIcons
              name="information"
              size={20}
              color="#FF6B35"
            />
            <Text style={styles.infoTexto}>
              Você receberá notificações push quando um cliente pagar pelo corte
            </Text>
          </View>

          {/* Link para cadastro (se necessário) */}
          <TouchableOpacity style={styles.linkCadastro}>
            <Text style={styles.textoCadastro}>
              Não tem conta? {''}
              <Text style={{ fontWeight: 'bold', color: '#FF6B35' }}>
                Cadastre-se
              </Text>
            </Text>
          </TouchableOpacity>
        </View>

        {/* Footer de informações técnicas (dev only) */}
        <View style={styles.footerDev}>
          <Text style={styles.textoDev}>
            🔔 Firebase Cloud Messaging habilitado
          </Text>
          <Text style={styles.textoDev}>
            📱 Device Token será capturado após login
          </Text>
        </View>
      </ScrollView>
    </KeyboardAvoidingView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5'
  },
  scrollViewContent: {
    flexGrow: 1,
    justifyContent: 'space-between',
    padding: 20
  },
  headerContainer: {
    alignItems: 'center',
    marginVertical: 40
  },
  icon: {
    marginBottom: 16
  },
  titulo: {
    fontSize: 32,
    fontWeight: 'bold',
    color: '#333',
    marginBottom: 8
  },
  subtitulo: {
    fontSize: 16,
    color: '#666',
    marginBottom: 24
  },
  form: {
    backgroundColor: '#fff',
    borderRadius: 12,
    padding: 24,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3
  },
  inputGroup: {
    flexDirection: 'row',
    alignItems: 'center',
    borderBottomWidth: 1,
    borderBottomColor: '#e0e0e0',
    marginBottom: 20,
    paddingBottom: 12
  },
  inputIcon: {
    marginRight: 12,
    marginTop: 4
  },
  input: {
    flex: 1,
    fontSize: 16,
    color: '#333',
    paddingVertical: 8
  },
  eyeIcon: {
    padding: 4,
    marginLeft: 8
  },
  botaoLogin: {
    backgroundColor: '#FF6B35',
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
    paddingVertical: 16,
    borderRadius: 8,
    marginTop: 20,
    marginBottom: 20
  },
  botaoDisabled: {
    opacity: 0.6
  },
  botaoTexto: {
    color: '#fff',
    fontSize: 16,
    fontWeight: 'bold'
  },
  infoBox: {
    flexDirection: 'row',
    backgroundColor: '#FFF3E0',
    borderRadius: 8,
    padding: 12,
    marginBottom: 16,
    alignItems: 'flex-start'
  },
  infoTexto: {
    color: '#333',
    marginLeft: 8,
    fontSize: 13,
    flex: 1,
    lineHeight: 18
  },
  linkCadastro: {
    alignItems: 'center',
    marginTop: 16
  },
  textoCadastro: {
    color: '#666',
    fontSize: 14
  },
  footerDev: {
    alignItems: 'center',
    marginTop: 20,
    paddingTop: 20,
    borderTopWidth: 1,
    borderTopColor: '#e0e0e0'
  },
  textoDev: {
    fontSize: 12,
    color: '#999',
    marginVertical: 4
  }
});

export default TelaLoginFreelancer;
