import React, { useState } from 'react'
import { Building2, Camera, Hash, LogOut, MapPin, Phone, Store, Upload, User, X } from 'lucide-react'
import { Button, Input } from './Common'
import { isValidCNPJ, isValidCPF, maskCNPJ, maskCPF } from '../utils/documentValidation'

// Dados do perfil pedidos DEPOIS do cadastro rápido (e-mail + senha), já dentro do app.
// Cliente: nome e telefone (pode pular). Freelancer: dados + fotos + documento para
// a análise do ADM. Proprietário: dados da barbearia para aparecer na busca.

const temposExperiencia = [
  'Menos de 1 ano', '1 ano', '2 anos', '3 anos', '4 anos', '5 anos', '6 anos ou mais',
]

const TEXTOS = {
  cliente: {
    titulo: 'Complete seu perfil',
    subtitulo: 'Seu nome e telefone ajudam o profissional a te encontrar no atendimento.',
  },
  barbeiro: {
    titulo: 'Complete seu perfil profissional',
    subtitulo: 'Envie seus dados, fotos e documento. Depois disso seu perfil vai para análise do ADM.',
  },
  barbearia: {
    titulo: 'Complete os dados da barbearia',
    subtitulo: 'Com esses dados sua barbearia aparece na busca e você pode contratar cadeiras.',
  },
}

const formVazio = {
  nome: '',
  telefone: '',
  cpf: '',
  cnpj: '',
  tipoDocumento: '',
  nomeBarbearia: '',
  cep: '',
  endereco: '',
  tempoExperiencia: '',
}

