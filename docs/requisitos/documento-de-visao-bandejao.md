# Documento de Visão — Bandejão

> Documento de visão do **Bandejão**, uma PWA que reúne cardápio, avaliações das refeições e, na Release 2, informações de fila dos Restaurantes Universitários da UnB. Projeto do Grupo 6 na disciplina Métodos de Desenvolvimento de Software (FCTE/UnB, Brasília, 2026), organizado conforme o modelo de documento de visão do IBM DOORS Next.

---

## 1. Introdução

### 1.1 Propósito

O documento de visão define o escopo de alto nível e o propósito do software a ser desenvolvido, estabelecendo expectativas e reduzindo os riscos do produto para o cliente e para os desenvolvedores. Este documento apresenta uma visão ampla do Bandejão: sua proposta, características, utilidades e funcionalidades.

### 1.2 Escopo

O Bandejão é um projeto da disciplina de Métodos de Desenvolvimento de Software (MDS), do curso de Engenharia de Software da Faculdade de Ciências e Tecnologias em Engenharia (FCTE) da Universidade de Brasília (UnB), realizado pelo Grupo 6 com orientação da professora Carla Rocha.

Seu objetivo é auxiliar quem usufrui dos restaurantes universitários (RU) dos campi da UnB, oferecendo:

- **MVP:** acesso fácil e visualização dinâmica do cardápio dos campi, com filtros de marcadores alimentares e de dieta, e avaliações das refeições;
- **Release 2:** check-in no RU e previsão do horário de pico da fila, calculada a partir dos check-ins dos usuários;
- **Backlog:** nível da fila em tempo real (nível agora) e ícones de marcadores nos pratos.

O escopo restringe-se aos RUs dos campi da UnB. O Restaurante Executivo do Campus Darcy Ribeiro não faz parte do escopo (Seção 6). Os requisitos funcionais, não funcionais e inversos, com seus critérios de aceite, estão detalhados no Documento de Requisitos de Software, que tem este documento como base.

### 1.3 Definições, acrônimos e abreviações

Os termos do domínio abaixo seguem o glossário do projeto (`CONTEXT.md`).

**Siglas e termos do projeto**

- **UnB** — Universidade de Brasília.
- **FCTE** — Faculdade de Ciências e Tecnologias em Engenharia.
- **MDS** — Métodos de Desenvolvimento de Software.
- **RU** — Restaurante Universitário: restaurante oficial da UnB em um campus. É o único tipo de restaurante coberto pelo Bandejão.
- **Bandejão** — nome do site PWA.
- **PWA (Progressive Web App)** — aplicação web que se comporta como aplicativo nativo: pode ser instalada na tela inicial do dispositivo e funcionar parcialmente off-line. É a forma de entrega técnica do Bandejão.
- **MVP (Release 1)** — Produto Mínimo Viável: conjunto de funcionalidades priorizadas para a primeira entrega.
- **Release 2** — segunda entrega do produto, com as funcionalidades de prioridade média (Seção 8).
- **Backlog** — funcionalidades de baixa prioridade, sem release agendada (Seção 8).
- **Épico** — agrupamento de funcionalidades relacionadas que representa uma grande etapa da jornada do usuário: Login, Visualização do Cardápio, Visualização da Fila/Previsão de Pico e Avaliação das Refeições (Seção 5).

**Pessoas**

- **Frequentadores do RU** — todas as pessoas que se alimentam nos RUs da UnB, tenham conta no Bandejão ou não. Inclui a Comunidade, terceirizados e externos.
- **Comunidade** — estudantes (com matrícula de aluno) e professores/servidores (com SIAPE/matrícula funcional) da UnB. É o público que pode ter conta no Bandejão.
- **Visitante** — quem usa o Bandejão sem estar logado, tenha ou não conta. Consulta o cardápio e, na Release 2, a previsão de pico, mas não avalia refeições nem faz check-in. É uma condição de uso, não um tipo de pessoa: quem faz login deixa de ser Visitante.
- **Usuário** — conta no Bandejão, ligada a exatamente uma matrícula ou um SIAPE. É a conta que se autentica, avalia e faz check-in, não a pessoa: quem tem mais de uma vinculação pode ter mais de um Usuário.
- **Tipo de usuário** — vínculo declarado no cadastro: Estudante (matrícula) ou Professor/Servidor (SIAPE/matrícula funcional).
- **Matrícula / SIAPE** — identificador institucional informado no cadastro (SIAPE/matrícula funcional para professores e servidores). É dado privado: nunca é exibido a outros usuários.
- **Apelido** — nome público do usuário, escolhido uma única vez no cadastro e único entre os usuários. É sob ele que as avaliações aparecem.

