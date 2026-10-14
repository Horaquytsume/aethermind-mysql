# AetherMind — Python + MySQL

Versão reorganizada do protótipo enviado: mantém a interface escura e colorida, mas separa frontend, backend e banco. O cadastro, login e histórico usam uma API Flask e MySQL; a senha nunca é gravada em texto puro.

## O que foi melhorado

- Backend em Python/Flask e banco MySQL 8.
- Senhas protegidas com hash seguro do Werkzeug — não criptografia reversível.
- Sessão em cookie `HttpOnly`/`SameSite`, proteção CSRF nas operações que alteram dados e troca da sessão depois do login.
- Consultas SQL parametrizadas, validação no servidor e pool de conexões MySQL.
- Questionários e resultados salvos por usuário; exclusão da conta remove também o histórico.
- A interface usa `textContent` para mostrar conteúdo e não coloca respostas do usuário em HTML executável.
- A análise atual é **heurística e transparente**. Não chama uma IA generativa nem consulta vagas, clubes ou estatísticas em tempo real; os resultados não são previsões nem garantias.

## Iniciar com Docker

É o caminho mais simples: o Compose sobe o MySQL, cria as tabelas e inicia o app em `http://127.0.0.1:5000`.

1. Copie `.env.example` para `.env`.
2. No `.env`, substitua `APP_SECRET_KEY`, `MYSQL_PASSWORD` e `MYSQL_ROOT_PASSWORD` por valores fortes e diferentes. Gere a chave do app com:

   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(48))"
   ```

3. Inicie o projeto:

   ```bash
   docker compose up --build
   ```

4. Abra `http://127.0.0.1:5000`. O endpoint `http://127.0.0.1:5000/api/health` mostra se o servidor consegue falar com o MySQL.

O arquivo `.env` contém segredos locais e está no `.gitignore`; nunca o publique. O usuário MySQL do app é separado do root. O esquema é aplicado automaticamente **somente quando o volume do MySQL é criado pela primeira vez**; faça backup antes de qualquer reinicialização ou alteração de volume.

## Iniciar sem Docker

1. Instale Python 3.10+ e MySQL 8; crie o banco `aethermind` com `utf8mb4`.
2. Copie `.env.example` para `.env`, gere `APP_SECRET_KEY` e informe host, usuário e senha do banco.
3. Aplique `schema.sql` no banco configurado.
4. Instale as dependências e rode localmente:

   ```bash
   python -m venv .venv
   # Linux/macOS: source .venv/bin/activate
   # Windows PowerShell: .venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   python app.py
   ```

O servidor embutido do Flask serve apenas para desenvolvimento local. Para produção, use HTTPS e Gunicorn atrás de um proxy reverso.

## Estrutura

- `app.py` — API, sessão, proteção CSRF, validação e acesso ao MySQL.
- `recommendations.py` — recomendações reproduzíveis por regras explícitas.
- `schema.sql` — tabelas `users` e `analyses`, com chave estrangeira e exclusão em cascata.
- `templates/index.html` — interface baseada no HTML enviado.
- `static/app.js` — login, questionário, histórico e apresentação dos resultados.
- `static/site.css`, `static/tailwind-config.js` — estilos e tema.
- `tests/` — testes das recomendações sem exigir conexão com MySQL.

## Dados e privacidade

O app salva nome, e-mail, hash da senha e respostas do questionário no MySQL de quem o hospeda. As perguntas de idade e cidade são dados pessoais; não informe dados sensíveis. O próprio usuário pode excluir a conta pela tela, o que apaga suas análises associadas. Antes de publicar para outras pessoas, revise a política de privacidade, retenção e consentimento aplicável ao seu caso.

A interface ainda carrega Tailwind e a fonte do Google por CDN para manter o visual do protótipo. Isso exige internet no navegador; para produção, compile e hospede os estilos localmente e revise a política de segurança de conteúdo.

> **Importante:** a interface original dizia “IA” e “banco estatístico”, mas não havia integração real com modelo ou fonte de mercado. O código corrigido informa isso ao usuário e calcula apenas uma sugestão inicial local no servidor.
