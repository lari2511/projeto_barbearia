// Dados do cadastro do freelancer: nome, tempo de profissão e fotos dos trabalhos.
// Usado na tela de cadastro e, se algo falhar lá, na tela de completar perfil.

export const TEMPOS_PROFISSAO = ['Menos de 1 ano', '1 ano', '2 anos', '3 anos', '4 anos', '5 anos ou mais']
export const MAX_FOTOS_TRABALHOS = 5
export const IDADE_MINIMA_FREELANCER = 18

// Idade completa na data de hoje a partir de "AAAA-MM-DD" (input type=date). null se inválida.
export const idadeCompleta = (dataIso) => {
  const [ano, mes, dia] = String(dataIso || '').split('-').map(Number)
  if (!ano || !mes || !dia) return null
  const hoje = new Date()
  let idade = hoje.getFullYear() - ano
  if (hoje.getMonth() + 1 < mes || (hoje.getMonth() + 1 === mes && hoje.getDate() < dia)) idade -= 1
  return idade
}

// Mensagem de erro da data de nascimento do freelancer ('' = ok). O servidor confere de novo.
export const erroDataNascimentoFreelancer = (dataIso) => {
  const idade = idadeCompleta(dataIso)
  if (idade === null) return 'Informe sua data de nascimento'
  if (idade < 0 || idade > 120) return 'Data de nascimento inválida'
  if (idade < IDADE_MINIMA_FREELANCER) return 'É preciso ter 18 anos completos para se cadastrar como freelancer.'
  return ''
}

const uploadImagem = async (API_URL, token, file, pasta) => {
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

// Sobe as fotos (vinculadas ao perfil do freelancer) e conclui o cadastro -> fica EM ANÁLISE.
// `fotosJaEnviadas`/`onFotosEnviadas` evitam duplicar fotos numa nova tentativa.
export async function enviarCadastroFreelancer({ API_URL, token, nome, tempoExperiencia, dataNascimento, fotos, fotosJaEnviadas = false, onFotosEnviadas }) {
  if (!fotosJaEnviadas) {
    for (const file of fotos) {
      const url = await uploadImagem(API_URL, token, file, 'portfolio')
      const res = await fetch(`${API_URL}/api/v1/barbeiro/portfolio`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ url_imagem: url, tipo_servico: 'corte', descricao: 'Portfólio inicial' }),
      })
      if (!res.ok) throw new Error('Falha ao salvar foto dos trabalhos')
    }
    onFotosEnviadas?.()
  }

  const res = await fetch(`${API_URL}/api/v1/cadastro/completar`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
    body: JSON.stringify({ nome: nome.trim(), tempo_experiencia: tempoExperiencia, data_nascimento: dataNascimento || undefined }),
  })
  const data = await res.json().catch(() => ({}))
  if (!res.ok) throw new Error(typeof data?.detail === 'string' ? data.detail : 'Não foi possível salvar')
  return data
}
