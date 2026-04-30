# Estudo no Hospital

Site educacional em Flask para criancas e adolescentes internados, com login, escolha de disciplina, nivel escolar, explicacao do assunto, atividades adaptativas e registro de progresso.

## Como rodar

1. Instale Python 3.9 ou superior.
2. Crie e ative um ambiente virtual:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

3. Instale as dependencias:

```powershell
pip install -r requirements.txt
```

4. Copie `.env.example` para `.env`, troque a `SECRET_KEY` e configure o banco.

Para usar SQLite local, deixe:

```env
DATABASE_URL=sqlite:///hospital_estudos.db
```

Para usar MySQL, crie o banco no MySQL e use uma URL neste formato:

```env
DATABASE_URL=mysql+pymysql://usuario:senha@127.0.0.1:3306/nome_do_banco?charset=utf8mb4
```

Exemplo de criacao do banco no MySQL:

```sql
CREATE DATABASE nome_do_banco CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

Ao iniciar a aplicacao, o Flask-SQLAlchemy cria as tabelas `users`, `progress` e `activity_logs` automaticamente.

## IA real gratis para demonstracao

O projeto pode usar Groq para gerar atividades com IA real. Ele exige uma conta e uma chave de API, mas funciona bem para demonstracao e costuma responder rapido.

No `.env`, configure:

```env
AI_PROVIDER=groq
GROQ_API_KEY=sua_chave_groq
GROQ_MODEL=llama-3.1-8b-instant
```

Crie a chave em `https://console.groq.com/keys`. Se a API falhar, estiver sem limite ou a chave nao estiver configurada, o sistema volta automaticamente para o gerador local.

5. Inicie o Flask:

```powershell
python run.py
```

6. Abra `http://127.0.0.1:5000`.

## Como rodar com Docker

Com Docker Desktop instalado e aberto, rode na pasta do projeto:

```powershell
docker compose up --build
```

Depois acesse:

```text
http://127.0.0.1:5000
```

Para outra pessoa ou outro computador na mesma rede acessar, descubra o IP do seu computador:

```powershell
ipconfig
```

Procure o `IPv4` da sua rede Wi-Fi ou Ethernet e envie o link neste formato:

```text
http://SEU-IP:5000
```

Exemplo:

```text
http://192.168.1.25:5000
```

O `docker-compose.yml` usa SQLite dentro da pasta `instance/`, com volume persistente para manter o banco entre reinicios. Se quiser usar MySQL pelo Docker acessando um MySQL instalado no seu computador, troque o host `127.0.0.1` por `host.docker.internal` no `DATABASE_URL`.

Por seguranca, o Docker nao carrega sua `.env` inteira automaticamente. A configuracao padrao usa `AI_PROVIDER=local`. Se quiser usar Groq no Docker, adicione `AI_PROVIDER`, `GROQ_API_KEY` e `GROQ_MODEL` manualmente no bloco `environment` do `docker-compose.yml`.

## Como publicar no Render

O projeto pode ser publicado no Render usando o `Dockerfile`. Para manter usuarios, progresso e logs sem depender do filesystem temporario do Render, use um banco PostgreSQL gerenciado.

1. Suba este projeto para um repositorio no GitHub.
2. No Render, crie um banco em `New > Postgres`.
3. Copie a `Internal Database URL` do Postgres criado.
4. Crie o site em `New > Web Service`.
5. Conecte o repositorio do GitHub.
6. Em `Runtime`, escolha `Docker`.
7. Em `Environment Variables`, configure:

```env
SECRET_KEY=troque-por-uma-chave-grande-e-secreta
DATABASE_URL=cole-a-internal-database-url-do-postgres
SESSION_COOKIE_SECURE=true
AI_PROVIDER=local
GROQ_API_KEY=
GROQ_MODEL=llama-3.1-8b-instant
```

8. Clique em `Deploy Web Service`.

O Render define a porta automaticamente pela variavel `PORT`; o `Dockerfile` ja esta preparado para isso. Ao iniciar, a aplicacao cria as tabelas do banco automaticamente.

## Onde cada codigo fica

- `run.py`: ponto de entrada. Cria o app Flask e inicia o servidor.
- `requirements.txt`: extensoes externas que precisam ser instaladas.
- `.env.example`: exemplo de variaveis de ambiente.
- `app/config.py`: configuracao do Flask, banco, cookies e seguranca de sessao.
- `app/__init__.py`: fabrica da aplicacao. Liga Flask, SQLAlchemy, rotas e cria tabelas.
- `app/domain/catalog.py`: catalogo de disciplinas, niveis escolares e assuntos.
- `app/application/user_service.py`: regras de cadastro e login.
- `app/application/security.py`: hash de senha e token CSRF.
- `app/application/ai_provider.py`: gerador local que simula IA. Troque esta classe por uma API real quando quiser.
- `app/application/learning_service.py`: caso de uso das atividades. Gera questao, mede latencia, salva log e ajusta dificuldade.
- `app/infrastructure/db/database.py`: instancia do SQLAlchemy.
- `app/infrastructure/db/models.py`: tabelas `users`, `progress` e `activity_logs`.
- `app/infrastructure/repositories.py`: acesso ao banco, isolado da camada de aplicacao.
- `app/presentation/routes.py`: paginas HTML e endpoints REST JSON.
- `app/presentation/templates/`: telas de login, cadastro, painel, disciplina e estudo.
- `app/presentation/static/css/styles.css`: visual do site.
- `app/presentation/static/js/`: interacao do painel e das atividades.

## Requisitos do enunciado

- Confiabilidade: cada questao gerada recebe `request_id` e fica salva em `activity_logs`, garantindo rastreio da entrega e da resposta.
- Latencia: o endpoint de geracao mede `latency_ms` e retorna esse tempo ao front-end.
- Complexidade e multiplos protocolos: o projeto entrega paginas HTML tradicionais e API REST JSON.
- Seguranca: senha com hash, cookie `HttpOnly`, `SameSite=Lax`, token CSRF nos formularios e chamadas API. Em producao, use HTTPS e `SESSION_COOKIE_SECURE=true`.
- Flask: rotas web e endpoints REST.
- SQLAlchemy: usuarios, progresso e logs persistidos em SQLite por padrao ou MySQL via `DATABASE_URL`.
- Clean Architecture: dominio, aplicacao, infraestrutura e apresentacao separados.
- Python 3.9+: compativel com Python 3.9 ou superior.

## Como usar IA real depois

Hoje `LocalLearningAI` gera atividades sem internet nem chave de API. Para usar uma IA externa, crie uma classe com os mesmos metodos:

- `generate_explanation(discipline, level, topic)`
- `generate_activity(discipline, level, topic, difficulty, excluded_questions=None)`
- `evaluate(expected_answer, user_answer, discipline, topic)`

Depois troque a instancia em `app/presentation/routes.py`, dentro da funcao `services()`.

## Observacao de producao

Para hospital ou dados reais, adicione HTTPS obrigatorio, controle de responsavel/professor, politica de privacidade, backups, monitoramento de erro e revisao de conteudo gerado por IA.
"# Projeto-Ia-Criancas" 
