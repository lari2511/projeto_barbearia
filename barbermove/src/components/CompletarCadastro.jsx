import React, { useState } from 'react'
import { Building2, Hash, LogOut, MapPin, Phone, Store, User } from 'lucide-react'
import { Button, Input } from './Common'
import { isValidCNPJ, isValidCPF, maskCNPJ, maskCPF } from '../utils/documentValidation'
import CamposFreelancer from './CamposFreelancer'
import { enviarCadastroFreelancer } from '../utils/cadastroFreelancer'

// Dados do perfil pedidos DEPOIS do cadastro rápido (e-mail + senha), já dentro do app.
// Cliente: nome e telefone (pode pular). Freelancer: nome, tempo de profissão e fotos
// para a análise do ADM (normalmente já enviados na tela de cadastro).
// Proprietário: dados da barbearia para aparecer na busca.

const TEXTOS = {
  cliente: {
    titulo: 'Complete seu perfil',
    subtitulo: 'Seu nome e telefone ajudam o profissional a te encontrar no atendimento.',
  },
  barbeiro: {
    titulo: 'Complete seu perfil profissional',
    subtitulo: 'Informe seu nome, tempo de profissão e fotos dos trabalhos. Depois disso seu perfil fica em análise do ADM.',
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

  const validar = () => {
    if (form.nome.trim().length < 3) return 'Informe seu nome completo'

    if (tipo === 'barbeiro') {
      if (!form.tempoExperiencia) return 'Informe quanto tempo de profissão você tem'
      if (!fotosEnviadas && portfolio.length === 0) return 'Adicione pelo menos 1 foto dos seus trabalhos'
      return ''
    }

    if (form.telefone.trim().length < 8) return 'Informe um telefone com DDD'

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
      if (tipo === 'barbeiro') {
        // Fotos sobem uma vez só: se o envio dos dados falhar, tentar de novo não duplica.
        await enviarCadastroFreelancer({
          API_URL,
          token,
          nome: form.nome,
          tempoExperiencia: form.tempoExperiencia,
          fotos: portfolio.map((foto) => foto.file),
          fotosJaEnviadas: fotosEnviadas,
          onFotosEnviadas: () => setFotosEnviadas(true),
        })
        notify?.('Perfil enviado para análise do ADM', 'success')
        onConcluido?.()
        return
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

          {tipo !== 'barbeiro' && (
            <Input label="Telefone" icon={Phone} value={form.telefone} onChange={handleChange('telefone')} placeholder="(11) 99999-9999" required />
          )}

          {tipo === 'barbeiro' && (
            <CamposFreelancer
              tempo={form.tempoExperiencia}
              onTempoChange={(valor) => setForm((atual) => ({ ...atual, tempoExperiencia: valor }))}
              fotos={portfolio}
              onFotosChange={setPortfolio}
              onErro={setErro}
              mostrarFotos={!fotosEnviadas}
            />
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

          {tipo === 'barbeiro' && fotosEnviadas && (
            <p className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 px-3 py-2 text-xs text-emerald-200">
              ✓ Fotos dos trabalhos já enviadas.
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