**Lugares**

- **Campus/Campi** — unidades da UnB com RU: Darcy Ribeiro, Ceilândia, Gama, Planaltina e Fazenda Água Limpa.
- **Restaurante Executivo** — restaurante do Campus Darcy Ribeiro, fora do escopo do Bandejão.

**Cardápio e avaliação**

- **Refeição** — cada serviço de café da manhã, almoço ou jantar de um dia em um campus. É a unidade avaliada pelo usuário (5.13).
- **Categoria** — linha do cardápio de uma refeição (Bebidas, Guarnição, Sopa, Prato principal ovolactovegetariano…).
- **Prato** — cada opção individual dentro de uma categoria. Não é unidade de avaliação.
- **Marcador** — cada um dos 10 ícones da legenda do cardápio oficial: cogumelo, leite e derivados, mel, pimenta, soja, trigo/glúten, amendoim, oleaginosa, ovo e suíno. Sinaliza a presença de um ingrediente ou característica em um prato.
- **Dieta** — uma das três linhas de prato principal do cardápio oficial: padrão, ovolactovegetariano e vegetariano estrito (no café da manhã, o "complemento" equivalente).
- **Avaliação** — nota de 1 a 5 estrelas dada por um usuário a uma refeição, com comentário opcional, exibida com o apelido do autor.

**Fila**

- **Check-in** — registro de presença do usuário no RU de um campus durante uma refeição (Release 2). É a única fonte de dados da fila: não há votação nem sensores.
- **Nível de fila** — classificação em quatro níveis: vazia, curta, moderada e longa. Aplica-se tanto à previsão de pico quanto ao nível agora.
- **Previsão de pico** — níveis de fila esperados em cada faixa de horário de uma refeição, calculados a partir do histórico de check-ins (Release 2).
- **Nível agora** — nível de fila atual da refeição em andamento, calculado a partir dos check-ins recentes (Backlog).

### 1.4 Referências

- FGA-EPS-MDS. *Documento de Visão — Projeto 2018.2-Lino*. Disponível em: https://github.com/fga-eps-mds/2018.2-Lino/blob/master/docs/documento-de-visao.md. Acesso em: 6 set. 2026.
- IBM. *Vision document*. In: IBM Engineering Lifecycle Management Suite — DOORS Next, versão 7.2.0. Disponível em: https://www.ibm.com/docs/pt-br/engineering-lifecycle-management-suite/doors-next/7.2.0?topic=requirements-vision-document. Acesso em: 6 set. 2026.
- Documento de Requisitos de Software — Bandejão, Grupo 6, FCTE/UnB, 2026.
- Decanato de Assuntos Comunitários/UnB. *Resolução nº 002/2024 — Regimento de funcionamento do Restaurante Universitário da Universidade de Brasília*. Disponível em: https://ru.unb.br/images/Artigos/00DRUResolucao2024/SEI_11843224_Resolucao_002.pdf.
- BRASIL. Lei nº 13.709, de 14 de agosto de 2018 (Lei Geral de Proteção de Dados Pessoais — LGPD).

### 1.5 Visão geral

O documento tem 11 seções, seguindo o modelo do IBM DOORS Next: Introdução (1), Posicionamento (2), Partes Interessadas e Usuários (3), Visão Geral do Produto (4), Recursos do Produto (5), Restrições (6), Faixas de Qualidade (7), Precedência e Prioridade (8), Outros Requisitos do Produto (9), Requisitos de Documentação (10) e Apêndice de Atributos do Recurso (11). Os requisitos detalhados estão no Documento de Requisitos de Software.

---

## 2. Posicionamento

### 2.1 Oportunidade de negócio

O cardápio atual do RU da UnB tem formato de planilha para cada refeição servida, o que dificulta a leitura. Além disso, os frequentadores do RU são pessoas atarefadas, com pouco tempo livre para as refeições, e a lotação do RU não segue um padrão fixo: a falta de previsibilidade os prejudica.

O Bandejão propõe resolver isso com:

- visualização fácil e dinâmica do cardápio diário e semanal dos campi, com filtros de marcadores alimentares e de dieta (MVP);
- avaliações das refeições feitas pelos próprios usuários (MVP);
- previsão do horário de pico da fila, em quatro níveis — vazia, curta, moderada e longa —, calculada a partir dos check-ins dos usuários (Release 2);
- nível da fila em tempo real, também a partir de check-ins (Backlog).

