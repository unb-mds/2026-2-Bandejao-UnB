# MySQL

**Integrante:** Luis Felipe
**Semana:** 00
**Data:** 31/08/2026
**Tags:** `mysql` `banco de dados` `sql` `backend` `sgbd`

---

## Resumo

O MySQL é um poderoso Sistema de Gerenciamento de Banco de Dados Relacional (SGBDR) de código aberto que opera no modelo cliente-servidor. Diferente do SQLite, que funciona como um arquivo embutido, o MySQL exige um servidor dedicado (rodando localmente ou na nuvem) para operar. Ele é projetado especificamente para lidar com alta concorrência, grande volume de dados e múltiplos usuários simultâneos com segurança, sendo uma das ferramentas primárias no desenvolvimento de arquiteturas de backend robustas.

Grande parte dessa robustez vem da engine de armazenamento **InnoDB** (padrão desde o MySQL 5.5), que suporta transações e chaves estrangeiras — diferente da engine mais antiga **MyISAM**, que é mais rápida para leitura mas não garante integridade referencial nem controle transacional. É essa característica que torna o MySQL adequado para um sistema com múltiplos usuários alterando dados ao mesmo tempo, como o site do RU.

## Aplicação no projeto

Pela sua arquitetura cliente-servidor, o MySQL é a escolha ideal para gerenciar o tráfego intenso do site do RU:

- **Autenticação e usuários:** gerenciar o alto volume de logins simultâneos de alunos de forma centralizada e segura, guardando credenciais, restrições alimentares e histórico.
- **Gestão de filas em tempo real:** processar requisições contínuas e concorrentes sobre o tamanho e o tempo de espera da fila sem risco de bloquear o banco de dados (*database lock*).
- **Histórico e previsão:** armazenar grandes massas de dados estruturados com métricas de horários de pico diários, servindo de base sólida para os modelos de previsão no backend.
- **Cardápio e feedbacks:** utilizar a integridade referencial para ligar avaliações e comentários diretamente ao perfil do aluno e aos pratos servidos no dia.

## Principais conceitos / como usar

- **Conexão e autenticação:** como os dados não ficam na pasta da aplicação, é necessário iniciar o serviço do MySQL e conectar o código a ele fornecendo *Host* (ex: `localhost`), *Porta* (padrão `3306`), *Usuário* e *Senha*.
- **Criação de estrutura:** utiliza-se `CREATE DATABASE` para criar o banco e `CREATE TABLE` para as tabelas. Tipos de dados comuns incluem `VARCHAR` (textos curtos), `TEXT` (textos longos), `INT`, `DATETIME` e `BOOLEAN`.

  Exemplo aplicado ao projeto do RU (fila de atendimento):

  ```sql
  CREATE TABLE aluno (
      id INT AUTO_INCREMENT PRIMARY KEY,
      nome VARCHAR(100) NOT NULL,
      email VARCHAR(100) UNIQUE NOT NULL,
      restricao_alimentar VARCHAR(100)
  );

  CREATE TABLE fila (
      id INT AUTO_INCREMENT PRIMARY KEY,
      aluno_id INT NOT NULL,
      entrada DATETIME NOT NULL,
      atendido BOOLEAN DEFAULT FALSE,
      FOREIGN KEY (aluno_id) REFERENCES aluno(id)
  );
  ```

- **Relacionamentos:** uso de chaves primárias (`PRIMARY KEY`) e chaves estrangeiras (`FOREIGN KEY`) para conectar dados entre diferentes tabelas, garantindo a organização relacional.
- **Índices (`INDEX`):** aceleram buscas em colunas consultadas com frequência — por exemplo, um índice em `aluno_id` na tabela `fila` deixa mais rápido verificar a posição de um aluno específico na fila, algo essencial num cenário de consultas em tempo real.
- **Manipulação de dados (CRUD):** uso dos comandos essenciais `INSERT`, `SELECT`, `UPDATE` e `DELETE` combinados com a cláusula `WHERE` para filtros específicos.
- **Transações (`TRANSACTION`, `COMMIT`, `ROLLBACK`):** agrupam várias operações como uma unidade só — se uma etapa falhar, tudo é desfeito (`ROLLBACK`). Importante, por exemplo, ao registrar uma avaliação vinculada a um prato: evita que o comentário seja salvo sem a referência correta ao prato ou ao aluno.
- **Integração com backend:** em Python, a conexão geralmente é feita por bibliotecas como `mysql-connector-python` ou mapeadores (ORMs) como o `SQLAlchemy`. O uso de parâmetros preparados é obrigatório para evitar falhas de *SQL Injection*.
- **Ferramentas visuais:** em vez de usar apenas a linha de comando, utiliza-se softwares como o *MySQL Workbench* ou o *DBeaver* para modelar e administrar o banco graficamente.

## Fontes e materiais usados

- Documentação oficial do MySQL: https://dev.mysql.com/doc/
- Playlist "Curso de SQL com MySQL (Completo)", de Otávio Miranda: https://www.youtube.com/playlist?list=PLbIBj8vQhvm2WT-pjGS5x7zUzmh4VgvRk
- Playlist "Curso de Banco de Dados MySQL", de Gustavo Guanabara (Curso em Vídeo): https://www.youtube.com/playlist?list=PLHz_AreHm4dkBs-795Dsgvau_ekxg8g1r
- Práticas no terminal e visualização de tabelas
