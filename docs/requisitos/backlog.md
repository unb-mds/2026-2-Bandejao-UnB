# Backlog — Bandejão

> Gerado a partir do **Documento de Requisitos de Software** (Grupo 6, MDS/FCTE/UnB), que por sua vez detalha o Documento de Visão original.

## Como ler este documento

- **ID**: cada História de Usuário recebe um ID `US-XX`, alinhado numericamente com o Requisito Funcional que a origina (`ref. RFxx`) — ou seja, `US-01` implementa `RF01`, `US-02` implementa `RF02`, e assim por diante. Mapeamento 1:1 entre RF e US.
- **Épico**: Login, Visualização do Cardápio, Visualização da Fila/Previsão de Pico, Avaliação das Refeições, ou a seção separada "Itens Transversais".
- **Release**: MVP (Release 1), Release 2, ou Backlog do produto (sem data prevista) — herdado diretamente do documento de requisitos (Seção 1.3: Essencial → MVP, Importante → Release 2, Desejável → Backlog).
- **Prioridade**: Alta (Essencial), Média (Importante) ou Baixa (Desejável) — mesma tradução usada no backlog anterior.
- **Esforço**: herdado da Matriz de Impacto x Esforço do Documento de Visão (Seção 8) para os itens já existentes no backlog anterior. Para o item novo introduzido pelo documento de requisitos (US-03 / RF04), o esforço é uma estimativa da equipe, sinalizada como tal — não há estimativa numérica (pontos de história) para nenhum item; isso fica para a sessão de planning poker.
- **Critérios de Aceite**: formato Gherkin (Dado/Quando/Então), derivados dos critérios de aceite em prosa do documento de requisitos.
- **Labels sugeridas**: para uso direto na criação da issue no GitHub.
- **Requisitos Não Funcionais e Inversos**: não viram Histórias de Usuário (não são testáveis no formato "Como/quero/para que" de um usuário final). Estão consolidados em seção própria ao final, com referência às histórias que afetam.

---

## Épico 1: Login

### Release: MVP

#### US-01 (ref. RF01) — Cadastro de usuário

**Prioridade:** Alta | **Esforço:** Baixo
**Labels sugeridas:** `epico:login`, `release:mvp`, `prioridade:alta`

**História:** Como usuário do RU (estudante, professor ou servidor), quero criar uma conta informando nome, e-mail e senha, para que eu possa acessar funcionalidades restritas do sistema, como avaliação de refeições.

**Critérios de Aceite:**
- Dado que informo um e-mail já cadastrado na base, quando tento me cadastrar, então o sistema rejeita o cadastro e exibe uma mensagem de erro específica.
- Dado que informo uma senha com menos de 8 caracteres, quando tento me cadastrar, então o sistema rejeita o cadastro.
- Dado que preencho nome, e-mail e senha válidos, quando confirmo o cadastro, então minha conta é criada e sou redirecionado à tela de login ou autenticado automaticamente.

#### US-02 (ref. RF02) — Login de usuário cadastrado

**Prioridade:** Alta | **Esforço:** Baixo
**Labels sugeridas:** `epico:login`, `release:mvp`, `prioridade:alta`

**História:** Como usuário previamente cadastrado, quero me autenticar informando e-mail e senha, para que eu acesse funcionalidades restritas, como a avaliação de refeições e, futuramente, a votação de fila.

**Critérios de Aceite:**
- Dado que informo credenciais corretas, quando faço login, então acesso o sistema autenticado e sou redirecionado à página inicial.
- Dado que informo credenciais incorretas, quando tento logar, então recebo uma mensagem de erro genérica, sem indicação de que o e-mail existe ou não na base.
- Dado que erro a senha 5 vezes seguidas para o mesmo e-mail em um intervalo de 10 minutos, quando faço uma nova tentativa, então o sistema bloqueia novas tentativas por 10 minutos.

#### US-03 (ref. RF04) — Navegação sem autenticação

**Prioridade:** Alta | **Esforço:** Baixo *(estimativa da equipe — item novo no documento de requisitos, sem esforço definido na Matriz de Impacto x Esforço original)*
**Labels sugeridas:** `epico:login`, `release:mvp`, `prioridade:alta`

