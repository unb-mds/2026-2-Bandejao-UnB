# Documento de Requisitos de Software — Bandejão

**Universidade de Brasília — Faculdade de Ciências e Tecnologias em Engenharia (FCTE)**
**Disciplina:** Métodos de Desenvolvimento de Software (MDS)
**Grupo 6** · **Orientadora:** Profa. Carla Silva Rocha Aguiar
**Brasília, 2026**

> Este documento tem como base o Documento de Visão do projeto Bandejão (Grupo 6, 2026) e detalha, a partir dele, os requisitos funcionais, não funcionais e inversos do sistema, organizados por épico e com rastreabilidade até as necessidades das partes interessadas.

---

## 1. Introdução

### 1.1 Propósito

Este documento especifica, de forma detalhada e verificável, os requisitos funcionais (RF), não funcionais (RNF) e inversos (RI) do sistema Bandejão, servindo como referência para o desenvolvimento, teste e avaliação do produto ao longo do projeto.

### 1.2 Escopo

O documento cobre a totalidade das funcionalidades do produto, independentemente da release em que estão alocadas — MVP, Release 2 ou Backlog do produto —, permitindo o planejamento e a rastreabilidade completa do sistema desde a primeira entrega até a visão de longo prazo do produto.

O escopo restringe-se aos restaurantes universitários (RU) dos campi da UnB. O Restaurante Executivo do Campus Darcy Ribeiro não faz parte do escopo (RI08).

### 1.3 Convenções deste documento

| Elemento | Convenção |
|---|---|
| ID de requisito funcional | `RF` + dois dígitos sequenciais, únicos em todo o documento (ex.: RF01, RF02, ...) |
| ID de requisito não funcional | `RNF` + dois dígitos sequenciais (ex.: RNF01, RNF02, ...) |
| ID de requisito inverso | `RI` + dois dígitos sequenciais (ex.: RI01, RI02, ...) |
| ID de limitação ou risco | `L` + dois dígitos sequenciais (ex.: L01, L02, ...) |
| Release | MVP, Release 2 ou Backlog, conforme a alocação de cada requisito neste documento |
| Prioridade | Derivada da alocação de release: **Essencial** (MVP), **Importante** (Release 2), **Desejável** (Backlog) |
| Origem | Épico e necessidade da parte interessada que o requisito atende. Quando o requisito resulta de uma decisão do grupo durante o refinamento do projeto, consta "decisão de projeto" |
| Parâmetros configuráveis | Valores ajustáveis sem alterar o requisito (horários, raios, limiares) estão no Anexo A |

### 1.4 Documentos de referência

- Documento de Visão — Bandejão, Grupo 6, FCTE/UnB, 2026.
- FGA-EPS-MDS. *Documento de Visão — Projeto 2018.2-Lino*. Disponível em: https://github.com/fga-eps-mds/2018.2-Lino/blob/master/docs/documento-de-visao.md.
- Decanato de Assuntos Comunitários/UnB. *Resolução nº 002/2024 — Regimento de funcionamento do Restaurante Universitário da Universidade de Brasília*. Disponível em: https://ru.unb.br/images/Artigos/00DRUResolucao2024/SEI_11843224_Resolucao_002.pdf.
- Restaurante Universitário da UnB. *Cardápio semanal — Campus Gama, 21/9 a 27/9/2026* (exemplo do arquivo de cardápio lido pelo sistema).
- ADR 0001 — Escolha da stack de backend (`docs/adr/0001-escolha-stack-backend.md`).
- ADR 0002 — Matrícula e apelido extraídos do e-mail institucional (`docs/adr/0002-matricula-apelido-extraidos-do-email.md`).

### 1.5 Termos

| Termo | Significado |
|---|---|
| **Visitante** | Pessoa que usa o Bandejão sem estar logada, tenha ou não conta. Consulta o cardápio e, na Release 2, a previsão de pico, mas não avalia refeições nem faz check-in. É uma condição de uso, não um tipo de pessoa: quem faz login deixa de ser visitante |
| **Usuário** | Conta no Bandejão, ligada a exatamente uma matrícula ou um SIAPE. É a conta que se autentica, avalia e faz check-in, não a pessoa: quem tem mais de uma vinculação pode ter mais de um usuário |
| **Tipo de usuário** | Vínculo declarado no cadastro: Estudante (matrícula) ou Professor/Servidor (SIAPE/matrícula funcional). É um único tipo interno: "Professor" e "Servidor" são duas opções na tela de cadastro que levam ao mesmo fluxo |
| **Matrícula / SIAPE** | Identificador associado à conta. Para Estudante, extraído do e-mail institucional; para Professor/Servidor, informado diretamente no cadastro. O sistema confere apenas o formato; não confere existência, situação ativa nem titularidade. É dado privado |
| **E-mail institucional** | E-mail da UnB informado no cadastro (`matricula@aluno.unb.br` para estudantes, `@unb.br` para professores/servidores), único canal de confirmação de cadastro e de recuperação de senha; fonte da Matrícula (estudantes) e do Apelido (professores/servidores) |
| **Apelido** | Nome público, escolhido uma única vez no cadastro e único entre os usuários, sob o qual as avaliações são exibidas. Escolhido manualmente por Estudante; extraído do e-mail institucional para Professor/Servidor |
| **Refeição** | Cada serviço de café da manhã, almoço ou jantar de um dia em um campus. É a unidade avaliada |
| **Categoria** | Linha do cardápio de uma refeição (Bebidas, Guarnição, Sopa, Prato principal ovolactovegetariano…) |
| **Prato** | Cada opção individual dentro de uma categoria. "ou/OU" separa pratos; "/" não separa. Não recebe nota própria |
| **Marcador** | Cada um dos 10 ícones da legenda do cardápio oficial: cogumelo, leite e derivados, mel, pimenta, soja, trigo/glúten, amendoim, oleaginosa, ovo e suíno |
| **Dieta** | Uma das três linhas de prato principal do cardápio oficial: padrão, ovolactovegetariano e vegetariano estrito (no café da manhã, o "complemento" equivalente) |
| **Avaliação** | Nota de 1 a 5 estrelas a uma refeição, com comentário opcional, exibida com o apelido do autor |
| **Campus** | Unidade da UnB com RU: Darcy Ribeiro, Ceilândia, Gama, Planaltina e Fazenda Água Limpa |
| **Check-in** | Registro de presença do usuário no RU de um campus durante uma refeição (Release 2). É a única fonte de dados da fila: não há votação nem sensores |
| **Nível de fila** | Classificação em quatro níveis: vazia, curta, moderada e longa. Aplica-se tanto à previsão de pico quanto ao nível agora |
| **Previsão de pico** | Estimativa do nível de fila esperado em cada faixa de horário de uma refeição, calculada exclusivamente a partir dos check-ins |
| **Nível agora** | Nível de fila atual da refeição em andamento, calculado a partir dos check-ins recentes (Backlog) |

