import React from 'react';
import { Star, ThumbsUp } from 'lucide-react';

export default function ListaAvaliacoes({ avaliacoes = [] }) {
    if (!avaliacoes || avaliacoes.length === 0) {
        return (
            <div className="text-center py-12 text-zinc-500">
                <Star size={32} className="mx-auto mb-3 opacity-50" />
                <p>Nenhuma avaliação ainda</p>
            </div>
        );
    }

    // Calcular média de notas
    const mediaNotas = (avaliacoes.reduce((sum, av) => sum + (av.nota || 0), 0) / avaliacoes.length).toFixed(1);
    const totalAvaliacoes = avaliacoes.length;

    // Contar distribuição de notas
    const distribuicao = {
        5: avaliacoes.filter(av => av.nota === 5).length,
        4: avaliacoes.filter(av => av.nota === 4).length,
        3: avaliacoes.filter(av => av.nota === 3).length,
        2: avaliacoes.filter(av => av.nota === 2).length,
        1: avaliacoes.filter(av => av.nota === 1).length,
    };

    return (
        <div className="space-y-6">
            {/* Resumo */}
            <div className="bg-gradient-to-br from-orange-500/10 to-red-500/10 border border-orange-500/30 rounded-2xl p-6">
                <div className="flex items-end gap-4">
                    <div>
                        <div className="text-5xl font-bold text-orange-500">{mediaNotas}</div>
                        <p className="text-zinc-400 text-sm mt-1">{totalAvaliacoes} avaliação{totalAvaliacoes !== 1 ? 'ões' : ''}</p>
                    </div>

                    {/* Estrelas */}
                    <div className="flex gap-1">
                        {[1, 2, 3, 4, 5].map((i) => (
                            <Star
                                key={i}
                                size={24}
                                className={i <= Math.round(mediaNotas) ? 'fill-orange-500 text-orange-500' : 'text-zinc-700'}
                            />
                        ))}
                    </div>
                </div>

                {/* Distribuição */}
                <div className="mt-6 space-y-2">
                    {[5, 4, 3, 2, 1].map((estrela) => (
                        <div key={estrela} className="flex items-center gap-3">
                            <div className="flex gap-1 w-12">
                                {[...Array(estrela)].map((_, i) => (
                                    <Star key={i} size={12} className="fill-orange-500 text-orange-500" />
                                ))}
                            </div>
                            <div className="flex-1 h-2 bg-zinc-800 rounded-full overflow-hidden">
                                <div
                                    className="h-full bg-orange-500 transition-all"
                                    style={{ width: `${(distribuicao[estrela] / totalAvaliacoes) * 100}%` }}
                                />
                            </div>
                            <span className="text-zinc-500 text-xs w-8 text-right">{distribuicao[estrela]}</span>
                        </div>
                    ))}
                </div>
            </div>

            {/* Lista de Avaliações */}
            <div className="space-y-3">
                <h3 className="font-bold text-white">Avaliações Recentes</h3>
                {avaliacoes.slice(0, 5).map((avaliacao) => (
                    <div
                        key={avaliacao.id}
                        className="bg-zinc-900 border border-zinc-800 rounded-xl p-4 hover:border-zinc-700 transition-colors"
                    >
                        {/* Cabeçalho */}
                        <div className="flex items-start justify-between mb-2">
                            <div>
                                <p className="font-bold text-white text-sm">{avaliacao.avaliador_nome || 'Usuário'}</p>
                                <p className="text-zinc-500 text-xs">
                                    {new Date(avaliacao.criado_em).toLocaleDateString('pt-BR')}
                                </p>
                            </div>
                            <div className="flex gap-1">
                                {[1, 2, 3, 4, 5].map((i) => (
                                    <Star
                                        key={i}
                                        size={16}
                                        className={i <= avaliacao.nota ? 'fill-orange-500 text-orange-500' : 'text-zinc-700'}
                                    />
                                ))}
                            </div>
                        </div>

                        {/* Comentário */}
                        {avaliacao.comentario && (
                            <p className="text-zinc-300 text-sm leading-relaxed">{avaliacao.comentario}</p>
                        )}
                    </div>
                ))}
            </div>

            {/* Botão Ver Mais */}
            {avaliacoes.length > 5 && (
                <button className="w-full py-3 bg-zinc-800 hover:bg-zinc-700 text-white rounded-lg font-bold text-sm transition-colors">
                    Ver todas as {avaliacoes.length} avaliações
                </button>
            )}
        </div>
    );
}
