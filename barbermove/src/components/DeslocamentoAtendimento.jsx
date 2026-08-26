import { useEffect, useState } from 'react';
import TrackingMapRealtime from './TrackingMapRealtime';

// Acompanhamento (somente leitura) do deslocamento de freelancer/cliente até a
// barbearia, para o painel do proprietário. Ao contrário do TrackingPanel (usado
// por cliente/freelancer), este componente NUNCA ativa o GPS de quem o renderiza
// — só consome o snapshot já calculado pelo backend em /tracking/chamados/{id}/eta,
// que já restringe o acesso ao dono da própria barbearia do chamado.
export default function DeslocamentoAtendimento({ chamado, token, API_URL }) {
  const [tracking, setTracking] = useState(null);

  useEffect(() => {
    if (!chamado?.id || !token || !API_URL) return;
    let cancelado = false;

    const carregar = async () => {
      try {
        const res = await fetch(`${API_URL}/api/v1/tracking/chamados/${chamado.id}/eta`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!res.ok || cancelado) return;
        const data = await res.json();
        if (!cancelado) setTracking(data);
      } catch (_err) {
        // mantém o último estado conhecido
      }
    };

    carregar();
    const interval = setInterval(carregar, 5000);
    return () => {
      cancelado = true;
      clearInterval(interval);
    };
  }, [chamado?.id, token, API_URL]);

  // mostrar_mapa vem do backend (_tracking_ativo_por_status): só true enquanto o
  // chamado está confirmado/aceito. Assim que vira em_atendimento (ou é
  // cancelado), essa seção some sozinha e o atendimento passa a aparecer em
  // "Atendimentos em andamento" — cobre a transição A caminho → Chegou → Atendimento iniciado.
  if (!tracking || !tracking.mostrar_mapa) return null;

  const coordsBarbearia = tracking.barbearia?.latitude != null && tracking.barbearia?.longitude != null
    ? { lat: Number(tracking.barbearia.latitude), lon: Number(tracking.barbearia.longitude) }
    : null;
  const coordsCliente = tracking.coordenadas_cliente?.lat != null && tracking.coordenadas_cliente?.lon != null
    ? { lat: Number(tracking.coordenadas_cliente.lat), lon: Number(tracking.coordenadas_cliente.lon) }
    : null;
  const coordsBarbeiro = tracking.coordenadas_barbeiro?.lat != null && tracking.coordenadas_barbeiro?.lon != null
    ? { lat: Number(tracking.coordenadas_barbeiro.lat), lon: Number(tracking.coordenadas_barbeiro.lon) }
    : null;

  const nomeFreelancer = chamado.barbeiro_nome || chamado.nome_barbeiro || 'Freelancer';
  const nomeCliente = chamado.cliente_nome || chamado.nome_cliente || 'Cliente';

  return (
    <div className="space-y-2">
      {chamado.barbeiro_id && (
        <div className="bm-card p-3.5 space-y-2">
          <span className={`inline-flex text-[11px] font-extrabold px-2 py-1 rounded-full ${tracking.barbeiro_chegou ? 'bg-emerald-600/20 text-emerald-300' : 'bg-yellow-500/20 text-yellow-300'}`}>
            {tracking.barbeiro_chegou ? '🟢 FREELANCER CHEGOU' : '🟡 FREELANCER A CAMINHO'}
          </span>
          <p className="text-xs text-zinc-300">Freelancer: <span className="font-semibold text-white">{nomeFreelancer}</span></p>
          <p className="text-xs text-zinc-300">Cliente: <span className="font-semibold text-white">{nomeCliente}</span></p>
          {!tracking.barbeiro_chegou && coordsBarbeiro && coordsBarbearia && (
            <TrackingMapRealtime
              origem={coordsBarbeiro}
              destino={coordsBarbearia}
              titulo="Freelancer para barbearia"
              subtitulo={tracking.freelancer_distancia_ate_barbearia_km != null ? `Distância: ${Number(tracking.freelancer_distancia_ate_barbearia_km).toFixed(2)} km` : null}
              height="200px"
              isMoving
            />
          )}
        </div>
      )}

      <div className="bm-card p-3.5 space-y-2">
        <span className={`inline-flex text-[11px] font-extrabold px-2 py-1 rounded-full ${tracking.cliente_chegou ? 'bg-emerald-600/20 text-emerald-300' : 'bg-yellow-500/20 text-yellow-300'}`}>
          {tracking.cliente_chegou ? '🟢 CLIENTE CHEGOU' : '🟡 CLIENTE A CAMINHO'}
        </span>
        <p className="text-xs text-zinc-300">Cliente: <span className="font-semibold text-white">{nomeCliente}</span></p>
        <p className="text-xs text-zinc-300">Freelancer: <span className="font-semibold text-white">{nomeFreelancer}</span></p>
        {!tracking.cliente_chegou && coordsCliente && coordsBarbearia && (
          <TrackingMapRealtime
            origem={coordsCliente}
            destino={coordsBarbearia}
            titulo="Cliente para barbearia"
            subtitulo={tracking.cliente_distancia_ate_barbearia_km != null ? `Distância: ${Number(tracking.cliente_distancia_ate_barbearia_km).toFixed(2)} km` : null}
            height="200px"
            isMoving
          />
        )}
      </div>
    </div>
  );
}