### 1.6 Stack tecnológica

O backend é em Python, com Django REST Framework (DRF) para construir a API. O banco de dados é SQLite em desenvolvimento e MySQL em produção. A justificativa da escolha está na ADR 0001 (`docs/adr/0001-escolha-stack-backend.md`).

---

## 2. Requisitos Funcionais

Cada requisito funcional é descrito com um identificador único, sua descrição, ao menos um critério de aceite objetivo e testável, a release em que está alocado, a prioridade e a origem (épico e necessidade da parte interessada, ou decisão de projeto).

### Épico 1 — Login

#### RF01 — Cadastro de usuário

**Descrição:** O sistema deve permitir que uma pessoa da comunidade da UnB crie uma conta em duas etapas. Na primeira, a pessoa escolhe o tipo de usuário: Estudante, Professor ou Servidor (Professor e Servidor levam ao mesmo fluxo e são internamente o mesmo Tipo de usuário — ver glossário). Na segunda, aparecem os campos daquele tipo:

- **Estudante:** apelido, senha e e-mail institucional no formato `matricula@aluno.unb.br`. A matrícula não é digitada separadamente: o sistema a extrai da parte antes do "@" do e-mail informado.
- **Professor/Servidor:** matrícula funcional/SIAPE, e-mail institucional `@unb.br` e senha. O apelido não é digitado: o sistema o extrai automaticamente do texto antes do "@" do e-mail informado (geralmente no formato nome.sobrenome, mas qualquer texto é aceito).

O sistema confere apenas o formato da matrícula/SIAPE; não verifica se ela existe, se está ativa ou se pertence a quem a informa (ver L01).

**Critério de aceite:**
- Para Estudante, o sistema aceita matrícula (extraída do e-mail institucional) com exatamente 9 dígitos numéricos, sujeita à checagem adicional abaixo. Matrícula com 8 dígitos (padrão anterior a 2010) é rejeitada nesta fase (ver L10). Para Professor/Servidor, aceita SIAPE/matrícula funcional com exatamente 7 dígitos numéricos. Valores com outros formatos ou com pontuação são rejeitados com mensagem específica.
- **Checagem dos 3 primeiros dígitos da matrícula de Estudante (ano/semestre de ingresso):** os 2 primeiros dígitos devem corresponder aos 2 últimos dígitos de um ano entre 2010 e o ano corrente, e o 3º dígito deve ser `1` (primeiro semestre) ou `2` (segundo semestre). O intervalo válido é calculado dinamicamente a partir da data do sistema, do código `101` (2010, primeiro semestre) até o código do semestre corrente (ex.: `262` para o 2º semestre de 2026) — nenhum código fora desse intervalo, incluindo códigos "futuros", é aceito. O ano e o semestre correntes usados nesse cálculo são parâmetros configuráveis (Anexo A).
- **Checagem dos 6 dígitos restantes da matrícula de Estudante:** o bloco de 6 dígitos é rejeitado se formar uma sequência inteira crescente (ex.: `123456`), uma sequência inteira decrescente (ex.: `654321`) ou se todos os dígitos forem iguais (ex.: `111111`).
- Para Estudante, o e-mail institucional deve seguir exatamente o formato `matricula@aluno.unb.br`, em que a parte antes do "@" é a matrícula extraída e validada pelas regras acima; qualquer outro formato de e-mail é rejeitado com mensagem específica. Para Professor/Servidor, o e-mail institucional deve pertencer ao domínio `@unb.br`; a parte antes do "@" é extraída como apelido (ver regra de apelido abaixo).
- O sistema rejeita cadastro com matrícula/SIAPE já associada a outra conta, com mensagem de erro específica. Cada matrícula/SIAPE pertence a uma única conta.
- O sistema rejeita e-mail institucional com formato inválido ou já associado a outra conta.
- O apelido (digitado por Estudante ou extraído do e-mail para Professor/Servidor) tem de 3 a 20 caracteres, sem espaços, é único entre os usuários (sem distinção de maiúsculas e minúsculas), é definido apenas no cadastro e não pode ser alterado depois. Se o apelido extraído do e-mail de um Professor/Servidor já estiver em uso por outra conta, o cadastro automático é rejeitado e o sistema pede que a pessoa digite um apelido alternativo manualmente.
- O sistema rejeita senhas com menos de 8 caracteres.
- O cadastro só é concluído se o usuário confirmar ciência de um aviso de privacidade que informa quais dados são coletados e para quê (recuperação de senha e identificação do autor de avaliações).
- Após o cadastro, a conta fica pendente até a confirmação do e-mail (RF02).

