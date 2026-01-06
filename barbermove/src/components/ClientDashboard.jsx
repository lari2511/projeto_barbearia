import React, { useState, useEffect } from 'react';
import { LogOut, Search, MapPin, Star, History, Calendar, ArrowRight, CheckCircle } from 'lucide-react';

const getShopImage = (id) => `https://images.unsplash.com/photo-${id % 2 === 0 ? '1521590832874-552721032d00' : '1503951914290-d20607416905'}?auto=format&fit=crop&w=800&q=80`;

export default function ClientDashboard({ token, logout, API_URL, notify }) {
    const [shops, setShops] = useState([]);
    const [tab, setTab] = useState('lojas'); 
    const [selectedShop, setSelectedShop] = useState(null);
    const [services, setServices] = useState([]);
    const [myOrders, setMyOrders] = useState([]);
    const [barbeiroInfo, setBarbeiroInfo] = useState(null);

    useEffect(() => {
        fetch(`${API_URL}/barbearias`)
            .then(r => r.json())
            .then(setShops)
            .catch(() => {
                setShops([
                    {id: 1, nome: "Barbearia do Zé", endereco: "Rua Augusta, 100", avaliacao: 4.8}, 
                    {id: 2, nome: "Estilo & Corte", endereco: "Av. Paulista, 200", avaliacao: 4.5}
                ]);
            });

        fetch(`${API_URL}/meus-agendamentos`, { headers: {'Authorization': `Bearer ${token}`} })
            .then(r => r.json())
            .then(setMyOrders)
            .catch(() => setMyOrders([]));
    }, [API_URL, token]);

    const handleSelectShop = async (shop) => {
        setSelectedShop(shop);
        try {
            const res = await fetch(`${API_URL}/barbearia/${shop.id}/servicos`);
            const data = await res.json();
            setServices(data);
            
            // Buscar informações do barbeiro/barbearia para verificação
            const infoRes = await fetch(`${API_URL}/usuario/${shop.usuario_id}`, {
                headers: {'Authorization': `Bearer ${token}`}
            });
            if (infoRes.ok) {
                const info = await infoRes.json();
                setBarbeiroInfo(info);
            }
        } catch {
            setServices([{id: 1, nome: "Corte Cabelo", valor: 35}, {id: 2, nome: "Barba Completa", valor: 25}]);
        }
    };

    const handleBooking = async (service) => {
        if(!confirm(`Agendar ${service.nome} por R$${service.valor}?`)) return;
        
        try {
            await fetch(`${API_URL}/agendar`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
                body: JSON.stringify({ servico_id: service.id, barbearia_id: selectedShop.id })
            });
            notify("Agendamento realizado!", "success");
            setSelectedShop(null);
            setTab('pedidos');
        } catch {
            notify("Erro ao agendar (Mock: Sucesso)", "success");
            setSelectedShop(null);
            setTab('pedidos');
        }
    };

    return (
      <div className="bg-black h-full flex flex-col w-full text-white font-sans">
        {!selectedShop ? (
          <>
            <div className="p-5 pt-8 sticky top-0 bg-black/80 backdrop-blur-md z-20 border-b border-zinc-800">
                <div className="flex justify-between items-center mb-4">
                    <h1 className="text-xl font-bold">Olá, Cliente</h1>
                    <button onClick={logout} className="p-2 bg-zinc-900 rounded-full text-zinc-400 hover:text-white"><LogOut size={16}/></button>
                </div>
                {tab === 'lojas' && (
                    <div className="relative">
                        <Search className="absolute left-3 top-3 text-zinc-500" size={18} />
                        <input placeholder="Buscar barbearia..." className="w-full bg-zinc-900 pl-10 pr-4 py-3 rounded-xl border border-zinc-800 outline-none focus:border-orange-500 text-sm" />
                    </div>
                )}
            </div>

            <div className="flex-1 overflow-y-auto p-4 space-y-4 pb-24">
                {tab === 'lojas' ? shops.map(shop => (
                    <div key={shop.id} onClick={() => handleSelectShop(shop)} className="bg-zinc-900 rounded-2xl overflow-hidden border border-zinc-800 active:scale-95 transition-transform cursor-pointer group">
                        <div className="h-32 w-full relative">
                            <img src={getShopImage(shop.id)} className="w-full h-full object-cover opacity-60 group-hover:opacity-80 transition-opacity" alt={shop.nome} />
                            <div className="absolute bottom-2 left-3 font-bold text-lg shadow-black drop-shadow-md">{shop.nome}</div>
                            <div className="absolute top-2 right-2 bg-black/60 px-2 py-1 rounded text-[10px] font-bold flex gap-1 items-center"><Star size={10} className="text-orange-500 fill-orange-500"/> {shop.avaliacao || 5.0}</div>
                        </div>
                        <div className="p-3 flex justify-between items-center">
                            <p className="text-xs text-zinc-400 flex items-center gap-1"><MapPin size={12}/> {shop.endereco}</p>
                            <span className="text-green-500 text-[10px] font-bold px-2 py-1 bg-green-900/20 rounded">ABERTO</span>
                        </div>
                    </div>
                )) : (
                    <div className="space-y-3">
                        <h2 className="font-bold text-sm text-zinc-400 uppercase tracking-widest mb-4">Meus Agendamentos</h2>
                        {myOrders.length === 0 && <p className="text-zinc-600 text-center py-10">Nenhum agendamento.</p>}
                        {myOrders.map((p, i) => (
                            <div key={i} className="bg-zinc-900 p-4 rounded-xl border border-zinc-800 flex gap-4 items-center">
                                <div className="h-10 w-10 rounded-full bg-orange-600/20 flex items-center justify-center text-orange-500"><Calendar size={18}/></div>
                                <div className="flex-1">
                                    <h3 className="font-bold text-sm">{p.servico_nome || "Corte Masculino"}</h3>
                                    <p className="text-xs text-zinc-500">{p.barbearia_nome || "Barbearia Zé"}</p>
                                </div>
                                <div className="text-right">
                                    <span className="block text-green-400 font-bold text-sm">R$ {p.valor || 35.00}</span>
                                    <span className="text-[10px] text-zinc-500">{p.status || "Agendado"}</span>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>

            <div className="absolute bottom-0 left-0 w-full bg-zinc-950/90 backdrop-blur-lg border-t border-zinc-800 p-2 pb-6 flex justify-around items-center z-50">
              <button onClick={() => setTab('lojas')} className={`flex flex-col items-center gap-1 p-2 w-20 ${tab === 'lojas' ? 'text-orange-500' : 'text-zinc-600'}`}><Search size={20} /><span className="text-[10px] font-bold">Explorar</span></button>
              <button onClick={() => setTab('pedidos')} className={`flex flex-col items-center gap-1 p-2 w-20 ${tab === 'pedidos' ? 'text-orange-500' : 'text-zinc-600'}`}><History size={20} /><span className="text-[10px] font-bold">Agenda</span></button>
            </div>
          </>
        ) : (
          <div className="h-full flex flex-col bg-zinc-900 w-full animate-in slide-in-from-right">
             <div className="relative h-64 shrink-0">
                <img src={getShopImage(selectedShop.id)} className="w-full h-full object-cover" alt="Shop" />
                <div className="absolute inset-0 bg-gradient-to-t from-black via-transparent to-transparent"></div>
                <button onClick={() => setSelectedShop(null)} className="absolute top-4 left-4 p-2 bg-black/50 rounded-full text-white backdrop-blur"><ArrowRight size={20} className="rotate-180"/></button>
                <div className="absolute bottom-4 left-4">
                    <div className="flex items-center gap-2 mb-1">
                        <h1 className="text-2xl font-bold">{selectedShop.nome}</h1>
                        {barbeiroInfo?.documento_verificado && (
                            <CheckCircle size={24} className="text-blue-500 fill-blue-500" title="Verificado ✓" />
                        )}
                    </div>
                    <p className="text-zinc-300 text-xs flex items-center gap-1"><MapPin size={12}/> {selectedShop.endereco}</p>
                </div>
            </div>
            <div className="flex-1 bg-black -mt-6 rounded-t-3xl p-6 relative z-10 overflow-y-auto pb-20">
                <div className="w-10 h-1 bg-zinc-800 rounded-full mx-auto mb-6"></div>
                <h3 className="text-zinc-500 text-[10px] font-bold uppercase tracking-widest mb-3">Serviços</h3>
                <div className="space-y-3">
                    {services.map(s => (
                        <div key={s.id} className="flex justify-between items-center bg-zinc-900 p-4 rounded-xl border border-zinc-800">
                            <div><span className="block font-bold text-sm">{s.nome}</span><span className="text-green-400 text-xs font-bold">R$ {s.valor}</span></div>
                            <button onClick={() => handleBooking(s)} className="bg-white text-black px-4 py-2 rounded-lg font-bold text-xs flex items-center gap-2 active:scale-95">Agendar</button>
                        </div>
                    ))}
                </div>
            </div>
          </div>
        )}
      </div>
    );
}