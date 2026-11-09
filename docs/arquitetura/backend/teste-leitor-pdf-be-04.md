# Teste do leitor do PDF do cardápio (BE-04)

> Resultado do BE-04 (issue #94): teste do leitor com os PDFs reais, escolha
> da biblioteca, lista de casos difíceis e decisão entre o leitor e o plano B.
> Código em `backend/apps/cardapio/leitor/cardapio_pdf_parser.py`, testes em
> `backend/apps/cardapio/tests/test_leitor_pdf.py`, PDFs em
> `backend/apps/cardapio/tests/fixtures/cardapios/`.

## 1. PDFs testados

| PDF | Semana | Gerado por | Refeições e dias | Ícones |
|---|---|---|---|---|
| Gama | 21 a 27/09/2026 | Firefox (cairo) | Café e jantar de 2ª a 6ª; almoço de 2ª a sábado | 86, um por imagem |
| Ceilândia | 09 a 15/11/2026 | Microsoft Word | Café e almoço de 2ª a sábado; jantar de 2ª a 6ª | Juntos em imagens de 2 ou 3 |
| Darcy Ribeiro | 09 a 15/11/2026 | Microsoft Word | As três refeições de 2ª a domingo | Juntos em imagens de 2 ou 3 |

## 2. Resultado

O leitor extrai dos três PDFs **todas** as refeições, dias, categorias, pratos, linhas de dieta e marcadores. O critério do BE-04 ("uma refeição com pratos e marcadores corretos") foi atendido com folga:

- O **almoço inteiro do Gama** (6 dias) e o **almoço inteiro do Darcy** (7 dias, com domingo) estão nos testes como esperado, conferidos prato a prato e ícone a ícone contra a imagem de cada página.
- As outras páginas foram conferidas a olho contra a imagem renderizada, e os casos difíceis delas viraram testes próprios.
- Nenhum ícone ficou sem marcador ou sem prato nos três PDFs.
- Cada PDF é lido em cerca de 1 s.

### Decisão (tomada em 08/11/2026)

**Seguir com o leitor automático (BE-12). O cadastro pelo Django Admin (plano B) fica só como contingência.**

Motivos:

1. A parte de maior risco (L03: identificar os ícones e associá-los aos pratos pela posição) funcionou em todos os ícones dos três PDFs, inclusive com os dois geradores diferentes (Firefox e Word).
2. Tudo roda em Python, com uma biblioteca MIT: a ADR 0003 (leitor como módulo do backend) continua valendo.
3. O desenho do Nível 4 do Leitor serviu de base, com ajustes que a implementação mostrou: a `PaginaExtraida` e o `estruturar()` deram lugar à `Grade` e ao `CardapioPDFParser`, que monta a refeição; o `MarcadorIconMatcher` associa um ícone por vez; e entrou a `FormatoPDFInvalidoError`. O diagrama 4a foi atualizado.

O plano B continua útil se um PDF futuro vier sem as bordas da tabela ou com ícones fora da legenda. Nesses casos, o RF06.3 e o RF06.4 já preveem publicar só em texto ou manter o último cardápio válido.

## 3. Biblioteca: `pdfplumber`

| Critério | pdfplumber 0.11.10 | PyMuPDF 2.1 |
|---|---|---|
| Licença | **MIT** | AGPL-3.0 (ou comercial) |
| Palavras com coordenadas | Sim | Sim |
| Bordas da tabela | Sim (`page.rects`) | Sim (`get_drawings`) |
| Imagens com posição **e conteúdo** | Sim (`page.images`) | Sim |
| Velocidade | ~1 s por PDF | Mais rápida, mas irrelevante (3 páginas por campus por semana) |
| Já estudada pelo grupo | Sim (`docs/estudos/semana01-extracao-pdf-e-media-ponderada.md`) | Não |

As duas resolvem o problema. O `pdfplumber` foi escolhido pela licença MIT (a AGPL do PyMuPDF exigiria avaliar as condições de distribuição do backend) e porque o grupo já o estudou. Ele já traz o Pillow, usado para comparar os ícones. Está em `backend/requirements.txt`.

## 4. Como o leitor funciona

Cada página do PDF é uma refeição, com uma tabela de bordas desenhadas. Os ícones são imagens, fora da camada de texto (RF06.3).

1. **`Grade`**: monta as células com as bordas da tabela (retângulos de até 2,5 pt de espessura). Duas células vizinhas sem borda entre elas são unidas: assim aparecem as células mescladas (por exemplo, BEBIDAS do café, que vale para a semana toda).
2. **Cabeçalho**: a célula "COMPOSIÇÃO" marca a coluna das categorias. Cada coluna à direita com texto precisa ter uma data válida no formato dia/mês/ano (`21/9/2026`, `09/11/2026` ou com ano de 2 dígitos), sem repetir, e a data precisa cair no dia da semana escrito acima dela ("2ª FEIRA", "SÁBADO"…); senão o PDF é recusado. O nome da refeição vem do texto girado da primeira coluna (`cafe`, `almoco`, `jantar`, como em `TipoRefeicao`).
3. **`LegendaValidator`**: cada imagem abaixo da tabela, com o rótulo logo embaixo, vira uma referência. Os rótulos precisam ser exatamente os 10 marcadores conhecidos, sem repetir e com imagem legível, senão `LegendaInvalidaError`. O leitor devolve os nomes do dicionário de dados (`leite_e_derivados`, `trigo_gluten`…).
4. **`MarcadorIconMatcher.dividir`**: separa as imagens que trazem vários ícones, primeiro pelas colunas brancas entre eles e depois pela proporção, quando os anéis se encostam.
5. **`MarcadorIconMatcher.identificar`**: corta as bordas brancas do ícone, reduz a 24×24 px e compara com as 10 referências. Acima da distância 35, o ícone é desconhecido; se o segundo colocado ficar a menos de 1,3 vez da distância do primeiro, o ícone é ambíguo. Nos dois casos, `AssociacaoFalhouError`. Nos três PDFs, o pior acerto ficou em 28, e o segundo colocado ficou sempre pelo menos 1,48 vez mais longe que o certo. Qualquer imagem dentro da tabela mais alta que um ícone (25 pt) também gera `AssociacaoFalhouError`, em vez de ser ignorada.
6. **`CardapioEstruturador.separar_pratos`**:
   - "ou"/"OU" separa pratos, inclusive no fim da linha; "/" não separa (RF06.2).
   - "Opção:" separa como "ou" e sai da descrição ("Opção: Fruta" vira "Fruta").
   - Linha nova que começa com **maiúscula** começa outro prato ("Arroz branco e integral" / "Feijão preto"). Com **minúscula** ou "(", continua o prato.
   - Se a linha anterior termina em conector ("e", "com", "de", "ao"…) ou vírgula, a linha nova continua o prato mesmo com maiúscula.
7. **`MarcadorIconMatcher.associar`**: o ícone vai para o prato da última palavra à esquerda dele, na mesma linha. Se a linha só tem ícones, vai para o prato da linha de texto acima.
8. **Dieta**: "PRATO PRINCIPAL" ou "COMPLEMENTO" + PADRÃO, OVOLACTOVEGETARIANO ou VEGETARIANO ESTRITO viram `padrao`, `ovolacto` ou `vegetariano_estrito` (valores de `Dieta`). Uma linha de prato principal com outra dieta ("PRATO PRINCIPAL VEGANO") recusa o PDF, porque dieta vazia quer dizer "comum a todas" no filtro do RF09.

### Exceções e fallbacks

O leitor nunca devolve um cardápio vazio ou incompleto em silêncio. Todas as exceções herdam de `LeitorCardapioError`, e as mensagens dizem a página.

| Exceção | Quando | O que acontece |
|---|---|---|
| `DownloadError` | Falha de rede ou HTTP | Fica para o BE-12 (`CardapioDownloader`): mantém o último cardápio válido |
| `FormatoPDFInvalidoError` | Arquivo que não é PDF, tabela sem bordas, sem COMPOSIÇÃO, sem dias, data inválida, repetida ou fora do dia da semana, célula com pratos fora dos dias, refeição ou dieta desconhecida | O `extrair()` lança: o PDF inteiro é recusado e o BE-12 mantém o último cardápio válido (RF06.4) |
| `LegendaInvalidaError` | Legenda sem os 10 marcadores, com rótulo repetido ou imagem ilegível | O `extrair()` trata **por página**: a página sai só em texto, com `alergenos_indisponiveis=True` e o `motivo`, e gera um aviso. As outras páginas não são afetadas (RF06.3) |
| `AssociacaoFalhouError` | Ícone desconhecido, ambíguo, sem prato, fora das células de pratos, ou imagem grande na tabela | Igual à anterior |

## 5. Casos difíceis

| # | Caso | Onde | Como o leitor trata | Status |
|---|---|---|---|---|
| 1 | Célula mesclada por vários dias | Café: BEBIDAS e GORDURA | União das células sem borda; vale para todos os dias cobertos | OK |
| 2 | Categoria com duas linhas na tabela | Café: BEBIDAS | A célula da categoria cobre as duas | OK |
| 3 | Número de dias diferente | 5, 6 ou 7 dias, conforme o campus e a refeição | Dias vêm do cabeçalho | OK |
| 4 | "ou" no fim da linha | "Pão francês [trigo] ou" | "ou" separa em qualquer posição | OK |
| 5 | Quebra de linha que é outro prato | "Arroz branco e integral" / "Feijão preto" | Regra da maiúscula | OK, mas é **heurística** |
| 6 | Quebra de linha que é o mesmo prato | "Cubos de frango com" / "manteiga de ervas" | Regra da minúscula | OK |
| 7 | Maiúscula depois de conector | Ceilândia: "Arroz branco e" / "Integral" | Regra do conector | OK |
| 8 | Palavra com hífen quebrada | Darcy: "couve-" / "flor" | Junta em "couve-flor" | OK |
| 9 | Subtítulo em fonte menor | "Legumes sauté" / "(batata, chuchu e cenoura)" | Fica na descrição do prato | OK; o BE-12 pode guardar à parte |
| 10 | "Opção:" como alternativa | "Mix de doces" / "Opção: Fruta" | "Opção:" separa como "ou" e sai da descrição: vira o prato "Fruta" | OK (decidido em 08/11) |
| 11 | Texto solto numa célula | Gama, almoço de 2ª (21/09): "Limão" na última linha da célula do prato ovolactovegetariano, abaixo do ícone de trigo do "Quibe de legumes com quinoa gratinado" | Vira um prato "Limão" | **Não tratado** (decidido em 08/11): erro de quem montou o PDF. O teste registra o que sai hoje, marcado como defeito conhecido do PDF |
| 12 | Palavras grudadas no PDF | Ceilândia e Darcy: "Tomate recheadocom" | Lidas como estão | Erro do próprio PDF |
| 13 | Ícone na linha de baixo do texto | "Ovos mexidos" / [leite][ovo] | Prato da linha acima | OK |
| 14 | Dois pratos com ícones na mesma linha | "Leite Integral [leite] OU Bebida de Soja [soja]" | Última palavra à esquerda do ícone | OK |
| 15 | Ícones de um prato com "/" | Darcy: "Rosé [leite][ovo] / Limão" | Tudo no prato "Rosé / Limão" (a barra não separa) | OK pela regra do RF06.2 |
| 16 | Vários ícones numa imagem só | Ceilândia e Darcy (PDF do Word) | Divisão pelas colunas brancas | OK |
| 17 | Ícones encostados | Ceilândia e Darcy: Yakissoba, 3 anéis colados | Divisão pela proporção | OK |
| 18 | Imagem achatada (ícones ovais) | Darcy e Ceilândia: imagem 105×36 com 2 ícones | Colunas brancas + corte das bordas antes de comparar | OK |
| 19 | Ícone em JPEG | Ceilândia e Darcy: oleaginosa da legenda | Decodifica JPEG (DCTDecode) e RGB cru | OK |
| 20 | Ícones da tabela ≠ ícones da legenda | Todos (tamanhos diferentes) | Comparação pelo conteúdo | OK; mel, trigo e oleaginosa têm cores parecidas |
| 21 | Rótulo em fonte menor embaralhado | Darcy: "PRATO PRINCIPAL OVOLACTOVEGETARIANO" | Palavras extraídas por célula, não pela página | OK |
| 22 | Texto girado | Nome da refeição | Lido de baixo para cima, sem espaços | OK |
| 23 | Célula vazia | OPÇÃO EXTRA na maioria dos dias | Dia sem prato na categoria | OK |
| 24 | Peixe sem marcador | Gama e Darcy | Nenhum marcador (L04) | OK |
| 25 | Logos são imagens | Topo da página | Só contam imagens baixas dentro da tabela | OK |

## 6. Para o BE-12

- Rodar o leitor em mais semanas e no PDF de Planaltina e juntar aqui os casos novos.
- Ligar o leitor ao `CardapioDownloader`, ao `CardapioRepository` e ao `AlertaEquipeService`: `DownloadError` e `FormatoPDFInvalidoError` mantêm o último válido; refeição com `alergenos_indisponiveis` grava `status_leitura = alergenos_indisponiveis` e gera alerta.
- O leitor devolve a dieta por categoria; o model `Prato` guarda a dieta no prato. O `CardapioRepository` copia a dieta da categoria para cada prato dela.
