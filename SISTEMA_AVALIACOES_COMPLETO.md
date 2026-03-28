# 📊 SISTEMA DE AVALIAÇÕES - BARBERMOVIE

## 🎯 Visão Geral

Sistema completo de avaliações mútuas que permite:

- ⭐ **Cliente avaliar Barbeiro** - Nota (1-5), comentário, foto do resultado e tempo de serviço
- ⭐ **Barbeiro avaliar Cliente** - Nota (1-5) e comentário (pontualidade, educação)
- ⭐ **Cliente/Barbeiro avaliar Barbearia** - Nota (1-5) e comentário (ambiente, estrutura)

---

## 🗄️ Estrutura do Banco de Dados

### Tabela: `avaliacoes_freelancer`

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `id` | Integer | ID único |
| `freelancer_id` | Integer | FK - Freelancer sendo avaliado |
| `avaliador_id` | Integer | FK - Usuário que avaliou |
| `chamado_id` | Integer | FK - Atendimento associado |
| `nota` | Integer | 1-5 estrelas |
| `comentario` | String | Texto do comentário (opcional) |
| `foto_corte_url` | String | URL da foto do resultado (opcional) |
| `tempo_real_servico_min` | Integer | Tempo em minutos (opcional) |
| `tipo_avaliador` | String | "cliente" ou "barbearia" |
| `criado_em` | DateTime | Data/hora da avaliação |

### Tabela: `avaliacoes_barbearia`

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `id` | Integer | ID único |
| `barbearia_id` | Integer | FK - Barbearia sendo avaliada |
| `avaliador_id` | Integer | FK - Usuário que avaliou |
| `chamado_id` | Integer | FK - Atendimento associado |
| `nota` | Integer | 1-5 estrelas |
| `comentario` | String | Texto do comentário (opcional) |
| `tipo_avaliador` | String | "cliente" ou "freelancer" |
| `criado_em` | DateTime | Data/hora da avaliação |

---

## 📡 Endpoints da API

### 1️⃣ Avaliar Freelancer (Cliente avalia Barbeiro)

```http
POST /api/v1/avaliacoes/freelancer/{freelancer_id}
```

**Headers:**
```json
{
  "Authorization": "Bearer seu_token_jwt"
}
```

**Body:**
```json
{
  "chamado_id": 123,
  "nota": 5,
  "comentario": "Excelente corte, muito caprichado!",
  "foto_corte_url": "https://s3.amazonaws.com/barbermovie/cortes/abc123.jpg",
  "tempo_real_servico_min": 45
}
```

**Resposta (201 Created):**
```json
{
  "message": "Avaliação enviada com sucesso!",
  "avaliacao_id": 456,
  "nova_media": 4.8
}
```

**Validações:**
- ✅ Chamado deve estar com status "concluido"
- ✅ Usuário logado deve ser o cliente do chamado
- ✅ Nota deve estar entre 1 e 5
- ✅ Não pode avaliar duas vezes o mesmo serviço

---

### 2️⃣ Avaliar Barbearia

```http
POST /api/v1/avaliacoes/barbearia/{barbearia_id}
```

**Headers:**
```json
{
  "Authorization": "Bearer seu_token_jwt"
}
```

**Body:**
```json
{
  "chamado_id": 123,
  "nota": 4,
  "comentario": "Ambiente limpo e aconchegante, excelente atendimento!"
}
```

**Resposta (201 Created):**
```json
{
  "message": "Avaliação enviada com sucesso!",
  "avaliacao_id": 457,
  "nova_media": 4.6
}
```

---

### 3️⃣ Listar Avaliações de um Freelancer

```http
GET /api/v1/avaliacoes/freelancer/{freelancer_id}/recebidas?limite=10
```

**Resposta (200 OK):**
```json
[
  {
    "id": 456,
    "nota": 5,
    "comentario": "Excelente corte, muito caprichado!",
    "tipo_avaliador": "cliente",
    "foto_corte_url": "https://s3.amazonaws.com/barbermovie/cortes/abc123.jpg",
    "tempo_real_servico_min": 45,
    "criado_em": "2026-01-11T14:30:00",
    "avaliador_nome": "João Silva",
    "avaliador_foto": "https://s3.amazonaws.com/perfis/joao.jpg"
  }
]
```

---

### 4️⃣ Listar Avaliações de uma Barbearia

```http
GET /api/v1/avaliacoes/barbearia/{barbearia_id}/recebidas?limite=10
```

