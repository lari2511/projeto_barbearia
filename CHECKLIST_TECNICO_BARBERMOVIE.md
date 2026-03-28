# 📋 CHECKLIST TÉCNICO – BARBERMOVIE

## 🎯 ARQUITETURA GERAL

### Backend (API)
- [ ] Autenticação JWT com 3 tipos de usuário (barbearia, freelancer, cliente)
- [ ] Sistema de assinaturas/mensalidades (R$49,90/mês para barbearia)
- [ ] Cálculo automático de comissões (4% para freelancers após 1º mês)
- [ ] Geolocalização (barbearias e freelancers próximos)
- [ ] Upload e armazenamento de imagens (portfólio)
- [ ] Sistema de avaliações mútuas (3 vias)
- [ ] Notificações em tempo real (aceite/recusa de atendimentos)
- [ ] Rastreamento de origem do cliente (BarberMovie vs próprio)

### Frontend (App)
- [ ] PWA com suporte offline
- [ ] Autenticação e gestão de sessão
- [ ] Interface responsiva (mobile-first)
- [ ] Upload de imagens otimizado
- [ ] Integração de mapas (Google Maps / Leaflet)
- [ ] Sistema de notificações push
- [ ] Chat ou mensagens (opcional)

---

## 🏪 NICHO: DONO DA BARBEARIA

### Backend
- [ ] **Modelo de dados**
  - [ ] Tabela `barbearias` (nome, endereço, telefone, lat/lng, status_online)
  - [ ] Tabela `cadeiras` (barbearia_id, numero, status: disponível/bloqueada)
  - [ ] Relacionamento com tabela `usuarios` (tipo: barbearia)
  - [ ] Campo `assinatura_ativa` e `data_vencimento`
  
- [ ] **Endpoints**
  - [ ] `POST /api/barbearia/cadastro` – Cadastro inicial + trial
  - [ ] `GET /api/barbearia/minha` – Dados da barbearia logada
  - [ ] `PATCH /api/barbearia/status` – Alterar online/offline
  - [ ] `GET /api/barbearia/cadeiras` – Listar cadeiras
  - [ ] `POST /api/barbearia/cadeiras` – Adicionar cadeira
  - [ ] `PATCH /api/barbearia/cadeiras/:id/status` – Bloquear/desbloquear
  - [ ] `GET /api/barbearia/freelancers-proximos` – Listar freelancers disponíveis (raio geográfico)
  - [ ] `GET /api/barbearia/agendamentos` – Histórico de atendimentos
  - [ ] `POST /api/barbearia/avaliar-freelancer/:id` – Avaliar freelancer
  - [ ] `GET /api/barbearia/avaliacoes-recebidas` – Ver avaliações recebidas

- [ ] **Regras de negócio**
  - [ ] Validar mensalidade ativa antes de aceitar atendimentos
  - [ ] Bloquear cadeira = não aparece para freelancers
  - [ ] Freelancer pode usar cadeira disponível ilimitadamente (se mensalidade ok)

### Frontend
- [ ] **Telas**
  - [ ] Dashboard com status online/offline
  - [ ] Gestão de cadeiras (lista + toggle bloqueado/disponível)
  - [ ] Mapa de freelancers próximos
  - [ ] Histórico de atendimentos
  - [ ] Tela de avaliações (dar e receber)
  - [ ] Configurações de assinatura e pagamento

---

## ✂️ NICHO: FREELANCER

### Backend
- [ ] **Modelo de dados**
  - [ ] Tabela `freelancers` (usuario_id, tempo_experiencia, nivel_tecnico, lat/lng, status_pausado)
  - [ ] Tabela `especialidades` (freelancer_id, tipo: corte/barba/sobrancelha/facial/quimica)
  - [ ] Tabela `portfolio` (freelancer_id, tipo_servico, url_imagem)
  - [ ] Campo `comissao_ativa` (ativa após 1º mês grátis)
  - [ ] Campo `data_cadastro` (para calcular trial)

