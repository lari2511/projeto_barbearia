import PainelBarberMovePremium from './PainelBarberMovePremium';

export default function BarberDashboard({ token, logout, API_URL, notify }) {
  return <PainelBarberMovePremium token={token} logout={logout} API_URL={API_URL} notify={notify} />;
}
