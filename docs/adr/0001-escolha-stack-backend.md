# ADR 0001 — Escolha da stack de backend

**Status:** Aceita
**Data:** 2026-09-24
**Projeto:** Bandejão (Grupo 6, MDS, FCTE/UnB)

## Contexto

O Bandejão precisa de uma API que sirva ao menos três recursos principais ao frontend — cardápio, avaliação de refeições e, na Release 2, fila/previsão de pico —, sem que o frontend precise saber como esses dados estão armazenados ou como são calculados. A equipe está no primeiro projeto de maior porte da disciplina de MDS e tem tempo limitado (um semestre) para entregar o MVP.

Cada recurso (`/cardapio/`, `/avaliacao/`, `/fila/`, `/previsao/`, entre outros) segue o mesmo padrão de exposição: listar, detalhar, criar e atualizar dados por HTTP, com validação de entrada e serialização para JSON.

## Decisão

O backend será em **Python**, usando **Django REST Framework (DRF)** para construir a API. O banco de dados será **SQLite em desenvolvimento** e **MySQL em produção**.

O DRF cobre, de forma pronta, boa parte do que a equipe teria que construir manualmente para cada recurso REST: validação e serialização de entrada/saída (Serializer), permissões e autenticação, paginação, e o roteamento de URLs para views. O fluxo básico testado pela equipe (com um app de exemplo, `Task`, seguindo o mesmo padrão a ser usado em `Cardapio`, `Fila` etc.) é:

- **Model** — define a estrutura do dado no banco (ex.: campos do cardápio).
- **Serializer** — converte o model em JSON para o frontend consumir, e valida o JSON recebido antes de gravar.
- **View** — decide o que fazer a cada requisição (buscar fila, calcular previsão de pico etc.) e devolve a resposta.
- **URL** — conecta um endpoint (ex.: `/api/cardapio/`) à view correspondente.

Esse fluxo (Model → Serializer → View → URL) é a base a ser replicada para os recursos principais do projeto. O uso de Viewsets e Routers do DRF é o próximo passo natural para manter um padrão consistente entre `/api/cardapio/`, `/api/cardapio/1/`, `/api/fila/` etc.

O SQLite em desenvolvimento evita a necessidade de configurar um servidor de banco de dados à parte durante o desenvolvimento local; o MySQL em produção foi escolhido pela familiaridade da equipe e por ser amplamente suportado pelas opções de hospedagem consideradas para manter o sistema no ar após a disciplina (4.4 do Documento de Visão, ainda a definir).

## Consequências

- A arquitetura de módulos exigida pela manutenibilidade (RNF06) se reflete diretamente em apps Django separados por recurso (cadastro/autenticação, cardápio, avaliação, fila), cada um com seu próprio conjunto de models, serializers, views e URLs.
- O time herda as convenções e limitações do Django/DRF (ex.: ORM próprio, sistema de migrations, autenticação integrada), o que reduz código a escrever à mão, mas também molda como outras decisões futuras (ex.: mecanismo de autenticação de API, hospedagem) serão tomadas.
- Usar SQLite em desenvolvimento e MySQL em produção introduz uma diferença entre ambientes que precisa ser testada (tipos de dado, comportamento de constraints); a equipe deve garantir que as migrations e queries usadas sejam compatíveis com os dois bancos.
- Reverter essa escolha depois de o MVP estar em andamento teria custo alto, já que os três recursos principais (cardápio, avaliação, fila) seriam construídos sobre o padrão Model → Serializer → View → URL do DRF.