- [ ] **Endpoints**
  - [ ] `POST /api/freelancer/cadastro` – Cadastro com validação de nível mínimo intermediário
  - [ ] `POST /api/freelancer/especialidades` – Adicionar especialidades
  - [ ] `POST /api/freelancer/portfolio` – Upload de fotos (obrigatório)
  - [ ] `GET /api/freelancer/portfolio/:id` – Ver portfólio de freelancer
  - [ ] `GET /api/freelancer/barbearias-proximas` – Listar barbearias com cadeiras disponíveis
  - [ ] `GET /api/freelancer/solicitacoes` – Ver solicitações de atendimento pendentes
  - [ ] `POST /api/freelancer/aceitar-atendimento/:id` – Aceitar atendimento
  - [ ] `POST /api/freelancer/recusar-atendimento/:id` – Recusar atendimento
  - [ ] `PATCH /api/freelancer/pausar` – Pausar atendimentos (ex.: almoço)
  - [ ] `GET /api/freelancer/historico` – Ver histórico de atendimentos
  - [ ] `POST /api/freelancer/avaliar-barbearia/:id` – Avaliar barbearia
  - [ ] `POST /api/freelancer/avaliar-cliente/:id` – Avaliar cliente
  - [ ] `GET /api/freelancer/comissoes` – Relatório de comissões a pagar

- [ ] **Regras de negócio**
  - [ ] Nível técnico mínimo: intermediário (validação no cadastro)
  - [ ] Portfólio obrigatório (bloquear ativação sem fotos)
  - [ ] 1º mês grátis (comissão só após 30 dias de cadastro)
  - [ ] Comissão 4% apenas sobre atendimentos via BarberMovie
  - [ ] Clientes próprios = 0% de comissão (flag `origem_cliente` no agendamento)
  - [ ] Freelancer pausado = não recebe novas solicitações

### Frontend
- [ ] **Telas**
  - [ ] Cadastro com upload de portfólio
  - [ ] Seleção de especialidades
  - [ ] Mapa de barbearias próximas
  - [ ] Lista de solicitações (aceitar/recusar)
  - [ ] Histórico de atendimentos
  - [ ] Botão "pausar atendimento"
  - [ ] Tela de avaliações (dar e receber)
  - [ ] Relatório de ganhos e comissões

---

## 👤 NICHO: CLIENTE

### Backend
- [ ] **Modelo de dados**
  - [ ] Tabela `clientes` (usuario_id, lat/lng opcional)
  - [ ] Tabela `agendamentos` (cliente_id, freelancer_id, barbearia_id, servico, preco, data_hora, status, origem: app/proprio)

- [ ] **Endpoints**
  - [ ] `POST /api/cliente/cadastro` – Cadastro simplificado
  - [ ] `GET /api/cliente/freelancers-proximos` – Listar freelancers com portfólio e avaliações
  - [ ] `GET /api/cliente/freelancer/:id/portfolio` – Ver portfólio detalhado
  - [ ] `GET /api/cliente/barbearias-proximas` – Listar barbearias com cadeiras disponíveis
  - [ ] `POST /api/cliente/solicitar-atendimento` – Solicitar atendimento (freelancer + barbearia)
  - [ ] `GET /api/cliente/meus-agendamentos` – Ver agendamentos (passados e futuros)
  - [ ] `POST /api/cliente/avaliar-freelancer/:id` – Avaliar freelancer
  - [ ] `POST /api/cliente/avaliar-barbearia/:id` – Avaliar barbearia

- [ ] **Regras de negócio**
  - [ ] Cliente escolhe freelancer primeiro, depois barbearia
  - [ ] Validar se cadeira está disponível antes de criar agendamento
  - [ ] Marcar origem como `app` (para cálculo de comissão do freelancer)

### Frontend
- [ ] **Telas**
  - [ ] Mapa de freelancers próximos
  - [ ] Cards de freelancers com portfólio e avaliações
  - [ ] Visualização de portfólio (galeria)
  - [ ] Seleção de barbearia após escolher freelancer
  - [ ] Confirmação de agendamento
  - [ ] Histórico de atendimentos
  - [ ] Tela de avaliações (freelancer + barbearia)

---

## ⭐ SISTEMA DE AVALIAÇÕES

### Backend
- [ ] **Modelo de dados**
  - [ ] Tabela `avaliacoes` (avaliador_id, avaliado_id, tipo_avaliado: barbearia/freelancer, agendamento_id, nota 1-5, comentario)
  - [ ] Campo calculado `media_avaliacoes` em barbearias e freelancers

- [ ] **Endpoints**
  - [ ] `POST /api/avaliacoes` – Criar avaliação (com validação de relacionamento)
  - [ ] `GET /api/avaliacoes/barbearia/:id` – Ver avaliações de barbearia
  - [ ] `GET /api/avaliacoes/freelancer/:id` – Ver avaliações de freelancer

- [ ] **Regras de negócio**
  - [ ] Só pode avaliar após atendimento concluído
  - [ ] Avaliação única por agendamento
  - [ ] Reputação influencia ordem de exibição (ordenar por média + quantidade)

