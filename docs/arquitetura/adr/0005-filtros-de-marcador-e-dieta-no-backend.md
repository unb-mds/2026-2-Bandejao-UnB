# ADR 0005 — Filtros de marcador e de dieta aplicados no backend

**Status:** Aceita
**Data:** 2026-09-27
**Projeto:** Bandejão (Grupo 6, MDS, FCTE/UnB)

## Contexto

O cardápio exibido ao usuário pode ser filtrado por **marcadores** a evitar
(RF08) e por **dieta** (RF09), combináveis entre si. O campus, os marcadores
e a dieta escolhidos ficam lembrados no aparelho do usuário (RF07, RF08,
RF09), ou seja, são estado do PWA. Isso deixava em aberto onde a lógica de
filtro deveria rodar:

- **No frontend (Vue):** o backend devolve o cardápio estruturado da refeição
  com os marcadores de cada prato, e o PWA decide o que esconder ou
  sinalizar com base na seleção salva localmente.
- **No backend:** o PWA envia os marcadores e a dieta selecionados como
  parâmetros da requisição, e o backend devolve o cardápio já filtrado.

As regras a implementar não são triviais: o RF08 exige sinalizar cada prato
que contém um marcador selecionado, avisar "sem opção compatível" quando
todos os pratos de uma categoria são afetados e desativar o filtro nas
refeições marcadas como "informação de alérgenos indisponível" (RF06/L03); o
RF09 exige ocultar linhas de prato principal conforme a dieta escolhida,
mantendo as demais categorias visíveis.

## Decisão

Os filtros de marcador (RF08) e de dieta (RF09) são aplicados **no backend**.

- O endpoint de cardápio (`GET /api/cardapio/`) recebe campus, semana, dia,
  refeição (opcional, com padrão definido pelos horários do Anexo A) e, como
  parâmetros de consulta, os marcadores selecionados e a dieta escolhida.
  Devolve o cardápio já filtrado.
- O componente Exposição do Cardápio implementa a regra em dois serviços
  separados, aplicados em sequência: `FiltroDietaService` primeiro (a dieta
  pode ocultar linhas inteiras) e `FiltroMarcadorService` depois (sinaliza os
  pratos e as categorias do que restou).
- Quando a refeição está marcada como "informação de alérgenos indisponível",
  `FiltroMarcadorService` não sinaliza nada e a resposta informa que o filtro
  de marcador está desativado, para a interface explicar o motivo.
- A **preferência continua sendo lembrada no aparelho**: o PWA decide quais
  parâmetros enviar a cada requisição. O backend não persiste preferência de
  filtro de nenhum usuário, e o Visitante (sem login) usa os filtros do mesmo
  jeito.

O desenho de classes está em `c4-nivel-4-exposicao-cardapio.md`.

## Consequências

- As regras do RF08 e do RF09 ficam em um único lugar, em serviços
  testáveis sem interface, o que ajuda a meta de cobertura de 60% em módulos
  críticos (RNF06), e não são reimplementadas em JavaScript.
- Cada troca de filtro passa a exigir uma requisição ao backend. Em rede
  móvel lenta ou sem conexão, o filtro não responde como responderia se
  fosse aplicado localmente sobre um cardápio já carregado; isso pesa em um
  PWA instalável e mobile-first, e a equipe deve avaliar, na implementação,
  se compensa guardar em cache local as respostas já obtidas.
- As respostas passam a variar conforme os parâmetros de filtro, o que
  reduz a eficácia de qualquer cache de resposta por endereço.
- A mensagem "sem opção compatível" e o estado "filtro desativado" viram
  campos da resposta (`semOpcaoCompativel`, `filtroMarcadorDesativado`), e o
  contrato entre PWA e backend precisa ser combinado entre as duplas das
  duas frentes.
- Reverter a decisão (mover o filtro para o frontend) exigiria reescrever as
  regras em JavaScript e simplificar o endpoint; o custo é moderado, desde que
  a regra continue isolada nos dois serviços.

## Alternativa considerada

**Filtro no frontend.** Simplificaria o backend, que só serializaria o
cardápio, e evitaria uma requisição por troca de filtro. Não foi adotada
porque a equipe optou por manter as regras de filtro no backend, onde ficam
centralizadas e testáveis.

## Relacionadas

- Requisitos: RF06, RF07, RF08, RF09, RNF06.
- `docs/arquitetura/adr/0001-escolha-stack-backend.md` (padrão Model → Serializer → View
  → URL, no qual os serviços de filtro se apoiam).

## Nota — protótipo da Release 1 (28/09/2026)

Como a Release 1 é um protótipo somente de frontend, sem backend real, os filtros de marcador e de dieta rodam **no navegador** (`frontend/src/utils/cardapio.js`). O código segue a mesma regra desta ADR e do RF08: o prato com marcador evitado **continua visível e é sinalizado** (não é ocultado), e a categoria recebe "sem opção compatível" quando todos os seus pratos são sinalizados.

A decisão desta ADR continua valendo para a **Release 2**: quando o endpoint de cardápio existir, a regra passa a rodar nos serviços do backend e o código de filtro sai do frontend (histórias US-08.1 e US-09.1 e tarefa TT-05 do backlog).
