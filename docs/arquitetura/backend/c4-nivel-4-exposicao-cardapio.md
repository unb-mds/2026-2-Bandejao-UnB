# Arquitetura C4 — Nível 4 (Exposição do Cardápio) — Bandejão

> Detalha, em diagrama de classes, o componente **Exposição do Cardápio**,
> desenhado no Nível 3 do backend dentro da fronteira do App Cardápio (ver
> `c4-nivel-3-backend.md`), ao lado do Leitor de Cardápio
> (`c4-nivel-4-leitor-cardapio.md`) — os dois compartilham os mesmos models
> Django (`Refeicao`, `Categoria`, `Prato`, `Marcador`), mas um escreve e o
> outro só lê. Cobre a parte de exibição do Épico Cardápio: exibição por
> campus/refeição/dia (RF07), filtro de marcadores (RF08), filtro de dieta
> (RF09) e exibição da semana seguinte (RF18). Na Release 2, também publica
> a lista de campi com o centro e o raio de detecção de cada um, usada pelo
> PWA para detectar o campus no aparelho (RF20.1, ADR 0009).
>
> **Decisão tomada neste refinamento:** os filtros de marcador (RF08) e de
> dieta (RF09) são aplicados **no backend** — o endpoint recebe os
> marcadores/dieta selecionados como parâmetros e já devolve o cardápio
> filtrado, em vez de o PWA filtrar um cardápio bruto já carregado. Isso é
> o que justifica `FiltroMarcadorService` e `FiltroDietaService` existirem
> como serviços de backend testáveis à parte, e não apenas como lógica no
> Vue. Decisão registrada na ADR 0005
> (`docs/arquitetura/adr/0005-filtros-de-marcador-e-dieta-no-backend.md`).

Há dois diagramas: **4a** cardápio filtrado e **4b** lista de campi para a detecção. Cada diagrama tem no máximo 20 elementos e um título próprio, seguindo a skill c4-architecture usada pelo grupo; classes compartilhadas (como `Conta` ou as configurações) aparecem em mais de um diagrama.

## Nível 4a — Cardápio filtrado

```mermaid
---
title: "Nível 4a — Exposição do Cardápio: consulta e filtros"
---
classDiagram
  class CardapioView {
    +get(request) Response
  }
  class CardapioQueryService {
    +obterCardapio(campus: Campus, semana: Semana, dia: date, refeicao: str, marcadoresSelecionados: list~str~, dieta: DietaSelecionada) CardapioFiltrado
  }
  class RefeicaoRepository {
    +buscarRefeicao(campus: Campus, data: date, tipo: str) Refeicao
    +refeicoesDoDia(campus: Campus, data: date) list~Refeicao~
    +proximoDiaComServico(campus: Campus, depoisDe: date) date
    +existeCardapioPublicado(campus: Campus, semana: Semana) bool
  }
  class HorarioRefeicaoResolver {
    +refeicaoPadrao(agora: datetime, refeicoesDoDia: list~Refeicao~) RefeicaoPadrao
    +refeicaoEmAndamento(agora: datetime, refeicoesDoDia: list~Refeicao~) str
    +proximaRefeicao(agora: datetime, refeicoesDoDia: list~Refeicao~) str
    +ultimaRefeicaoDoDia(refeicoesDoDia: list~Refeicao~) str
  }
  class HorariosRefeicaoConfig {
    +horarioCafe: tuple
    +horarioAlmoco: tuple
    +horarioJantar: tuple
  }
  class SemanaCardapioResolver {
    +semanasDisponiveis(campus: Campus) list~Semana~
  }
  class Semana {
    +inicio: date
    +fim: date
    +vigente: bool
  }
  class DietaSelecionada {
    <<enumeration>>
    SEM_FILTRO
    OVOLACTOVEGETARIANO
    VEGETARIANO_ESTRITO
  }
  class FiltroDietaService {
    +aplicar(refeicao: Refeicao, dieta: DietaSelecionada) list~Categoria~
  }
  class FiltroMarcadorService {
    +aplicar(categorias: list~Categoria~, marcadoresSelecionados: list~str~, alergenosIndisponivel: bool) list~CategoriaFiltrada~
    -contemTodosMarcados(pratos: list~Prato~, marcadoresSelecionados: list~str~) bool
  }
  class CardapioFiltrado {
    +campus: Campus
    +refeicao: str
    +data: date
    +refeicaoEncerrada: bool
    +status: StatusCardapio
    +avisoSujeitoAAlteracao: str
    +alergenosIndisponivel: bool
    +filtroMarcadorDesativado: bool
    +categorias: list~CategoriaFiltrada~
  }
  class StatusCardapio {
    <<enumeration>>
    PUBLICADO
    NAO_PUBLICADO
  }
  class CategoriaFiltrada {
    +nome: str
    +semOpcaoCompativel: bool
    +pratos: list~PratoFiltrado~
  }
  class PratoFiltrado {
    +descricao: str
    +marcadores: list~str~
    +contemMarcadorSelecionado: bool
  }
  class Refeicao {
    +campus: Campus
    +tipo: str
    +data: date
    +alergenosIndisponivel: bool
  }
  class Categoria {
    +nome: str
    +dieta: str
  }
  class Prato {
    +descricao: str
  }
  class Marcador {
    +nome: str
  }

  CardapioView --> CardapioQueryService : obterCardapio()
  CardapioQueryService --> RefeicaoRepository : busca refeição(ões)
  CardapioQueryService --> HorarioRefeicaoResolver : resolve refeição padrão quando não informada (RF07, RN05)
  CardapioQueryService --> SemanaCardapioResolver : resolve semana vigente/seguinte (RF18)
  CardapioQueryService --> FiltroDietaService : 1. filtra por dieta (RF09)
  CardapioQueryService --> FiltroMarcadorService : 2. sinaliza marcadores (RF08)
  CardapioQueryService --> CardapioFiltrado : monta resposta
  HorarioRefeicaoResolver --> HorariosRefeicaoConfig : usa parâmetros do Anexo A
  SemanaCardapioResolver --> Semana : produz
  RefeicaoRepository ..> Refeicao : lê
  RefeicaoRepository ..> Categoria : lê
  RefeicaoRepository ..> Prato : lê
  RefeicaoRepository ..> Marcador : lê
  FiltroDietaService --> Categoria : lê linhas de dieta
  FiltroMarcadorService --> CategoriaFiltrada : produz
  FiltroMarcadorService --> PratoFiltrado : produz
  CardapioFiltrado --> StatusCardapio : tem
  CardapioFiltrado *-- CategoriaFiltrada
  CategoriaFiltrada *-- PratoFiltrado
```