**Release:** MVP · **Prioridade:** Essencial
**Origem:** Épico Login · Pré-requisito para avaliação de refeições (necessidade "Saber a qualidade da comida antes de decidir comer no RU") · Decisão de projeto

---

#### RF02 — Confirmação de e-mail

**Descrição:** O sistema deve enviar ao e-mail institucional informado no cadastro um link de confirmação. A conta só pode se autenticar depois de confirmar o e-mail, que é o único canal de recuperação de senha (RF04).

**Critério de aceite:**
- O link de confirmação é de uso único e válido por 24 horas.
- Após a confirmação, a conta passa a poder se autenticar (RF03).
- Se o link expirou, o usuário pode solicitar o reenvio de um novo link.
- Uma tentativa de login com matrícula/SIAPE e senha corretas em conta ainda não confirmada é recusada com mensagem orientando a confirmação e oferecendo o reenvio do link.

**Release:** MVP · **Prioridade:** Essencial
**Origem:** Épico Login · Decisão de projeto (se o e-mail estiver errado, a pessoa perde o único canal de recuperação de senha)

---

#### RF03 — Login de usuário cadastrado

**Descrição:** O sistema deve permitir que um usuário com conta confirmada se autentique informando matrícula/SIAPE e senha, para acessar as funcionalidades restritas (avaliação de refeições e, na Release 2, check-in). A tela de login tem um único campo de identificador, que aceita tanto matrícula (9 dígitos) quanto SIAPE/matrícula funcional (7 dígitos); o sistema identifica automaticamente qual é o caso pela quantidade de dígitos informada, sem exigir que o usuário escolha o tipo antes de digitar.

**Critério de aceite:**
- Credenciais corretas resultam em sessão autenticada e redirecionamento à página inicial.
- Credenciais incorretas exibem mensagem de erro genérica, sem indicar se a matrícula/SIAPE existe ou não na base (proteção contra enumeração de contas).
- Um identificador com quantidade de dígitos diferente de 7 ou de 9 é rejeitado antes mesmo de consultar a base, com mensagem de formato inválido.
- Após 5 tentativas malsucedidas consecutivas para o mesmo identificador em um intervalo de 10 minutos, o sistema bloqueia novas tentativas por 10 minutos.

**Release:** MVP · **Prioridade:** Essencial
**Origem:** Épico Login · Pré-requisito para avaliação de refeições · Decisão de projeto

---

#### RF04 — Recuperação de senha

**Descrição:** O sistema deve permitir que um usuário que perdeu a senha defina uma nova, por meio de um link enviado ao e-mail cadastrado.

**Critério de aceite:**
- O usuário solicita a redefinição informando a matrícula/SIAPE. A resposta é sempre a mesma ("se houver conta, enviaremos o e-mail"), exista ou não a conta.
- O link de redefinição é de uso único e válido por 1 hora.
- São aceitas no máximo 3 solicitações de redefinição por hora para a mesma matrícula/SIAPE.
- A nova senha segue a regra de mínimo de 8 caracteres. Após a redefinição, a senha anterior deixa de valer e as sessões ativas da conta são encerradas.
- Sem acesso ao e-mail cadastrado, não há recuperação de senha no MVP (ver L07).

**Release:** MVP · **Prioridade:** Essencial
**Origem:** Épico Login · Decisão de projeto

---

#### RF05 — Navegação sem autenticação

**Descrição:** O sistema deve permitir que qualquer visitante, sem necessidade de cadastro ou login, consulte o cardápio diário/semanal dos campi.

**Critério de aceite:**
- A página de cardápio é acessível a partir da URL raiz do sistema sem exigir autenticação.
- Funcionalidades que exigem autenticação (avaliar refeição e, na Release 2, fazer check-in) exibem um convite ao cadastro/login ao serem acionadas por um visitante, em vez de erro genérico.

**Release:** MVP · **Prioridade:** Essencial
**Origem:** Transversal (perspectiva do produto — sistema como "porta") · Necessidade "Planejar a refeição com informação antecipada"

---

### Épico 2 — Visualização do Cardápio

#### RF06 — Leitura automatizada do arquivo de cardápio

**Descrição:** O sistema deve extrair automaticamente as informações do cardápio a partir do arquivo PDF semanal publicado no site oficial do RU para cada campus (uma página por refeição: café da manhã, almoço e jantar). A extração cobre as categorias, os pratos, os marcadores de cada prato e as linhas de dieta, sem intervenção manual da equipe em condições normais de publicação. Os marcadores são ícones gráficos sobrepostos ao texto e não fazem parte da camada de texto do PDF, de modo que a leitura precisa associar cada ícone ao prato correspondente pela posição e identificá-lo pela legenda do arquivo.

**Critério de aceite:**
- Diante de uma nova publicação do PDF de um campus, o cardápio exibido no sistema é atualizado em até 24 horas.
- Os dias e as refeições servidos em cada campus são os que constam no PDF (por exemplo, almoço de sábado quando presente).
- Cada prato é associado aos marcadores cujos ícones aparecem junto a ele. Opções separadas por "ou/OU" são pratos distintos, cada um com seus marcadores.
- O sistema valida que a legenda do arquivo contém exatamente os 10 marcadores conhecidos. Se surgir um ícone desconhecido, ou se os ícones de uma refeição não puderem ser associados a pratos, o cardápio em texto é publicado, a refeição é marcada como "informação de alérgenos indisponível", o filtro de marcadores (RF08) fica desativado para ela e a equipe recebe um alerta.
- Caso a leitura do texto falhe (ex.: mudança no formato do arquivo), o sistema mantém em exibição o último cardápio lido com sucesso e registra um alerta para a equipe, em vez de exibir uma página vazia ou quebrada.

