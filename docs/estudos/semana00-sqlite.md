# Semana 00 — SQLite

**Integrante:** Josué Xavier Carneiro

## Resumo

SQLite é um sistema de gerenciamento de banco de dados relacional que funciona como uma biblioteca embutida, rodando localmente na própria aplicação — sem depender de um servidor externo. Ele armazena todos os dados em um único arquivo no disco, o que o torna leve, rápido e portátil entre diferentes sistemas operacionais.

É amplamente utilizado em aplicações mobile, desktop e sistemas embarcados, justamente por sua simplicidade de uso e baixa complexidade de configuração. Por outro lado, não é recomendado para sistemas com muitos usuários simultâneos, já que não foi projetado para cenários de alta concorrência como um servidor de banco de dados tradicional (MySQL, PostgreSQL, etc.).

## Aplicação no projeto

O SQLite pode ser usado em diversas frentes do site do RU:

- **Previsão de pico:** armazenar o histórico de horários de pico anteriores, servindo de base de dados para os modelos de previsão.
- **Fila:** salvar e armazenar os dados atuais do estado da fila em tempo real.
- **Usuários:** guardar dados de login dos usuários, permitindo autenticação e, a partir disso, associar feedbacks e histórico de uso ao usuário.
- **Feedbacks e infraestrutura:** registrar feedbacks dos usuários e dados relacionados ao estado da infraestrutura do RU.
- **Cardápio (opcional):** caso seja útil para o projeto, também pode guardar o histórico de cardápios de semanas anteriores.

## Principais conceitos / como usar

- **Criação de tabelas:** usa-se `CREATE TABLE`, com tipos de dados como `INTEGER`, `TEXT`, `REAL` e `BLOB`.
- **Comandos SQL básicos:** `INSERT`, `SELECT`, `UPDATE`, `DELETE` e `JOIN` para manipulação e consulta dos dados.
- **`PRAGMA`:** usado para configurações do banco, como ativar o suporte a chaves estrangeiras (foreign keys).
- **Conexão via linguagens de programação:** em Python, por exemplo, usa-se a biblioteca nativa `sqlite3`. Para evitar SQL Injection, usam-se placeholders (`?`) nas queries em vez de concatenar valores diretamente na string SQL.
- **Ferramentas:** existe a CLI oficial (`sqlite3`) para uso via terminal, além de ferramentas gráficas como o DB Browser for SQLite para inspecionar e manipular o banco visualmente.

## Fontes e materiais usados

- Vídeo: https://www.youtube.com/watch?v=8f2jZaBMso0
- Vídeo: https://www.youtube.com/watch?v=8Xyn8R9eKB8
- Documentação oficial: https://sqlite.org/about.html
- Resumo e tira-dúvidas com o Claude