### Notas do diagrama (4a)

- **A decisão de filtrar no backend é o que dá origem a
  `FiltroDietaService` e `FiltroMarcadorService` como classes próprias**,
  em vez de o `CardapioQueryService` devolver um cardápio bruto para o Vue
  filtrar. Cada serviço cobre uma regra de negócio isolada e testável sem
  precisar simular a interface — bom para a meta de cobertura da RNF06 — e
  os dois são aplicados em sequência (`CardapioQueryService` chama primeiro
  `FiltroDietaService`, depois `FiltroMarcadorService`), porque a dieta pode
  esconder categorias/linhas inteiras (RF09) e o filtro de marcador só
  precisa então avaliar o que sobrou.
- **`FiltroMarcadorService.aplicar` recebe `alergenosIndisponivel` como
  parâmetro** para respeitar o RF08: se a refeição está marcada como
  "informação de alérgenos indisponível" (RF06/L03), o filtro fica
  desativado para ela — o serviço não aplica sinalização nenhuma e
  `CardapioFiltrado.filtroMarcadorDesativado` fica `true`, para a interface
  informar o motivo.
- **`CategoriaFiltrada.semOpcaoCompativel`** cobre o caso do RF08 em que
  todos os pratos de uma categoria têm algum marcador selecionado — é uma
  informação calculada por `FiltroMarcadorService`, não um campo do model
  `Categoria`, porque depende da seleção de filtro de cada requisição, não
  é um dado fixo do cardápio.
- **Refeição padrão da Release 2 (RN05).** Quando o PWA não informa a
  refeição, `HorarioRefeicaoResolver.refeicaoPadrao` aplica a ordem da RN05:
  1. a refeição em andamento;
  2. senão, a próxima refeição ainda por vir no mesmo dia;
  3. senão (todas as refeições do dia já terminaram), a última refeição do
     dia (`ultimaRefeicaoDoDia`), até as 23h59, com
     `CardapioFiltrado.refeicaoEncerrada = true`: o PWA mostra "refeição
     encerrada" no lugar da previsão e do check-in, e a avaliação continua
     aberta (RF15.1, RF20.3);
  4. depois da meia-noite, volta a valer o item 2, e o café da manhã do novo
     dia passa a ser o padrão;
  5. se o campus não serve refeições no dia (ex.: domingo), o
     `CardapioQueryService` pede ao `RefeicaoRepository` o
     `proximoDiaComServico` e mostra a primeira refeição desse dia;
     `CardapioFiltrado.data` indica o dia exibido.

  Os dias e as refeições servidos são os do PDF (RF06.2). Se o dia a exibir
  for de uma semana cujo PDF ainda não foi lido, o `status` vem
  `NAO_PUBLICADO` (RF18). O resultado (`RefeicaoPadrao`) traz a refeição, o
  dia e se ela está encerrada.
- **`HorarioRefeicaoResolver` e `SemanaCardapioResolver` existem separados
  do `CardapioQueryService`** pelo mesmo motivo do `MatriculaValidator` no
  Cadastro/Autenticação: são duas regras de negócio compostas e
  independentes — "qual refeição está em andamento agora" (RF07, depende
  dos horários do Anexo A) e "a semana seguinte já pode ser exibida?"
  (RF18, depende só de o PDF daquela semana já ter sido lido com sucesso
  pelo Leitor de Cardápio) — testáveis cada uma com seus próprios casos de
  borda, sem precisar montar cenário completo de cardápio para testar só
  uma das duas.