**Release:** MVP · **Prioridade:** Essencial
**Origem:** Épico Cardápio · Necessidade "Planejar a refeição com informação antecipada" · Decisão de projeto (leitura dos marcadores e das dietas)

---

#### RF07 — Exibição do cardápio por campus, refeição e dia

**Descrição:** O sistema deve permitir que o usuário, logado ou não, escolha no início da jornada o campus cujo cardápio deseja ver e exibir o cardápio de uma refeição de um dia por vez, com apresentação visual refinada e voltada a dispositivos móveis. As categorias aparecem em lista hierarquizada; a tabela do PDF não é reproduzida.

**Critério de aceite:**
- O campus escolhido fica lembrado no aparelho, sem exigir login, e pode ser trocado a qualquer momento.
- O usuário consegue alternar entre ao menos dois campi distintos e visualizar cardápios diferentes para cada um.
- O seletor de refeição oferece apenas as refeições que o PDF traz para aquele campus e dia. Por padrão, é exibida a refeição em andamento ou, se nenhuma estiver em andamento, a próxima do dia, conforme os horários configurados (Anexo A).
- O usuário navega entre os dias da semana vigente e, quando o RU publicar, da semana seguinte, sem recarregar a página inteira (abas ou equivalente). A semana é definida pelas datas do PDF do campus. Semanas anteriores não são exibidas.
- Quando um campus ainda não tem cardápio publicado para a semana, o sistema exibe "cardápio ainda não publicado".
- O cardápio exibe o aviso de que está sujeito a alteração.
- A apresentação tem hierarquia visual clara entre categorias, destaca as linhas de dieta, é funcional em telas a partir de 360 px e é validada por revisão de design da equipe.

**Release:** MVP · **Prioridade:** Essencial
**Origem:** Épico Cardápio · Necessidade "Planejar a refeição com informação antecipada" · Decisão de projeto (visualização refinada já no MVP)

---

#### RF08 — Filtro de marcadores alimentares

**Descrição:** O sistema deve permitir que o usuário escolha, entre os 10 marcadores da legenda do cardápio oficial (cogumelo, leite e derivados, mel, pimenta, soja, trigo/glúten, amendoim, oleaginosa, ovo e suíno), quais deseja evitar, sinalizando os pratos que os contêm.

**Critério de aceite:**
- Pratos com um marcador selecionado permanecem visíveis e exibem um alerta que indica o marcador (ex.: "Contém: leite e derivados").
- Uma categoria em que todos os pratos têm algum marcador selecionado exibe "sem opção compatível".
- A seleção fica lembrada no aparelho e permanece ativa ao navegar entre dias, refeições e campi.
- Junto ao filtro há um aviso fixo informando que ele se baseia no cardápio oficial, que está sujeito a alteração; que a ausência de marcador não garante que o prato esteja livre do ingrediente; e que o cardápio oficial não marca peixe nem frutos do mar.
- Em refeição marcada como "informação de alérgenos indisponível" (RF06), o filtro fica desativado e informa o motivo.

**Release:** MVP · **Prioridade:** Essencial
**Origem:** Épico Cardápio · Necessidade "Saber o que posso comer com minha restrição alimentar ou alergia, sem ler o cardápio inteiro" · Decisão de projeto

---

#### RF09 — Filtro de dieta

**Descrição:** O sistema deve permitir que o usuário escolha uma dieta ("Sem filtro", "Ovolactovegetariano" ou "Vegetariano estrito") e exiba as linhas de prato compatíveis do cardápio.

**Critério de aceite:**
- Com "Ovolactovegetariano", o sistema exibe as linhas ovolactovegetariana e vegetariana estrita (prato principal no almoço e no jantar; complemento no café da manhã) e oculta a linha padrão.
- Com "Vegetariano estrito", exibe apenas a linha vegetariana estrita e oculta as demais.
- As demais categorias (saladas, guarnição, acompanhamentos, sopa, torrada etc.) permanecem visíveis, por serem comuns a todas as dietas conforme o cardápio oficial.
- Um botão "mostrar todas" reverte temporariamente o filtro.
- A escolha fica lembrada no aparelho e pode ser combinada com o filtro de marcadores (RF08).

**Release:** MVP · **Prioridade:** Essencial
**Origem:** Épico Cardápio · Necessidade "Saber o que posso comer com minha restrição alimentar ou alergia, sem ler o cardápio inteiro" · Decisão de projeto

---

#### RF10 — Ícones de indicação de marcadores

**Descrição:** O sistema deve exibir, ao lado de cada prato do cardápio, os ícones dos marcadores que ele contém, independentemente de qualquer filtro ativo.

**Critério de aceite:**
- Cada prato com um ou mais marcadores exibe os ícones correspondentes, visíveis sem necessidade de interação adicional (hover ou clique).

**Release:** Backlog · **Prioridade:** Desejável
**Origem:** Épico Cardápio · Necessidade "Saber o que posso comer com minha restrição alimentar ou alergia, sem ler o cardápio inteiro"

---

### Épico 3 — Visualização da Fila e Previsão de Pico

Todos os requisitos deste épico pertencem à Release 2 ou ao Backlog; o MVP não inclui funcionalidade de fila. A previsão de pico é calculada exclusivamente a partir dos check-ins dos usuários: não há votação nem sensores (RI05).

