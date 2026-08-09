import React, { useMemo, useState } from 'react'
import { ArrowLeft, Building2, Hash, Mail, MapPin, Phone, Scissors, Store, User, Lock, Camera, Upload, X } from 'lucide-react'
import { useApp } from '../contexts/AppContext'
import { Button, Input } from './Common'

const userTypes = [
  {
    type: 'cliente',
    label: 'Cliente',
    description: 'Compra serviços e acompanha agendamentos',
    icon: User,
    accent: 'from-sky-600 to-sky-700',
  },
  {
    type: 'barbeiro',
    label: 'Freelancer',
    description: 'Profissional autônomo com CPF e endereço',
    icon: Scissors,
    accent: 'from-emerald-600 to-emerald-700',
  },
  {
    type: 'barbearia',
    label: 'Barbearia',
    description: 'Negócio físico com endereço obrigatório',
    icon: Store,
    accent: 'from-orange-600 to-orange-700',
  },
]

const emptyForm = {
  nome: '',
  email: '',
  senha: '',
  telefone: '',
  cpf: '',
  endereco: '',
  cep: '',
  cnpj: '',
}

const emptyPhotos = {
  portfolio: [],
  rgCpf: null
}

function buildPayload(tipo, form) {
  const base = {
    nome: form.nome.trim(),
    email: form.email.trim().toLowerCase(),
    senha: form.senha,
    telefone: form.telefone.trim(),
  }

  if (tipo === 'cliente') {
    return {
      ...base,
      cpf: form.cpf.trim(),
    }
  }

  if (tipo === 'barbeiro') {
    return {
      ...base,
      cpf: form.cpf.trim(),
      endereco: form.endereco.trim(),
    }
  }

  return {
    ...base,
    endereco: form.endereco.trim(),
    cep: form.cep.trim(),
    cpf: form.cpf.trim(),
    cnpj: form.cnpj.trim(),
  }
}

