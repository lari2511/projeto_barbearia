import React from 'react';
import { Image, Camera, Trash2, X } from 'lucide-react';

// Tab: Portfólio do Barbeiro
export function TabPortfolioBarbeiro({ 
  portfolioImages, 
  _setPortfolioImages,
  editing,
  handlePortfolioImageChange,
  removePortfolioImage,
  setImageModal
}) {
  return (
    <div className="space-y-3">
      <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
        <div className="flex items-center justify-between mb-3">
          <div>
            <h3 className="font-bold text-white flex items-center gap-2">
              <Image size={18} className="text-red-500" />
              Portfólio ({portfolioImages.length}/10)
            </h3>
            <p className="text-xs text-zinc-400 mt-1">⚠️ Mínimo 3 fotos obrigatório</p>
          </div>
          {editing && portfolioImages.length < 10 && (
            <label className="bg-red-500 text-white px-3 py-1.5 rounded-lg text-xs font-bold cursor-pointer hover:bg-red-600 active:scale-95">
              + Adicionar
              <input
                type="file"
                accept="image/*"
                multiple
                className="hidden"
                onChange={handlePortfolioImageChange}
              />
            </label>
          )}
        </div>
        
        {portfolioImages.length > 0 ? (
          <div className="grid grid-cols-3 gap-2">
            {portfolioImages.map((img, index) => (
              <div key={index} className="relative aspect-square rounded-lg overflow-hidden border border-zinc-700 group">
                <img 
                  src={img} 
                  alt={`Trabalho ${index + 1}`} 
                  className="w-full h-full object-cover cursor-pointer"
                  onClick={() => setImageModal(img)}
                />
                {editing && (
                  <button
                    onClick={() => removePortfolioImage(index)}
                    className="absolute top-1 right-1 bg-red-600 p-1.5 rounded-full opacity-0 group-hover:opacity-100 transition-opacity active:scale-95"
                  >
                    <Trash2 size={14} className="text-white" />
                  </button>
                )}
              </div>
            ))}
            {editing && portfolioImages.length < 10 && (
              <label className="aspect-square rounded-lg border-2 border-dashed border-zinc-700 flex items-center justify-center cursor-pointer hover:border-red-500 hover:bg-red-500/10 transition-colors">
                <div className="text-center">
                  <Camera size={24} className="text-zinc-600 mx-auto mb-1" />
                  <p className="text-[10px] text-zinc-500 font-bold">Adicionar</p>
                </div>
                <input
                  type="file"
                  accept="image/*"
                  multiple
                  className="hidden"
                  onChange={handlePortfolioImageChange}
                />
              </label>
            )}
          </div>
        ) : (
          <div className="text-center py-8 border-2 border-dashed border-zinc-800 rounded-lg">
            <Image size={32} className="text-zinc-700 mx-auto mb-2" />
            <p className="text-zinc-500 text-sm mb-1">Nenhuma foto ainda</p>
            <p className="text-zinc-600 text-xs">Adicione fotos dos seus trabalhos</p>
            {editing && (
              <label className="mt-3 inline-block bg-red-500 text-white px-4 py-2 rounded-lg text-xs font-bold cursor-pointer hover:bg-red-600 active:scale-95">
                + Adicionar Fotos
                <input
                  type="file"
                  accept="image/*"
                  multiple
                  className="hidden"
                  onChange={handlePortfolioImageChange}
                />
              </label>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

// Tab: Avaliações do Barbeiro
export function TabAvaliacoesBarbeiro({ 
  avaliacoes, 
  avaliacaoMedia, 
  avaliacoesLoading,
  hasMoreAvaliacoes = false,
  carregandoMais = false,
  onCarregarMais = null
}) {
  return (
    <div className="space-y-3">
      <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
        <div className="flex items-center justify-between mb-2">
          <h3 className="font-bold text-white">Avaliações</h3>
          {avaliacaoMedia && (
            <span className="text-xs text-zinc-400">
              Média: <span className="text-yellow-400 font-bold">{avaliacaoMedia.media}</span> ({avaliacaoMedia.total_avaliacoes || 0})
            </span>
          )}
        </div>
        {avaliacoesLoading ? (
          <p className="text-xs text-zinc-500">Carregando avaliações...</p>
        ) : avaliacoes.length === 0 ? (
          <div className="text-center py-8">
            <p className="text-zinc-500 text-sm">Sem avaliações ainda</p>
            <p className="text-zinc-600 text-xs mt-1">Complete agendamentos para receber avaliações</p>
          </div>
        ) : (
          <div className="space-y-2">
            {avaliacoes.map((av, idx) => {
              const nota = Math.max(0, Math.min(5, Number(av?.nota || 0)));
              const chave = av?.id ?? `${av?.criado_em || 'sem-data'}-${idx}`;
              return (
                <div key={chave} className="bg-black/30 border border-zinc-800/50 rounded-lg p-3 text-xs">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-yellow-400 text-base">{'★'.repeat(nota)}{'☆'.repeat(5 - nota)}</span>
                    <span className="text-zinc-500">
                      {av.criado_em ? new Date(av.criado_em).toLocaleDateString('pt-BR') : ''}
                    </span>
                  </div>
                  {av.comentario && (
                    <p className="text-zinc-300 mt-2">{av.comentario}</p>
                  )}
                  {av.avaliador_nome && (
                    <p className="text-zinc-500 text-[10px] mt-2">— {av.avaliador_nome}</p>
                  )}
                </div>
              );
            })}

            {hasMoreAvaliacoes && typeof onCarregarMais === 'function' && (
              <button
                onClick={onCarregarMais}
                disabled={carregandoMais}
                className="w-full bg-zinc-800 hover:bg-zinc-700 disabled:opacity-60 text-white px-4 py-2 rounded-lg text-xs font-bold active:scale-95"
              >
                {carregandoMais ? 'Carregando...' : 'Carregar mais avaliações'}
              </button>
            )}

            {!hasMoreAvaliacoes && avaliacoes.length > 0 && !avaliacoesLoading && (
              <p className="text-center text-[11px] text-zinc-500 py-1">
                Você chegou ao fim da lista de avaliações.
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