- **`Refeicao`, `Categoria`, `Prato` e `Marcador` são os mesmos models do
  Nível 4 do Leitor de Cardápio** — aqui aparecem só como origem de leitura
  do `RefeicaoRepository`; nenhuma dessas classes é escrita por este
  componente, reforçando a nota do Nível 3 de que Leitor de Cardápio e
  Exposição do Cardápio têm perfis diferentes dentro do mesmo app (um
  escreve, o outro só lê).
- **Campus, filtro de marcador e dieta escolhidos continuam "lembrados no
  aparelho" do lado do PWA (RF07, RF08, RF09)** — isso não muda com a
  decisão de filtrar no backend: o dispositivo ainda decide *quais*
  parâmetros mandar a cada requisição, o backend só deixou de ser "burro"
  em relação ao que fazer com eles. Por isso não há, neste diagrama, nenhuma
  classe de preferência de usuário persistida — não é responsabilidade
  deste componente.
- **RF10 (ícones de marcador sempre visíveis, Backlog) não exige nenhuma
  classe nova**: `PratoFiltrado.marcadores` já carrega essa informação
  independentemente do filtro estar ativo ou não; falta só a interface
  exibir os ícones sem exigir interação, o que é responsabilidade do PWA.

## Nível 4b — Lista de campi para a detecção

```mermaid
---
title: "Nível 4b — Exposição do Cardápio: campi com centro e raio de detecção"
---
classDiagram
  class CampiView {
    +get(request) Response
  }
  class CampusPublico {
    +id: int
    +nome: str
    +centro: PontoGeografico
    +raioDeteccaoMetros: int
  }
  class PontoGeografico {
    +latitude: float
    +longitude: float
  }
  class LocalizacaoCampusConfig {
    <<lê CAMPUS, valores do Anexo A>>
    +campi() list~Campus~
    +centro(campus: Campus) PontoGeografico
    +raioDeteccaoMetros(campus: Campus) int
  }

  CampiView --> LocalizacaoCampusConfig : lê centro e raio de detecção
  CampiView --> CampusPublico : produz lista
  CampusPublico --> PontoGeografico : tem
```

### Notas do diagrama (4b)

- **`GET /api/campi/` publica o que o PWA precisa para detectar o campus no
  aparelho (RF20.1, ADR 0009, decisão 6).** É público, não depende de login
  e devolve, para cada campus, id, nome, centro e raio de detecção:

  ```json
  [
    {"id": 1, "nome": "Gama", "centro": {"latitude": -15.989, "longitude": -48.044}, "raioDeteccaoMetros": 800}
  ]
  ```

  (Valores ilustrativos; os reais vêm do Anexo A.) Fica numa view própria,
  separada do `CardapioView`, porque campi e cardápio mudam em ritmos
  diferentes: o PWA não precisa baixar um cardápio só para descobrir os
  raios. A resposta vai com cabeçalhos de cache (`Cache-Control` e `ETag`),
  e o PWA guarda a última versão no `localStorage`, para a detecção caber no
  limite de 5 s mesmo com rede lenta (RN03).
- **O raio de detecção não é o raio de confirmação do check-in.** O raio de
  detecção (campus inteiro) fica em `LocalizacaoCampusConfig`; o raio de
  confirmação (só o prédio do RU) fica em `LocalizacaoRUConfig`, no Nível 4
  da Fila, e **não é publicado**, porque quem confirma o check-in é o
  backend (RF12). As coordenadas do usuário nunca chegam a este endpoint: a
  comparação é feita no aparelho, e o servidor recebe só o identificador do
  campus (RI09).
- **De onde vêm os valores (decisão tomada com o time de banco de dados).**
  As duas configurações leem a tabela `CAMPUS`, preenchida por fixture com
  os valores do Anexo A, que separa o que é do campus do que é do RU:
  - `LocalizacaoCampusConfig` lê `centro_latitude`, `centro_longitude` e
    `raio_deteccao_metros` (detecção, ADR 0009);
  - `LocalizacaoRUConfig`, na Fila, lê `ru_latitude`, `ru_longitude` e
    `raio_confirmacao_metros` (confirmação do check-in, RF12).
- **A conta de distância existe nos dois lados**, no PWA (detecção) e na
  `DistanciaGeografica` da Fila (confirmação do check-in). Os dois devem usar
  a mesma fórmula e os mesmos casos de teste, com as coordenadas reais dos
  RUs e dos campi, para não darem resultados diferentes.

## Notas gerais

- Este diagrama é uma **proposta de decomposição inicial**, coerente com a
  decisão de filtrar no backend tomada agora — se a equipe encontrar, na
  prática, uma razão para mover algum desses filtros de volta para o
  frontend (ex.: latência, simplicidade do PWA), vale atualizar este
  arquivo e registrar a mudança em uma nova ADR que substitua a ADR 0005.
