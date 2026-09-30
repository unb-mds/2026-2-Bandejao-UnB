# ADR 0003 — Leitor de PDF como módulo do backend


**Status:** Aceita
**Data:** 2026-09-27
**Projeto:** Bandejão (Grupo 6, MDS, FCTE/UnB)

## Contexto

O cardápio do Bandejão vem de um PDF semanal publicado no site oficial do RU
para cada campus, com uma página por refeição (RF06). O sistema precisa
extrair categorias, pratos, marcadores e linhas de dieta sem intervenção
manual em condições normais, e atualizar o cardápio exibido em até 24 horas
depois de uma nova publicação. Os marcadores são ícones gráficos sobrepostos
ao texto, fora da camada de texto do PDF, e precisam ser associados aos
pratos pela posição e identificados pela legenda do arquivo.

Essa leitura é a principal fonte de instabilidade do sistema: o formato do PDF
é controlado por terceiros e pode mudar sem aviso (L05), e a associação dos
ícones pode falhar (L03). Três requisitos moldam onde esse código deve
ficar:

- **RNF06:** a arquitetura deve separar claramente os módulos críticos, de
  modo que uma mudança no formato do PDF exija alteração apenas no módulo de
  leitura de cardápio, com cobertura mínima de 60% de testes.
- **RNF02:** se a leitura falhar, o sistema continua exibindo o último
  cardápio lido com sucesso.
- **Contexto da equipe:** primeiro projeto de maior porte na disciplina, com
  um semestre para entregar o MVP, e backend já decidido em Python com Django
  REST Framework (ADR 0001).

Havia duas formas de organizar a leitura: como um **módulo dentro do
backend** ou como um **serviço separado**, com seu próprio processo de
implantação. Ainda não se sabe qual biblioteca de leitura de PDF dá o melhor
resultado, e isso depende de um teste com o PDF real do RU do Gama.

## Decisão

O Leitor de Cardápio é um **módulo do Backend API**, implementado como um app
Django com fronteira nítida (models, lógica e testes próprios), e **não** um
container separado.

- O módulo baixa o PDF de cada campus do site do RU por HTTPS, interpreta o
  conteúdo e grava o cardápio estruturado no banco, sem passar pela API REST.
- A leitura é **disparada por cron do sistema operacional**. O cron é
  infraestrutura de implantação, e não um elemento da aplicação, por isso não
  aparece como componente nos diagramas C4.
- A fronteira do módulo é mantida de forma que, se a melhor biblioteca de
  leitura de PDF exigir outra linguagem, ele possa ser promovido a container
  separado. Essa promoção só será feita se o teste com o PDF real do RU do
  Gama mostrar essa necessidade.

O detalhamento do módulo está em `c4-nivel-4-leitor-cardapio.md`.

## Consequências

- Um único artefato de implantação, com a mesma linguagem, o mesmo banco e o
  mesmo pipeline de testes do restante do backend. Isso reduz a carga
  operacional para uma equipe inexperiente.
- A separação exigida pela RNF06 é atendida pela fronteira do app Django: uma
  mudança no formato do PDF fica restrita a esse módulo.
- A escolha da biblioteca de PDF fica limitada, por ora, ao ecossistema
  Python. Se o teste com o PDF do Gama mostrar que uma biblioteca de outra
  linguagem é claramente superior, esta ADR precisa ser revisada, e o custo
  de extrair o módulo depende de a fronteira ter sido respeitada.
- O disparo por cron exige que a hospedagem escolhida permita agendar tarefas
  no servidor. A hospedagem ainda não foi definida (4.4 do Documento de
  Visão), então isso deve ser conferido quando ela for escolhida.
- A frequência do cron precisa garantir a meta de atualização em até 24 horas
  do RF06, com margem. O valor exato ainda não foi decidido.
- O cron é configuração de implantação e não está no código. Vale
  documentá-lo junto com as instruções de deploy, para não se perder na troca
  de hospedagem ou de responsáveis.
- Falhas na leitura não derrubam o sistema (RNF02), mas precisam avisar a
  equipe. Esse aviso está definido na ADR 0006.

## Alternativa considerada

**Serviço separado para a leitura do PDF.** Permitiria usar qualquer
linguagem ou biblioteca e isolar completamente uma falha da leitura. Não foi
adotada por ora porque adiciona um artefato de implantação, comunicação entre
processos e mais infraestrutura para manter, sem que exista, até agora,
evidência de que a linguagem do backend seja um limite real. Fica como caminho
de evolução se o teste com o PDF do Gama indicar o contrário.

## Relacionadas

- Requisitos: RF06, RNF02, RNF06, L03, L05.
- `docs/arquitetura/adr/0001-escolha-stack-backend.md` (linguagem e framework do backend).
- `docs/arquitetura/adr/0006-alerta-de-falha-do-leitor-por-email.md` (aviso à equipe em
  caso de falha de leitura).

## Atualização (28/09/2026)

- As duas pendências desta ADR viraram spikes com prazo no backlog do produto (`docs/requisitos/backlog.md`): a **biblioteca de leitura de PDF**, testada com o PDF real do RU do Gama, é decidida no **SP-01**; a **hospedagem** e a **frequência do cron** (com margem para a meta de 24 horas do RF06) são decididas no **SP-02**. Esta ADR deve ser atualizada com as duas escolhas quando os spikes terminarem.
- O mesmo agendador do sistema operacional roda também o job de exclusão de cadastros pendentes expirados (RF02) e a limpeza de sessões do Django (ADR 0007).
- O Leitor de Cardápio faz parte da Release 2. No protótipo da Release 1, o cardápio é simulado dentro do frontend.
