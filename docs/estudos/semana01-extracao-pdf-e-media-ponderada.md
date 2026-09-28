# Extração de PDF e Média Ponderada

**Integrante:** Cristiano
**Semana:** 01
**Data:** 2026-09-11
**Tags:** pdfplumber, extração de dados, média móvel exponencial, EMA, cardápio, fila

## Resumo

O `pdfplumber` é uma biblioteca Python para leitura de PDFs que abre o arquivo e o segmenta por página, identificando cada elemento (texto, linha, tabela) por coordenadas geométricas (x, y). Ele oferece dois métodos principais: `extract_text()`, que captura todo o texto corrido da página, e `extract_table()`/`extract_tables()`, que extrai tabelas com linhas e divisões explícitas. O desafio do "cardápio de verdade" — onde não há bordas de tabela, só espaços separando prato e preço — é resolvido passando um dicionário `table_settings` com estratégias de detecção (por exemplo, baseadas no alinhamento do texto em vez de linhas visíveis), induzindo o pdfplumber a "enxergar" colunas invisíveis.

Já a média móvel exponencial (EMA) é uma técnica de cálculo de média onde os valores mais recentes têm peso muito maior que os antigos, e esse peso cai rapidamente (não linearmente) à medida que o dado envelhece. Isso serve para invalidar rapidamente relatos antigos, dando prioridade quase total às informações mais recentes.

## Aplicação no projeto

O `pdfplumber` será usado no módulo de **cardápio**: a ideia é extrair automaticamente o texto e as tabelas do PDF semanal do cardápio do RU, convertendo pratos e preços em dados estruturados que alimentam o site. Ainda está em aberto se essa extração vai rodar de forma agendada (ex: toda semana ao publicar o novo PDF) ou ser disparada manualmente por alguém do grupo — isso deve ser decidido em uma sprint futura.

A média móvel exponencial será usada no módulo de **fila**: os usuários do site enviam Relatos em tempo real sobre o tamanho da fila do RU, e esse cálculo combina os relatos válidos mais recentes com peso muito maior que os antigos, gerando um "estado atual" da fila que reflete a situação de agora, e não uma média histórica diluída.

## Principais conceitos / como usar

**pdfplumber — extração de tabela:**
```python
import pdfplumber

# Abre o PDF
with pdfplumber.open("documento.pdf") as pdf:
    pagina = pdf.pages[0]  # seleciona a página desejada

    # Configurações de extração da tabela
    configuracoes = {
        "vertical_strategy": "lines",   # alinha pelas linhas verticais visíveis
        "horizontal_strategy": "text",  # alinha pelas quebras de texto (para tabelas sem bordas)
        "snap_tolerance": 3,            # tolerância para unir linhas próximas
        "join_tolerance": 3             # tolerância para conectar segmentos de linha
    }

    tabelas = pagina.extract_tables(table_settings=configuracoes)

    for tabela in tabelas:
        for linha in tabela:
            print(linha)
```

Pontos-chave:
- `vertical_strategy`/`horizontal_strategy` controlam como o pdfplumber decide onde começam/terminam colunas e linhas — `"lines"` usa bordas visíveis, `"text"` usa o alinhamento do texto (essencial quando o cardápio não tem grade desenhada).
- `snap_tolerance`/`join_tolerance` ajustam a sensibilidade a pequenas imperfeições geométricas no PDF, evitando que uma tabela "quebre" em pedaços errados.
- `extract_tables()` retorna uma lista de tabelas, cada uma como lista de linhas (listas de células).

**Média móvel exponencial (EMA) — cálculo do estado da fila:**

Fórmula: `EMA(t) = α·X(t) + (1-α)·EMA(t-1)`, onde `α` (alfa) é o fator de suavização entre 0 e 1, `X(t)` é o novo relato recebido, e `EMA(t-1)` é a média calculada anteriormente.

```
INÍCIO
    Definir lista_de_valores = [relatos históricos válidos]
    Definir alfa = valor_entre_0_e_1 (ex: 0.3)

    media_atual = lista_de_valores[0]  # a EMA começa no primeiro valor

    PARA CADA valor EM lista_de_valores (a partir do segundo):
        media_atual = (alfa * valor) + ((1 - alfa) * media_atual)
    FIM PARA

    EXIBIR media_atual
FIM
```

Pontos-chave:
- Quanto maior `α`, mais peso os relatos recentes têm (reage rápido, mas é mais sensível a ruído); quanto menor, mais suave e "conservadora" é a média.
- Não precisa guardar todo o histórico — basta o valor de `EMA(t-1)` e o novo relato para atualizar o estado, o que é ótimo para cálculo em tempo real.

## Fontes / materiais usados

- https://www.youtube.com/watch?v=yKAuUAPREMw
- https://www.youtube.com/watch?v=3y9GESSZmS0
