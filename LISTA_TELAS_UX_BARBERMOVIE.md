# 📱 BARBERMOVIE – LISTA DE TELAS (UX)

## 🔐 AUTENTICAÇÃO E ONBOARDING

### Comum (todos os usuários)
1. **Splash Screen**
   - Logo BarberMovie
   - Loading inicial

2. **Tela de Boas-vindas**
   - Carrossel explicativo (3 slides)
   - Botões: "Entrar" | "Cadastrar"

3. **Escolha do Tipo de Usuário**
   - Card "Sou Cliente"
   - Card "Sou Freelancer"
   - Card "Tenho uma Barbearia"

4. **Login**
   - Campo: Email
   - Campo: Senha
   - Botão: "Entrar"
   - Link: "Esqueci minha senha"
   - Link: "Criar conta"

5. **Recuperação de Senha**
   - Campo: Email
   - Botão: "Enviar link de recuperação"

---

## 🏪 FLUXO: DONO DA BARBEARIA

### Cadastro
6. **Cadastro Barbearia - Passo 1**
   - Campo: Nome da barbearia
   - Campo: Email
   - Campo: Senha
   - Campo: Confirmar senha
   - Botão: "Continuar"

7. **Cadastro Barbearia - Passo 2**
   - Campo: Telefone
   - Campo: CEP (auto-completa endereço)
   - Campo: Rua
   - Campo: Número
   - Campo: Complemento
   - Campo: Bairro
   - Campo: Cidade/Estado
   - Botão: "Continuar"

8. **Cadastro Barbearia - Passo 3**
   - Mapa interativo (arrastar pin)
   - Botão: "Confirmar localização"

9. **Cadastro Barbearia - Passo 4**
   - Campo: Número de cadeiras
   - Info: "Você pagará R$49,90/mês por uso ilimitado"
   - Checkbox: "Aceito os termos"
   - Botão: "Criar conta"

10. **Pagamento - Assinatura**
    - Dados do cartão
    - Botão: "Assinar e ativar"
    - Info: "Trial de 7 dias grátis" (se aplicável)

### Dashboard
11. **Home - Barbearia**
    - Header: Nome da barbearia + foto
    - Toggle: Online / Offline (verde/vermelho)
    - Card: Resumo do dia (atendimentos, faturamento)
    - Card: Cadeiras (lista com status)
    - Card: Próximos agendamentos
    - Botão flutuante: "+ Adicionar cadeira"

12. **Gestão de Cadeiras**
    - Lista de cadeiras:
      - Cadeira 1 - Disponível | Bloqueada (toggle)
      - Cadeira 2 - Disponível | Bloqueada (toggle)
    - Botão: "+ Adicionar cadeira"
    - Cada item:
      - Nome/número da cadeira
      - Status atual
      - Freelancer usando (se ocupada)
      - Ações: Bloquear | Excluir

13. **Freelancers Próximos**
    - Mapa com pins de freelancers
    - Lista de cards:
      - Foto do freelancer
      - Nome
      - Especialidades (ícones)
      - Avaliação (estrelas + número)
      - Distância (ex.: 2.5 km)
      - Botão: "Ver portfólio"

14. **Portfólio do Freelancer** (visualização)
    - Foto de perfil
    - Nome
    - Avaliação média
    - Total de atendimentos
    - Especialidades
    - Galeria de fotos
    - Avaliações recentes
    - Botão: "Fechar"

15. **Agendamentos**
    - Filtro: Hoje | Semana | Mês | Todos
    - Lista de cards:
      - Data/hora
      - Nome do cliente
      - Nome do freelancer
      - Serviço
      - Status (confirmado, concluído, cancelado)
      - Botão: "Ver detalhes"

16. **Detalhes do Agendamento**
    - Cliente: foto + nome
    - Freelancer: foto + nome
    - Cadeira: número
    - Serviço + preço
    - Data/hora
    - Status
    - Botões: "Avaliar freelancer" (se concluído)

17. **Avaliar Freelancer**
    - Foto + nome do freelancer
    - Seletor de estrelas (1-5)
    - Campo: Comentário (opcional)
    - Botão: "Enviar avaliação"

