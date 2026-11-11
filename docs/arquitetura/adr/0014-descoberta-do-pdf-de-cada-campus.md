# ADR 0014 — Descoberta do PDF de cada campus na página de cardápios do RU

**Status:** Proposta
**Data:** 2026-11-11
**Projeto:** Bandejão (Grupo 6, MDS, FCTE/UnB)

## Contexto

O Leitor de Cardápio baixa o PDF semanal de cada campus (RF06, ADR 0003),
mas nenhum documento dizia **de onde** vem o link desse PDF, e a ADR 0003
deixou a frequência do cron em aberto.

O RU publica os cardápios em <https://ru.unb.br/cardapio-refeitorio/>. Em
2026-11-11, a página tinha a seguinte estrutura (WordPress com Elementor):

- um título por campus: "Cardápio Darcy Ribeiro", "Cardápio Ceilândia",
  "Cardápio Gama", "Cardápio Planaltina" e "Cardápio Fazenda Água Limpa";
- logo abaixo de cada título, um link para o PDF da semana, com texto no
  formato "ISM – 09/11/2026 À 15/11/2026". Nessa data havia um link por
  campus, mas o RF18 prevê a semana seguinte assim que o RU a publicar, e as
  páginas por campus já mostram duas semanas juntas. O desenho não pode
  supor um link só;
- os PDFs ficam em `wp-content/uploads/<ano>/<mês>/`, com nomes como
  `Gama-Semana-04-09-11-a-15-11.pdf`.

O que foi observado e pesa na decisão:

1. **O link muda toda semana.** O nome do arquivo traz o número e as datas da
   semana, e a pasta muda com o mês do envio. Não existe URL fixa por campus.
2. **O nome do arquivo não é confiável sozinho.** Quando o RU reenvia um
   arquivo, o WordPress acrescenta `-1`, `-2` ao nome (por exemplo,
   `Darcy-Ribeiro-Semana-04-09-11-a-15-11-2.pdf` e
   `Planaltina-Semana-04-09-11-a-15-11-1.pdf`).
3. **A ordem dos blocos na página não é garantida.** Hoje ela é Darcy
   Ribeiro, Ceilândia, Gama, Planaltina e Fazenda Água Limpa, mas nada indica
   que o RU vá mantê-la. Ela não pode ser critério para associar um PDF a um
   campus.
4. **A publicação não tem dia fixo, e há correções no meio da semana.** O PDF
   do Gama da semana de 09/11 foi enviado na quinta-feira anterior (05/11). O
   do Darcy foi reenviado na segunda-feira (09/11, à tarde), já com a semana
   em andamento. Segundo a equipe, a atualização costuma sair no fim de semana,
   mas às vezes só na segunda-feira.
5. **Outras fontes do site são ambíguas.** As páginas por campus (por exemplo,
   `/cardapio-gama/`) mostram também o PDF da semana anterior. A biblioteca de
   mídia do WordPress (`/wp-json/wp/v2/media`) lista PDFs sem campus no nome
   (por exemplo, `SEMANA-04-09-11-a-13-11.pdf`), que podem ser do Restaurante
   Executivo, fora do escopo (RI08).
6. **O RF06 exige leitura sem intervenção manual** em condições normais, e a
   atualização em até 24 horas depois da publicação (RF06.1).

## Decisão

O Leitor **lê a página `cardapio-refeitorio`** a cada execução e, para cada
campus, pega os links de PDF do bloco cujo título tem **o nome daquele
campus**, um por semana. O desenho de classes está no Nível 4c do Leitor de Cardápio
(`c4-nivel-4-leitor-cardapio.md`).

### 1. Associação do link ao campus

- **O critério é o nome do campus no título, nunca a posição na página.** A
  ordem dos blocos não é usada. Cada título encontrado é comparado com os
  rótulos configurados.
- Cada `CAMPUS` tem um **rótulo na página do RU** (`rotulo_pagina_ru`:
  "Darcy Ribeiro", "Ceilândia", "Gama", "Planaltina", "Fazenda Água Limpa"),
  povoado por fixture (Anexo A). A comparação ignora acentos, maiúsculas e
  espaços extras.
- Ao encontrar um título "Cardápio <rótulo>", o Leitor associa a esse campus
  **todos os links para `.pdf` em `ru.unb.br/wp-content/uploads/`** que
  aparecem depois dele e antes do próximo título, seja qual for a posição do
  bloco na página. Cada link é uma semana, identificada pelas datas do texto
  do link, e é tratado à parte. Assim a semana vigente e a seguinte (RF18)
  podem estar no mesmo bloco. Dois links do mesmo campus para a mesma semana
  são falha daquela semana, e o Leitor não escolhe um deles.
- Um título que não corresponde a nenhum campus é ignorado. Um campus sem
  título, ou com o título repetido, é falha daquele campus: o Leitor não
  escolhe um dos links.