Assim, quem frequenta os RUs poderá planejar o que vai comer, de acordo com suas restrições alimentares e preferências e, a partir da Release 2, o horário das refeições. Quem nunca experimentou as refeições poderá ver como as refeições recentes da semana foram avaliadas e o que os colegas comentam sobre a refeição em andamento, para decidir o que provar primeiro.

### 2.2 Descrição do problema

A falta de previsibilidade na lotação do RU e a dificuldade de ler o cardápio atual (2.1) afetam estudantes, professores, servidores e demais frequentadores dos RUs dos campi da UnB. O impacto é:

- tempo perdido em filas nos horários de pico;
- dificuldade de quem tem restrição alimentar ou alergia para saber o que pode comer sem ler o cardápio inteiro;
- ausência de um canal de feedback sobre a qualidade das refeições.

Uma solução bem-sucedida seria uma PWA que centralizasse cardápio, filtros alimentares, avaliação de refeições e informação de fila (Release 2).

### 2.3 Instrução de posição do produto

Para a comunidade da UnB (estudantes de graduação, pós-graduação, mestrado e doutorado, professores e servidores) que frequenta os RUs de qualquer campus e precisa de mais previsibilidade e informação sobre cardápio, qualidade das refeições e fila, o Bandejão é uma plataforma web (PWA) que oferece o cardápio diário/semanal por campus, com filtros de marcadores alimentares e de dieta, as avaliações das refeições feitas pelos próprios usuários e, a partir da Release 2, a previsão do horário de pico da fila. Diferentemente da observação presencial e da informação boca a boca, o Bandejão centraliza esses dados em um único lugar, atualizado e avaliado de forma colaborativa pela Comunidade que frequenta o RU.

O cardápio e a previsão de pico podem ser consultados por qualquer visitante, sem cadastro. A conta, criada com matrícula ou SIAPE/matrícula funcional, é necessária para avaliar refeições e, na Release 2, para fazer check-in. Terceirizados e demais pessoas sem matrícula ou SIAPE usam o Bandejão como visitantes.

---

## 3. Descrições das partes interessadas e do usuário

### 3.1 Demográficos de mercado

O público-alvo são os frequentadores dos RUs da UnB, distribuídos entre os cinco campi com RU: Darcy Ribeiro, Ceilândia, Gama, Planaltina e Fazenda Água Limpa. A Comunidade da UnB (estudantes e professores/servidores) pode criar conta; os demais frequentadores, como terceirizados, usam o sistema como visitantes. O levantamento quantitativo não foi aprofundado nesta fase, conforme orientação da disciplina.

### 3.2 Resumo das partes interessadas

| Nome | Representa | Função |
|---|---|---|
| Equipe de Desenvolvimento de Software | Estudantes da disciplina de MDS | Desenvolve e testa o software descrito neste documento e opera o sistema, incluindo a moderação manual de avaliações e contas |
| Orientadora | Professora da FCTE/UnB, atual professora das disciplinas MDS e Sistemas de Bancos de Dados 2 | Orienta as equipes de desenvolvimento e gestão em eventuais dúvidas |
| Frequentadores do RU | Estudantes, professores, servidores e demais pessoas que frequentam os RUs da UnB | Usuários finais; fonte primária de dados, por meio das avaliações de refeições e (Release 2) dos check-ins |

### 3.3 Resumo do usuário

| Nome | Descrição | Parte interessada |
|---|---|---|
| Estudante | Estudante da UnB em qualquer nível (graduação, pós-graduação, mestrado, doutorado) que se alimenta no RU do seu campus. Cadastra-se com a matrícula de aluno | Frequentadores do RU |
| Professor/Servidor | Professor ou servidor da UnB que se alimenta no RU, geralmente com agenda de compromissos apertada. Cadastra-se com o SIAPE/matrícula funcional | Frequentadores do RU |
| Visitante | Pessoa que usa o Bandejão sem estar logada, tenha ou não conta (inclui terceirizados e demais frequentadores sem matrícula ou SIAPE). Consulta o cardápio e, na Release 2, a previsão de pico; não avalia refeições nem faz check-in | Frequentadores do RU |

Estudante e Professor/Servidor são os tipos de usuário. Cada usuário é uma conta ligada a exatamente uma matrícula ou SIAPE.

### 3.4 Ambiente do usuário