#### RF11 — Check-in no RU

**Descrição:** O sistema deve permitir que um usuário autenticado registre sua presença no RU do campus escolhido durante uma refeição (check-in).

**Critério de aceite:**
- Cada usuário faz no máximo um check-in por refeição por dia; uma nova tentativa para a mesma refeição é rejeitada com mensagem informativa.
- O check-in só é aceito entre o início e o fim da refeição, conforme os horários configurados (Anexo A); fora desse intervalo, é rejeitado com mensagem informando o horário da refeição.
- O check-in não pode ser desfeito.
- Um visitante que tenta fazer check-in recebe o convite ao cadastro/login (RF05).
- O check-in só é efetivado após a confirmação de localização (RF12).

**Release:** Release 2 · **Prioridade:** Importante
**Origem:** Épico Fila · Necessidade "Evitar longas filas no horário de pico" · Decisão de projeto (o check-in passa a ser a única fonte de dados da previsão)

---

#### RF12 — Confirmação de check-in por GPS

**Descrição:** O sistema deve utilizar a localização do dispositivo para confirmar que o usuário está nas imediações do RU do campus escolhido; somente então o check-in é aceito.

**Critério de aceite:**
- O check-in só é aceito quando a localização do dispositivo está dentro do raio configurado (Anexo A) do RU do campus escolhido. Fora do raio, o sistema informa que o check-in não pôde ser confirmado por localização, inclusive quando o usuário está no RU de outro campus.
- Antes do primeiro check-in, o usuário é informado da necessidade de conceder permissão de localização ao navegador. Sem a permissão, o check-in não é possível.
- As coordenadas são usadas apenas na conferência e descartadas; não são armazenadas (RI09).
- Cada tentativa registra usuário, campus, refeição, data/hora e resultado (confirmado ou rejeitado).

**Release:** Release 2 · **Prioridade:** Importante
**Origem:** Épico Fila · Necessidade "Evitar longas filas no horário de pico" (confiabilidade da previsão) · Decisão de projeto

---

#### RF13 — Previsão de pico por faixa de horário

**Descrição:** O sistema deve exibir, para a refeição, o campus e o dia escolhidos, o nível de fila esperado em cada faixa de 15 minutos, em quatro níveis (vazia, curta, moderada e longa), calculado exclusivamente a partir dos check-ins confirmados, e destacar a faixa de maior movimento (pico). A previsão pode ser consultada sem login.

**Critério de aceite:**
- As faixas são de 15 minutos e cobrem o horário da refeição (Anexo A).
- Para cada faixa, o sistema calcula a média de check-ins nas últimas 4 semanas para o mesmo dia da semana, o mesmo campus e a mesma refeição, considerando apenas os dias com dados.
- O nível de cada faixa é a razão entre a sua média e a média da faixa mais cheia: menos de 25% é vazia; de 25% a menos de 50% é curta; de 50% a menos de 75% é moderada; 75% ou mais é longa. A faixa mais cheia é sempre longa.
- A previsão só é exibida quando há check-ins em ao menos 3 dias distintos dentro da janela de 4 semanas. Caso contrário, o sistema exibe "dados insuficientes", sem valor de reserva.

**Release:** Release 2 · **Prioridade:** Importante
**Origem:** Épico Fila · Necessidades "Evitar longas filas no horário de pico" e "Planejar a refeição com informação antecipada" · Decisão de projeto

---

#### RF14 — Nível de fila em tempo real ("agora")

**Descrição:** O sistema deve exibir o nível de fila atual (vazia, curta, moderada ou longa) da refeição em andamento, com base nos check-ins recentes.

**Critério de aceite:**
- O nível atual é exibido com os mesmos quatro níveis do RF13. A janela de check-ins considerada e os limiares serão definidos quando o item for priorizado, considerando o risco de indicar "vazia" por baixa adesão dos usuários (ver L08).

**Release:** Backlog · **Prioridade:** Desejável
**Origem:** Épico Fila · Necessidade "Evitar longas filas no horário de pico" · Decisão de projeto

---

### Épico 4 — Avaliação das Refeições

#### RF15 — Avaliação de refeição por estrelas e comentário

**Descrição:** O sistema deve permitir que um usuário autenticado avalie uma refeição (campus + dia + tipo de refeição) atribuindo uma nota de 1 a 5 estrelas e, opcionalmente, um comentário em texto livre que pode citar pratos ou ingredientes. A avaliação é exibida publicamente com o apelido do autor. Não há nota por prato.

**Critério de aceite:**
- A nota é obrigatória; o comentário é opcional e tem no máximo 500 caracteres.
- Só é possível avaliar refeições do dia corrente e somente depois que a refeição começou, conforme os horários configurados (Anexo A). Antes do início, ou em outro dia, a avaliação fica indisponível e o sistema informa o motivo.
- Cada usuário registra no máximo uma avaliação por refeição; uma segunda tentativa edita a avaliação anterior. A edição é permitida até as 23h59 do mesmo dia.
- A avaliação é exibida junto ao cardápio da refeição, com o apelido do autor, para qualquer visitante. Matrícula/SIAPE e e-mail nunca são exibidos (RI10).
- Cada refeição exibe sua nota média, a quantidade de avaliações e a lista de comentários com apelido, inclusive para os dias já passados da semana vigente. Sem avaliações, exibe "sem avaliações ainda".
- Avaliações de semanas anteriores deixam de ser exibidas na interface, mas permanecem armazenadas, sem limite de retenção.

**Release:** MVP · **Prioridade:** Essencial
**Origem:** Épico Avaliação · Necessidade "Saber a qualidade da comida antes de decidir comer no RU" · Decisão de projeto

