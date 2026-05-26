Resumo das alterações visuais aplicadas

Objetivo: Converter UI para tema dark/premium, padronizar botões CTA (laranja gradiente), remover blocos brancos grandes e garantir consistência de bordas, tipografia e espaçamentos.

Arquivos alterados (principais):
- src/screens/TelaPrincipalApp.jsx
- src/components/AppCard.jsx
- src/App.jsx
- src/components/Common.jsx
- src/components/InstallPWA.jsx
- src/components/BannerVencimentoAssinatura.jsx
- src/components/TelaAssinaturaBarbearia.jsx
- src/components/TelaMensalidadeAssinatura.jsx
- src/components/AssinaturaPage.jsx
- src/components/ModalBloqueio.jsx
- src/components/SeletorServicoBarbearia.jsx
- src/components/PoliticaPrivacidade.jsx
- src/components/TermosDeUso.jsx
- src/components/PerfilCard.jsx (parciais)
- src/components/MapEmbed.jsx (verificação de wrapper)
- src/components/BarberDashboard.jsx (ajuste de indicadores)
- src/components/FreelancerDashboard.jsx
- src/components/ShopDashboard.jsx (CTA 'Nova')

Principais mudanças aplicadas:
- Removidos estilos inline sempre que possível; substituídos por classes Tailwind.
- Padronização de `AppCard` com `bg-zinc-900 rounded-2xl p-5`.
- Botões de ação principais convertidos para `bg-gradient-to-r from-orange-600 to-red-600 text-white font-extrabold rounded-2xl`.
- Inputs e containers convertidos para variantes escuras (`bg-zinc-800`, `border-zinc-700/800`, `text-zinc-200`).
- QR codes mantidos em bloco branco pequeno para contraste, mas contêineres e modais são escuros.
- Bottom nav e botões ativos estilizados para realçar CTA central.

Próximos passos sugeridos:
1. Rodar `npm run dev` em `barbermove` e verificar visual no navegador (http://localhost:5173).
2. Capturar screenshots e ajustar espaçamentos finos (pixel-perfect) conforme prints de referência.
3. Revisar `ClientDashboard.jsx`, `BarberDashboard.jsx` e `ShopDashboard.jsx` em telas específicas (se quiser, faço isso automaticamente).

Notas:
- Mantive pequenas áreas brancas apenas para QR codes por questões de legibilidade.
- Se desejar eliminar até essas pequenas caixas brancas, posso substituir por outline claro + fundo transparente, mas a leitura do QR pode ser prejudicada em alguns navegadores.

Se quiser que eu rode o servidor de desenvolvimento e gere screenshots, autorize e eu executo os comandos necessários.