18. **Avaliações Recebidas**
    - Tabs: De Freelancers | De Clientes
    - Lista de cards:
      - Foto + nome do avaliador
      - Estrelas
      - Comentário
      - Data

19. **Configurações - Barbearia**
    - Seções:
      - **Perfil**: editar nome, telefone, endereço
      - **Assinatura**: status, próximo vencimento, método de pagamento
      - **Notificações**: toggle para cada tipo
      - **Segurança**: alterar senha
      - **Suporte**: chat/email
    - Botão: "Sair"

---

## ✂️ FLUXO: FREELANCER

### Cadastro
20. **Cadastro Freelancer - Passo 1**
    - Campo: Nome completo
    - Campo: Email
    - Campo: Senha
    - Campo: Confirmar senha
    - Botão: "Continuar"

21. **Cadastro Freelancer - Passo 2**
    - Campo: Telefone
    - Seletor: Tempo de experiência (1-2 anos, 3-5, 5+)
    - Seletor: Nível técnico (Intermediário, Avançado, Expert)
    - Validação: bloqueia se < Intermediário
    - Botão: "Continuar"

22. **Cadastro Freelancer - Passo 3**
    - Título: "Selecione suas especialidades"
    - Checkboxes:
      - ✓ Corte
      - ✓ Barba
      - ✓ Sobrancelha
      - ✓ Facial
      - ✓ Química
    - Validação: mínimo 1 selecionada
    - Botão: "Continuar"

23. **Cadastro Freelancer - Passo 4**
    - Título: "Monte seu portfólio (obrigatório)"
    - Upload de imagens:
      - Seção: Cortes (min. 3 fotos)
      - Seção: Barba (min. 2 fotos)
      - Seção: Facial (min. 1 foto)
    - Botão: "Enviar fotos"
    - Validação: bloqueia avanço sem mínimo
    - Botão: "Concluir cadastro"

24. **Bem-vindo Freelancer**
    - Mensagem: "Parabéns! 1 mês grátis, depois 4% de comissão"
    - Botão: "Começar a usar"

### Dashboard
25. **Home - Freelancer**
    - Header: Foto + nome
    - Toggle: Disponível / Pausado
    - Card: Resumo do dia (atendimentos, ganhos)
    - Card: Solicitações pendentes (badge com número)
    - Card: Próximos agendamentos
    - Botão: "Ver barbearias próximas"

26. **Solicitações de Atendimento**
    - Lista de cards (modelo Uber):
      - Nome do cliente
      - Foto do cliente
      - Serviço solicitado
      - Barbearia (nome + endereço)
      - Distância
      - Horário
      - Preço
      - Botões: "Aceitar" | "Recusar"
    - Timer de expiração (ex.: 2 min)

27. **Barbearias Próximas**
    - Mapa com pins de barbearias
    - Lista de cards:
      - Foto da barbearia
      - Nome
      - Endereço
      - Distância
      - Avaliação (estrelas)
      - Cadeiras disponíveis (número)
      - Botão: "Ver detalhes"

28. **Detalhes da Barbearia**
    - Fotos do espaço
    - Nome
    - Endereço + mapa
    - Telefone
    - Avaliação média
    - Cadeiras disponíveis
    - Avaliações recentes
    - Botão: "Ver no mapa"

29. **Meus Agendamentos - Freelancer**
    - Filtro: Pendentes | Hoje | Passados
    - Lista de cards:
      - Cliente (foto + nome)
      - Serviço
      - Barbearia
      - Data/hora
      - Status
      - Botão: "Ver detalhes"

30. **Detalhes do Agendamento - Freelancer**
    - Cliente: foto + nome + telefone
    - Barbearia: nome + endereço + mapa
    - Serviço + preço
    - Data/hora
    - Status
    - Botões: "Avaliar cliente" | "Avaliar barbearia" (se concluído)

31. **Avaliar Cliente**
    - Foto + nome do cliente
    - Estrelas (1-5)
    - Comentário (opcional)
    - Botão: "Enviar"

32. **Avaliar Barbearia**
    - Foto + nome da barbearia
    - Estrelas (1-5)
    - Comentário (opcional)
    - Botão: "Enviar"