**História:** Como visitante do site (sem cadastro ou login), quero consultar o cardápio diário/semanal dos campi, para que eu possa planejar minha refeição com informação antecipada mesmo sem ter conta no sistema.

**Critérios de Aceite:**
- Dado que não estou autenticado, quando acesso a URL raiz do sistema, então consigo visualizar o cardápio sem necessidade de cadastro ou login.
- Dado que não estou autenticado, quando tento avaliar uma refeição ou votar no nível da fila, então o sistema exibe um convite ao cadastro/login, em vez de um erro genérico.

### Release: Release 2

#### US-04 (ref. RF03) — Login validado por matrícula/SIAPE

**Prioridade:** Média | **Esforço:** Alto
**Labels sugeridas:** `epico:login`, `release:release-2`, `prioridade:media`

**História:** Como estudante ou professor/servidor da UnB, quero validar meu login pela matrícula (estudante) ou SIAPE/matrícula funcional (servidor), para que meu voto no sistema de fila tenha validade e o cálculo colaborativo seja confiável.

**Critérios de Aceite:**
- Dado que informo um número de matrícula ou SIAPE em formato inválido, quando tento validar, então o sistema recusa o cadastro/login e explica o motivo.
- Dado que meu login foi validado por matrícula/SIAPE, quando tento votar no nível da fila, então sou habilitado a votar; sem essa validação, não sou.

---

## Épico 2: Visualização do Cardápio

### Release: MVP

#### US-05 (ref. RF05) — Leitura automatizada do PDF do cardápio

**Prioridade:** Alta | **Esforço:** Baixo
**Labels sugeridas:** `epico:cardapio`, `release:mvp`, `prioridade:alta`

**História:** Como usuário do Bandejão, quero que o cardápio seja extraído automaticamente do PDF publicado pelo RU, para que eu não precise consultar o PDF original, de leitura difícil.

**Critérios de Aceite:**
- Dado que o RU publica um novo PDF de cardápio, quando o sistema realiza a leitura automatizada, então o cardápio exibido é atualizado em até 24 horas.
- Dado que a leitura automatizada falha (ex.: mudança no formato do arquivo), quando isso ocorre, então o sistema mantém em exibição o último cardápio lido com sucesso e registra um alerta para a equipe, em vez de exibir uma página vazia ou quebrada.

#### US-06 (ref. RF06) — Exibição do cardápio por dia e por campus

**Prioridade:** Alta | **Esforço:** Baixo
**Labels sugeridas:** `epico:cardapio`, `release:mvp`, `prioridade:alta`

**História:** Como usuário do Bandejão, quero visualizar o cardápio dividido por dia e por campus, para que eu encontre rapidamente a refeição do meu campus no dia desejado.

**Critérios de Aceite:**
- Dado que estou na página do cardápio, quando seleciono um campus entre pelo menos dois disponíveis (ex.: Darcy Ribeiro, Gama), então vejo o cardápio correspondente àquele campus.
- Dado que selecionei um campus, quando escolho um dia da semana corrente, então vejo as refeições daquele dia sem recarregar a página inteira (navegação em abas ou equivalente).

#### US-07 (ref. RF07) — Filtro de restrições alimentares e alergias

**Prioridade:** Alta | **Esforço:** Baixo
**Labels sugeridas:** `epico:cardapio`, `release:mvp`, `prioridade:alta`

**História:** Como usuário com restrição alimentar ou alergia, quero filtrar o cardápio por alérgenos, para que eu veja apenas pratos seguros para mim sem precisar ler o cardápio inteiro.

**Critérios de Aceite:**
- Dado que estou visualizando o cardápio, quando ativo um filtro de restrição/alergia (ex.: lactose, glúten, frutos do mar), então os pratos correspondentes deixam de aparecer na listagem padrão ou passam a exibir uma marcação visual explícita de alerta.
- Dado que ativei um filtro, quando navego entre dias ou campi na mesma sessão, então o filtro selecionado permanece ativo.

### Release: Release 2

#### US-08 (ref. RF09) — Cardápio com visualização de design refinado