- **Conferência pelo nome do arquivo:** o nome do PDF precisa começar pelo
  prefixo do campus (`prefixo_arquivo_pdf`: `Darcy-Ribeiro`, `Ceilandia`,
  `Gama`, `Planaltina`, `Fazenda`), sem considerar os sufixos `-1`, `-2`.
  Assim, um link colado no bloco errado pelo RU não vira o cardápio de outro
  campus no app.
- **Conferência pelas datas:** todos os dias que o `CardapioPDFParser` lê no
  cabeçalho do PDF precisam estar **dentro do intervalo** do texto do link
  ("09/11/2026 À 15/11/2026"). A regra não é a igualdade, porque o link cobre
  a semana inteira e o PDF traz só os dias em que o campus serve refeição: o
  Gama tem 5 ou 6 dias, e o Darcy Ribeiro, 7 (RF06.2). A conferência pega um
  PDF da semana errada publicado com o texto do link atualizado.

### 2. Quando ler o PDF de novo

- A cada execução, o Leitor acha os links do campus e baixa cada PDF (cerca
  de 170 KB). Ele calcula o SHA-256 do arquivo e compara a URL e o SHA-256 com
  os da última leitura com sucesso daquele campus e daquela semana.
- Se os dois forem iguais, o Leitor para ali, sem ler o PDF nem gravar nada.
  Se um deles mudou, o PDF é lido. Comparar o conteúdo cobre o caso de o RU
  substituir o arquivo sem mudar o nome.
- A última leitura com sucesso fica na tabela nova **`FONTE_CARDAPIO`**, uma
  linha por campus e semana: `semana_inicio`, `url`, `sha256`,
  `verificado_em` e `processado_em`. A `url` e o `sha256` só mudam depois de
  uma leitura com sucesso, para que um PDF com falha seja tentado de novo na
  execução seguinte.
- **Leitura com sucesso** é a que grava o cardápio da semana, mesmo que
  alguma refeição saia só em texto, marcada como "informação de alérgenos
  indisponível" (RF06.3). Nesse caso o PDF não é lido de novo a cada 3 horas,
  o que repetiria o mesmo alerta; ele volta a ser lido quando o RU corrige o
  arquivo e o SHA-256 muda. É a mesma noção de "lido com sucesso" do RF18 e
  da Exposição do Cardápio.
- O rótulo e o prefixo de cada campus ficam em **colunas novas de `CAMPUS`**,
  porque são configuração fixa, povoada por fixture, como as coordenadas.
  `FONTE_CARDAPIO` guarda o estado, que muda a cada leitura.

### 3. Frequência do cron

- O cron roda **a cada 3 horas, todos os dias**. Isso cumpre com folga as
  24 horas do RF06.1, inclusive quando a publicação só sai na segunda-feira,
  e pega as correções feitas no meio da semana. Resolve o ponto deixado em
  aberto pela ADR 0003.
- O custo é baixo: por execução, uma requisição à página (cerca de 150 KB) e
  um PDF pequeno por campus e semana listada. Só os que mudaram são lidos.
- As requisições usam `beautifulsoup4` e `requests`, com `User-Agent`
  identificando o projeto, tempo limite e nenhuma repetição em sequência
  curta, para não sobrecarregar o site do RU.

### 4. Falhas

Em todas as falhas abaixo, o Leitor mantém o último cardápio válido
(RF06.4) e alerta a equipe com o tipo já existente `FALHA_LEITURA_PDF`
(ADR 0006), com uma mensagem que diz qual etapa falhou. Nenhum tipo novo é
criado no `TipoAlerta` nem no banco.

- **Página fora do ar ou erro HTTP:** `DownloadError`, já previsto.
- **Título do campus ausente ou repetido, nome do arquivo que não bate com
  o campus, link sem datas legíveis ou dois links para a mesma semana:**
  `FonteNaoEncontradaError`, nova exceção filha de `LeitorCardapioError`.
- **Dias do PDF fora do intervalo do link:** `FormatoPDFInvalidoError`, já
  previsto.

**Link ainda da semana anterior** (o RU ainda não publicou) **não é falha**.
Nada muda, e o app mostra "cardápio ainda não publicado" para a semana nova
(RF07.3). O alerta só sai se a semana vigente ainda não tem `FONTE_CARDAPIO`
daquele campus depois de **segunda-feira às 12h, no horário de Brasília**
(Anexo A), já que pode haver atraso normal até a segunda-feira.

## Consequências

- O link de cada campus é descoberto sem trabalho manual, mesmo com o nome do
  arquivo mudando toda semana, com os sufixos de reenvio e com qualquer ordem
  dos blocos na página.
- O campus vem do **título da página**, e o nome do arquivo e as datas servem
  de conferência. Um erro de publicação do RU vira alerta, e não um cardápio
  trocado entre campi.
