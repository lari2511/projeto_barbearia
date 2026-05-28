// Shim for @react-native-firebase/messaging
const AuthorizationStatus = {
  AUTHORIZED: 1,
  PROVISIONAL: 2,
  DENIED: 0
};

export default () => ({
  AuthorizationStatus,
  requestPermission: async () => AuthorizationStatus.AUTHORIZED,
  getToken: async () => null,
  onMessage: (cb) => ({ remove: () => {} }),
  setBackgroundMessageHandler: (cb) => {}
});
