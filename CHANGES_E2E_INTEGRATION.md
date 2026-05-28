Resumo das alterações locais - Integração E2E (frontend/backend)

- Backend: `app/main.py`
  - Adicionada origem `http://localhost:5174` ao `ALLOWED_ORIGINS` padrão para evitar bloqueios CORS durante desenvolvimento.

- Frontend (dev helpers): `public/set_token.js`
  - Substituído comportamento que injetava token automaticamente por um prompt de inserção manual para maior segurança em ambientes compartilhados.

- Frontend (mini-pages): `public/mini_e2e.html`, `public/mini_e2e.js`
  - Página e script para executar um fluxo E2E (login opcional via token, gerar/confirmar PIX, listar e liberar cadeiras).

- Scripts: `scripts/e2e_api_test.py`
  - Script Python para rodar o fluxo E2E via terminal (login, criar/confirmar assinatura, liberar/aceitar cadeira).

Testes executados:
- Rodei o script Python `scripts/e2e_api_test.py` e verifiquei geração/confirmacao de PIX, criação de assinatura e fluxo de cadeiras.
- Executei a página `/mini_e2e.html` no dev server e rodei o fluxo via browser, confirmando o funcionamento.

Próximos passos sugeridos:
- Rever e commitar as alterações no repositório remoto.
- Remover qualquer token sensível e ajustar variáveis de ambiente para o ambiente de produção.