33. **Meu Portfólio** (edição)
    - Seções por especialidade
    - Grid de fotos
    - Botão: "+ Adicionar foto" em cada seção
    - Botão: "Excluir" em cada foto

34. **Ganhos e Comissões**
    - Período: Mês atual
    - Card: Total de atendimentos
    - Card: Ganhos brutos
    - Card: Comissões a pagar (4% dos atendimentos via app)
    - Card: Ganhos líquidos
    - Lista detalhada:
      - Data
      - Cliente
      - Serviço
      - Valor
      - Comissão
      - Origem (App | Próprio)
    - Botão: "Solicitar saque"

35. **Avaliações Recebidas - Freelancer**
    - Tabs: De Clientes | De Barbearias
    - Média geral (destaque)
    - Lista de cards com avaliações

36. **Configurações - Freelancer**
    - Perfil: editar nome, telefone, foto
    - Especialidades: editar lista
    - Notificações: toggles
    - Segurança: alterar senha
    - Financeiro: dados bancários para saque
    - Suporte
    - Botão: "Sair"

---

## 👤 FLUXO: CLIENTE

### Cadastro
37. **Cadastro Cliente - Passo 1**
    - Campo: Nome
    - Campo: Email
    - Campo: Senha
    - Campo: Confirmar senha
    - Botão: "Criar conta"

38. **Cadastro Cliente - Passo 2**
    - Título: "Permitir localização?"
    - Texto: "Para encontrar freelancers e barbearias próximas"
    - Botão: "Permitir"
    - Link: "Pular"

### Dashboard
39. **Home - Cliente**
    - Busca: "Procurar freelancer ou serviço"
    - Seção: "Freelancers em destaque" (carrossel)
    - Seção: "Barbearias próximas" (carrossel)
    - Botão: "Ver todos os freelancers"
    - Botão: "Ver todas as barbearias"

40. **Freelancers Próximos - Cliente**
    - Mapa com pins
    - Filtros: Especialidade | Avaliação | Distância
    - Lista de cards:
      - Foto do freelancer
      - Nome
      - Especialidades (ícones)
      - Avaliação (estrelas + número)
      - Distância
      - "A partir de R$ XX"
      - Botão: "Ver portfólio"

41. **Portfólio do Freelancer - Cliente**
    - Foto de perfil
    - Nome
    - Avaliação média (destaque)
    - Total de atendimentos
    - Especialidades
    - Galeria de fotos (grid navegável)
    - Seção: Avaliações recentes (últimas 5)
    - Botão flutuante: "Agendar com este freelancer"

42. **Agendar - Passo 1: Escolher Serviço**
    - Freelancer selecionado (card no topo)
    - Lista de serviços:
      - Corte - R$ XX
      - Barba - R$ XX
      - Sobrancelha - R$ XX
      - Facial - R$ XX
    - Seleção múltipla (checkboxes)
    - Total em destaque
    - Botão: "Continuar"

43. **Agendar - Passo 2: Escolher Barbearia**
    - Título: "Onde você quer ser atendido?"
    - Mapa com pins de barbearias próximas
    - Lista de cards:
      - Foto da barbearia
      - Nome
      - Endereço
      - Distância
      - Avaliação
      - Cadeiras disponíveis
      - Botão: "Selecionar"

44. **Agendar - Passo 3: Data e Hora**
    - Freelancer + barbearia (resumo no topo)
    - Calendário (dias disponíveis)
    - Lista de horários disponíveis (ex.: 09:00, 10:00...)
    - Botão: "Confirmar agendamento"

45. **Confirmação de Agendamento**
    - Card resumo:
      - Freelancer (foto + nome)
      - Barbearia (nome + endereço)
      - Serviços
      - Data/hora
      - Total
    - Status: "Aguardando confirmação do freelancer"
    - Botão: "Cancelar agendamento"
    - Botão: "Voltar ao início"

46. **Meus Agendamentos - Cliente**
    - Tabs: Pendentes | Confirmados | Concluídos | Cancelados
    - Lista de cards:
      - Freelancer (foto + nome)
      - Barbearia
      - Serviço
      - Data/hora
      - Status
      - Botão: "Ver detalhes"