- O pico de uso varia conforme o dia, mas normalmente se concentra por volta das 11h40, com espera na fila que pode passar de 25 minutos, sem contar o tempo do almoço.
- Grande parte dos estudantes mora longe do campus, o que torna o RU sua principal opção viável de alimentação.
- Professores e servidores também costumam morar longe e preferem não se deslocar para comer, mas têm agendas apertadas de aulas e reuniões.
- O sistema é um site (PWA) acessível a visitantes e a usuários logados, pensado primeiro para dispositivos móveis (telas a partir de 360 px) e também utilizável pelo navegador no desktop. O GPS do dispositivo é usado na Release 2 para confirmar o check-in.

### 3.5 Perfis das partes interessadas

A descrição de cada parte interessada está na Seção 3.2.

**Frequentadores do RU**
- **Tipo:** usuário casual a frequente.
- **Responsabilidades:** fornecer avaliações das refeições (quem tem conta) e, na Release 2, check-ins que alimentam a previsão de pico.
- **Critérios de sucesso:** ter mais informação e previsibilidade ao decidir comer no RU.
- **Envolvimento:** uso e alimentação de dados do sistema.

**Equipe de Desenvolvimento de Software**
- **Representantes:** Alana Cristyna Feitosa Dias, Álvaro Bento Moura da Silva, Corina Xavier Carneiro, Cristiano Monteiro Coelho Lacerda Póvoas, Josué Xavier Carneiro e Luís Felipe Albuquerque Fernandes.
- **Tipo:** estudantes da UnB, da disciplina de MDS.
- **Responsabilidades:** especificar, projetar, implementar e documentar o produto; operar o sistema, incluindo a moderação manual de avaliações e contas, a revisão dos parâmetros de configuração e o tratamento de alertas.
- **Critérios de sucesso:** entregar um MVP funcional e bem documentado, com os filtros de marcadores e de dieta e a apresentação refinada do cardápio operando nele, e manter o sistema no ar após o fim da disciplina.
- **Envolvimento:** execução direta do projeto.
- **Entregas:** Documento de Requisitos de Software, Documento de Visão e MVP funcional.
- **Problemas/comentários:** desenvolver o software no tempo estabelecido; inexperiência da equipe com algumas das linguagens de programação escolhidas; a intenção de manter o sistema no ar após a disciplina ainda não tem responsáveis, custo e hospedagem definidos (4.3 e 4.4).

**Orientadora**
- **Representante:** Profa. Carla Silva Rocha Aguiar.
- **Tipo:** orientadora e avaliadora, que dá suporte ao desenvolvimento do Bandejão.
- **Responsabilidades:** avaliar a equipe e orientá-la em eventuais dúvidas.
- **Critérios de sucesso:** observar o sucesso da equipe de desenvolvimento.
- **Envolvimento:** revisão e avaliação das entregas.
- **Entregas:** feedback e nota de avaliação.

### 3.6 Perfis do usuário

A descrição de cada perfil está na Seção 3.3. Estudantes e professores/servidores com conta entregam avaliações por estrelas e comentários sobre as refeições (5.13).

**Estudante**
- **Tipo:** usuário frequente, sensível a preço e tempo.
- **Responsabilidades:** consultar o cardápio, avaliar refeições e (Release 2) fazer check-in.
- **Critérios de sucesso:** saber com antecedência a qualidade da comida e evitar filas longas.
- **Envolvimento:** uso diário/semanal do site; principal fonte de avaliações.
- **Problemas/comentários:** a fila e a falta de informação prejudicam a experiência, já que o RU é a opção mais viável (3.4).

**Professor/Servidor**
- **Tipo:** usuário frequente, sensível a tempo e previsibilidade.
- **Responsabilidades:** consultar o cardápio com antecedência, avaliar refeições e (Release 2) fazer check-in.
- **Critérios de sucesso:** comer rapidamente sem comprometer a agenda de aulas e reuniões.
- **Envolvimento:** uso do site para planejar o horário da refeição.
- **Problemas/comentários:** precisa de previsibilidade e agilidade para conciliar a refeição no RU com uma agenda apertada.

**Visitante**
- **Tipo:** usuário casual, sem conta ou sem login no momento.
- **Responsabilidades:** nenhuma; consulta o cardápio e, na Release 2, a previsão de pico.
- **Critérios de sucesso:** chegar ao cardápio do seu campus com poucos toques, sem precisar se cadastrar.
- **Envolvimento:** consulta ocasional.
- **Problemas/comentários:** sem login, não avalia refeições nem faz check-in; ao tentar, recebe um convite ao cadastro/login. Terceirizados e demais pessoas sem matrícula ou SIAPE só têm acesso ao sistema nesse perfil.

### 3.7 Principais necessidades da parte interessada ou do usuário