- O Leitor passa a depender também da **estrutura HTML** da página, e não só
  do formato do PDF. Esse risco passa a constar como **L15** no Documento de
  Requisitos. Se o RU mudar o layout ou os títulos, a descoberta falha. A
  falha é visível (alerta, último cardápio mantido) e o ajuste fica num único
  ponto, no `CardapioDownloader`, ou só na fixture de `CAMPUS`, se o RU
  apenas renomear um título.
- **Teste de caracterização:** uma cópia do HTML real da página (como a de
  2026-11-11) entra como fixture, junto aos PDFs reais (ADR 0013, plano de
  testes). Devem ser cobertos: os cinco campi, **os blocos em outra ordem**
  (o resultado tem que ser o mesmo), sufixo `-1`/`-2`, campus sem título,
  título repetido, arquivo de outro campus, dias do PDF fora do intervalo do
  link, bloco com a semana vigente e a seguinte, dois links para a mesma
  semana, e a mesma URL com o mesmo SHA-256 (o PDF não é lido de novo).
- **Mudança no banco:** colunas `rotulo_pagina_ru` e `prefixo_arquivo_pdf` em
  `CAMPUS` e tabela `FONTE_CARDAPIO` (Níveis 3 e 4 do banco, item BD-16 do
  backlog). A `REFEICAO.fonte_pdf_url`, que já existe, continua guardando de
  qual PDF cada refeição veio.
- **Novas dependências:** `beautifulsoup4` e `requests` (ou equivalente).
- A frequência de 3 horas, o prazo de segunda-feira às 12h, a URL da página
  e os rótulos e prefixos são valores iniciais do Anexo A. Como os demais
  parâmetros, devem ser configuráveis e revistos depois de algumas semanas de
  uso.

## Alternativas consideradas

- **URL fixa por campus:** impossível, porque o RU não mantém um nome estável
  para o arquivo.
- **Associar pela ordem dos blocos na página:** descartada, porque o RU não
  garante a ordem, e uma troca de posição mostraria o cardápio de um campus
  em outro sem nenhum erro visível.
- **Cadastro manual do link pela equipe a cada semana** (no banco, ADR 0004):
  simples, mas vai contra o RF06 ("sem intervenção manual") e atrasa o
  cardápio sempre que ninguém da equipe estiver disponível.
- **Identificar o campus só pelo nome do arquivo:** frágil. O nome é digitado
  pelo RU e já varia (sufixos, abreviações como "Fazenda"). Fica apenas como
  conferência.
- **Páginas por campus** (`/cardapio-gama/` etc.): mostram também o PDF da
  semana anterior, e seria preciso decidir qual dos dois é o atual. Ficam
  como plano B se a página `cardapio-refeitorio` deixar de existir.
- **API de mídia do WordPress** (`/wp-json/wp/v2/media`): lista todos os PDFs
  do site, inclusive alguns sem campus no nome e possivelmente do Restaurante
  Executivo (RI08). Não diz qual arquivo está publicado como cardápio atual.
- **Pegar só o primeiro link de cada bloco, com uma linha por campus:**
  mais simples, mas impediria a semana seguinte do RF18 quando o RU listar as
  duas semanas no mesmo bloco.
- **Exigir que as datas do link e as do PDF sejam iguais:** recusaria os
  PDFs corretos dos campi que não servem refeição todos os dias.
- **Comparar só a URL, sem SHA-256:** mais simples, mas deixaria passar um
  arquivo substituído pelo RU com o mesmo nome.
- **Tipo de alerta novo para as falhas da descoberta:** daria um filtro mais
  fino na tabela de alertas, mas exigiria mudar o `TipoAlerta`, o banco e o
  limite de avisos da ADR 0006. A mensagem do alerta já diz qual etapa
  falhou.

## Pontos em aberto

- Confirmar com o RU se a página `cardapio-refeitorio` é o endereço oficial e
  estável dos cardápios.
- Confirmar o que significa "ISM" no texto do link e se ele muda.

## Relacionadas

- Requisitos: RF06 (RF06.1, RF06.2, RF06.3, RF06.4, RF06.5), RF07.3, RF18, RI08, L15, Anexo A.
- Documento de Visão: 4.3 (dependência), Seção 6 (cardápio em PDF) e 11.4
  (risco).
- `docs/arquitetura/adr/0003-leitor-pdf-como-modulo-do-backend.md` (módulo do
  Leitor e disparo por cron).
- `docs/arquitetura/adr/0006-alerta-de-falha-do-leitor-por-email.md` (alertas
  e limite de avisos).
- `docs/arquitetura/adr/0013-estrategia-de-testes-e-portas-de-qualidade.md`
  (testes de caracterização com fixtures reais).
- `docs/arquitetura/backend/c4-nivel-4-leitor-cardapio.md` (Nível 4c:
  descoberta do PDF).
- `docs/arquitetura/banco-de-dados/C4-nivel-4-banco-de-dados-bandejao.md`
  (`CAMPUS` e `FONTE_CARDAPIO`).