---

#### RF16 — Histórico de refeições anteriores

**Descrição:** O sistema deve disponibilizar uma tela dedicada para consultar refeições de semanas anteriores, com o cardápio, a nota média e os comentários de cada uma.

**Critério de aceite:**
- O usuário navega por campus, data e refeição, em modo somente leitura (não é possível avaliar refeições passadas).
- Uma refeição sem avaliações exibe "sem avaliações ainda".
- O histórico começa na primeira leitura de cardápio feita pelo sistema; não há carga de PDFs anteriores como requisito.

**Release:** Release 2 · **Prioridade:** Importante
**Origem:** Épico Avaliação · Necessidade "Saber a qualidade da comida antes de decidir comer no RU"

---

### Transversal

#### RF17 — Design e identidade visual do site

**Descrição:** O sistema deve seguir uma distribuição de informações e paleta de cores definidas e consistentes em todas as telas, garantindo identidade visual coesa ao produto.

**Critério de aceite:**
- Todas as telas do sistema utilizam a mesma paleta de cores e os mesmos padrões de tipografia e espaçamento definidos pelo guia de estilo da equipe, verificável por inspeção visual comparativa entre telas.

**Release:** MVP · **Prioridade:** Essencial
**Origem:** Transversal (item "Design do site" do Documento de Visão)

---

## 3. Requisitos Não Funcionais

Os requisitos não funcionais abaixo detalham as faixas de qualidade do Documento de Visão (Seção 7), que resume as metas principais (RNF01, RNF02, RNF03 e RNF06). Os valores foram calibrados para serem **defensáveis e verificáveis em operação**, e ao mesmo tempo **alcançáveis por uma equipe iniciante em projetos de maior porte**, evitando metas irreais que comprometeriam a entrega do MVP.

#### RNF01 — Desempenho

O sistema deve responder a requisições de visualização de cardápio (e, na Release 2, de previsão de pico) em até **3 segundos**, em condições normais de operação (até **2.000 usuários simultâneos**), medido do lado do servidor em pelo menos 95% das requisições.

**Justificativa:** torna verificável a meta de eficiência do projeto, com uma escala compatível com a comunidade que frequenta os RUs nos horários de pico e acessível a um projeto acadêmico.

---

#### RNF02 — Disponibilidade e confiabilidade

O sistema deve estar disponível pelo menos **95% do tempo** durante o horário de funcionamento dos RUs (das 7h às 19h30) nos dias em que há refeição servida. Em caso de falha na leitura automatizada do cardápio (RF06), o sistema deve continuar exibindo o último cardápio lido com sucesso, em vez de ficar indisponível.

**Justificativa:** meta realista para um serviço mantido por uma equipe estudantil, ainda assim protegendo a experiência do usuário contra a principal fonte de instabilidade identificada (dependência do PDF externo).

---

#### RNF03 — Usabilidade

Um visitante deve conseguir visualizar o cardápio de um campus em **no máximo 3 interações** (cliques/toques) na primeira visita. Nas visitas seguintes, o campus e a refeição escolhidos ficam lembrados no aparelho e o cardápio abre sem interação adicional. A interface deve ser funcional em telas a partir de **360px de largura**, compatível com o caráter PWA/mobile do produto.

**Justificativa:** o perfil de usuário descrito no ambiente do usuário do Documento de Visão é de pessoas com pouco tempo disponível; a usabilidade precisa refletir isso objetivamente.

---

#### RNF04 — Segurança

Senhas de usuário devem ser armazenadas de forma **criptografada (hash)**, nunca em texto plano. Toda comunicação entre cliente e servidor deve utilizar **HTTPS**. Entradas de usuário (ex.: comentários de avaliação, apelido) devem ser tratadas para prevenir injeção de código (XSS) e injeção de consultas (SQL Injection), usando consultas parametrizadas ou ORM. Os links de confirmação de e-mail e de redefinição de senha devem ser gerados com token aleatório imprevisível, de uso único e com prazo de validade (RF02, RF04). Matrícula/SIAPE e e-mail nunca devem ser retornados em respostas públicas nem a outros usuários (RI10).

**Justificativa:** conjunto mínimo de boas práticas de segurança viável para uma equipe em seu primeiro projeto de maior porte, sem exigir maturidade de segurança de nível corporativo.

---

#### RNF05 — Portabilidade e compatibilidade

O sistema, como PWA, deve funcionar corretamente nas **duas versões mais recentes** dos navegadores Chrome, Firefox, Edge e Safari, tanto em desktop quanto em dispositivos móveis, e deve ser instalável na tela inicial do dispositivo conforme os critérios básicos de instalabilidade de um PWA (manifest válido e service worker registrado).

**Justificativa:** decorre diretamente do requisito de sistema de entrega como PWA definido no Documento de Visão.

---

#### RNF06 — Manutenibilidade

O código-fonte deve manter cobertura de testes automatizados de, no mínimo, **60% nos módulos críticos** (leitura de cardápio, incluindo a leitura dos ícones de marcadores; cadastro e autenticação; avaliação de refeições e, na Release 2, check-in e previsão de pico), e a arquitetura deve separar claramente esses módulos, de modo que uma mudança no formato do PDF do cardápio exija alteração apenas no módulo de leitura de cardápio. No backend em Django REST Framework (1.6, ADR 0001), essa separação se reflete em apps Django distintos por recurso (ex.: cadastro/autenticação, cardápio, avaliação, fila), cada um com seu próprio conjunto de models, serializers, views e URLs.

