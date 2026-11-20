# Fixtures de referência — BD-03

## Carregamento

Com o ambiente e as variáveis do projeto configurados:

```cmd
python manage.py migrate
python manage.py loaddata campi marcadores
```

As fixtures usam IDs fixos. Recarregá-las atualiza os registros desses IDs sem criar novas cópias. Os IDs dos campi não devem ser alterados após o deploy, pois o PWA pode guardá-los no aparelho.

Recarregar as fixtures sobrescreve os campos presentes nos arquivos para os IDs correspondentes. Ajustes manuais de coordenadas, raios ou `confirmacao_ativa` voltam aos valores da fixture. Portanto, os valores validados no BD-06 também devem ser atualizados em `campi.json` antes de uma nova carga.

## Campi e confirmação de localização

As coordenadas de `campi.json` foram fornecidas pela equipe a partir de um levantamento aproximado em mapas. Foram arredondadas para seis casas decimais e ainda não foram validadas em campo.

| ID | Campus | Raio de confirmação | Confirmação ativa |
|---|---|---|---|
| 1 | Darcy Ribeiro | 150 m | Sim |
| 2 | Ceilândia | 150 m | Sim |
| 3 | Gama | 150 m | Sim |
| 4 | Planaltina | 150 m | Sim |
| 5 | Fazenda Água Limpa | 0 — indisponível | Não |

Os 150 m são uma definição provisória da equipe. A validação e os ajustes em campo pertencem ao BD-06, incluindo a avaliação do caso do Restaurante Executivo no Darcy Ribeiro.

Os campos `centro_latitude` e `centro_longitude` repetem provisoriamente as coordenadas cadastradas para o RU. O `raio_deteccao_metros` repete o raio de confirmação até a definição dos parâmetros de detecção no BD-E3.

## Fazenda Água Limpa

O ponto disponível representa a fazenda, não a localização confirmada do RU. Por isso, a fixture registra:

- `confirmacao_ativa = false`;
- `raio_confirmacao_metros = 0`;
- `raio_deteccao_metros = 0`.

Zero representa ausência de raio ativo. Não deve autorizar confirmação por coincidência com a coordenada cadastrada.

A BE-09 deverá consultar `confirmacao_ativa` antes do cálculo de distância e recusar a confirmação quando o campo for falso. O BD-03 configura os dados; não implementa o fluxo do endpoint de check-in.

A ativação da FAL depende da identificação do ponto do RU e da definição de um raio adequado, com atualização da fixture.

## Origem do cardápio (BD-16)

`campi.json` traz também o rótulo de cada campus na página de cardápios do RU e o prefixo esperado do nome do PDF (ADR 0014, Anexo A):

| ID | `rotulo_pagina_ru` | `prefixo_arquivo_pdf` |
|---|---|---|
| 1 | Darcy Ribeiro | `Darcy-Ribeiro` |
| 2 | Ceilândia | `Ceilandia` |
| 3 | Gama | `Gama` |
| 4 | Planaltina | `Planaltina` |
| 5 | Fazenda Água Limpa | `Fazenda` |

As duas colunas são únicas. Se o RU renomear um título ou mudar o nome dos arquivos, o ajuste é feito aqui, sem mudar o código do Leitor. Os campos não são publicados na API.

## Marcadores

`marcadores.json` contém os dez códigos definidos no Nível 4 do banco e utilizados pelo leitor do cardápio.

## Referências

- Issue #89 — BD-03.
- BD-06 — validação das coordenadas e dos raios em campo.
- BD-E3 — definição dos parâmetros de detecção de campus.