| Necessidade | Prioridade | Preocupação | Solução atual | Solução proposta |
|---|---|---|---|---|
| Saber a qualidade da comida antes de decidir comer no RU | Alta | Decisão de última hora, sem informação prévia | Comentário boca a boca e observação presencial | Avaliação da refeição por estrelas (1 a 5) e comentários (5.13). No MVP, o usuário vê as avaliações das refeições recentes da semana vigente e, ao longo do dia, as da refeição em andamento; o histórico de refeições anteriores (5.14) completa a necessidade na Release 2. **Atendida parcialmente no MVP e completa na Release 2** |
| Evitar longas filas no horário de pico (esperas superiores a 25 min) | Alta | Perda significativa de tempo, atraso em compromissos | Observação presencial da fila | Previsão do horário de pico por faixa de horário, calculada a partir de check-ins (5.9 a 5.11, Release 2) e, no Backlog, nível da fila agora (5.12). **Atendida a partir da Release 2: o MVP não inclui recursos de fila** |
| Planejar a refeição com informação antecipada, sem comprometer a agenda | Alta | Falta de previsibilidade sobre tempo de espera e disponibilidade | Cardápio semanal em PDF e em formato de tabela | Cardápio semanal com as refeições de cada dia em abas separadas e formatação dinâmica (5.4, 5.5); na Release 2, a previsão de pico ajuda a escolher o horário (5.11) |
| Saber o que posso comer com minha restrição alimentar ou alergia, sem ler o cardápio inteiro | Alta | Dificuldade de saber o que pode comer sem ler o cardápio inteiro | Leitura manual do cardápio em PDF e em formato de tabela | Filtros de marcadores e de dieta (5.6, 5.7, MVP) e, no Backlog, ícones dos marcadores nos pratos (5.8). O filtro é auxiliar: a ausência de marcador não garante que o prato esteja livre do ingrediente (Seção 6) |

### 3.8 Alternativas e concorrência

| Nome | Principais pontos fortes | Principais pontos fracos |
|---|---|---|
| Site do cardápio do RU da UnB | Disponível com antecedência antes da primeira refeição de uma nova semana; cardápio oficial fornecido pela universidade | Formatação de tabela, que prejudica o entendimento |
| App UnBRU | Visualização dinâmica | Frequentemente fora do ar e com refeições diferentes das do cardápio oficial |

---

## 4. Visão geral do produto

### 4.1 Perspectiva do produto

O Bandejão é um sistema web PWA independente e autocontido. Para funcionar em sua capacidade total, depende de fontes externas e de recursos do dispositivo:

- **Leitura automatizada do PDF do cardápio** publicado no site do RU, fonte externa e não estruturada, fora do controle da equipe (4.3 e Seção 6).
- **Identidade por matrícula/SIAPE:** o cadastro exige matrícula (estudantes) ou SIAPE/matrícula funcional (professores e servidores), mas o sistema valida apenas o formato do identificador: não confere se ele existe, se está ativo nem se pertence a quem o informa. Validação real de identidade junto a sistemas da UnB não está prevista (Seção 6).
- **Localização do dispositivo (Release 2):** o GPS do navegador confirma o check-in no RU do campus; as coordenadas são usadas apenas na conferência e não são armazenadas.

O sistema se comporta "como uma espécie de porta": o visitante pode consultar o cardápio (e, na Release 2, a previsão de pico) sem se cadastrar; o usuário, com conta e login, acessa funcionalidades adicionais: avaliação de refeições e, na Release 2, check-in.

### 4.2 Resumo das capacidades

| Benefício para o usuário | Recursos de suporte | Release |
|---|---|---|
| Não perde tempo decidindo o que comer | Cardápio diário/semanal por campus, refeição e dia, extraído automaticamente do PDF publicado pelo RU e com apresentação refinada (5.4, 5.5) | MVP |
| Encontra o que pode comer com sua restrição alimentar | Filtros de marcadores e de dieta (5.6, 5.7) e, depois, ícones dos marcadores nos pratos (5.8) | MVP / Backlog |
| Sabe como as refeições recentes foram avaliadas | Avaliação por estrelas (1 a 5) e comentários, exibidos com o apelido do autor (5.13); histórico de refeições anteriores (5.14) | MVP / Release 2 |
| Consegue se planejar mesmo sem saber o tamanho exato da fila | Previsão de pico por faixa de horário, a partir de check-ins (5.9 a 5.11) | Release 2 |
| Evita ficar preso em filas longas sem necessidade | Nível da fila agora (5.12) | Backlog |

### 4.3 Suposições e dependências

