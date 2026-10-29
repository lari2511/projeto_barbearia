import React from 'react'
import { Calendar, Camera, Upload, X } from 'lucide-react'
import { Input } from './Common'
import { IDADE_MINIMA_FREELANCER, MAX_FOTOS_TRABALHOS, TEMPOS_PROFISSAO } from '../utils/cadastroFreelancer'

// "Há quanto tempo você trabalha como barbeiro(a)?" +"Adicione até 5 fotos dos seus trabalhos".
// fotos = [{ file, preview }]
// Data de nascimento (AAAA-MM-DD) só aparece quando onNascimentoChange é passado.
export default function CamposFreelancer({ tempo, onTempoChange, fotos, onFotosChange, onErro, mostrarFotos = true, nascimento, onNascimentoChange }) {
  const adicionar = (event) => {
    const files = Array.from(event.target.files || [])
    event.target.value = ''
    if (fotos.length + files.length > MAX_FOTOS_TRABALHOS) {
      onErro?.(`Máximo de ${MAX_FOTOS_TRABALHOS} fotos`)
      return
    }
    onFotosChange([...fotos, ...files.map((file) => ({ file, preview: URL.createObjectURL(file) }))])
  }

  return (
    <>
      {onNascimentoChange && (
        <div>
          <Input
            label="Data de nascimento"
            type="date"
            icon={Calendar}
            value={nascimento || ''}
            onChange={(event) => onNascimentoChange(event.target.value)}
            required
          />
          <p className="-mt-2 mb-3 text-[11px] text-zinc-500">Freelancers precisam ter {IDADE_MINIMA_FREELANCER} anos completos.</p>
        </div>
      )}

      <div className="mb-4">
        <p className="mb-2 block text-sm font-medium text-zinc-300">Há quanto tempo você trabalha como barbeiro(a)?</p>
        <div className="grid grid-cols-2 gap-2">
          {TEMPOS_PROFISSAO.map((opcao) => (
            <label
              key={opcao}
              className={`flex cursor-pointer items-center gap-2 rounded-xl border px-3 py-2 text-sm transition ${tempo === opcao ? 'border-orange-500 bg-orange-500/10 text-white' : 'border-zinc-700 bg-black/30 text-zinc-300'}`}
            >
              <input
                type="radio"
                name="tempo_profissao"
                value={opcao}
                checked={tempo === opcao}
                onChange={() => onTempoChange(opcao)}
                className="accent-orange-500"
              />
              {opcao}
            </label>
          ))}
        </div>
      </div>

      {mostrarFotos && (
        <div className="mb-2 rounded-2xl border border-zinc-800 bg-black/30 p-3 space-y-3">
          <div className="flex items-center gap-2">
            <Camera size={18} className="text-orange-400" />
            <h3 className="text-sm font-bold">Adicione até {MAX_FOTOS_TRABALHOS} fotos dos seus trabalhos</h3>
          </div>
          <div className="grid grid-cols-3 gap-2">
            {fotos.map((foto, index) => (
              <div key={foto.preview} className="relative aspect-square">
                <img src={foto.preview} alt={`Trabalho ${index + 1}`} className="w-full h-full object-cover rounded-lg" />
                <button
                  type="button"
                  onClick={() => onFotosChange(fotos.filter((_, i) => i !== index))}
                  className="absolute top-1 right-1 rounded-full bg-red-500 p-1 text-white hover:bg-red-600"
                >
                  <X size={14} />
                </button>
              </div>
            ))}
            {fotos.length < MAX_FOTOS_TRABALHOS && (
              <label className="aspect-square flex flex-col items-center justify-center rounded-lg border-2 border-dashed border-zinc-700 hover:border-orange-500 cursor-pointer transition">
                <Upload size={20} className="text-zinc-400 mb-1" />
                <span className="text-xs text-zinc-400">Adicionar</span>
                <input type="file" accept="image/*" multiple onChange={adicionar} className="hidden" />
              </label>
            )}
          </div>
          <p className="text-xs text-zinc-500 text-center">{fotos.length}/{MAX_FOTOS_TRABALHOS} fotos</p>
        </div>
      )}
    </>
  )
}