**Prioridade:** Média | **Esforço:** Alto
**Labels sugeridas:** `epico:cardapio`, `release:release-2`, `prioridade:media`

**História:** Como usuário do Bandejão, quero visualizar o cardápio num formato mais próximo de um cardápio tradicional, para que a leitura seja mais agradável do que uma listagem de texto extraída do PDF.

**Critérios de Aceite:**
- Dado que o cardápio foi extraído do PDF, quando exibido na página, então segue um layout com hierarquia visual clara entre categorias de prato (ex.: prato principal, acompanhamento, sobremesa), e não uma listagem simples de texto extraído.

### Release: Backlog do produto

#### US-09 (ref. RF08) — Ícones de indicação de alérgenos

**Prioridade:** Baixa | **Esforço:** Baixo
**Labels sugeridas:** `epico:cardapio`, `release:backlog`, `prioridade:baixa`

**História:** Como usuário do Bandejão, quero ver ícones indicando os alérgenos de cada prato, para que eu identifique rapidamente riscos sem precisar abrir um filtro.

**Critérios de Aceite:**
- Dado que um prato contém um alérgeno cadastrado (ex.: cogumelo, leite e derivados, mel), quando o prato é exibido no cardápio, então o ícone correspondente aparece automaticamente ao lado do nome do prato, sem necessidade de hover ou clique.
- Dado que um prato não contém alérgenos mapeados, quando é exibido, então nenhum ícone de alérgeno aparece.

---

## Épico 3: Visualização da Fila/Previsão de Pico

### Release: MVP

#### US-10 (ref. RF10) — Previsão de horário de pico (simples/estática)

**Prioridade:** Alta | **Esforço:** Baixo
**Labels sugeridas:** `epico:fila`, `release:mvp`, `prioridade:alta`

**História:** Como usuário do RU, quero ver uma previsão simples do horário de pico, para que eu possa planejar quando ir ao RU e evitar filas longas, mesmo sem dados de votação em tempo real.

**Critérios de Aceite:**
- Dado que acesso a tela de fila e nenhum voto foi registrado ainda, quando a previsão é exibida, então vejo ao menos uma faixa de horário identificada como "horário de pico esperado" para o dia corrente, baseada em padrões conhecidos de uso.
- Dado que não há dados de votação em tempo real disponíveis, quando a previsão é exibida, então ela continua funcionando com a estimativa estática, sem depender da Release 2.

### Release: Release 2

#### US-11 (ref. RF11) — Nível da fila em tempo real por votação

**Prioridade:** Média | **Esforço:** Alto
**Labels sugeridas:** `epico:fila`, `release:release-2`, `prioridade:media`

**História:** Como usuário cadastrado e validado do RU, quero ver e votar no nível atual da fila (vazia, curta, moderada, longa), para que outros usuários tenham uma estimativa colaborativa e atualizada da lotação.

**Critérios de Aceite:**
- Dado que sou um usuário validado, quando registro meu voto sobre o nível da fila, então ele é refletido no nível de fila exibido em até 1 minuto.
- Dado que meu voto tem mais de 15 minutos, quando o sistema recalcula o nível da fila, então esse voto expirado deixa de contar.
- Dado que votei há menos de 15 minutos, quando tento votar novamente, então o sistema rejeita a nova tentativa e informa o tempo restante do cooldown.

#### US-12 (ref. RF12) — Sistema de monitoramento/informativo da fila

**Prioridade:** Média | **Esforço:** Alto
**Labels sugeridas:** `epico:fila`, `release:release-2`, `prioridade:media`

**História:** Como usuário do RU, quero um painel informativo consolidado sobre a fila, para que eu entenda a situação atual e sua evolução ao longo do dia, sem precisar interpretar votos individuais.

**Critérios de Aceite:**
- Dado que existem votos válidos registrados ao longo do dia, quando acesso o painel da fila, então vejo, na mesma tela, o nível atual e um histórico simplificado (gráfico ou lista) do nível registrado nas últimas horas de funcionamento do RU.
- Dado que não há votos válidos recentes, quando acesso o painel, então o sistema indica que a informação está desatualizada ou indisponível, em vez de exibir um dado incorreto.