**Resposta (200 OK):**
```json
[
  {
    "id": 457,
    "nota": 4,
    "comentario": "Ambiente limpo e aconchegante!",
    "tipo_avaliador": "cliente",
    "criado_em": "2026-01-11T14:35:00",
    "avaliador_nome": "Maria Santos",
    "avaliador_foto": "https://s3.amazonaws.com/perfis/maria.jpg"
  }
]
```

---

### 5️⃣ Minhas Avaliações Recebidas (Perfil Autenticado)

```http
GET /api/v1/avaliacoes/minhas-avaliacoes-recebidas
```

**Headers:**
```json
{
  "Authorization": "Bearer seu_token_jwt"
}
```

**Resposta (200 OK):**
```json
{
  "como_freelancer": [
    {
      "id": 456,
      "nota": 5,
      "comentario": "Excelente corte!",
      "tipo_avaliador": "cliente",
      "foto_corte_url": "https://s3.amazonaws.com/...",
      "tempo_real_servico_min": 45,
      "criado_em": "2026-01-11T14:30:00",
      "avaliador_nome": "João Silva",
      "avaliador_foto": "https://..."
    }
  ],
  "como_barbearia": [
    {
      "id": 457,
      "nota": 4,
      "comentario": "Ambiente limpo!",
      "tipo_avaliador": "cliente",
      "criado_em": "2026-01-11T14:35:00",
      "avaliador_nome": "Maria Santos",
      "avaliador_foto": "https://..."
    }
  ],
  "media_freelancer": 4.8,
  "media_barbearia": 4.6
}
```

---

## 🎨 Fluxo no Frontend (React)

### 1. Depois que um Agendamento é Concluído

```jsx
// Quando status muda para 'concluido', abrir modal de avaliação
if (agendamento.status === 'concluido' && !agendamentoJaAvaliado) {
  <ModalAvaliacaoBarbeiro 
    freelancerId={agendamento.freelancer_id}
    chamadoId={agendamento.id}
  />
}
```

### 2. Componente de Avaliação (ModalAvaliacaoBarbeiro.jsx)

```jsx
import React, { useState } from 'react';
import axios from 'axios';

export default function ModalAvaliacaoBarbeiro({ freelancerId, chamadoId, onSuccess }) {
  const [nota, setNota] = useState(0);
  const [comentario, setComentario] = useState('');
  const [fotoCorteUrl, setFotoCorteUrl] = useState(null);
  const [tempoServico, setTempoServico] = useState(null);
  const [loading, setLoading] = useState(false);
  const [sucesso, setSucesso] = useState(false);

  const handleEnviarAvaliacao = async () => {
    if (nota === 0) {
      alert('Por favor, selecione uma nota');
      return;
    }

    setLoading(true);
    try {
      const response = await axios.post(
        `${process.env.REACT_APP_API_URL}/api/v1/avaliacoes/freelancer/${freelancerId}`,
        {
          chamado_id: chamadoId,
          nota: nota,
          comentario: comentario,
          foto_corte_url: fotoCorteUrl,
          tempo_real_servico_min: tempoServico
        },
        {
          headers: {
            Authorization: `Bearer ${localStorage.getItem('access_token')}`
          }
        }
      );

      setSucesso(true);
      if (onSuccess) onSuccess(response.data);
    } catch (error) {
      console.error('Erro ao avaliar:', error);
      alert('Erro ao enviar avaliação');
    } finally {
      setLoading(false);
    }
  };

  if (sucesso) {
    return (
      <div className="modal-success">
        <h2>✅ Avaliação Enviada!</h2>
        <p>Obrigado por avaliar nosso barbeiro!</p>
      </div>
    );
  }

  return (
    <div className="modal-avaliacao">
      <h2>Como foi seu corte?</h2>

      {/* Estrelas */}
      <div className="estrelas">
        {[1, 2, 3, 4, 5].map((i) => (
          <button
            key={i}
            onClick={() => setNota(i)}
            className={nota >= i ? 'ativo' : ''}
          >
            ⭐
          </button>
        ))}
      </div>

      {/* Comentário */}
      <textarea
        placeholder="Deixe um comentário sobre o atendimento..."
        value={comentario}
        onChange={(e) => setComentario(e.target.value)}
      />

      {/* Upload de Foto */}
      <input
        type="file"
        accept="image/*"
        onChange={(e) => {
          // Aqui você faria upload para S3/Firebase
          // e setaria a URL em fotoCorteUrl
        }}
      />

      {/* Tempo de Serviço (opcional) */}
      <input
        type="number"
        placeholder="Quanto tempo levou? (minutos)"
        value={tempoServico}
        onChange={(e) => setTempoServico(parseInt(e.target.value))}
      />

      <button onClick={handleEnviarAvaliacao} disabled={loading}>
        {loading ? 'Enviando...' : 'Enviar Avaliação'}
      </button>
    </div>
  );
}
```