export default function CompletarCadastro({ tipo, token, API_URL, notify, onConcluido, onSair, onPular }) {
  const [form, setForm] = useState(formVazio)
  const [portfolio, setPortfolio] = useState([])
  const [documento, setDocumento] = useState(null)
  const [fotosEnviadas, setFotosEnviadas] = useState(false)
  const [erro, setErro] = useState('')
  const [salvando, setSalvando] = useState(false)
  const [loadingCep, setLoadingCep] = useState(false)

  const textos = TEXTOS[tipo] || TEXTOS.cliente

  const handleChange = (campo) => (event) => {
    const value = event.target.value
    setForm((atual) => ({ ...atual, [campo]: value }))
  }

  const handleDocumentoChange = (campo) => (event) => {
    const value = campo === 'cpf' ? maskCPF(event.target.value) : maskCNPJ(event.target.value)
    setForm((atual) => ({ ...atual, [campo]: value }))
  }

  const handleTipoDocumentoChange = (tipoDoc) => {
    setForm((atual) => ({ ...atual, tipoDocumento: tipoDoc, cpf: '', cnpj: '' }))
  }

  const buscarCep = async () => {
    const cepLimpo = String(form.cep || '').replace(/\D/g, '')
    if (cepLimpo.length !== 8) {
      setErro('CEP deve ter 8 dígitos')
      return
    }
    setLoadingCep(true)
    setErro('')
    try {
      const response = await fetch(`https://viacep.com.br/ws/${cepLimpo}/json/`)
      const data = await response.json()
      const logradouro = String(data?.logradouro || '').trim()
      const bairro = String(data?.bairro || '').trim()
      const localidade = String(data?.localidade || '').trim()
      const uf = String(data?.uf || '').trim()
      if (!response.ok || data?.erro || !logradouro || !localidade || !uf) {
        setErro('CEP não encontrado')
        setForm((atual) => ({ ...atual, endereco: '' }))
        return
      }
      setForm((atual) => ({
        ...atual,
        endereco: `${logradouro}${bairro ? `, ${bairro}` : ''}, ${localidade}/${uf}`,
        cep: String(data.cep || cepLimpo).replace(/^(\d{5})(\d{3})$/, '$1-$2'),
      }))
    } catch (_err) {
      setErro('Erro ao buscar CEP')
    } finally {
      setLoadingCep(false)
    }
  }

  const adicionarPortfolio = (event) => {
    const files = Array.from(event.target.files || [])
    if (portfolio.length + files.length > 5) {
      setErro('Máximo de 5 fotos de portfólio')
      return
    }
    setPortfolio((atual) => [...atual, ...files.map((file) => ({ file, preview: URL.createObjectURL(file) }))])
  }

  const removerPortfolio = (index) => {
    setPortfolio((atual) => atual.filter((_, i) => i !== index))
  }

  const escolherDocumento = (event) => {
    const file = event.target.files?.[0]
    if (file) setDocumento({ file, preview: URL.createObjectURL(file) })
  }

  // Mesmos endpoints que o cadastro antigo e a tela de perfil usam.
  const enviarFotosFreelancer = async () => {
    const uploadArquivo = async (file, pasta) => {
      const formData = new FormData()
      formData.append('file', file)
      const res = await fetch(`${API_URL}/api/v1/upload/imagem?pasta=${encodeURIComponent(pasta)}`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
        body: formData,
      })
      if (!res.ok) throw new Error('Falha no upload da imagem')
      const data = await res.json()
      const url = String(data?.path || data?.url || '').trim()
      if (!url) throw new Error('Upload sem URL')
      return url
    }

    for (const foto of portfolio) {
      const url = await uploadArquivo(foto.file, 'portfolio')
      const res = await fetch(`${API_URL}/api/v1/barbeiro/portfolio`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ url_imagem: url, tipo_servico: 'corte', descricao: 'Portfólio inicial' }),
      })
      if (!res.ok) throw new Error('Falha ao salvar foto de portfólio')
    }

    const urlDoc = await uploadArquivo(documento.file, 'perfil')
    const res = await fetch(`${API_URL}/api/v1/documentos/upload`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({ rg: form.cpf.trim(), documento_frente_url: urlDoc }),
    })
    if (!res.ok) throw new Error('Falha ao salvar o documento')
  }

  const validar = () => {
    if (form.nome.trim().length < 3) return 'Informe seu nome completo'
    if (form.telefone.trim().length < 8) return 'Informe um telefone com DDD'

    if (tipo === 'barbeiro') {
      if (!isValidCPF(form.cpf)) return 'CPF inválido'
      if (!form.tempoExperiencia) return 'Informe quanto tempo de experiência você tem como barbeiro'
      if (!fotosEnviadas && portfolio.length < 3) return 'Envie no mínimo 3 fotos de portfólio'
      if (!fotosEnviadas && !documento) return 'Envie a foto do RG/CPF para validação'
    }

    if (tipo === 'barbearia') {
      if (form.nomeBarbearia.trim().length < 2) return 'Nome da barbearia é obrigatório'
      if (!form.endereco.trim()) return 'Busque o CEP para preencher o endereço'
      if (!form.tipoDocumento) return 'Selecione o tipo de documento: CPF ou CNPJ'
      if (form.tipoDocumento === 'cpf' && !isValidCPF(form.cpf)) return 'CPF inválido'
      if (form.tipoDocumento === 'cnpj' && !isValidCNPJ(form.cnpj)) return 'CNPJ inválido'
    }
    return ''
  }

  const payload = () => {
    const base = { nome: form.nome.trim(), telefone: form.telefone.trim() }
    if (tipo === 'barbeiro') {
      return { ...base, cpf: form.cpf.trim(), tempo_experiencia: form.tempoExperiencia }
    }
    if (tipo === 'barbearia') {
      return {
        ...base,
        nome_barbearia: form.nomeBarbearia.trim(),
        cep: form.cep.trim(),
        endereco: form.endereco.trim(),
        cpf: form.tipoDocumento === 'cpf' ? form.cpf.trim() : '',
        cnpj: form.tipoDocumento === 'cnpj' ? form.cnpj.trim() : '',
      }
    }
    return base
  }

  const handleSubmit = async (event) => {
    event.preventDefault()
    const erroValidacao = validar()
    if (erroValidacao) {
      setErro(erroValidacao)
      return
    }

    setSalvando(true)
    setErro('')
    try {
      // Fotos sobem uma vez só: se o envio dos dados falhar, tentar de novo não duplica.
      if (tipo === 'barbeiro' && !fotosEnviadas) {
        await enviarFotosFreelancer()
        setFotosEnviadas(true)
      }

      const res = await fetch(`${API_URL}/api/v1/cadastro/completar`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify(payload()),
      })
      const data = await res.json().catch(() => ({}))
      if (!res.ok) throw new Error(typeof data?.detail === 'string' ? data.detail : 'Não foi possível salvar')

      notify?.(tipo === 'barbeiro' ? 'Perfil enviado para análise do ADM' : 'Perfil completo!', 'success')
      onConcluido?.()
    } catch (err) {
      setErro(err?.message || 'Não foi possível salvar')
    } finally {
      setSalvando(false)
    }
  }

  return (
    <div className="bg-black text-white flex flex-col justify-start px-1 pt-2 pb-6">
      <div className="w-full min-w-0 rounded-2xl border border-zinc-800/50 bg-[#1e1e24] shadow-xl p-3">
        <div className="mb-4 flex items-start justify-between gap-2">
          <div>
            <h1 className="text-xl font-black">{textos.titulo}</h1>
            <p className="mt-1 text-xs text-zinc-400">{textos.subtitulo}</p>
          </div>
          {onSair && (
            <button type="button" onClick={onSair} className="flex items-center gap-1 text-xs text-zinc-400 hover:text-white">
              <LogOut size={14} />
              Sair
            </button>
          )}
        </div>

        <form onSubmit={handleSubmit} className="space-y-1">
          <Input label="Nome completo" icon={User} value={form.nome} onChange={handleChange('nome')} placeholder="Seu nome" required />

          {tipo === 'barbearia' && (
            <Input
              label="Nome da barbearia"
              icon={Store}
              value={form.nomeBarbearia}
              onChange={handleChange('nomeBarbearia')}
              placeholder="Ex: Barbearia Guilhermina"
              required
            />
          )}

          <Input label="Telefone" icon={Phone} value={form.telefone} onChange={handleChange('telefone')} placeholder="(11) 99999-9999" required />

          {tipo === 'barbeiro' && (
            <>
              <Input label="CPF" icon={Hash} value={form.cpf} onChange={handleDocumentoChange('cpf')} placeholder="000.000.000-00" required />
              <div className="mb-4">
                <label className="mb-1 block text-sm font-medium text-zinc-300">
                  Quanto tempo de experiência você tem como barbeiro?
                </label>
                <select
                  value={form.tempoExperiencia}
                  onChange={handleChange('tempoExperiencia')}
                  required
                  className="w-full rounded-xl border border-zinc-700 bg-black/30 px-3 py-3 text-sm text-white"
                >
                  <option value="">Selecione</option>
                  {temposExperiencia.map((opcao) => (
                    <option key={opcao} value={opcao}>{opcao}</option>
                  ))}
                </select>
              </div>
            </>
          )}

          {tipo === 'barbearia' && (
            <div className="space-y-1">
              <Input label="CEP" icon={MapPin} value={form.cep} onChange={handleChange('cep')} placeholder="00000-000" required />
              <button
                type="button"
                onClick={buscarCep}
                disabled={loadingCep}
                className="w-full rounded-xl border border-zinc-800 bg-black/30 px-3 py-2 text-left text-sm font-semibold text-zinc-200 hover:bg-zinc-800 disabled:opacity-50"
              >
                {loadingCep ? 'Buscando...' : '🔍 Buscar CEP'}
              </button>
              {form.endereco && (
                <p className="rounded-xl border border-zinc-800 bg-black/30 px-3 py-2 text-xs text-zinc-300">📍 {form.endereco}</p>
              )}

              <div className="mb-4 pt-2">
                <label className="mb-1 block text-sm font-medium text-zinc-300">Tipo de documento</label>
                <div className="grid grid-cols-2 gap-2">
                  {['cpf', 'cnpj'].map((tipoDoc) => (
                    <button
                      key={tipoDoc}
                      type="button"
                      onClick={() => handleTipoDocumentoChange(tipoDoc)}
                      className={`rounded-xl border px-3 py-3 text-sm font-bold transition ${form.tipoDocumento === tipoDoc ? 'border-orange-500 bg-orange-500/10 text-white' : 'border-zinc-700 bg-black/30 text-zinc-400'}`}
                    >
                      {tipoDoc.toUpperCase()}
                    </button>
                  ))}
                </div>
              </div>

              {form.tipoDocumento === 'cpf' && (
                <Input label="CPF" icon={Hash} value={form.cpf} onChange={handleDocumentoChange('cpf')} placeholder="Digite o CPF" required />
              )}
              {form.tipoDocumento === 'cnpj' && (
                <Input label="CNPJ" icon={Building2} value={form.cnpj} onChange={handleDocumentoChange('cnpj')} placeholder="Digite o CNPJ" required />
              )}
            </div>
          )}

          {tipo === 'barbeiro' && !fotosEnviadas && (
            <>
              <div className="rounded-2xl border border-zinc-800 bg-black/30 p-3 space-y-3">
                <div className="flex items-center gap-2">
                  <Camera size={18} className="text-orange-400" />
                  <h3 className="text-sm font-bold">Fotos de Portfólio</h3>
                  <span className="text-xs text-zinc-400">(3-5 fotos obrigatórias)</span>
                </div>
                <div className="grid grid-cols-3 gap-2">
                  {portfolio.map((foto, index) => (
                    <div key={foto.preview} className="relative aspect-square">
                      <img src={foto.preview} alt={`Portfolio ${index + 1}`} className="w-full h-full object-cover rounded-lg" />
                      <button
                        type="button"
                        onClick={() => removerPortfolio(index)}
                        className="absolute top-1 right-1 rounded-full bg-red-500 p-1 text-white hover:bg-red-600"
                      >
                        <X size={14} />
                      </button>
                    </div>
                  ))}
                  {portfolio.length < 5 && (
                    <label className="aspect-square flex flex-col items-center justify-center rounded-lg border-2 border-dashed border-zinc-700 hover:border-orange-500 cursor-pointer transition">
                      <Upload size={20} className="text-zinc-400 mb-1" />
                      <span className="text-xs text-zinc-400">Adicionar</span>
                      <input type="file" accept="image/*" multiple onChange={adicionarPortfolio} className="hidden" />
                    </label>
                  )}
                </div>
                <p className="text-xs text-zinc-500 text-center">{portfolio.length}/5 fotos</p>
              </div>

              <div className="rounded-2xl border border-zinc-800 bg-black/30 p-3 space-y-3">
                <div className="flex items-center gap-2">
                  <Camera size={18} className="text-orange-400" />
                  <h3 className="text-sm font-bold">Foto do RG/CPF</h3>
                  <span className="text-xs text-zinc-400">(obrigatório)</span>
                </div>
                {documento ? (
                  <div className="relative aspect-video">
                    <img src={documento.preview} alt="RG/CPF" className="w-full h-full object-cover rounded-lg" />
                    <button
                      type="button"
                      onClick={() => setDocumento(null)}
                      className="absolute top-2 right-2 rounded-full bg-red-500 p-2 text-white hover:bg-red-600"
                    >
                      <X size={16} />
                    </button>
                  </div>
                ) : (
                  <label className="aspect-video flex flex-col items-center justify-center rounded-lg border-2 border-dashed border-zinc-700 hover:border-orange-500 cursor-pointer transition">
                    <Upload size={24} className="text-zinc-400 mb-2" />
                    <span className="text-sm text-zinc-400">Enviar foto do RG/CPF</span>
                    <input type="file" accept="image/*" onChange={escolherDocumento} className="hidden" />
                  </label>
                )}
              </div>
            </>
          )}

          {tipo === 'barbeiro' && fotosEnviadas && (
            <p className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 px-3 py-2 text-xs text-emerald-200">
              ✓ Fotos e documento já enviados.
            </p>
          )}

          {erro && (
            <div className="rounded-xl border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-200">{erro}</div>
          )}

          <Button type="submit" fullWidth disabled={salvando} className="mt-2">
            {salvando ? 'Salvando...' : tipo === 'barbeiro' ? 'Enviar para análise' : 'Salvar'}
          </Button>

          {onPular && (
            <button type="button" onClick={onPular} className="w-full py-2 text-xs text-zinc-400 hover:text-white">
              Agora não
            </button>
          )}
        </form>
      </div>
    </div>
  )
}