#### US-13 (ref. RF13) — Check-in no RU

**Prioridade:** Média | **Esforço:** Alto
**Labels sugeridas:** `epico:fila`, `release:release-2`, `prioridade:media`

**História:** Como usuário cadastrado do RU, quero fazer check-in ao chegar no restaurante, para que minha presença contribua para a precisão do sistema de fila.

**Critérios de Aceite:**
- Dado que estou autenticado, quando realizo o check-in pela interface do sistema, então minha presença é registrada e associada ao meu histórico de uso.
- Dado que já fiz check-in recentemente, quando tento fazer novamente, então o sistema evita o registro duplicado.

#### US-14 (ref. RF14) — Acesso ao GPS para confirmar voto

**Prioridade:** Média | **Esforço:** Alto
**Labels sugeridas:** `epico:fila`, `release:release-2`, `prioridade:media`

**História:** Como usuário cadastrado do RU, quero que o sistema confirme minha localização via GPS ao votar no nível da fila, para que apenas votos de pessoas realmente presentes no RU sejam contabilizados.

**Critérios de Aceite:**
- Dado que autorizo o acesso ao GPS, quando tento votar no nível da fila, então o sistema só aceita o voto se minha localização estiver dentro de um raio pré-definido do RU votado.
- Dado que minha localização está fora do raio esperado, quando tento votar, então o sistema informa que o voto não pôde ser confirmado por localização.
- Dado que ainda não votei nenhuma vez, quando acesso a funcionalidade de voto pela primeira vez, então sou informado sobre a necessidade de conceder permissão de localização ao navegador antes de votar.

### Release: Backlog do produto

#### US-15 (ref. RF15) — Confirmação de check-in por GPS

**Prioridade:** Baixa | **Esforço:** Baixo
**Labels sugeridas:** `epico:fila`, `release:backlog`, `prioridade:baixa`

**História:** Como usuário cadastrado do RU, quero que meu check-in seja confirmado automaticamente pelo GPS, para que eu não precise confirmar manualmente que estou no RU.

**Critérios de Aceite:**
- Dado que estou dentro do raio pré-definido do RU, quando realizo o check-in, então ele é marcado como "confirmado por localização" automaticamente, sem etapa manual adicional.
- Dado que estou fora do raio pré-definido do RU, quando realizo o check-in, então ele é marcado como "não confirmado".

---

## Épico 4: Avaliação das Refeições

### Release: MVP

#### US-16 (ref. RF16) — Avaliação de refeições por estrelas e comentários

**Prioridade:** Alta | **Esforço:** Baixo
**Labels sugeridas:** `epico:avaliacao`, `release:mvp`, `prioridade:alta`

**História:** Como usuário cadastrado do RU, quero avaliar as refeições do dia com estrelas (1 a 5) e comentários, para que eu compartilhe minha opinião e ajude outros usuários a decidir se vale a pena comer no RU naquele dia.

**Critérios de Aceite:**
- Dado que estou autenticado, quando avalio um prato do cardápio do dia com uma nota de 1 a 5 estrelas e, opcionalmente, um comentário, então a avaliação é registrada associada ao meu nome de usuário.
- Dado que minha avaliação foi registrada, quando qualquer visitante consulta aquele prato, então vê a nota e o comentário associados ao meu nome de usuário.
- Dado que já avaliei um prato hoje, quando tento avaliá-lo novamente no mesmo dia, então minha avaliação anterior é editada em vez de uma nova ser criada.
- Dado que não estou autenticado, quando tento avaliar uma refeição, então o sistema solicita que eu faça login antes.

#### US-17 (ref. RF17) — Menu com avaliações salvas de pratos anteriores

**Prioridade:** Alta | **Esforço:** Baixo
**Labels sugeridas:** `epico:avaliacao`, `release:mvp`, `prioridade:alta`

**História:** Como usuário do Bandejão, quero consultar um menu separado com as avaliações salvas de pratos já servidos anteriormente, para que eu saiba, antes de provar, quais pratos costumam ser mais bem avaliados.