### 3. Exibir Avaliações no Perfil do Barbeiro

```jsx
import React, { useState, useEffect } from 'react';
import axios from 'axios';

export default function PerfilBarbeiro({ freelancerId }) {
  const [avaliacoes, setAvaliacoes] = useState([]);
  const [media, setMedia] = useState(0);

  useEffect(() => {
    carregarAvaliacoes();
  }, [freelancerId]);

  const carregarAvaliacoes = async () => {
    try {
      const response = await axios.get(
        `${process.env.REACT_APP_API_URL}/api/v1/avaliacoes/freelancer/${freelancerId}/recebidas`
      );
      
      setAvaliacoes(response.data);
      
      // Calcular média
      const soma = response.data.reduce((acc, av) => acc + av.nota, 0);
      setMedia(soma / response.data.length);
    } catch (error) {
      console.error('Erro ao carregar avaliações:', error);
    }
  };

  return (
    <div className="perfil-barbeiro">
      <h1>João Barbeiro</h1>
      
      {/* Média de Avaliações */}
      <div className="media-avaliacoes">
        <span className="estrelas">⭐ {media.toFixed(1)}</span>
        <span className="total">({avaliacoes.length} avaliações)</span>
      </div>

      {/* Lista de Avaliações */}
      <div className="avaliacoes-lista">
        {avaliacoes.map((av) => (
          <div key={av.id} className="avaliacao-card">
            <div className="header">
              <img src={av.avaliador_foto} alt={av.avaliador_nome} />
              <div>
                <h4>{av.avaliador_nome}</h4>
                <span className="estrelas">{'⭐'.repeat(av.nota)}</span>
              </div>
            </div>

            <p>{av.comentario}</p>

            {/* Exibir foto do corte */}
            {av.foto_corte_url && (
              <img src={av.foto_corte_url} alt="Resultado do corte" className="foto-corte" />
            )}

            {/* Exibir tempo */}
            {av.tempo_real_servico_min && (
              <p className="tempo">⏱️ {av.tempo_real_servico_min} minutos</p>
            )}

            <small>{new Date(av.criado_em).toLocaleDateString('pt-BR')}</small>
          </div>
        ))}
      </div>
    </div>
  );
}
```

---

## 🔧 Dicas de Implementação

### Upload de Foto (Firebase/AWS S3)

Antes de chamar o endpoint de avaliação, faça upload da foto:

```jsx
const handleUploadFoto = async (file) => {
  // Exemplo com Firebase Storage
  const storage = getStorage();
  const storageRef = ref(storage, `avaliacoes/${Date.now()}_${file.name}`);
  
  const snapshot = await uploadBytes(storageRef, file);
  const url = await getDownloadURL(snapshot.ref);
  
  setFotoCorteUrl(url); // Salva para enviar na avaliação
};
```

### Cálculo de Média

A API já retorna a `nova_media` ao criar avaliação. Para listar:

```javascript
// Backend calcula automaticamente
const media = avaliacoes.reduce((acc, av) => acc + av.nota, 0) / avaliacoes.length;
```

---

## 🚀 Próximos Passos

1. ✅ **Implementar upload de fotos** - S3 ou Firebase
2. ✅ **Adicionar filtros** - Ordenar por nota, data recente
3. ✅ **Notificações** - Avisar quando receber avaliação
4. ✅ **Responder avaliações** - Permitir que barbeiro responda comentários
5. ✅ **Dashboard de Métricas** - Gráficos de satisfação

---

## 📝 Resumo das Mudanças

| Arquivo | Alteração |
|---------|-----------|
| `app/models.py` | Adicionado `foto_corte_url` e `tempo_real_servico_min` em `AvaliacaoFreelancer` |
| `app/schemas.py` | Atualizado `AvaliacaoCreate` e `AvaliacaoFreelancerResponse` com novos campos |
| `app/routes_avaliacoes.py` | Rotas agora retornam foto e tempo nas avaliações |

✅ **Sistema pronto para usar!**