- **Dependência:** publicação regular do cardápio, em PDF, no site oficial do RU. É uma fonte externa fora do controle da equipe; o risco está descrito na Seção 6.
- **Suposição (MVP):** os usuários avaliam as refeições de boa-fé. Como a matrícula/SIAPE não é validada e não se exige prova de presença para avaliar, a confiabilidade da nota média depende dessa boa-fé (11.4).
- **Suposição (Release 2):** os usuários farão check-in com regularidade. A previsão só é exibida quando há check-ins em 3 dias distintos nas últimas 4 semanas; no início da operação, é esperado que ela apareça como "dados insuficientes".
- **Regra de negócio (Release 2):** a previsão de pico é calculada exclusivamente a partir dos check-ins, sem votação nem sensores (Seção 6).
- **Suposição (operação):** a moderação de avaliações e de contas é manual no início, feita diretamente pela equipe, sem tela administrativa. Há a intenção de automatizá-la após o fim da disciplina.
- **Suposição (continuidade):** há a intenção de manter o sistema no ar após o fim da disciplina. Responsáveis, custo e hospedagem ainda não foram definidos (4.4).

### 4.4 Custo e precificação

O Bandejão é um projeto acadêmico da disciplina de MDS, sem indicação de fins comerciais. Há a intenção de manter o sistema no ar após o fim da disciplina, mas custo, hospedagem e responsáveis pela manutenção ainda não foram definidos (a definir).

### 4.5 Licenciamento e instalação

Por ser PWA, a instalação é opcional e feita pelo próprio usuário, diretamente pelo navegador, a partir da URL do sistema. Licenciamento a definir.

---

## 5. Recursos do produto

A alocação de cada recurso é indicada abaixo (MVP, Release 2 ou Backlog); impacto e esforço estão na Seção 8. Cada recurso indica os requisitos funcionais (RF) correspondentes no Documento de Requisitos.

### Épico 1 — Login

- **5.1** Cadastro por matrícula (estudantes) ou SIAPE/matrícula funcional (professores e servidores), com confirmação de e-mail e login; inclui aviso de privacidade (RF01 a RF03) — MVP
- **5.2** Recuperação de senha por e-mail (RF04) — MVP
- **5.3** Navegação sem login: consulta ao cardápio sem necessidade de cadastro (RF05) — MVP

### Épico 2 — Visualização do Cardápio

- **5.4** Leitura automatizada do PDF do cardápio publicado no site do RU, incluindo marcadores e dietas (RF06) — MVP
- **5.5** Exibição do cardápio por campus, refeição e dia, em abas, com apresentação refinada e voltada a dispositivos móveis (RF07) — MVP
- **5.6** Filtro de marcadores alimentares (RF08) — MVP
- **5.7** Filtro de dieta (RF09) — MVP
- **5.8** Ícones de indicação de marcadores nos pratos (ex.: cogumelo, leite e derivados, mel) (RF10) — Backlog

### Épico 3 — Visualização da Fila e Previsão de Pico

Todos os recursos deste épico pertencem à Release 2 ou ao Backlog. A fila é calculada exclusivamente a partir de check-ins, sem votação nem sensores.

- **5.9** Check-in no RU (RF11) — Release 2
- **5.10** Confirmação do check-in por meio do GPS do dispositivo (RF12) — Release 2
- **5.11** Previsão de horário de pico por faixa de horário, em quatro níveis (RF13) — Release 2
- **5.12** Nível da fila agora, com base nos check-ins recentes (RF14) — Backlog

### Épico 4 — Avaliação das Refeições

- **5.13** Avaliação da refeição como um todo, por estrelas (1 a 5), com caixa de comentário opcional para comentar pratos ou ingredientes específicos; a avaliação é exibida com o apelido do autor (RF15) — MVP
- **5.14** Tela com o histórico de refeições de semanas anteriores, com cardápio, nota média e comentários (RF16) — Release 2

### Transversal

- **5.15** Design do site (identidade visual) — distribuição das informações e cores utilizadas (RF17) — MVP

---

## 6. Restrições