**Critérios de Aceite:**
- Dado que um prato já foi servido e avaliado anteriormente, quando o busco em uma tela dedicada de avaliações salvas, então vejo a nota média e os comentários históricos daquele prato, mesmo fora do dia em que foi avaliado.
- Dado que um prato nunca foi servido/avaliado antes, quando o busco nesse menu, então o sistema indica que ainda não há avaliações disponíveis.

---

## Itens Transversais

> Não pertencem a um épico específico do produto — perpassam toda a experiência do usuário.

### Release: MVP

#### US-18 (ref. RF18) — Design do site

**Prioridade:** Alta | **Esforço:** Baixo
**Labels sugeridas:** `epico:transversal`, `release:mvp`, `prioridade:alta`

**História:** Como usuário do Bandejão, quero uma interface com distribuição clara de informações e uso consistente de cores, para que a navegação pelo cardápio, fila e avaliações seja intuitiva.

**Critérios de Aceite:**
- Dado que acesso qualquer página do Bandejão, quando a página carrega, então os elementos seguem a mesma paleta de cores e os mesmos padrões de tipografia e espaçamento das demais páginas.
- Dado que uso o site em desktop ou em dispositivo móvel (PWA), quando navego pelas funcionalidades, então a interface se mantém legível e utilizável em ambos os contextos.

---

## Requisitos Não Funcionais e Requisitos Inversos

> Introduzidos pelo Documento de Requisitos (Seções 3 e 4). Não viram Histórias de Usuário — são transversais e não são testáveis no formato "Como/quero/para que" de um usuário final — mas afetam diretamente a implementação e os critérios de "pronto" das histórias acima. Sugestão de label comum: `tipo:rnf` ou `tipo:ri`, combinada à label de épico afetado.

### Requisitos Não Funcionais

| ID | Categoria | Descrição resumida | Histórias afetadas | Release |
|---|---|---|---|---|
| **RNF01** | Desempenho | Resposta às requisições de cardápio em até 3s, com até 300 usuários simultâneos, em 95% das requisições. | US-05, US-06, US-07 | MVP |
| **RNF02** | Disponibilidade e confiabilidade | Sistema disponível ≥95% do tempo em horário de funcionamento dos RUs; falha na leitura do PDF não deve derrubar o site. | US-05 | MVP |
| **RNF03** | Usabilidade | Cardápio do dia acessível em no máximo 3 interações a partir da home, sem login; interface funcional a partir de 360px de largura. | US-03, US-05, US-06, US-18 | MVP |
| **RNF04** | Segurança | Senhas com hash (nunca texto plano); comunicação via HTTPS; sanitização de entradas contra XSS e SQL Injection. | US-01, US-02, US-16 | MVP |
| **RNF05** | Portabilidade e compatibilidade | PWA funcional nas duas versões mais recentes de Chrome, Firefox, Edge e Safari; instalável via manifest válido e service worker. | US-18 | MVP |
| **RNF06** | Manutenibilidade | Cobertura de testes automatizados ≥60% nos módulos críticos (cardápio, autenticação, avaliação e, na Release 2, fila); módulos isolados entre si. | US-01, US-02, US-05, US-11, US-16 | MVP / Release 2 |

### Requisitos Inversos

| ID | Descrição | Histórias afetadas |
|---|---|---|
| **RI01** | Não permitir que usuários não autenticados registrem avaliações de refeições ou votos de nível de fila. | US-03, US-11, US-16 |
| **RI02** | Não exibir cardápios ou informações de restaurantes/cantinas que não sejam os RUs oficiais da UnB. | US-05, US-06 |
| **RI03** | Não computar mais de um voto de fila do mesmo usuário dentro da janela de cooldown de 15 minutos. | US-11 |
| **RI04** | Não armazenar senhas de usuário em texto plano, sob nenhuma circunstância. | US-01, US-02 |
| **RI05** | Não depender de sensores físicos (câmeras, contadores de pessoas) para estimar o nível de fila — apenas votação colaborativa. | US-11, US-13, US-14 |
| **RI06** | Não bloquear o acesso à visualização do cardápio para usuários que optem por não se cadastrar. | US-03 |
