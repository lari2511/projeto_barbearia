import React, { useState, useEffect } from 'react';
import { MapPin, Clock, Phone, MessageCircle, AlertCircle, X } from 'lucide-react';

const TelaRotasAtivos = ({ chamado, userType, userLocation, clienteLocation, barbeiroLocation, barbearia, barbeiro, onNotify, onClose }) => {
  const [rotaInfo, setRotaInfo] = useState(null);
  const [tempoChegada, setTempoChegada] = useState(null);
  const [distancia, setDistancia] = useState(null);
  const [erroMapa, setErroMapa] = useState(null);
  const [mostrandoRota, setMostrandoRota] = useState(true);

  // Calcula distância em km usando Haversine
  const calcularDistancia = (lat1, lon1, lat2, lon2) => {
    const toRad = (x) => (x * Math.PI) / 180;
    const R = 6371; // Raio da Terra em km
    const dLat = toRad(lat2 - lat1);
    const dLon = toRad(lon2 - lon1);
    const a = 
      Math.sin(dLat / 2) * Math.sin(dLat / 2) +
      Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) *
      Math.sin(dLon / 2) * Math.sin(dLon / 2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    return R * c;
  };

  // Estima tempo em minutos (velocidade média: 40 km/h em área urbana)
  const estimarTempo = (kmDistancia) => {
    return Math.ceil((kmDistancia / 40) * 60);
  };

  useEffect(() => {
    if (userType === 'cliente' && barbeiroLocation && barbearia) {
      // Para o cliente: rota do barbeiro até a barbearia
      const dist = calcularDistancia(
        barbeiroLocation.latitude,
        barbeiroLocation.longitude,
        barbearia.latitude,
        barbearia.longitude
      );
      const tempo = estimarTempo(dist);
      setDistancia(dist.toFixed(1));
      setTempoChegada(tempo);
    } else if (userType === 'barbeiro' && clienteLocation && barbearia) {
      // Para o barbeiro: rota do cliente até a barbearia
      const dist = calcularDistancia(
        clienteLocation.latitude,
        clienteLocation.longitude,
        barbearia.latitude,
        barbearia.longitude
      );
      const tempo = estimarTempo(dist);
      setDistancia(dist.toFixed(1));
      setTempoChegada(tempo);
    }
  }, [userType, barbeiroLocation, clienteLocation, barbearia]);

  if (!chamado || !barbearia) {
    return null;
  }

  const handleClose = () => {
    setMostrandoRota(false);
    if (onClose) onClose();
  };

  if (!mostrandoRota) {
    return null;
  }

  // Construir URL do Google Maps
  const getGoogleMapsUrl = () => {
    if (userType === 'cliente' && barbeiroLocation) {
      // Rota do barbeiro até a barbearia
      return `https://www.google.com/maps/dir/${barbeiroLocation.latitude},${barbeiroLocation.longitude}/${barbearia.latitude},${barbearia.longitude}`;
    } else if (userType === 'barbeiro' && clienteLocation) {
      // Rota do cliente até a barbearia
      return `https://www.google.com/maps/dir/${clienteLocation.latitude},${clienteLocation.longitude}/${barbearia.latitude},${barbearia.longitude}`;
    }
    return null;
  };

  const openMapApp = () => {
    const mapsUrl = getGoogleMapsUrl();
    if (mapsUrl) {
      window.open(mapsUrl, '_blank');
    }
  };

  return (
    <div className="fixed inset-0 bg-black/80 flex items-end z-50">
      <div className="w-full bg-zinc-900 rounded-t-3xl p-6 space-y-4 max-h-[80vh] overflow-y-auto">
        {/* Cabeçalho */}
        <div className="text-center border-b border-zinc-700 pb-4 relative">
          <button
            onClick={handleClose}
            className="absolute right-0 top-0 bg-zinc-800 hover:bg-zinc-700 text-white p-2 rounded-full transition"
          >
            <X className="w-5 h-5" />
          </button>
          <h2 className="text-2xl font-bold text-white mb-2">
            {userType === 'cliente' ? '🚗 Barbeiro a Caminho' : '🚗 Cliente a Caminho'}
          </h2>
          <p className="text-zinc-400 text-sm">
            {userType === 'cliente' 
              ? `${barbeiro?.nome || 'Barbeiro'} está vindo para a barbearia`
              : `Cliente está vindo para a barbearia`}
          </p>
        </div>

        {/* Info Principal */}
        <div className="bg-gradient-to-r from-orange-600 to-red-600 rounded-2xl p-6 text-white text-center">
          <div className="flex items-center justify-center gap-3 mb-2">
            <Clock className="w-6 h-6" />
            <div>
              <p className="text-sm opacity-80">Tempo de Chegada</p>
              <p className="text-3xl font-bold">{tempoChegada} min</p>
            </div>
          </div>
          <p className="text-sm opacity-80">Distância: {distancia} km</p>
        </div>

        {/* Info do Barbearia */}
        <div className="bg-zinc-800 rounded-xl p-4">
          <div className="flex items-start gap-3">
            <MapPin className="w-5 h-5 text-orange-500 mt-1 flex-shrink-0" />
            <div>
              <p className="text-white font-bold">{barbearia.nome}</p>
              <p className="text-zinc-400 text-sm">{barbearia.endereco || 'Localização não definida'}</p>
              {barbearia.telefone && (
                <p className="text-zinc-400 text-sm mt-2">{barbearia.telefone}</p>
              )}
            </div>
          </div>
        </div>

        {/* Info do Outro Usuário */}
        {userType === 'cliente' && barbeiro && (
          <div className="bg-zinc-800 rounded-xl p-4">
            <div className="flex items-start gap-3">
              <div className="w-10 h-10 bg-gradient-to-br from-orange-500 to-red-600 rounded-full flex items-center justify-center text-white font-bold flex-shrink-0">
                {barbeiro.nome?.[0]?.toUpperCase()}
              </div>
              <div className="flex-1">
                <p className="text-white font-bold">{barbeiro.nome}</p>
                <p className="text-zinc-400 text-sm">Barbeiro</p>
              </div>
            </div>
          </div>
        )}

        {/* Botão de Abrir Mapa */}
        <button
          onClick={openMapApp}
          className="w-full bg-orange-600 hover:bg-orange-700 text-white font-bold py-4 rounded-xl transition flex items-center justify-center gap-2"
        >
          <MapPin className="w-5 h-5" />
          Ver Rota Completa no Mapa
        </button>

        {/* Contato Rápido */}
        <div className="flex gap-3">
          {barbeiro?.telefone && userType === 'cliente' && (
            <a
              href={`tel:${barbeiro.telefone}`}
              className="flex-1 bg-green-600 hover:bg-green-700 text-white font-bold py-3 rounded-xl transition flex items-center justify-center gap-2"
            >
              <Phone className="w-5 h-5" />
              Ligar
            </a>
          )}
          {userType === 'cliente' && (
            <button
              onClick={() => onNotify && onNotify('Mensagem enviada para o barbeiro', 'info')}
              className="flex-1 bg-blue-600 hover:bg-blue-700 text-white font-bold py-3 rounded-xl transition flex items-center justify-center gap-2"
            >
              <MessageCircle className="w-5 h-5" />
              Mensagem
            </button>
          )}
        </div>

        {/* Status do Chamado */}
        <div className="bg-blue-900/30 border border-blue-600 rounded-xl p-4">
          <div className="flex items-start gap-2">
            <AlertCircle className="w-5 h-5 text-blue-400 mt-0.5 flex-shrink-0" />
            <div className="text-sm text-blue-200">
              <p className="font-semibold">Status: {chamado.status?.toUpperCase()}</p>
              <p className="mt-1">Serviço: {chamado.descricao || 'Não especificado'}</p>
              <p>Valor: R$ {chamado.valor || '0,00'}</p>
            </div>
          </div>
        </div>

        {/* Aviso */}
        <div className="bg-yellow-900/30 border border-yellow-600 rounded-xl p-3">
          <p className="text-yellow-200 text-xs text-center">
            O tempo estimado pode variar. Acompanhe a localização em tempo real no mapa.
          </p>
        </div>
      </div>
    </div>
  );
};

export default TelaRotasAtivos;