- **Cardápio em PDF:** o cardápio vem de um PDF publicado pelo próprio RU, fonte não estruturada e fora do controle da equipe. Mudanças no formato do arquivo podem comprometer a leitura automatizada (4.3).
- **Fila sem sensor e sem votação:** a previsão de pico (Release 2) não usa sensor físico, votação nem fonte de dados independente; depende inteiramente dos check-ins dos usuários cadastrados (4.3).
- **Identidade não validada:** o cadastro exige matrícula ou SIAPE/matrícula funcional em formato válido, mas o sistema não valida a existência, a situação ativa nem a titularidade do identificador; não há validação real prevista. Terceirizados e demais pessoas sem matrícula ou SIAPE não podem se cadastrar e usam o sistema como visitantes.
- **Filtros auxiliares:** os filtros de marcadores e de dieta se baseiam no cardápio oficial, que está sujeito a alteração. A ausência de marcador não garante que o prato esteja livre do ingrediente, e o cardápio oficial não marca peixe nem frutos do mar.
- **Escopo:** restrito às informações dos RUs dos campi da UnB, sem abranger outros restaurantes ou cantinas. O Restaurante Executivo do Campus Darcy Ribeiro está excluído do escopo.

---

## 7. Faixas de qualidade

Os requisitos não funcionais estão detalhados no Documento de Requisitos (RNF01 a RNF08). As metas principais, calibradas para serem verificáveis em operação e alcançáveis por uma equipe iniciante em projetos de maior porte, são:

| Categoria | Meta | Requisito |
|---|---|---|
| Desempenho (Métrica de Eficiência) | Visualização do cardápio (e, na Release 2, da previsão de pico) respondida em até 3 segundos em pelo menos 95% das requisições, com até 2.000 usuários simultâneos | RNF01 |
| Disponibilidade e confiabilidade | Pelo menos 95% do tempo durante o horário de funcionamento dos RUs (7h às 19h30), nos dias com refeição servida; se a leitura do PDF falhar, o sistema continua exibindo o último cardápio lido com sucesso | RNF02 |
| Usabilidade | Cardápio de um campus em no máximo 3 interações na primeira visita; interface funcional em telas a partir de 360 px | RNF03 |
| Manutenibilidade | Cobertura de testes automatizados de no mínimo 60% nos módulos críticos | RNF06 |

Os demais requisitos não funcionais — segurança (RNF04), portabilidade e compatibilidade como PWA (RNF05), privacidade e proteção de dados pessoais (RNF07) e rastreabilidade e moderação (RNF08) — estão descritos no Documento de Requisitos.

---

## 8. Precedência e prioridade

A priorização parte da Matriz de Impacto x Esforço elaborada pela equipe (11.8). O refinamento posterior, feito na elaboração do Documento de Requisitos, reclassificou alguns itens; nesses casos, a coluna "Motivo" indica "decisão de projeto". As prioridades equivalem às do Documento de Requisitos: **Alta** = Essencial (MVP), **Média** = Importante (Release 2) e **Baixa** = Desejável (Backlog).

O MVP inclui, além do cadastro/login, da leitura do cardápio e da avaliação das refeições, os filtros de marcadores e de dieta e a apresentação refinada do cardápio, que devem estar operando nele.

| Item (Seção 5) | Alocação | Prioridade | Quadrante original da matriz | Motivo |
|---|---|---|---|---|
| 5.1 Cadastro, confirmação de e-mail e login | MVP | Alta | Alto impacto / Baixo esforço | Matriz |
| 5.2 Recuperação de senha | MVP | Alta | — | Decisão de projeto (item novo) |
| 5.3 Navegação sem login | MVP | Alta | — | Decisão de projeto (formalizada como recurso) |
| 5.4 Leitura automatizada do PDF | MVP | Alta | Alto impacto / Baixo esforço | Matriz |
| 5.5 Exibição por campus, refeição e dia, com apresentação refinada | MVP | Alta | Alto impacto / Baixo esforço (exibição); Alto impacto / Alto esforço (design refinado) | Matriz; decisão de projeto (apresentação refinada já no MVP) |
| 5.6 Filtro de marcadores | MVP | Alta | Alto impacto / Baixo esforço | Matriz |
| 5.7 Filtro de dieta | MVP | Alta | Alto impacto / Baixo esforço | Matriz |
| 5.13 Avaliação por estrelas e comentário | MVP | Alta | Alto impacto / Baixo esforço | Matriz |
| 5.15 Design do site (identidade visual) | MVP | Alta | Alto impacto / Baixo esforço | Matriz |
| 5.9 Check-in no RU | Release 2 | Média | Alto impacto / Alto esforço | Matriz |
| 5.10 Confirmação do check-in por GPS | Release 2 | Média | Alto impacto / Alto esforço (uso do GPS); Baixo impacto / Baixo esforço (confirmação do check-in) | Matriz; decisão de projeto (GPS passa a ser parte obrigatória do check-in) |
| 5.11 Previsão de pico | Release 2 | Média | Alto impacto / Baixo esforço (versão estática) | Decisão de projeto (a previsão depende do histórico de check-ins; não há versão estática) |
| 5.14 Histórico de refeições anteriores | Release 2 | Média | Alto impacto / Baixo esforço | Decisão de projeto (o MVP exibe apenas a semana vigente) |
| 5.8 Ícones de marcadores nos pratos | Backlog | Baixa | Baixo impacto / Baixo esforço | Matriz |
| 5.12 Nível da fila agora | Backlog | Baixa | Alto impacto / Alto esforço (nível em tempo real por votação) | Decisão de projeto (depende da adesão ao check-in; ver 11.4) |

