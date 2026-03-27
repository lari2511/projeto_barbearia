import React, { useState, useEffect } from 'react';
import { Star, X, Send, AlertCircle } from 'lucide-react';

export default function AvaliacaoModal({ isOpen, onClose, onSubmit, titulo = "Avaliar Serviço" }) {
    const [nota, setNota] = useState(0);
    const [hoverNota, setHoverNota] = useState(0);
    const [comentario, setComentario] = useState('');
    const [enviando, setEnviando] = useState(false);
    const [erro, setErro] = useState('');

    // Resetar campos quando título muda (novo chamado é selecionado)
    useEffect(() => {
        if (isOpen) {
            setNota(0);
            setComentario('');
            setErro('');
        }
    }, [titulo, isOpen]);

    const handleSubmit = async () => {
        if (nota === 0) {
            setErro('Por favor, selecione uma nota');
            return;
        }

        setEnviando(true);
        setErro('');

        try {
            const sucesso = await onSubmit({ nota, comentario });
            if (sucesso === false) {
                return;
            }
            setNota(0);
            setComentario('');
            onClose();
        } catch (_err) {
            setErro('Erro ao enviar avaliação. Tente novamente.');
        } finally {
            setEnviando(false);
        }
    };

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-[9999] p-4">
            <div className="bg-zinc-900 rounded-2xl w-full max-w-sm border border-zinc-800 animate-in scale-in-95">
                {/* Header */}
                <div className="flex justify-between items-center p-6 border-b border-zinc-800">
                    <h2 className="text-xl font-bold text-white">{titulo}</h2>
                    <button
                        onClick={onClose}
                        className="text-zinc-400 hover:text-white p-1 hover:bg-zinc-800 rounded-lg"
                    >
                        <X size={20} />
                    </button>
                </div>

                {/* Body */}
                <div className="p-6 space-y-6">
                    {/* Seleção de Estrelas */}
                    <div className="text-center">
                        <p className="text-zinc-400 text-sm mb-4">Qual foi sua experiência?</p>
                        <div className="flex justify-center gap-2">
                            {[1, 2, 3, 4, 5].map((estrela) => (
                                <button
                                    key={estrela}
                                    onClick={() => setNota(estrela)}
                                    onMouseEnter={() => setHoverNota(estrela)}
                                    onMouseLeave={() => setHoverNota(0)}
                                    className="transition-transform hover:scale-110"
                                >
                                    <Star
                                        size={48}
                                        className={`transition-colors ${
                                            (hoverNota || nota) >= estrela
                                                ? 'fill-orange-500 text-orange-500'
                                                : 'text-zinc-700'
                                        }`}
                                    />
                                </button>
                            ))}
                        </div>
                        {nota > 0 && (
                            <p className="text-orange-500 font-bold mt-3 text-lg">
                                {nota === 1 ? 'Péssimo 😞' : nota === 2 ? 'Ruim 😐' : nota === 3 ? 'Bom 😊' : nota === 4 ? 'Muito Bom 😄' : 'Excelente! 🤩'}
                            </p>
                        )}
                    </div>

                    {/* Comentário */}
                    <div>
                        <label className="text-zinc-400 text-sm font-bold mb-2 block">
                            Deixe um comentário (opcional)
                        </label>
                        <textarea
                            value={comentario}
                            onChange={(e) => setComentario(e.target.value)}
                            placeholder="Conte-nos sua experiência..."
                            maxLength={500}
                            className="w-full bg-zinc-800 border border-zinc-700 rounded-lg p-3 text-white placeholder-zinc-500 focus:border-orange-500 outline-none resize-none"
                            rows={4}
                        />
                        <p className="text-zinc-500 text-xs mt-2">
                            {comentario.length}/500 caracteres
                        </p>
                    </div>

                    {/* Mensagem de Erro */}
                    {erro && (
                        <div className="flex items-center gap-2 bg-red-900/20 border border-red-800 rounded-lg p-3">
                            <AlertCircle size={16} className="text-red-500" />
                            <p className="text-red-300 text-sm">{erro}</p>
                        </div>
                    )}
                </div>

                {/* Footer */}
                <div className="flex gap-3 p-6 border-t border-zinc-800">
                    <button
                        onClick={onClose}
                        disabled={enviando}
                        className="flex-1 bg-zinc-800 hover:bg-zinc-700 text-white py-3 rounded-lg font-bold disabled:opacity-50"
                    >
                        Cancelar
                    </button>
                    <button
                        onClick={handleSubmit}
                        disabled={enviando || nota === 0}
                        className="flex-1 bg-orange-600 hover:bg-orange-700 disabled:bg-zinc-700 text-white py-3 rounded-lg font-bold flex items-center justify-center gap-2 disabled:opacity-50"
                    >
                        <Send size={16} />
                        {enviando ? 'Enviando...' : 'Enviar'}
                    </button>
                </div>
            </div>
        </div>
    );
}