**Justificativa:** meta de cobertura de testes compatível com uma equipe sem experiência prévia em projetos de grande porte, mas suficiente para reduzir o risco já identificado de dependência do PDF externo e de inexperiência da equipe com as tecnologias escolhidas.

---

#### RNF07 — Privacidade e proteção de dados pessoais

O sistema trata como dados pessoais a matrícula/SIAPE, o e-mail e o apelido, e deve observar a Lei Geral de Proteção de Dados (Lei nº 13.709/2018). Os dados são coletados apenas para as finalidades declaradas no aviso de privacidade do cadastro (login, recuperação de senha e identificação do autor de avaliações). A matrícula/SIAPE é armazenada de forma que a equipe possa recuperá-la a partir do apelido (não como hash irreversível), com acesso restrito à equipe. A exclusão de conta é feita por solicitação à equipe, e as avaliações do usuário permanecem de forma anônima ("usuário removido"). A localização do usuário não é armazenada (RI09).

**Justificativa:** o cadastro por matrícula/SIAPE cria um vínculo entre identidade e comportamento no sistema; o tratamento precisa ser transparente e minimizado.

---

#### RNF08 — Rastreabilidade e moderação

Toda avaliação deve manter vínculo permanente com a conta, o apelido e a matrícula/SIAPE de quem a escreveu, de modo que a equipe possa identificar o autor de uma avaliação problemática por consulta administrativa manual. A moderação (ocultar avaliações, suspender contas, tratar matrículas contestadas) é executada diretamente pela equipe; não há tela administrativa no escopo. O site deve divulgar um canal de contato para reclamações.

**Justificativa:** como a matrícula/SIAPE não é validada (L01), a rastreabilidade posterior é o principal instrumento de responsabilização por uso indevido.

---

## 4. Requisitos Inversos

Requisitos inversos definem explicitamente o que o sistema **não deve** fazer, delimitando o escopo e prevenindo interpretações equivocadas durante o desenvolvimento.

| ID | Descrição |
|---|---|
| **RI01** | O sistema não deve permitir que usuários não autenticados registrem avaliações de refeições ou check-ins. |
| **RI02** | O sistema não deve exibir cardápios ou informações de restaurantes/cantinas que não sejam os RUs oficiais da UnB. |
| **RI03** | O sistema não deve computar mais de um check-in do mesmo usuário para a mesma refeição no mesmo dia. |
| **RI04** | O sistema não deve armazenar senhas de usuário em texto plano, sob nenhuma circunstância. |
| **RI05** | O sistema não deve depender de sensores físicos (câmeras, contadores de pessoas) nem de votação dos usuários para estimar a fila — a previsão deve se basear exclusivamente nos check-ins. |
| **RI06** | O sistema não deve bloquear o acesso à visualização do cardápio para usuários que optem por não se cadastrar. |
| **RI07** | O sistema não deve permitir cadastro sem matrícula ou SIAPE em formato válido; terceirizados e demais pessoas sem esses identificadores ficam fora do público de cadastro. |
| **RI08** | O sistema não deve exibir cardápio, avaliações ou informações de fila do Restaurante Executivo do Campus Darcy Ribeiro, que não faz parte do escopo do projeto. |
| **RI09** | O sistema não deve armazenar as coordenadas de localização do usuário. |
| **RI10** | O sistema não deve exibir a matrícula/SIAPE ou o e-mail de um usuário a outros usuários. |

---

## 5. Limitações e Riscos Conhecidos

| ID | Limitação ou risco | Mitigação |
|---|---|---|
| **L01** | **Matrícula alheia ou inventada.** O sistema confere só o formato da matrícula/SIAPE. Alguém pode cadastrar a matrícula de outra pessoa, que ficará sem poder se cadastrar, ou uma matrícula inventada de formato válido. | E-mail único e confirmado (RF02), rastreabilidade (RNF08). Matrícula contestada é resolvida manualmente pela equipe. |
| **L02** | **Contas múltiplas ou falsas.** Uma pessoa pode criar várias contas, inclusive por ter mais de uma vinculação (por exemplo, matrícula de aluno e SIAPE). Isso distorce a nota média das avaliações já no MVP e a previsão de pico na Release 2. | Para as avaliações: e-mail único e confirmado (RF02), rastreabilidade e moderação (RNF08). Para a previsão de pico: confirmação por GPS (RF12), um check-in por refeição (RI03), e-mail único. |
| **L03** | **Leitura dos ícones de marcadores.** Os ícones são imagens; a associação a pratos pode falhar. | Validação da legenda, refeição marcada como "informação de alérgenos indisponível" e alerta à equipe (RF06). |
| **L04** | **Os filtros são auxiliares.** A ausência de marcador não garante que o prato esteja livre do ingrediente; o cardápio oficial não marca peixe nem frutos do mar e está sujeito a alteração. | Aviso fixo junto ao filtro (RF08); pratos com marcador permanecem visíveis com alerta. |
| **L05** | **Parâmetros mantidos manualmente.** Horários das refeições e raios de GPS dependem de atualização pela equipe; os horários podem mudar. | Tabela de configuração (Anexo A) revisada pela equipe. |
| **L06** | **Avaliação sem prova de presença.** No MVP, qualquer usuário autenticado pode avaliar uma refeição do dia depois que ela começou, sem comprovar que comeu. | O check-in (Release 2) permanece independente da avaliação. |
| **L07** | **Recuperação de senha depende do e-mail.** Sem acesso ao e-mail cadastrado, o usuário não recupera a conta no MVP. | Confirmação do e-mail no cadastro (RF02). |
| **L08** | **Baixa adesão ao check-in.** A previsão depende de os usuários fazerem check-in; com pouca adesão, ela é pouco representativa. | Exibição de "dados insuficientes" abaixo do mínimo de dados (RF13); nível "agora" mantido no Backlog (RF14). |
| **L09** | **Avaliações de semanas anteriores.** No MVP, elas não são exibidas na interface, embora permaneçam armazenadas. | Histórico de refeições na Release 2 (RF16). |
| **L10** | **Matrícula de estudante com menos de 9 dígitos não suportada.** O sistema só aceita matrícula de estudante com exatamente 9 dígitos (padrão em uso desde 2010). Estudantes com matrícula de 8 dígitos (anterior a 2010) não conseguem se cadastrar nesta fase. | Decisão de projeto consciente de adiar o tratamento desse caso; forma de abordá-lo fica para decisão futura da equipe. |

