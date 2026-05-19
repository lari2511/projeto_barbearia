import React, { useEffect, useState, useRef } from 'react';

export default function ChatRoom({ chamadoId, token, API_URL, compact = true }) {
    const [messages, setMessages] = useState([]);
    const [text, setText] = useState('');
    const listRef = useRef(null);

    useEffect(() => {
        if (!chamadoId) return;

        const carregarMensagens = async () => {
            try {
                const res = await fetch(`${API_URL}/api/v1/chat/${chamadoId}/mensagens`, {
                    headers: { 'Authorization': `Bearer ${token}` }
                });
                if (!res.ok) return;
                const data = await res.json();
                setMessages(Array.isArray(data) ? data : []);
            } catch (_err) {
                // ignore
            }
        };

        carregarMensagens();
        const interval = window.setInterval(carregarMensagens, 3000);
        return () => window.clearInterval(interval);
    }, [chamadoId, token, API_URL]);

    const send = async () => {
        if (!text || !chamadoId) return;
        try {
            const res = await fetch(`${API_URL}/api/v1/chat/mensagem`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
                body: JSON.stringify({ chamado_id: chamadoId, mensagem: text })
            });
            if (!res.ok) return;
            setText('');
            const data = await res.json().catch(() => null);
            if (data) {
                setMessages((prev) => [...prev, data]);
            }
        } catch (_err) {
            // ignore
        }
    };
    useEffect(() => {
        // rolar para baixo quando mensagens mudarem
        if (listRef.current) {
            listRef.current.scrollTop = listRef.current.scrollHeight;
        }
    }, [messages]);

    return (
        <div className={`${compact ? 'bg-zinc-900/60 border border-zinc-800 rounded-lg p-2 space-y-2' : 'bg-zinc-950 border border-zinc-800 rounded-2xl p-4 space-y-4 text-sm'}`}>
            <div ref={listRef} className={`${compact ? 'max-h-40' : 'max-h-[65vh]'} overflow-auto space-y-3`}>
                {messages.map((m, i) => (
                    <div key={i} className={`${compact ? 'text-xs p-1 rounded bg-black/30' : 'p-3 rounded-lg bg-black/30'} `}>
                        {!compact && <div className="text-[11px] text-zinc-400 mb-1 font-medium">{m.remetente_id}</div>}
                        <div className={`${compact ? 'text-white' : 'text-white text-sm'}`}>{m.mensagem}</div>
                        <div className={`${compact ? 'text-[10px] text-zinc-500' : 'text-[11px] text-zinc-500 mt-2'}`}>{new Date(m.criado_em || Date.now()).toLocaleTimeString()}</div>
                    </div>
                ))}
            </div>
            <div className="flex gap-2 items-center">
                <input value={text} onChange={e => setText(e.target.value)} placeholder="Mensagem..." className={`${compact ? 'flex-1 bg-black/40 rounded p-2 text-xs outline-none' : 'flex-1 bg-black/30 rounded-lg p-3 text-sm outline-none'}`} />
                <button onClick={send} className={`${compact ? 'bg-orange-600 px-3 py-2 rounded text-xs' : 'bg-orange-600 px-4 py-3 rounded-lg text-sm font-bold'}`}>Enviar</button>
            </div>
        </div>
    );
}