export default function Cadastro({ initialType = 'cliente', onBack, onSuccess }) {
  const { register, loading, notify, API_URL } = useApp()
  const [selectedType, setSelectedType] = useState(initialType || 'cliente')
  const [form, setForm] = useState(emptyForm)
  const [photos, setPhotos] = useState(emptyPhotos)
  const [localError, setLocalError] = useState('')
  const [loadingCep, setLoadingCep] = useState(false)

  const selectedConfig = useMemo(
    () => userTypes.find((item) => item.type === selectedType) || userTypes[0],
    [selectedType]
  )

  const handleChange = (field) => (event) => {
    const value = event.target.value
    setForm((current) => ({ ...current, [field]: value }))
  }

  // Buscar endereço por CEP
  const buscarCep = async () => {
    const cepLimpo = String(form.cep || '').replace(/\D/g, '')
    if (cepLimpo.length !== 8) {
      setLocalError('CEP deve ter 8 dígitos')
      setForm((current) => ({ ...current, endereco: '' }))
      return
    }

    setLoadingCep(true)
    setLocalError('')
    try {
      const response = await fetch(`https://viacep.com.br/ws/${cepLimpo}/json/`)
      const data = await response.json()

      if (!response.ok || data.erro) {
        setLocalError('CEP não encontrado')
        setForm((current) => ({ ...current, endereco: '' }))
        return
      }

      const logradouro = String(data.logradouro || '').trim()
      const bairro = String(data.bairro || '').trim()
      const localidade = String(data.localidade || '').trim()
      const uf = String(data.uf || '').trim()
      if (!logradouro || !localidade || !uf) {
        setLocalError('CEP não encontrado')
        setForm((current) => ({ ...current, endereco: '' }))
        return
      }

      const enderecoCompleto = `${logradouro}${bairro ? `, ${bairro}` : ''}, ${localidade}/${uf}`
      const cepFormatado = String(data.cep || cepLimpo).replace(/^(\d{5})(\d{3})$/, '$1-$2')

      setForm((current) => ({
        ...current,
        endereco: enderecoCompleto,
        cep: cepFormatado
      }))
    } catch (error) {
      setLocalError('Erro ao buscar CEP')
      setForm((current) => ({ ...current, endereco: '' }))
    } finally {
      setLoadingCep(false)
    }
  }

  // Upload de foto de portfólio
  const handlePortfolioPhoto = (event) => {
    const files = Array.from(event.target.files)
    if (photos.portfolio.length + files.length > 5) {
      setLocalError('Máximo de 5 fotos de portfólio')
      return
    }
    
    const newPhotos = files.map(file => ({
      file,
      preview: URL.createObjectURL(file)
    }))
    
    setPhotos((current) => ({
      ...current,
      portfolio: [...current.portfolio, ...newPhotos]
    }))
  }

  // Remover foto de portfólio
  const removePortfolioPhoto = (index) => {
    setPhotos((current) => ({
      ...current,
      portfolio: current.portfolio.filter((_, i) => i !== index)
    }))
  }

  // Upload de foto de RG/CPF
  const handleRgCpfPhoto = (event) => {
    const file = event.target.files[0]
    if (file) {
      setPhotos((current) => ({
        ...current,
        rgCpf: {
          file,
          preview: URL.createObjectURL(file)
        }
      }))
    }
  }

  // Remover foto de RG/CPF
  const removeRgCpfPhoto = () => {
    setPhotos((current) => ({
      ...current,
      rgCpf: null
    }))
  }

  // Envia ao servidor as fotos de portfólio + documento coletadas no cadastro do freelancer.
  // Roda depois que a conta já existe, usando o token recém-emitido, e reaproveita os mesmos
  // endpoints que a tela de perfil usa (upload multipart -> registrar no barbeiro).
  const enviarFotosFreelancer = async (token) => {
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

    let falhas = 0

    for (const foto of photos.portfolio) {
      try {
        const url = await uploadArquivo(foto.file, 'portfolio')
        const res = await fetch(`${API_URL}/api/v1/barbeiro/portfolio`, {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ url_imagem: url, tipo_servico: 'corte', descricao: 'Portfólio inicial' }),
        })
        if (!res.ok) falhas += 1
      } catch (_err) {
        falhas += 1
      }
    }

    if (photos.rgCpf?.file) {
      try {
        const url = await uploadArquivo(photos.rgCpf.file, 'perfil')
        const res = await fetch(`${API_URL}/api/v1/documentos/upload`, {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ rg: form.cpf.trim(), documento_frente_url: url }),
        })
        if (!res.ok) falhas += 1
      } catch (_err) {
        falhas += 1
      }
    }

    return falhas
  }

  const handleSubmit = async (event) => {
    event.preventDefault()
    setLocalError('')

    if (!selectedType) {
      setLocalError('Selecione um tipo de cadastro')
      return
    }

    if (!form.nome.trim() || !form.email.trim() || !form.senha || !form.cpf.trim() || !form.telefone.trim()) {
      setLocalError('Preencha todos os campos obrigatórios')
      return
    }

    if ((selectedType === 'barbeiro' || selectedType === 'barbearia') && !form.endereco.trim()) {
      setLocalError('Endereço é obrigatório')
      return
    }

    if (selectedType === 'barbearia' && (!form.cep.trim() || !form.cnpj.trim())) {
      setLocalError('CEP e CNPJ são obrigatórios para barbearia')
      return
    }

    if (selectedType === 'barbeiro') {
      if (photos.portfolio.length < 3) {
        setLocalError('Barbeiro deve ter no mínimo 3 fotos de portfólio')
        return
      }
      if (!photos.rgCpf) {
        setLocalError('Barbeiro deve enviar foto do RG/CPF para validação')
        return
      }
    }

    const payload = buildPayload(selectedType, form)
    const result = await register(selectedType, payload)

    if (result && selectedType === 'barbeiro' && result.access_token) {
      const falhas = await enviarFotosFreelancer(result.access_token)
      if (falhas > 0) {
        notify('Conta criada, mas algumas fotos não foram enviadas. Você pode reenviá-las depois em Meu Perfil.', 'error')
      }
    }

    if (result && onSuccess) {
      onSuccess(result)
    }
  }

  return (
    <div className="bg-black text-white flex flex-col justify-start px-1 pt-2 pb-6">
      <div className="w-full min-w-0 rounded-2xl border border-zinc-800/50 bg-[#1e1e24] shadow-xl p-3">
        <button
          type="button"
          onClick={onBack}
          className="mb-3 flex items-center gap-2 text-sm text-zinc-400 hover:text-white"
        >
          <ArrowLeft size={16} />
          Voltar
        </button>

        <div className="mb-4 text-center">
          <div className={`mx-auto mb-3 flex h-16 w-16 items-center justify-center rounded-3xl bg-gradient-to-br ${selectedConfig.accent} shadow-[0_14px_32px_rgba(0,0,0,0.35)]`}>
            <selectedConfig.icon size={28} className="text-white" />
          </div>
          <h1 className="text-xl font-black">Criar conta</h1>
          <p className="mt-1 text-xs text-zinc-400">Escolha o perfil e preencha os dados do backend.</p>
        </div>

        <div className="grid grid-cols-3 gap-2 mb-3">
          {userTypes.map((item) => {
            const Icon = item.icon
            const active = selectedType === item.type
            return (
              <button
                key={item.type}
                type="button"
                onClick={() => setSelectedType(item.type)}
                className={`rounded-2xl border p-2 text-left transition ${active ? 'border-orange-500 bg-orange-500/10' : 'border-zinc-800 bg-black/30'}`}
              >
                <Icon size={18} className={`mb-2 ${active ? 'text-orange-400' : 'text-zinc-400'}`} />
                <div className="text-xs font-black leading-tight">{item.label}</div>
              </button>
            )
          })}
        </div>

        {localError && (
          <div className="mb-3 rounded-xl border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-200">
            {localError}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-1">
          <Input
            label="Nome completo"
            icon={User}
            value={form.nome}
            onChange={handleChange('nome')}
            placeholder="Seu nome"
            required
          />

          <Input
            label="Email"
            type="email"
            icon={Mail}
            value={form.email}
            onChange={handleChange('email')}
            placeholder="voce@email.com"
            required
          />

          <Input
            label="Senha"
            type="password"
            icon={Lock}
            value={form.senha}
            onChange={handleChange('senha')}
            placeholder="••••••"
            required
          />

          <Input
            label="Telefone"
            icon={Phone}
            value={form.telefone}
            onChange={handleChange('telefone')}
            placeholder="(11) 99999-9999"
          />

          <Input
            label="CPF"
            icon={Hash}
            value={form.cpf}
            onChange={handleChange('cpf')}
            placeholder="000.000.000-00"
            required
          />

          {(selectedType === 'barbeiro' || selectedType === 'barbearia') && (
            <>
              <Input
                label="Endereço"
                icon={MapPin}
                value={form.endereco}
                onChange={handleChange('endereco')}
                placeholder="Rua, número, bairro"
                required
              />

              {selectedType === 'barbearia' && (
                <div className="grid grid-cols-2 gap-2">
                  <div className="space-y-1">
                    <Input
                      label="CEP"
                      value={form.cep}
                      onChange={handleChange('cep')}
                      placeholder="00000-000"
                      required
                    />
                    <button
                      type="button"
                      onClick={buscarCep}
                      disabled={loadingCep}
                      className="w-full rounded-xl border border-zinc-800 bg-black/30 px-3 py-2 text-left text-sm font-semibold text-zinc-200 hover:bg-zinc-800 disabled:opacity-50"
                    >
                      {loadingCep ? 'Buscando...' : '🔍 Buscar CEP'}
                    </button>
                  </div>
                  <Input
                    label="CNPJ"
                    icon={Building2}
                    value={form.cnpj}
                    onChange={handleChange('cnpj')}
                    placeholder="00.000.000/0000-00"
                    required
                  />
                </div>
              )}
            </>
          )}

          {selectedType === 'barbeiro' && (
            <>
              <div className="rounded-2xl border border-zinc-800 bg-black/30 p-3 space-y-3">
                <div className="flex items-center gap-2">
                  <Camera size={18} className="text-orange-400" />
                  <h3 className="text-sm font-bold">Fotos de Portfólio</h3>
                  <span className="text-xs text-zinc-400">(3-5 fotos obrigatórias)</span>
                </div>
                
                <div className="grid grid-cols-3 gap-2">
                  {photos.portfolio.map((photo, index) => (
                    <div key={index} className="relative aspect-square">
                      <img
                        src={photo.preview}
                        alt={`Portfolio ${index + 1}`}
                        className="w-full h-full object-cover rounded-lg"
                      />
                      <button
                        type="button"
                        onClick={() => removePortfolioPhoto(index)}
                        className="absolute top-1 right-1 rounded-full bg-red-500 p-1 text-white hover:bg-red-600"
                      >
                        <X size={14} />
                      </button>
                    </div>
                  ))}
                  {photos.portfolio.length < 5 && (
                    <label className="aspect-square flex flex-col items-center justify-center rounded-lg border-2 border-dashed border-zinc-700 hover:border-orange-500 cursor-pointer transition">
                      <Upload size={20} className="text-zinc-400 mb-1" />
                      <span className="text-xs text-zinc-400">Adicionar</span>
                      <input
                        type="file"
                        accept="image/*"
                        multiple
                        onChange={handlePortfolioPhoto}
                        className="hidden"
                      />
                    </label>
                  )}
                </div>
                <p className="text-xs text-zinc-500 text-center">
                  {photos.portfolio.length}/5 fotos
                </p>
              </div>

              <div className="rounded-2xl border border-zinc-800 bg-black/30 p-3 space-y-3">
                <div className="flex items-center gap-2">
                  <Camera size={18} className="text-orange-400" />
                  <h3 className="text-sm font-bold">Foto do RG/CPF</h3>
                  <span className="text-xs text-zinc-400">(obrigatório)</span>
                </div>
                
                {photos.rgCpf ? (
                  <div className="relative aspect-video">
                    <img
                      src={photos.rgCpf.preview}
                      alt="RG/CPF"
                      className="w-full h-full object-cover rounded-lg"
                    />
                    <button
                      type="button"
                      onClick={removeRgCpfPhoto}
                      className="absolute top-2 right-2 rounded-full bg-red-500 p-2 text-white hover:bg-red-600"
                    >
                      <X size={16} />
                    </button>
                  </div>
                ) : (
                  <label className="aspect-video flex flex-col items-center justify-center rounded-lg border-2 border-dashed border-zinc-700 hover:border-orange-500 cursor-pointer transition">
                    <Upload size={24} className="text-zinc-400 mb-2" />
                    <span className="text-sm text-zinc-400">Enviar foto do RG/CPF</span>
                    <input
                      type="file"
                      accept="image/*"
                      onChange={handleRgCpfPhoto}
                      className="hidden"
                    />
                  </label>
                )}
              </div>
            </>
          )}

          <div className="rounded-2xl border border-zinc-800 bg-black/30 p-3 text-xs text-zinc-400">
            {selectedType === 'cliente' && 'Clientes são aprovados automaticamente e recebem token logo após o cadastro.'}
            {selectedType === 'barbeiro' && 'Freelancers recebem token e seguem o fluxo de verificação de email.'}
            {selectedType === 'barbearia' && 'Barbearias são vinculadas ao cadastro da empresa e podem entrar no painel após o registro.'}
          </div>

          <Button type="submit" fullWidth disabled={loading} className="mt-2">
            {loading ? 'Criando conta...' : 'Criar conta'}
          </Button>
        </form>
      </div>
    </div>
  )
}
