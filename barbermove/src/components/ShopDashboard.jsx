import React, { useState, useEffect } from 'react';
import { Store, LogOut, CheckCircle, AlertCircle } from 'lucide-react';

export default function ShopDashboard({ token, logout, notify, API_URL }) {
    const [services, setServices] = useState([{id: 1, nome: "Corte Simples", valor: 30}]);
    const [newService, setNewService] = useState({nome: '', valor: ''});
    const [user, setUser] = useState(null);

    useEffect(() => {
        // Buscar informações do usuário para verificar status
        fetch(`${API_URL}/api/v1/documentos/status`, {
            headers: {'Authorization': `Bearer ${token}`}
        })
        .then(r => r.json())
        .then(data => setUser(data))
        .catch(() => {});
    }, [API_URL, token]);

    const addService = (e) => {
        e.preventDefault();
        setServices([...services, {id: Date.now(), nome: newService.nome, valor: parseFloat(newService.valor)}]);
        setNewService({nome: '', valor: ''});
        notify("Serviço adicionado!", "success");
    };

    return (
        <div className="bg-black h-full p-4 text-white font-sans">
            <div className="flex justify-between items-center mb-6 pt-4">
                <div className="flex items-center gap-2">
                    <h1 className="text-xl font-bold flex items-center gap-2">
                        <Store className="text-orange-500"/> Gestão da Loja
                    </h1>
                    {user?.documento_verificado && (
                        <CheckCircle size={20} className="text-blue-500 fill-blue-500" title="Verificado ✓" />
                    )}
                </div>
                <button onClick={logout} className="text-zinc-500"><LogOut size={20}/></button>
            </div>

            {/* Alerta de verificação pendente */}
            {user && !user.documento_verificado && (
                <div className="bg-yellow-600/10 border border-yellow-600/30 p-4 rounded-xl mb-4 flex items-center gap-3">
                    <AlertCircle size={20} className="text-yellow-500"/>
                    <div className="flex-1">
                        <span className="text-yellow-500 font-bold text-sm block">Verificação Pendente</span>
                        <span className="text-yellow-400 text-xs">Complete sua verificação para ativar a loja</span>
                    </div>
                </div>
            )}

            <div className="bg-zinc-900 p-5 rounded-2xl border border-zinc-800 mb-6">
                <h3 className="font-bold mb-4 text-sm">Adicionar Serviço</h3>
                <form onSubmit={addService} className="flex gap-2 mb-4">
                    <input className="flex-1 bg-black rounded-lg p-3 border border-zinc-800 text-sm outline-none focus:border-orange-500" placeholder="Nome (ex: Barba)" value={newService.nome} onChange={e => setNewService({...newService, nome: e.target.value})} required/>
                    <input className="w-20 bg-black rounded-lg p-3 border border-zinc-800 text-sm outline-none focus:border-orange-500 text-center" type="number" placeholder="R$" value={newService.valor} onChange={e => setNewService({...newService, valor: e.target.value})} required/>
                    <button className="bg-white text-black w-10 rounded-lg font-bold text-xl flex items-center justify-center hover:bg-zinc-200">+</button>
                </form>
                <div className="space-y-2">
                    {services.map(s => (
                        <div key={s.id} className="flex justify-between items-center bg-black/40 p-3 rounded-lg border border-zinc-800/50">
                            <span className="text-sm">{s.nome}</span>
                            <span className="font-bold text-green-400">R$ {s.valor}</span>
                        </div>
                    ))}
                </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
                <div className="bg-zinc-900 p-4 rounded-xl border border-zinc-800 text-center">
                    <h4 className="text-zinc-500 text-[10px] uppercase font-bold mb-2">Faturamento Hoje</h4>
                    <p className="text-2xl font-bold text-green-500">R$ 450</p>
                </div>
                <div className="bg-zinc-900 p-4 rounded-xl border border-zinc-800 text-center">
                    <h4 className="text-zinc-500 text-[10px] uppercase font-bold mb-2">Agendamentos</h4>
                    <p className="text-2xl font-bold text-white">12</p>
                </div>
            </div>
        </div>
    );
}