### Frontend
- [ ] Sistema de estrelas (1-5)
- [ ] Campo de comentário opcional
- [ ] Exibição de média e quantidade de avaliações
- [ ] Filtro/ordenação por avaliação

---

## 💰 SISTEMA DE MONETIZAÇÃO

### Backend
- [ ] **Modelo de dados**
  - [ ] Tabela `assinaturas` (barbearia_id, plano, valor: 49.90, status: ativa/cancelada, proximo_vencimento)
  - [ ] Tabela `comissoes` (freelancer_id, agendamento_id, valor_servico, comissao_percentual: 4%, valor_comissao, status: pendente/pago)

- [ ] **Endpoints**
  - [ ] `POST /api/pagamentos/assinar` – Criar assinatura (integração gateway)
  - [ ] `POST /api/pagamentos/cancelar-assinatura` – Cancelar assinatura
  - [ ] `GET /api/pagamentos/barbearia/status` – Ver status de assinatura
  - [ ] `GET /api/pagamentos/freelancer/comissoes-pendentes` – Listar comissões a pagar
  - [ ] `POST /api/pagamentos/freelancer/solicitar-saque` – Solicitar pagamento de comissões

- [ ] **Regras de negócio**
  - [ ] Trial automático de 1 mês para freelancers
  - [ ] Barbearia: mensalidade fixa R$49,90 (sem comissão)
  - [ ] Freelancer: 4% de comissão apenas em atendimentos via app
  - [ ] Bloquear funcionalidades se assinatura da barbearia vencida

### Frontend
- [ ] Integração com gateway de pagamento (Stripe/Mercado Pago)
- [ ] Tela de gestão de assinatura (barbearia)
- [ ] Relatório de comissões (freelancer)
- [ ] Histórico de pagamentos

---

## 🔔 NOTIFICAÇÕES

### Backend
- [ ] WebSockets ou Firebase Cloud Messaging
- [ ] Notificar freelancer: nova solicitação de atendimento
- [ ] Notificar cliente: freelancer aceitou/recusou
- [ ] Notificar barbearia: novo agendamento confirmado
- [ ] Lembrete de avaliação pós-atendimento

### Frontend
- [ ] Push notifications (service worker)
- [ ] Centro de notificações no app
- [ ] Badges de notificações não lidas

---

## 🗺️ GEOLOCALIZAÇÃO

### Backend
- [ ] Função de cálculo de distância (Haversine ou PostGIS)
- [ ] Endpoint com parâmetro `raio` (ex.: 5km)
- [ ] Indexação geográfica (lat/lng)

### Frontend
- [ ] Permissão de localização do usuário
- [ ] Exibição em mapa (Google Maps / Leaflet / Mapbox)
- [ ] Filtro por distância

---

## 🔐 AUTENTICAÇÃO E SEGURANÇA

### Backend
- [ ] JWT com refresh token
- [ ] Middleware de autorização por tipo de usuário
- [ ] Validação de email (opcional)
- [ ] Rate limiting (evitar spam)
- [ ] HTTPS obrigatório em produção

### Frontend
- [ ] Armazenamento seguro de tokens (localStorage/sessionStorage)
- [ ] Auto-logout em caso de token expirado
- [ ] Validação de formulários

---

## 📊 RELATÓRIOS E ANALYTICS

### Backend
- [ ] Dashboard de métricas (admin)
- [ ] Relatório de faturamento (barbearia)
- [ ] Relatório de comissões (freelancer)
- [ ] Histórico de atendimentos por período

### Frontend
- [ ] Gráficos de faturamento
- [ ] Gráficos de avaliações
- [ ] Exportação de relatórios (PDF/CSV)

---

## 🧪 TESTES

- [ ] Testes unitários (backend)
- [ ] Testes de integração (API)
- [ ] Testes E2E (fluxo completo)
- [ ] Testes de performance (load testing)

---

## 🚀 DEPLOY E INFRAESTRUTURA

- [ ] CI/CD (GitHub Actions / GitLab CI)
- [ ] Containerização (Docker)
- [ ] Banco de dados em produção (PostgreSQL/MySQL)
- [ ] CDN para imagens (Cloudflare/AWS S3)
- [ ] Monitoramento (Sentry, LogRocket)
- [ ] Backup automático

---

## 📱 EXTRAS (FUTURO)

- [ ] Chat entre freelancer e cliente
- [ ] Sistema de agendamento recorrente
- [ ] Programa de fidelidade
- [ ] Integração com calendário (Google Calendar)
- [ ] Multi-idioma (i18n)
- [ ] Dark mode