---

## 6. Matriz de Rastreabilidade

Necessidades das partes interessadas conforme o Documento de Visão.

| ID | Épico | Necessidade da Parte Interessada / origem | Release |
|---|---|---|---|
| RF01 | Login | Pré-requisito de avaliação — "Saber a qualidade da comida antes de decidir comer no RU"; decisão de projeto | MVP |
| RF02 | Login | Decisão de projeto (canal de recuperação de senha); pré-requisito de avaliação | MVP |
| RF03 | Login | Pré-requisito de avaliação e, na Release 2, de check-in; decisão de projeto | MVP |
| RF04 | Login | Decisão de projeto; pré-requisito de avaliação | MVP |
| RF05 | Login / Transversal | "Planejar a refeição com informação antecipada" | MVP |
| RF06 | Cardápio | "Planejar a refeição com informação antecipada"; decisão de projeto | MVP |
| RF07 | Cardápio | "Planejar a refeição com informação antecipada"; decisão de projeto | MVP |
| RF08 | Cardápio | "Saber o que posso comer com minha restrição alimentar ou alergia, sem ler o cardápio inteiro"; decisão de projeto | MVP |
| RF09 | Cardápio | "Saber o que posso comer com minha restrição alimentar ou alergia, sem ler o cardápio inteiro"; decisão de projeto | MVP |
| RF10 | Cardápio | "Saber o que posso comer com minha restrição alimentar ou alergia, sem ler o cardápio inteiro" | Backlog |
| RF11 | Fila | "Evitar longas filas no horário de pico"; decisão de projeto | Release 2 |
| RF12 | Fila | "Evitar longas filas no horário de pico" (confiabilidade da previsão); decisão de projeto | Release 2 |
| RF13 | Fila | "Evitar longas filas no horário de pico"; "Planejar a refeição com informação antecipada"; decisão de projeto | Release 2 |
| RF14 | Fila | "Evitar longas filas no horário de pico"; decisão de projeto | Backlog |
| RF15 | Avaliação | "Saber a qualidade da comida antes de decidir comer no RU"; decisão de projeto | MVP |
| RF16 | Avaliação | "Saber a qualidade da comida antes de decidir comer no RU" | Release 2 |
| RF17 | Transversal | Experiência geral do usuário | MVP |
| RNF01–RNF06 | Transversal | Métrica de eficiência e requisitos de sistema (entrega como PWA) | MVP / Release 2 |
| RNF07–RNF08 | Transversal | Decisão de projeto | MVP |

---

## 7. Resumo por Release

| Release | Requisitos Funcionais |
|---|---|
| **MVP** | RF01, RF02, RF03, RF04, RF05, RF06, RF07, RF08, RF09, RF15, RF17 |
| **Release 2** | RF11, RF12, RF13, RF16 |
| **Backlog** | RF10, RF14 |

Todos os requisitos não funcionais (RNF01–RNF08) e todos os requisitos inversos (RI01–RI10) aplicam-se transversalmente a partir do MVP, ainda que alguns (ex.: RNF06 quanto a check-in e previsão, RI03, RI05, RI09) só se manifestem completamente a partir da entrada em vigor das funcionalidades de fila na Release 2.

---

## Anexo A — Parâmetros configuráveis

Valores ajustáveis pela equipe sem alterar os requisitos.

| Parâmetro | Valor inicial | Usado em |
|---|---|---|
| Horário do café da manhã | 7h00 às 9h30 | RF07, RF11, RF13, RF15 |
| Horário do almoço | 11h00 às 14h30 | RF07, RF11, RF13, RF15 |
| Horário do jantar | 17h00 às 19h30 | RF07, RF11, RF13, RF15 |
| Estrutura dos horários | Campus × refeição × dia da semana. Os dias e as refeições servidos vêm do PDF | RF06, RF07 |
| Coordenadas e raio de confirmação por RU | A definir pela equipe para cada RU; o raio do Darcy Ribeiro deve excluir o Restaurante Executivo | RF12 |
| Faixa de horário da previsão | 15 minutos | RF13 |
| Janela de histórico da previsão | 4 semanas, mesmo dia da semana | RF13 |
| Mínimo de dados para exibir a previsão | Check-ins em 3 dias distintos | RF13 |
| Cortes dos níveis de fila | 25%, 50% e 75% da média da faixa mais cheia | RF13 |
| Validade do link de confirmação de e-mail | 24 horas | RF02 |
| Validade do link de redefinição de senha | 1 hora | RF04 |
| Limite de solicitações de redefinição | 3 por hora por matrícula/SIAPE | RF04 |
| Bloqueio de login | 5 tentativas em 10 minutos, bloqueio de 10 minutos | RF03 |
| Janela de validação do prefixo da matrícula de estudante | Dinâmica: de `101` (2010, 1º semestre) até o código do semestre corrente do sistema (ex.: `262` no 2º semestre de 2026), recalculada automaticamente a cada semestre | RF01 |