47. **Detalhes do Agendamento - Cliente**
    - Freelancer: foto + nome + especialidades
    - Barbearia: nome + endereço + mapa
    - Serviços + preço
    - Data/hora
    - Status
    - Botões:
      - "Ver no mapa" (navegação)
      - "Cancelar" (se pendente/confirmado)
      - "Avaliar" (se concluído)

48. **Avaliar Atendimento - Cliente**
    - Seção 1: Avaliar Freelancer
      - Foto + nome
      - Estrelas (1-5)
      - Comentário (opcional)
    - Seção 2: Avaliar Barbearia
      - Foto + nome
      - Estrelas (1-5)
      - Comentário (opcional)
    - Botão: "Enviar avaliações"

49. **Barbearias Próximas - Cliente**
    - Mapa com pins
    - Lista de cards:
      - Foto
      - Nome
      - Endereço
      - Distância
      - Avaliação
      - Botão: "Ver detalhes"

50. **Detalhes da Barbearia - Cliente**
    - Fotos do espaço
    - Nome
    - Endereço + mapa
    - Avaliação média
    - Avaliações recentes
    - Seção: "Freelancers disponíveis nesta barbearia"
      - Lista de freelancers
    - Botão: "Ver no mapa"

51. **Configurações - Cliente**
    - Perfil: editar nome, foto, telefone
    - Notificações: toggles
    - Segurança: alterar senha
    - Suporte
    - Botão: "Sair"

---

## 🔔 NOTIFICAÇÕES (todos os usuários)

52. **Central de Notificações**
    - Lista cronológica:
      - Ícone + título + descrição + tempo
      - Badge "não lida"
      - Ao clicar: vai para tela relacionada
    - Tipos de notificação:
      - **Barbearia**: "Novo agendamento confirmado"
      - **Freelancer**: "Nova solicitação de atendimento"
      - **Cliente**: "Seu agendamento foi confirmado"
      - **Todos**: "Você recebeu uma nova avaliação"

---

## 📊 TELAS ADICIONAIS

53. **Termos de Uso**
    - Scroll de texto
    - Checkbox: "Li e aceito"
    - Botão: "Aceitar"

54. **Política de Privacidade**
    - Scroll de texto

55. **Suporte / Ajuda**
    - FAQ (acordeão)
    - Botão: "Falar com suporte"
    - Chat ou formulário

56. **Sobre o BarberMovie**
    - Missão/visão
    - Versão do app
    - Links sociais

---

## 🎨 COMPONENTES REUTILIZÁVEIS

- **Card de Freelancer**: foto, nome, especialidades, avaliação, distância
- **Card de Barbearia**: foto, nome, endereço, avaliação, distância
- **Card de Agendamento**: cliente/freelancer, serviço, data, status
- **Avaliação (estrelas)**: componente de 1-5 estrelas interativo
- **Mapa**: com pins e filtros
- **Bottom Navigation**: (Home | Agendamentos | Notificações | Perfil)
- **Header**: com logo, título e ações (menu, notificações)
- **Modal de Confirmação**: para ações críticas (cancelar, excluir)
- **Loading**: spinner ou skeleton
- **Empty State**: quando não há dados

---

## 🗺️ NAVEGAÇÃO (Bottom Navigation)

### Barbearia
- Home
- Agendamentos
- Notificações
- Perfil

### Freelancer
- Home
- Solicitações
- Agendamentos
- Perfil

### Cliente
- Home
- Agendamentos
- Notificações
- Perfil

---

## 📱 TOTAL DE TELAS: 56

- Autenticação: 5 telas
- Barbearia: 15 telas
- Freelancer: 18 telas
- Cliente: 15 telas
- Comuns: 3 telas

---

## 🎯 PRIORIZAÇÃO (MVP)

### Fase 1 (Essencial)
- Autenticação completa
- Cadastro dos 3 tipos
- Home de cada tipo
- Portfólio do freelancer (visualização e edição)
- Agendamento (fluxo completo)
- Avaliações básicas

### Fase 2
- Gestão de cadeiras
- Solicitações (aceitar/recusar)
- Notificações push
- Filtros avançados
- Mapas interativos

### Fase 3
- Relatórios financeiros
- Sistema de pagamentos
- Chat/suporte
- Configurações avançadas