Dois recursos da versão anterior deste documento foram retirados: o "login validado por matrícula/SIAPE", porque não há validação real prevista (4.1), e o "sistema de monitoramento/informativo da fila", absorvido pelos recursos 5.11 e 5.12.

---

## 9. Outros requisitos do produto

### 9.1 Padrões aplicáveis

O tratamento dos dados pessoais (matrícula/SIAPE, e-mail e apelido) deve observar a Lei Geral de Proteção de Dados (Lei nº 13.709/2018), com aviso de privacidade no cadastro (RNF07). O site deve divulgar um canal de contato para reclamações (RNF08). A Resolução nº 002/2024, que regula o funcionamento do RU, é referência do domínio (1.4). Demais padrões não foram decididos nesta fase.

### 9.2 Requisitos de sistema

O requisito de sistema definido é a entrega como PWA, que exige navegador compatível (instalação na tela inicial, service workers), em desktop e dispositivos móveis (RNF05). Stack e hospedagem ainda a definir.

### 9.3 Requisitos de desempenho

Os requisitos de desempenho estão na Seção 7 (RNF01) e detalhados no Documento de Requisitos.

### 9.4 Requisitos ambientais

Não aplicável: trata-se de uma aplicação web acessada via navegador, sem requisitos ambientais de hardware.

---

## 10. Requisitos de documentação

### 10.1 Notas sobre a liberação, arquivo README

Não desenvolvido nesta fase.

### 10.2 Ajuda on-line

Não desenvolvido nesta fase.

### 10.3 Guias de instalação

A instalação é opcional e feita pelo navegador (4.5). Um guia passo a passo por navegador e sistema operacional não foi desenvolvido nesta fase.

### 10.4 Rotulagem e empacotamento

Não aplicável nesta fase.

---

## 11. Apêndice 1 — Atributos do recurso

### 11.1 Status

- **MVP:** Aprovado (selecionado pela Matriz de Impacto x Esforço para a primeira entrega e refinado no Documento de Requisitos).
- **Release 2 e Backlog:** Proposto.

### 11.2 Benefício

- **Alto impacto:** importante/crítico para a experiência do usuário.
- **Baixo impacto:** útil, sem impacto significativo caso não seja entregue.

### 11.3 Esforço

Definido pela Matriz de Impacto x Esforço: baixo ou alto esforço por item (Seção 8). Não há estimativas numéricas de tempo nem pontos de história.

### 11.4 Risco

Os riscos e as limitações conhecidos estão na Seção 5 do Documento de Requisitos (L01 a L09). Os que mais afetam a visão do produto são:

- **Dependência do PDF externo:** mudanças no formato do arquivo podem comprometer a leitura do cardápio (Seção 6).
- **Identidade não validada e contas múltiplas (L01, L02):** alguém pode cadastrar a matrícula de outra pessoa, uma matrícula inventada de formato válido ou várias contas. Isso afeta a confiabilidade da nota média já no MVP.
- **Avaliação sem prova de presença (L06):** no MVP, qualquer usuário autenticado pode avaliar uma refeição do dia depois que ela começou, sem comprovar que comeu.
- **Baixa adesão ao check-in (L08), risco da Release 2:** com poucos check-ins, a previsão de pico é pouco representativa.

### 11.5 Estabilidade

Não decidido até este momento do projeto.

### 11.6 Liberação de destino

Conforme a Seção 8: v1.0 (MVP, Release 1), Release 2 e Backlog (futuro, não agendado).

### 11.7 Designado para

Não há atribuição de responsáveis por funcionalidade até este ponto do projeto.

### 11.8 Motivo

A priorização inicial de prioridade, impacto e esforço tem como base a Matriz de Impacto x Esforço (*Impact Effort Matrix*), elaborada pela equipe na etapa de priorização, na seção de Requisitos do board do projeto. O refinamento posterior, feito durante a elaboração do Documento de Requisitos, reclassificou alguns itens; cada caso está identificado como "decisão de projeto" na Seção 8.
