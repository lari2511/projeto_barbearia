import React, { useState, useEffect } from 'react';
import { Scissors, LogOut, MapPin, CheckCircle, AlertCircle } from 'lucide-react';

export default function BarberDashboard({ token, logout, notify, API_URL }) {
    const [jobs, setJobs] = useState(() => [{ id: 1, cliente: "João Silva", servico: "Corte Degradê", valor: 40, endereco: "Rua B, 123" }]);
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

    const acceptJob = (id) => {
        notify("Trabalho aceito! Navegue até o cliente.", "success");
        setJobs(jobs.filter(j => j.id !== id));
    };

    return (
        <div className="bg-black h-full p-4 text-white font-sans">
            <div className="flex justify-between items-center mb-6 pt-4">
                <div className="flex items-center gap-2">
                    <h1 className="text-xl font-bold flex items-center gap-2">
                        <Scissors className="text-orange-500"/> Área do Barbeiro
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
                        <span className="text-yellow-400 text-xs">Complete sua verificação para receber chamados</span>
                    </div>
                </div>
            )}
            
            <div className="bg-orange-600/10 border border-orange-600/30 p-4 rounded-xl mb-6 flex items-center gap-3">
                <div className="h-2 w-2 bg-green-500 rounded-full animate-pulse"></div>
                <span className="text-orange-500 font-bold text-sm">Disponível para chamados</span>
            </div>
            <h3 className="text-zinc-500 text-xs font-bold uppercase mb-4">Novos Chamados</h3>
            <div className="space-y-4">
                {jobs.map(job => (
                    <div key={job.id} className="bg-zinc-900 p-5 rounded-2xl border border-zinc-800 relative">
                        <div className="absolute top-0 right-0 bg-orange-500 text-white text-[10px] font-bold px-3 py-1 rounded-bl-xl">NOVO</div>
                        <h3 className="font-bold text-lg mb-1">{job.cliente}</h3>
                        <p className="text-zinc-400 text-xs mb-3 flex items-center gap-1"><MapPin size={12}/> {job.endereco}</p>
                        <div className="bg-black/40 p-3 rounded-xl mb-3 border border-zinc-800/50 flex justify-between items-center">
                            <span className="text-sm font-medium">{job.servico}</span>
                            <span className="text-green-400 font-bold">R$ {job.valor}</span>
                        </div>
                        <button onClick={() => acceptJob(job.id)} className="w-full bg-white text-black py-3 rounded-xl font-bold text-sm hover:bg-zinc-200">ACEITAR CORRIDA</button>
                    </div>
                ))}
                {jobs.length === 0 && <p className="text-zinc-600 text-center text-sm py-10">Procurando clientes próximos...</p>}
            </div>
        </div>
    );
}