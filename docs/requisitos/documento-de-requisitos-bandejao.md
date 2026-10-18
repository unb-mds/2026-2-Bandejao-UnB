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

O MVP (Release 1) já foi entregue. A Release 2 é a entrega final do projeto na disciplina: além das funcionalidades de fila, ela acrescenta ao login o encerramento de sessão e a tela do campus (RF03.3 e RF03.4) e amplia comportamentos já entregues no MVP (a escolha do campus e da refeição padrão, nas RN04 e RN05, e o RNF03). O Backlog reúne o que fica sem release agendada.

O escopo restringe-se aos restaurantes universitários (RU) dos campi da UnB. O Restaurante Executivo do Campus Darcy Ribeiro não faz parte do escopo (RI08). Ele funciona no mesmo prédio do RU, com fila e cardápio próprios, e o sistema não trata nenhum dado sobre ele (RI08, L11).

### 1.3 Convenções deste documento

| Elemento | Convenção |
|---|---|
| ID de requisito funcional | `RF` + dois dígitos sequenciais, únicos em todo o documento (ex.: RF01, RF02, ...) |
| ID de subrequisito | `RFxx.y`: parte verificável de um RF (ex.: RF01.3). Quando há história correspondente no backlog, `RFxx.y` corresponde a `US-xx.y`. O RF que cobre um único comportamento não tem subrequisitos |
| ID de requisito não funcional | `RNF` + dois dígitos sequenciais (ex.: RNF01, RNF02, ...). O RNF07 tem itens `RNF07.y` |
| ID de requisito inverso | `RI` + dois dígitos sequenciais (ex.: RI01, RI02, ...) |
| ID de regra de negócio | `RN` + dois dígitos sequenciais (ex.: RN01, RN02, ...). As regras estão no Anexo B, e os requisitos as citam em vez de repeti-las |
| ID de limitação ou risco | `L` + dois dígitos sequenciais (ex.: L01, L02, ...) |
| Critério de aceite | Escrito em Dado/Quando/Então. Cada subrequisito tem um cenário (no máximo dois); o RF sem subrequisitos tem no máximo três (quatro no RF08). Os cenários citam os valores iniciais do Anexo A; se um valor mudar, o cenário acompanha |
| Release | MVP, Release 2 ou Backlog, conforme a alocação de cada requisito neste documento. O subrequisito herda a release do RF; quando difere, ela vem indicada no próprio subrequisito (ex.: RF03.3) |
| Prioridade | Derivada da alocação de release: **Essencial** (MVP), **Importante** (Release 2), **Desejável** (Backlog) |
| Origem | Épico e necessidade da parte interessada que o requisito atende. Quando o requisito resulta de uma decisão do grupo durante o refinamento do projeto, consta "decisão de projeto". A origem de cada RF está na Matriz de Rastreabilidade (Seção 6), e não nos blocos de requisito |
| Parâmetros configuráveis | Valores ajustáveis sem alterar o requisito (horários, raios, limiares) estão no Anexo A |
| Numeração e posição | Os IDs são únicos, seguem a ordem de criação e não mudam. Os requisitos acrescentados na Release 2 (RF18 a RF23) aparecem dentro do épico a que pertencem, e não ao fim do documento |

### 1.4 Documentos de referência

- Documento de Visão — Bandejão, Grupo 6, FCTE/UnB, 2026.
- FGA-EPS-MDS. *Documento de Visão — Projeto 2018.2-Lino*. Disponível em: https://github.com/fga-eps-mds/2018.2-Lino/blob/master/docs/documento-de-visao.md.
- Decanato de Assuntos Comunitários/UnB. *Resolução nº 002/2024 — Regimento de funcionamento do Restaurante Universitário da Universidade de Brasília*. Disponível em: https://ru.unb.br/images/Artigos/00DRUResolucao2024/SEI_11843224_Resolucao_002.pdf.
- Restaurante Universitário da UnB. *Cardápio semanal — Campus Gama, 21/9 a 27/9/2026* (exemplo do arquivo de cardápio lido pelo sistema).
- ADR 0001 — Escolha da stack de backend (`docs/adr/0001-escolha-stack-backend.md`).
- ADR 0002 — Matrícula e apelido extraídos do e-mail institucional (`docs/adr/0002-matricula-apelido-extraidos-do-email.md`).
- ADR 0009 — Detecção de campus feita no aparelho (`docs/adr/0009-deteccao-de-campus-no-aparelho.md`).
- ADR 0010 — Nível de fila calculado por chegadas, com espera estimada por saída da fila (`docs/adr/0010-nivel-por-chegadas-com-espera-estimada.md`).

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
| **Campus detectado** | Campus em que o dispositivo se encontra, identificado pela localização no início de uma sessão de uso (Release 2). Não é o mesmo que estar no RU: basta estar dentro da área do campus |
| **Check-in** | Registro de presença do usuário no RU de um campus durante uma refeição (Release 2). Junto com a saída da fila, é a fonte de dados da fila: ela é estimada exclusivamente a partir do que os próprios usuários informam sobre a sua presença e a sua saída da fila. Não há votação sobre o nível da fila nem sensores |
| **Nível de fila** | Classificação em quatro níveis: vazia, curta, moderada e longa. Aplica-se tanto à previsão de pico quanto ao nível agora |
| **Previsão de pico** | Estimativa do nível de fila esperado em cada faixa de horário de uma refeição. O nível é calculado exclusivamente a partir dos check-ins e pode vir acompanhado da espera estimada |
| **Nível agora** | Nível de fila atual da refeição em andamento, calculado a partir dos check-ins recentes (Backlog) |
| **Saída da fila** | Momento em que o usuário, depois de um check-in, deixa a fila e começa a comer, informado por ele mesmo ao responder a pergunta de saída da fila. É, junto com a desistência, o único desfecho posterior ao check-in registrado pelo sistema: o fim da refeição não é registrado |
| **Tempo de espera** | Intervalo entre o check-in e a saída da fila de um mesmo usuário em uma refeição. Só existe para check-ins que tiveram saída da fila informada |
| **Desistência** | Resposta do usuário à pergunta de saída da fila informando que desistiu de comer no RU depois de ter feito o check-in. Não gera saída da fila nem tempo de espera |
| **Pergunta de saída da fila** | Pergunta feita ao usuário, algum tempo depois do check-in, sobre se ele já saiu da fila e começou a comer. Sua resposta é a fonte da saída da fila |
| **Espera estimada** | Estimativa, em minutos, do tempo de espera em uma faixa de horário de uma refeição, calculada a partir do histórico de tempos de espera. Acompanha a previsão de pico quando há dados suficientes; não substitui o nível de fila |

### 1.6 Stack tecnológica

O backend é em Python, com Django REST Framework (DRF) para construir a API. O banco de dados é SQLite em desenvolvimento e MySQL em produção. A justificativa da escolha está na ADR 0001 (`docs/adr/0001-escolha-stack-backend.md`).

---

## 2. Requisitos Funcionais

Cada requisito funcional tem um identificador único, uma descrição curta, a release e a prioridade. Os critérios de aceite são escritos em Dado/Quando/Então. O RF que cobre mais de um comportamento independente é dividido em subrequisitos (`RFxx.y`), cada um com uma frase e um cenário de aceite. Regras detalhadas estão no Anexo B (RN01 a RN08) e valores ajustáveis, no Anexo A. A origem de cada requisito (épico e necessidade da parte interessada, ou decisão de projeto) está na Matriz de Rastreabilidade (Seção 6).

### Épico 1 — Login

#### RF01 — Cadastro de usuário

**Descrição:** O sistema deve permitir que uma pessoa da comunidade da UnB crie uma conta em duas etapas: a escolha do tipo de usuário (Estudante, Professor ou Servidor) e o preenchimento dos campos daquele tipo. O sistema confere apenas o formato da matrícula/SIAPE, não a existência nem a titularidade (L01).
**Release:** MVP · **Prioridade:** Essencial

**RF01.1 — Cadastro em duas etapas.** O sistema deve pedir primeiro o tipo de usuário e mostrar em seguida os campos correspondentes, deixando a conta pendente até a confirmação do e-mail (RF02).
- Dado que abro o cadastro, quando escolho "Estudante", então vejo os campos e-mail institucional, apelido e senha; quando escolho "Professor" ou "Servidor", então vejo os campos SIAPE/matrícula funcional, e-mail institucional e senha, no mesmo fluxo.
- Dado que informo uma senha com menos de 8 caracteres ou não confirmo ciência do aviso de privacidade (RNF07.1), quando envio, então o cadastro é rejeitado.

**RF01.2 — Cadastro de Estudante.** O sistema deve cadastrar o Estudante com apelido, senha e e-mail institucional no formato `matricula@aluno.unb.br`, extraindo a matrícula do e-mail (ADR 0002).
- Dado o e-mail `251098732@aluno.unb.br`, quando envio, então o sistema extrai a matrícula `251098732` e a valida conforme a RN01.
- Dado um e-mail fora do formato `matricula@aluno.unb.br` ou um apelido fora das regras da RN02, quando envio, então o cadastro é rejeitado com mensagem específica.

**RF01.3 — Validação do formato da matrícula de Estudante.** O sistema deve rejeitar matrículas de Estudante com formato impossível, conforme a RN01.
- Dado uma matrícula com 8 dígitos (L10), com letras ou pontuação, com prefixo fora do intervalo válido ou com os 6 dígitos finais em sequência óbvia (ex.: `123456`, `111111`), quando envio, então o cadastro é rejeitado com mensagem específica.
- Dado que o semestre corrente passa a ser outro, quando o sistema recalcula o intervalo de prefixos, então o novo código de semestre é aceito sem alteração de código.

**RF01.4 — Cadastro de Professor/Servidor.** O sistema deve cadastrar Professor/Servidor com SIAPE/matrícula funcional de 7 dígitos, e-mail institucional `@unb.br` e senha, gerando o apelido a partir do e-mail (RN02, ADR 0002).
- Dado o e-mail `maria.silva@unb.br` e um SIAPE de 7 dígitos, quando envio, então a conta é criada com o apelido `mariasilva`.
- Dado um SIAPE com formato diferente de 7 dígitos numéricos ou um e-mail fora do domínio `@unb.br`, quando envio, então o cadastro é rejeitado com mensagem específica.

**RF01.5 — Unicidade de matrícula/SIAPE, e-mail e apelido.** O sistema deve garantir que matrícula/SIAPE, e-mail institucional e apelido pertençam a uma única conta, confirmada ou pendente (RF02). O apelido é definido apenas no cadastro e não pode ser alterado depois.
- Dado que a matrícula/SIAPE ou o e-mail já está associado a outra conta, confirmada ou pendente, quando envio, então o cadastro é rejeitado com mensagem de erro específica.
- Dado que o apelido digitado já existe (sem distinguir maiúsculas e minúsculas), quando envio, então o cadastro é rejeitado; dado que o apelido gerado a partir do e-mail de Professor/Servidor já está em uso ou fora do tamanho (RN02), então o formulário pede um apelido digitado.

---

#### RF02 — Confirmação de e-mail

**Descrição:** O sistema deve enviar ao e-mail institucional informado no cadastro um link de confirmação. A conta só pode se autenticar depois de confirmar o e-mail, que é o único canal de recuperação de senha (RF04).
**Release:** MVP · **Prioridade:** Essencial

**RF02.1 — Confirmação por link.** O sistema deve ativar a conta quando o usuário abrir o link de confirmação, de uso único e com validade conforme o Anexo A.
- Dado um link ainda não usado, aberto dentro de 24 horas, quando o confirmo, então a conta passa a poder se autenticar (RF03).
- Dado um link expirado ou já usado, quando o abro, então a confirmação é recusada e posso pedir um novo link (RF02.2).

**RF02.2 — Reenvio do link.** O sistema deve permitir que o usuário com cadastro pendente peça um novo link dentro do prazo, o que renova a validade.
- Dado um cadastro pendente dentro das 24 horas, quando peço o reenvio, então um novo link é enviado e o prazo de 24 horas recomeça.
- Dado matrícula/SIAPE e senha corretas em conta ainda não confirmada, quando tento entrar, então o login é recusado com orientação para confirmar o e-mail e a opção de reenviar o link.

**RF02.3 — Exclusão de cadastro pendente expirado.** O sistema deve excluir o cadastro que não for confirmado dentro do prazo, liberando a matrícula/SIAPE e o e-mail para novo cadastro.
- Dado um cadastro pendente sem confirmação nem reenvio por mais de 24 horas, quando o prazo vence, então o cadastro é excluído e a matrícula/SIAPE e o e-mail ficam livres.

---

#### RF03 — Login de usuário cadastrado

**Descrição:** O sistema deve permitir que o usuário com conta confirmada se autentique com matrícula ou SIAPE e senha.
**Release:** MVP · **Prioridade:** Essencial

**RF03.1 — Login com identificador único.** O sistema deve aceitar matrícula ou SIAPE no mesmo campo, identificando o tipo pela quantidade de dígitos (RN01), sem revelar se a conta existe.
- Dado credenciais corretas de conta confirmada, quando entro, então a sessão é iniciada e sou levado à página inicial.
- Dado que informo credenciais incorretas, quando envio, então vejo uma mensagem genérica, sem indicar se a matrícula/SIAPE existe.

**RF03.2 — Bloqueio após tentativas malsucedidas.** O sistema deve bloquear novas tentativas de login após falhas consecutivas (Anexo A).
- Dado 5 tentativas malsucedidas consecutivas para o mesmo identificador em 10 minutos, quando faço a 6ª, então novas tentativas ficam bloqueadas por 10 minutos.

**RF03.3 — Sair da conta.** *(Release 2 · Importante)* O sistema deve permitir que o usuário encerre a sessão.
- Dado que estou logado, quando toco em "Sair", então a sessão termina e volto a navegar como Visitante.

**RF03.4 — Tela do campus após o login.** *(Release 2 · Importante)* O sistema deve levar o usuário, depois do login, à tela do campus (RF20), sem passo adicional.
- Dado credenciais corretas, quando entro, então vejo a tela do campus já resolvido conforme a RN04.

---

#### RF04 — Recuperação de senha

**Descrição:** O sistema deve permitir que um usuário que perdeu a senha defina uma nova, por meio de um link enviado ao e-mail cadastrado. Sem acesso a esse e-mail, não há recuperação de senha no MVP (L07).
**Release:** MVP · **Prioridade:** Essencial

**RF04.1 — Solicitar redefinição.** O sistema deve enviar o link de redefinição ao e-mail da conta identificada pela matrícula/SIAPE, sem revelar se a conta existe, e limitar as solicitações (Anexo A).
- Dado que informo uma matrícula/SIAPE, quando peço a redefinição, então a resposta é sempre "se houver conta, enviaremos o e-mail", exista ou não a conta.
- Dado 3 solicitações na última hora para a mesma matrícula/SIAPE, quando peço a 4ª, então nenhum e-mail é enviado.

**RF04.2 — Redefinir pelo link.** O sistema deve permitir definir a nova senha por um link de uso único, válido por 1 hora (Anexo A), e encerrar as sessões ativas da conta.
- Dado um link válido, quando defino uma nova senha com pelo menos 8 caracteres, então a senha anterior deixa de valer e as sessões ativas da conta são encerradas.
- Dado um link expirado ou já usado, quando tento redefinir, então a redefinição é recusada e posso pedir outro link.

---

#### RF05 — Navegação sem autenticação

**Descrição:** O sistema deve permitir que qualquer visitante, sem cadastro ou login, consulte o cardápio diário/semanal dos campi.
**Release:** MVP · **Prioridade:** Essencial

**Critérios de aceite:**
- Dado que não estou logado, quando acesso a URL raiz do sistema, então vejo o cardápio sem que seja exigida autenticação.
- Dado que não estou logado, quando aciono uma função que exige conta (avaliar refeição ou, na Release 2, fazer check-in), então vejo um convite ao cadastro/login, e não um erro genérico.

---

### Épico 2 — Visualização do Cardápio

#### RF06 — Leitura automatizada do arquivo de cardápio

**Descrição:** O sistema deve extrair automaticamente o cardápio do arquivo PDF semanal publicado no site oficial do RU para cada campus (uma página por refeição: café da manhã, almoço e jantar), incluindo categorias, pratos, marcadores e linhas de dieta, sem intervenção manual da equipe em condições normais de publicação.
**Release:** MVP · **Prioridade:** Essencial

**RF06.1 — Download e atualização semanal.** O sistema deve obter o PDF de cada campus e atualizar o cardápio exibido em até 24 horas depois de uma nova publicação.
- Dado que o RU publica um novo PDF para um campus, quando o sistema o processa, então o cardápio exibido é atualizado em até 24 horas.

**RF06.2 — Categorias, pratos e dietas.** O sistema deve extrair do PDF as categorias, os pratos e as linhas de dieta, respeitando os dias e as refeições servidos em cada campus.
- Dado o PDF de um campus, quando lido, então só existem as refeições e os dias que constam nele (por exemplo, almoço de sábado quando presente).
- Dado o texto "Arroz branco OU arroz integral", quando lido, então vira dois pratos; dado "Feijão carioca/preto", então continua um prato só ("ou/OU" separa pratos; "/" não separa).

**RF06.3 — Marcadores e validação da legenda.** O sistema deve associar a cada prato os marcadores cujos ícones aparecem junto a ele e validar que a legenda do arquivo contém exatamente os 10 marcadores conhecidos. Os ícones são imagens sobrepostas ao texto, fora da camada de texto do PDF: a associação é feita pela posição e a identificação, pela legenda.
- Dado os ícones de uma refeição, quando lidos, então cada prato fica associado aos marcadores cujos ícones aparecem junto a ele (opções separadas por "ou" têm cada uma os seus).
- Dado um ícone desconhecido, ou ícones que não podem ser associados a pratos, quando a refeição é lida, então o cardápio é publicado só em texto, a refeição fica marcada como "informação de alérgenos indisponível" (filtro de marcadores desativado, RF08) e a equipe recebe um alerta (RF06.5).

**RF06.4 — Manter o último cardápio válido.** O sistema deve continuar exibindo o último cardápio lido com sucesso quando a leitura falhar (RNF02).
- Dado que a leitura do texto falha (por exemplo, por mudança no formato do arquivo), quando isso ocorre, então o último cardápio lido com sucesso continua em exibição, sem página vazia ou quebrada, e a equipe recebe um alerta (RF06.5).

**RF06.5 — Alerta de falha à equipe.** O sistema deve alertar a equipe quando a leitura do cardápio falhar ou quando uma refeição ficar sem informação de alérgenos (ADR 0006).
- Dado uma falha de leitura ou uma refeição marcada como "informação de alérgenos indisponível", quando isso ocorre, então a equipe recebe um alerta.

---

#### RF07 — Exibição do cardápio por campus, refeição e dia

**Descrição:** O sistema deve permitir que o usuário, logado ou não, escolha o campus e exibir o cardápio de uma refeição de um dia por vez, com apresentação voltada a dispositivos móveis. As categorias aparecem em lista hierarquizada; a tabela do PDF não é reproduzida.
**Release:** MVP · **Prioridade:** Essencial

**RF07.1 — Exibição por refeição e dia.** O sistema deve exibir o cardápio de uma refeição por vez, com seletor de refeição e navegação entre os dias da semana vigente, definida pelas datas do PDF do campus. A semana seguinte é tratada no RF18.
- Dado o cardápio de um campus, quando troco de dia pelas abas (ou equivalente), então o cardápio do dia aparece sem recarregar a página inteira, e o seletor de refeição oferece só as refeições que o PDF traz para aquele campus e dia.
- Dado qualquer cardápio exibido, quando o consulto, então vejo o aviso de que está sujeito a alteração, categorias em lista hierarquizada com as linhas de dieta em destaque, e a tela é funcional a partir de 360 px, validada por revisão de design da equipe.

**RF07.2 — Campus escolhido e lembrado.** O sistema deve permitir escolher e trocar o campus a qualquer momento e lembrar no aparelho, sem login, o último campus escolhido manualmente (RN04).
- Dado que escolhi um campus, quando volto ao sistema, então o campus continua lembrado e o cardápio dele abre sem interação adicional.
- Dado dois campi distintos, quando alterno entre eles, então vejo um cardápio diferente para cada um.

**RF07.3 — Refeição padrão e cardápio ainda não publicado.** O sistema deve abrir a refeição padrão definida na RN05 e informar quando o campus ainda não tem cardápio publicado para a semana.
- Dado o horário atual (Anexo A), quando o cardápio abre, então é exibida a refeição padrão da RN05.
- Dado um campus sem cardápio publicado para a semana, quando o abro, então vejo "cardápio ainda não publicado".

---

#### RF08 — Filtro de marcadores alimentares

**Descrição:** O sistema deve permitir que o usuário escolha, entre os 10 marcadores do cardápio oficial (ver Marcador, 1.5), quais deseja evitar, sinalizando os pratos que os contêm.
**Release:** MVP · **Prioridade:** Essencial

**Critérios de aceite:**
- Dado que seleciono "leite e derivados", quando o cardápio é exibido, então os pratos com esse marcador permanecem visíveis e exibem "Contém: leite e derivados", e uma categoria em que todos os pratos têm marcador selecionado exibe "sem opção compatível".
- Dado que selecionei marcadores, quando troco de dia, de refeição ou de campus, ou reabro o sistema, então a seleção continua ativa (lembrada no aparelho).
- Dado uma refeição marcada como "informação de alérgenos indisponível" (RF06.3), quando exibida, então o filtro fica desativado e informa o motivo.
- Dado o filtro exibido, quando o consulto, então um aviso fixo informa que ele se baseia no cardápio oficial, sujeito a alteração, que a ausência de marcador não garante que o prato esteja livre do ingrediente e que peixe e frutos do mar não são marcados (L04).

---

#### RF09 — Filtro de dieta

**Descrição:** O sistema deve permitir que o usuário escolha uma dieta ("Sem filtro", "Ovolactovegetariano" ou "Vegetariano estrito") e exiba as linhas de prato compatíveis do cardápio.
**Release:** MVP · **Prioridade:** Essencial

**Critérios de aceite:**
- Dado "Ovolactovegetariano", quando aplicado, então aparecem as linhas ovolactovegetariana e vegetariana estrita e a linha padrão é ocultada; com "Vegetariano estrito", aparece só a linha vegetariana estrita.
- Dado qualquer dieta aplicada, quando o cardápio é exibido, então as demais categorias (saladas, guarnição, sopa etc.) continuam visíveis, e o botão "mostrar todas" reverte o filtro temporariamente.
- Dado que escolhi uma dieta, quando troco de dia, de refeição ou de campus, então ela continua ativa (lembrada no aparelho) e pode ser combinada com o filtro de marcadores (RF08).

---

#### RF10 — Ícones de indicação de marcadores

**Descrição:** O sistema deve exibir, ao lado de cada prato, os ícones dos marcadores que ele contém, independentemente de qualquer filtro ativo. Os ícones serão definidos com a equipe de frontend, para evitar a criação de novos ícones a cada cardápio.
**Release:** Backlog · **Prioridade:** Desejável

**Critérios de aceite:**
- Dado um prato com um ou mais marcadores, quando exibido, então os ícones correspondentes aparecem ao lado dele, sem necessidade de hover ou clique.

---

#### RF18 — Exibição do cardápio da semana seguinte

**Descrição:** O sistema deve exibir, além da semana vigente (RF07), os dias e as refeições da semana seguinte de um campus assim que o RU publicar o PDF correspondente, na mesma navegação por abas do RF07.1. Não há antecedência mínima de publicação: a aba depende apenas da leitura bem-sucedida do PDF (RF06).
**Release:** Release 2 · **Prioridade:** Importante

**Critérios de aceite:**
- Dado que o PDF da semana seguinte de um campus foi lido com sucesso, quando abro o cardápio, então aparece a aba da semana seguinte, na mesma navegação por abas e sem recarregar a página inteira.
- Dado que o PDF da semana seguinte ainda não foi lido, quando abro o cardápio, então só a semana vigente aparece.

---

#### RF19 — Aviso e permissão de localização

**Descrição:** O sistema deve pedir ao usuário, logado ou não, permissão para usar a localização do dispositivo, a fim de identificar o campus (RF20) e confirmar o check-in (RF12), em duas etapas: uma tela do próprio Bandejão e, se a pessoa aceitar, o pedido do navegador. O aviso também fica disponível em um ponto fixo da interface ("Usar minha localização").
**Release:** Release 2 · **Prioridade:** Importante

**Critérios de aceite:**
- Dado o primeiro acesso em um aparelho, como visitante ou logado, quando o sistema abre, então vejo o aviso do Bandejão com "Permitir" e "Agora não", explicando que a localização identifica o campus (coordenadas não saem do aparelho) e confirma o check-in (coordenadas descartadas após a conferência, RI09).
- Dado o aviso exibido, quando escolho "Permitir", então o navegador pede a permissão; quando escolho "Agora não", então o navegador não é acionado, o sistema segue com o campus lembrado ou o seletor (RN04) e o aviso não reaparece a cada abertura do app.
- Dado que tento fazer check-in sem permissão de localização, quando toco em "Fazer check-in", então vejo o aviso de novo ou, se o navegador já bloqueou, um passo a passo para liberar a localização; a recusa não impede o uso do cardápio, das avaliações nem da previsão.

---

#### RF20 — Detecção de campus e tela do campus

**Descrição:** O sistema deve identificar, pela localização do dispositivo, em qual campus a pessoa está e abrir a tela desse campus com as informações de que ela precisa (cardápio, avaliações e, quando houver dados, previsão de pico e espera estimada), para reduzir o número de toques até a informação. Vale para o visitante e para o usuário logado.
**Release:** Release 2 · **Prioridade:** Importante

**RF20.1 — Detecção no aparelho.** O sistema deve detectar o campus no aparelho, ao abrir o app e ao voltar ao primeiro plano depois do tempo parado do Anexo A, com permissão de localização (RF19). O raio de detecção é diferente do raio de confirmação do check-in (RF12).
- Dado que há permissão de localização, quando abro o app dentro do raio de detecção de um campus, então o campus é detectado no aparelho e o servidor recebe apenas o identificador do campus, nunca as coordenadas (RI09, ADR 0009).

**RF20.2 — Campus exibido.** O sistema deve exibir o campus conforme a RN04, abrindo de imediato com o campus lembrado (ou o seletor) enquanto a detecção corre em paralelo. A tela mostra o nome do campus com a opção "trocar" e, se ele veio da localização, indica isso.
- Dado que a detecção aponta um campus diferente do exibido, quando ela termina, então o app troca de campus e exibe um aviso com a opção de voltar ao anterior (ex.: "Você está no Campus Darcy Ribeiro · voltar para Gama").
- Dado que não há permissão, que o GPS está indisponível, que a leitura não atende à RN03 ou que estou fora do raio de qualquer campus, quando abro o app, então vale o campus lembrado ou, na falta dele, o seletor de campus.

**RF20.3 — Conteúdo da tela e refeição padrão.** O sistema deve mostrar uma refeição por vez (a padrão da RN05), com cardápio, nota média, quantidade de avaliações, comentários (RF15.2) e, quando existirem, previsão de pico e espera estimada (RF13, RF22); as demais refeições do dia ficam no seletor, cada uma com sua nota média.
- Dado a tela do campus, quando abre, então ela mostra a refeição padrão (RN05) com cardápio, nota média, avaliações e, quando existirem, previsão de pico e espera estimada.
- Dado que todas as refeições do dia já terminaram, quando abro a tela até as 23h59, então vejo a última refeição do dia, com a avaliação aberta (RF15.1) e a indicação "refeição encerrada" no lugar da previsão e do check-in.

**RF20.4 — Aviso sobre o Restaurante Executivo.** O sistema deve exibir, quando o campus exibido for o Darcy Ribeiro, uma linha fixa de texto, sem pop-up nem botão de fechar, informando que as informações são apenas do RU e não valem para o Restaurante Executivo (RI08, L11). Vale para visitante e logado e não se repete na tela de check-in.
- Dado que o campus exibido é o Darcy Ribeiro, seja por detecção, escolha manual ou campus lembrado, quando a tela abre, então vejo a linha fixa do aviso.

---

### Épico 3 — Visualização da Fila e Previsão de Pico

Todos os requisitos deste épico pertencem à Release 2 ou ao Backlog; o MVP não inclui funcionalidade de fila. A fila é estimada exclusivamente a partir de dados que os próprios usuários informam sobre a sua presença (check-in) e a sua saída da fila. Não há votação sobre o nível da fila nem sensores (RI05).

#### RF11 — Check-in no RU

**Descrição:** O sistema deve permitir que um usuário autenticado registre sua presença no RU do campus escolhido durante uma refeição (check-in), uma vez por refeição por dia. O check-in só vale depois da confirmação de localização (RF12) e não pode ser desfeito. Quem já tinha conta antes da Release 2 só faz o primeiro check-in depois de dar ciência ao aviso de privacidade atualizado (RNF07.1).
**Release:** Release 2 · **Prioridade:** Importante

**Critérios de aceite:**
- Dado que estou logado, dentro do horário da refeição (Anexo A) e com a localização confirmada (RF12), quando faço o check-in, então ele é registrado e a pergunta de saída da fila fica pendente (RF21.1).
- Dado que já fiz check-in nessa refeição hoje (RI03) ou que estou fora do horário da refeição, quando tento, então o check-in é rejeitado com mensagem informativa (no segundo caso, com o horário da refeição).
- Dado que sou visitante, quando tento fazer check-in, então recebo o convite ao cadastro/login (RF05).

---

#### RF12 — Confirmação de check-in por GPS

**Descrição:** O sistema deve utilizar a localização do dispositivo para confirmar que o usuário está nas imediações do RU do campus escolhido; somente então o check-in é aceito. Sem permissão de localização, o check-in não é possível (RF19). No Campus Darcy Ribeiro, o RU e o Restaurante Executivo funcionam no mesmo prédio e o GPS não os distingue (L11).
**Release:** Release 2 · **Prioridade:** Importante

**Critérios de aceite:**
- Dado que a posição está dentro do raio de confirmação do RU do campus escolhido (Anexo A) e atende à RN03, quando envio o check-in, então ele é confirmado.
- Dado que a posição está fora do raio, inclusive no RU de outro campus, ou que não atende à RN03, quando envio o check-in, então ele é rejeitado com mensagem informando que a localização não pôde ser confirmada (ou lida com precisão suficiente).
- Dado qualquer desfecho da conferência, quando ela termina, então as coordenadas foram descartadas e não ficam armazenadas (RI09), e a tentativa registra usuário, campus, refeição, data/hora e resultado (confirmado ou rejeitado), com vínculo à conta pelo prazo do RNF07.3.

---

#### RF13 — Previsão de pico por faixa de horário

**Descrição:** O sistema deve exibir, para a refeição, o campus e o dia escolhidos, o nível de fila esperado em cada faixa de 15 minutos (vazia, curta, moderada ou longa), calculado exclusivamente a partir dos check-ins confirmados, e destacar a faixa de maior movimento (pico). Quando há dados suficientes, cada faixa também mostra a espera estimada (RF22). A previsão pode ser consultada sem login.
**Release:** Release 2 · **Prioridade:** Importante

**Critérios de aceite:**
- Dado campus, refeição e dia escolhidos, quando abro a previsão, sem login, então vejo as faixas de 15 minutos cobrindo o horário da refeição (Anexo A), cada uma com seu nível (RN06), e a faixa de maior movimento destacada como pico.
- Dado check-ins em pelo menos 3 dias distintos dentro da janela de 4 semanas (Anexo A), quando abro a previsão, então ela é exibida; com menos dados, vejo "dados insuficientes", sem valor de reserva.
- Dado que há respostas à pergunta de saída da fila, quando o nível é calculado, então ele não muda: só os check-ins o determinam, e as respostas apenas alimentam a espera estimada (RF22).

---

#### RF14 — Nível de fila em tempo real ("agora")

**Descrição:** O sistema deve exibir o nível de fila atual (vazia, curta, moderada ou longa) da refeição em andamento, com base nos check-ins recentes.
**Release:** Backlog · **Prioridade:** Desejável

**Critérios de aceite:**
- Dado uma refeição em andamento, quando consulto o nível agora, então vejo um dos quatro níveis da RN06, calculado com os check-ins recentes. A janela e os limiares serão definidos quando o item for priorizado, considerando o risco de indicar "vazia" por baixa adesão dos usuários (L08).

---

#### RF21 — Pergunta de saída da fila

**Descrição:** O sistema deve perguntar ao usuário, algum tempo depois do check-in, se já saiu da fila e começou a comer, para registrar a saída e calcular o tempo de espera. A pergunta é um pop-up dentro do app, de resposta em um toque, e só o autor do check-in a recebe (RI01). O sistema não pergunta nem registra o fim da refeição.
**Release:** Release 2 · **Prioridade:** Importante

**RF21.1 — Registro e exibição da pergunta.** O sistema deve registrar no servidor uma pergunta pendente ao confirmar o check-in e exibi-la como pop-up quando o app estiver em primeiro plano e a hora prevista tiver passado, em qualquer aparelho em que o usuário esteja logado. Uma notificação push poderá ser acrescentada depois sem alterar o registro (RF23).
- Dado um check-in confirmado, quando passa o tempo até a primeira pergunta (Anexo A) com o app em primeiro plano, então o pop-up aparece, só para o autor do check-in, em qualquer aparelho em que ele esteja logado.

**RF21.2 — Respostas, repetição e expiração.** O sistema deve oferecer cinco respostas (RN07), repetir a pergunta uma vez se a resposta for "Ainda estou na fila", encerrá-la depois da expiração (Anexo A) e registrar cada resposta com a data/hora do servidor. Na desistência, o check-in continua contando no nível (RF13), mas não gera saída da fila nem tempo de espera (RN07).
- Dado o pop-up da pergunta, quando escolho uma das cinco respostas, então ela é registrada com a data/hora do servidor; com "Ainda estou na fila", a pergunta é repetida uma vez, após o intervalo do Anexo A.
- Dado que a pergunta expirou ou que fechei o pop-up sem responder, quando o app é aberto de novo, então a pergunta não aparece mais nem aceita resposta (exceto a repetição prevista).

---

#### RF22 — Espera estimada por faixa de horário

**Descrição:** O sistema deve exibir, junto à previsão de pico, a espera estimada em minutos para cada faixa em que houver dados suficientes, calculada a partir dos tempos de espera informados pelos usuários (RF21), para dar o tempo que a pessoa provavelmente vai gastar na fila, e não apenas um nível relativo. O visitante pode consultar a espera estimada.
**Release:** Release 2 · **Prioridade:** Importante

**RF22.1 — Cálculo do tempo de espera e da espera estimada.** O sistema deve calcular o tempo de espera de cada check-in a partir da resposta à pergunta de saída da fila (RN07) e a espera estimada da faixa como a mediana desses tempos na janela de histórico (RN08).
- Dado um check-in respondido 20 minutos depois com "Saí da fila há 5 a 10 min", quando o tempo de espera é calculado, então ele é de 12,5 minutos (a saída é situada 7,5 minutos antes da resposta).
- Dado a resposta "Saí da fila há mais de 10 min", uma desistência ou ausência de resposta, quando o tempo de espera é calculado, então não é gerado tempo de espera.

**RF22.2 — Exibição da espera estimada.** O sistema deve exibir a espera estimada em destaque nas faixas com dados suficientes (RN08) e só o nível nas demais, com um texto de apoio sobre a natureza da estimativa (L12).
- Dado uma faixa com dados suficientes e a previsão do RF13 exibida, quando abro a previsão, então os minutos aparecem em destaque e o nível aparece como cor ou rótulo; as faixas sem dados suficientes mostram só o nível.
- Dado a tela com espera estimada, quando a consulto, então um texto de apoio explica que o nível é relativo ao pico do dia, que os minutos são a espera típica observada e que é uma estimativa que pode ficar abaixo da realidade (L12).

---

#### RF23 — Notificação push da pergunta de saída da fila

**Descrição:** O sistema deve enviar uma notificação ao dispositivo do usuário quando a pergunta de saída da fila (RF21) estiver pronta, mesmo com o app fechado, para aumentar as respostas. A permissão de notificação é pedida em momento próprio, separado da de localização (RF19), e a inscrição do dispositivo é dado pessoal (RNF07). No iOS (16.4 ou superior), só funciona com o PWA instalado; sem ele, a pergunta aparece só dentro do app (RF21).
**Release:** Backlog · **Prioridade:** Desejável

**Critérios de aceite:**
- Dado uma pergunta pendente e uma inscrição ativa, quando chega a hora prevista, então o dispositivo recebe a notificação, mesmo com o app fechado, e tocar nela abre o app na pergunta pendente.
- Dado que recuso a permissão de notificação, quando uso o sistema, então tudo funciona normalmente e a pergunta aparece dentro do app (RF21).
- Dado uma inscrição ativa, quando a cancelo, então deixo de receber notificações.

---

### Épico 4 — Avaliação das Refeições

#### RF15 — Avaliação de refeição por estrelas e comentário

**Descrição:** O sistema deve permitir que um usuário autenticado avalie uma refeição (campus + dia + tipo de refeição) com uma nota de 1 a 5 estrelas e, opcionalmente, um comentário em texto livre que pode citar pratos ou ingredientes. A avaliação é exibida publicamente com o apelido do autor. Não há nota por prato.
**Release:** MVP · **Prioridade:** Essencial

**RF15.1 — Avaliar a refeição.** O sistema deve exigir a nota e aceitar comentário opcional de até 500 caracteres, apenas para refeições do dia corrente que já começaram (Anexo A), com uma avaliação por usuário por refeição, editável até as 23h59 do mesmo dia.
- Dado que estou logado e a refeição do dia já começou, quando envio nota de 1 a 5 e comentário opcional de até 500 caracteres, então a avaliação é salva ligada à minha conta; sem nota, ou com comentário maior que o limite, é rejeitada.
- Dado que já avaliei a refeição, quando avalio de novo até as 23h59 do mesmo dia, então a avaliação anterior é editada, não duplicada; dado uma refeição de outro dia ou que ainda não começou, então a avaliação fica indisponível e o sistema informa o motivo.

**RF15.2 — Ver as avaliações da refeição.** O sistema deve exibir, junto ao cardápio de cada refeição da semana vigente, a nota média, a quantidade de avaliações e os comentários com o apelido do autor, para qualquer visitante. Matrícula/SIAPE e e-mail nunca são exibidos (RI10). Avaliações de semanas anteriores deixam de ser exibidas na interface, mas permanecem armazenadas, sem limite de retenção (L09).
- Dado uma refeição da semana vigente, inclusive de dias passados, quando exibida, então vejo a nota média, a quantidade de avaliações e os comentários com apelido, mesmo sem login; sem avaliações, vejo "sem avaliações ainda".
- Dado qualquer exibição de avaliações, quando a inspeciono, então não aparecem matrícula/SIAPE nem e-mail do autor.

---

#### RF16 — Histórico de refeições anteriores

**Descrição:** O sistema deve disponibilizar uma tela dedicada para consultar refeições de semanas anteriores, com o cardápio, a nota média e os comentários de cada uma.
**Release:** Release 2 · **Prioridade:** Importante

**Critérios de aceite:**
- Dado a tela de histórico, quando navego por campus, data e refeição de semanas anteriores, então vejo cardápio, nota média e comentários, em modo somente leitura (não é possível avaliar refeições passadas).
- Dado uma refeição sem avaliações, quando exibida, então vejo "sem avaliações ainda".
- Dado uma data anterior à primeira leitura de cardápio feita pelo sistema, quando a procuro, então ela não está disponível (não há carga de PDFs anteriores).

---

### Transversal

#### RF17 — Design e identidade visual do site

**Descrição:** O sistema deve seguir uma distribuição de informações e paleta de cores definidas e consistentes em todas as telas, garantindo identidade visual coesa ao produto.
**Release:** MVP · **Prioridade:** Essencial

**Critérios de aceite:**
- Dado o guia de estilo da equipe, quando comparo todas as telas do sistema lado a lado, então todas usam a mesma paleta de cores e os mesmos padrões de tipografia e espaçamento.

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

Um visitante deve conseguir visualizar o cardápio de um campus em **no máximo 3 interações** (cliques/toques) na primeira visita. Nas visitas seguintes, o campus escolhido fica lembrado no aparelho e o cardápio abre sem interação adicional. A interface deve ser funcional em telas a partir de **360px de largura**, compatível com o caráter PWA/mobile do produto.

**Release 2:** na primeira visita, as etapas do aviso de localização (RF19) e do pedido do navegador contam como interações: com permissão, são 2 interações até o cardápio do campus detectado; sem permissão, "Agora não" e a escolha do campus também somam 2. Nas visitas seguintes, o cardápio abre sem interação, com o campus resolvido pela RN04, sem esperar a leitura da localização.

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

O código-fonte deve manter cobertura de testes automatizados de, no mínimo, **60% nos módulos críticos** (leitura de cardápio, incluindo a leitura dos ícones de marcadores; cadastro e autenticação; avaliação de refeições e, na Release 2, detecção de campus, check-in, pergunta de saída da fila e previsão de pico com espera estimada), e a arquitetura deve separar claramente esses módulos, de modo que uma mudança no formato do PDF do cardápio exija alteração apenas no módulo de leitura de cardápio. No backend em Django REST Framework (1.6, ADR 0001), essa separação se reflete em apps Django distintos por recurso (ex.: cadastro/autenticação, cardápio, avaliação, fila), cada um com seu próprio conjunto de models, serializers, views e URLs.

**Justificativa:** meta de cobertura de testes compatível com uma equipe sem experiência prévia em projetos de grande porte, mas suficiente para reduzir o risco já identificado de dependência do PDF externo e de inexperiência da equipe com as tecnologias escolhidas.

---

#### RNF07 — Privacidade e proteção de dados pessoais

O sistema deve tratar como dados pessoais a matrícula/SIAPE, o e-mail, o apelido e, na Release 2, os registros de check-in e de saída da fila ligados à conta, conforme a Lei Geral de Proteção de Dados (Lei nº 13.709/2018). A localização não é armazenada (RI09).

- **RNF07.1 Finalidade:** os dados são coletados só para as finalidades do aviso de privacidade (login, recuperação de senha, identificação do autor de avaliações e, na Release 2, estimativa da fila e uso da localização). Quem já tinha conta vê o aviso atualizado uma vez, no login seguinte (efeito sobre o check-in no RF11).
- **RNF07.2 Acesso:** a matrícula/SIAPE é armazenada de forma recuperável pela equipe (não como hash), com acesso restrito à equipe.
- **RNF07.3 Retenção:** o vínculo dos registros de check-in, de tentativas e de respostas com a conta dura a janela de 4 semanas (Anexo A); depois, resta só o registro anônimo (campus, refeição, data, faixa e tempo de espera).
- **RNF07.4 Exclusão:** a conta é excluída por solicitação à equipe; as avaliações permanecem como "usuário removido" e o vínculo dos registros de fila é removido na hora.

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
| **RI05** | O sistema não deve depender de sensores físicos (câmeras, contadores de pessoas) nem de votação dos usuários sobre o nível da fila para estimar a fila. A fila é estimada exclusivamente a partir de dados que os próprios usuários informam sobre a sua presença (check-in) e a sua saída da fila. |
| **RI06** | O sistema não deve bloquear o acesso à visualização do cardápio para usuários que optem por não se cadastrar. |
| **RI07** | O sistema não deve permitir cadastro sem matrícula ou SIAPE em formato válido; terceirizados e demais pessoas sem esses identificadores ficam fora do público de cadastro. |
| **RI08** | O sistema não deve exibir cardápio, avaliações ou informações de fila do Restaurante Executivo do Campus Darcy Ribeiro, que não faz parte do escopo do projeto. Isso vale mesmo funcionando o Executivo no mesmo prédio do RU, com fila e cardápio próprios: o sistema não trata nenhum dado sobre ele e, quando o campus exibido é o Darcy Ribeiro, a tela do campus informa que os dados são apenas do RU (RF20.4). |
| **RI09** | O sistema não deve armazenar as coordenadas de localização do usuário. Na detecção de campus (RF20.1), as coordenadas não saem do aparelho; no check-in (RF12), são enviadas ao servidor apenas para a conferência e descartadas em seguida. |
| **RI10** | O sistema não deve exibir a matrícula/SIAPE ou o e-mail de um usuário a outros usuários. |

---

## 5. Limitações e Riscos Conhecidos

| ID | Limitação ou risco | Mitigação |
|---|---|---|
| **L01** | **Matrícula alheia ou inventada.** O sistema confere só o formato da matrícula/SIAPE. Alguém pode cadastrar a matrícula de outra pessoa, que ficará sem poder se cadastrar, ou uma matrícula inventada de formato válido. | E-mail único e confirmado (RF02), rastreabilidade (RNF08). Matrícula contestada é resolvida manualmente pela equipe. |
| **L02** | **Contas múltiplas ou falsas.** Uma pessoa pode criar várias contas, inclusive por ter mais de uma vinculação (por exemplo, matrícula de aluno e SIAPE). Isso distorce a nota média das avaliações já no MVP e a previsão de pico na Release 2. | Para as avaliações: e-mail único e confirmado (RF02), rastreabilidade e moderação (RNF08). Para a previsão de pico: confirmação por GPS (RF12), um check-in por refeição (RI03), e-mail único. |
| **L03** | **Leitura dos ícones de marcadores.** Os ícones são imagens; a associação a pratos pode falhar. | Validação da legenda, refeição marcada como "informação de alérgenos indisponível" e alerta à equipe (RF06.3 e RF06.5). |
| **L04** | **Os filtros são auxiliares.** A ausência de marcador não garante que o prato esteja livre do ingrediente; o cardápio oficial não marca peixe nem frutos do mar e está sujeito a alteração. | Aviso fixo junto ao filtro (RF08); pratos com marcador permanecem visíveis com alerta. |
| **L05** | **Parâmetros mantidos manualmente.** Horários das refeições, raios de GPS e limites de leitura da localização dependem de definição e atualização pela equipe; os horários podem mudar, e os raios precisam ser validados em campo, porque a precisão do GPS em ambiente fechado varia. | Tabela de configuração (Anexo A) revisada pela equipe; teste em campo antes de fixar os raios. |
| **L06** | **Avaliação sem prova de presença.** No MVP, qualquer usuário autenticado pode avaliar uma refeição do dia depois que ela começou, sem comprovar que comeu. | O check-in (Release 2) permanece independente da avaliação. |
| **L07** | **Recuperação de senha depende do e-mail.** Sem acesso ao e-mail cadastrado, o usuário não recupera a conta no MVP. | Confirmação do e-mail no cadastro (RF02). |
| **L08** | **Baixa adesão ao check-in e à pergunta de saída da fila.** A previsão depende de os usuários fazerem check-in, e a espera estimada, de responderem à pergunta de saída da fila, que só aparece com o app aberto e tende a ser menos respondida que o check-in. Com pouca adesão, ambas são pouco representativas. | Exibição de "dados insuficientes" abaixo do mínimo de dados (RF13); espera estimada só com o mínimo de respostas (RF22), senão só o nível; nível "agora" mantido no Backlog (RF14); notificação push no Backlog (RF23). |
| **L09** | **Avaliações de semanas anteriores.** No MVP, elas não são exibidas na interface, embora permaneçam armazenadas. | Histórico de refeições na Release 2 (RF16). |
| **L10** | **Matrícula de estudante com menos de 9 dígitos não suportada.** O sistema só aceita matrícula de estudante com exatamente 9 dígitos (padrão em uso desde 2010). Estudantes com matrícula de 8 dígitos (anterior a 2010) não conseguem se cadastrar nesta fase. | Decisão de projeto consciente de adiar o tratamento desse caso; forma de abordá-lo fica para decisão futura da equipe. |
| **L11** | **Restaurante Executivo no mesmo prédio do RU do Darcy Ribeiro.** O Executivo tem fila e cardápio próprios e está fora do escopo, mas o GPS não o distingue do RU. Quem vai ao Executivo pode fazer check-in no Darcy Ribeiro e entrar na contagem de chegadas do RU. | Aviso discreto e fixo na tela do campus (RF20.4); o sistema não trata nenhum dado sobre o Executivo (RI08). |
| **L12** | **Espera estimada tende a ficar abaixo da realidade.** Ela usa só quem responde à pergunta de saída da fila. Quem desiste, quem não responde e quem responde "há mais de 10 min" ficam de fora, e quem diz "Ainda estou na fila" e não volta entra só com um piso. As esperas mais longas são as mais afetadas. | Pisos contados em vez de descartados (RN07) e uso da mediana (RN08); mínimo de respostas (RN08); texto na tela informando que é uma estimativa (RF22.2). |

---

## 6. Matriz de Rastreabilidade

Necessidades das partes interessadas conforme o Documento de Visão. A origem de cada requisito funcional consta aqui, e não nos blocos da Seção 2.

| ID | Subrequisitos | Épico | Necessidade da Parte Interessada / origem | Release |
|---|---|---|---|---|
| RF01 | RF01.1 a RF01.5 | Login | Pré-requisito de avaliação — "Saber a qualidade da comida antes de decidir comer no RU"; decisão de projeto | MVP |
| RF02 | RF02.1 a RF02.3 | Login | Decisão de projeto (se o e-mail estiver errado, a pessoa perde o único canal de recuperação de senha); pré-requisito de avaliação | MVP |
| RF03 | RF03.1 a RF03.4 | Login | Pré-requisito de avaliação e, na Release 2, de check-in; decisão de projeto. RF03.3: decisão de projeto (sair da conta, sobretudo em aparelho compartilhado). RF03.4: decisão de projeto (consequência do RF20) | MVP; RF03.3 e RF03.4 na Release 2 |
| RF04 | RF04.1, RF04.2 | Login | Decisão de projeto (canal de recuperação de senha); pré-requisito de avaliação | MVP |
| RF05 | — | Login / Transversal | "Planejar a refeição com informação antecipada" (perspectiva do produto: sistema como "porta") | MVP |
| RF06 | RF06.1 a RF06.5 | Cardápio | "Planejar a refeição com informação antecipada"; decisão de projeto (leitura dos marcadores e das dietas) | MVP |
| RF07 | RF07.1 a RF07.3 | Cardápio | "Planejar a refeição com informação antecipada"; decisão de projeto (visualização refinada já no MVP; ampliação na Release 2 pelas RN04 e RN05, conforme feedback da orientadora) | MVP |
| RF08 | — | Cardápio | "Saber o que posso comer com minha restrição alimentar ou alergia, sem ler o cardápio inteiro"; decisão de projeto | MVP |
| RF09 | — | Cardápio | "Saber o que posso comer com minha restrição alimentar ou alergia, sem ler o cardápio inteiro"; decisão de projeto | MVP |
| RF10 | — | Cardápio | "Saber o que posso comer com minha restrição alimentar ou alergia, sem ler o cardápio inteiro" | Backlog |
| RF19 | — | Cardápio (jornada) | "Planejar a refeição com informação antecipada"; decisão de projeto (feedback da orientadora: reduzir o número de toques até as informações) | Release 2 |
| RF20 | RF20.1 a RF20.4 | Cardápio (jornada) | "Planejar a refeição com informação antecipada"; "Evitar longas filas no horário de pico"; decisão de projeto (feedback da orientadora: reduzir o número de toques até as informações) | Release 2 |
| RF18 | — | Cardápio | "Planejar a refeição com informação antecipada"; decisão de projeto (correção de escopo: no refinamento anterior este item estava erroneamente descrito como parte do MVP) | Release 2 |
| RF11 | — | Fila | "Evitar longas filas no horário de pico"; decisão de projeto (o check-in passa a ser a única fonte de dados da previsão) | Release 2 |
| RF12 | — | Fila | "Evitar longas filas no horário de pico" (confiabilidade da previsão); decisão de projeto | Release 2 |
| RF13 | — | Fila | "Evitar longas filas no horário de pico"; "Planejar a refeição com informação antecipada"; decisão de projeto | Release 2 |
| RF14 | — | Fila | "Evitar longas filas no horário de pico"; decisão de projeto | Backlog |
| RF21 | RF21.1, RF21.2 | Fila | "Evitar longas filas no horário de pico"; decisão de projeto (feedback da orientadora: melhorar o cálculo da previsão) | Release 2 |
| RF22 | RF22.1, RF22.2 | Fila | "Evitar longas filas no horário de pico"; decisão de projeto (feedback da orientadora: melhorar o cálculo da previsão; foco na precisão do tempo de fila) | Release 2 |
| RF23 | — | Fila | "Evitar longas filas no horário de pico"; decisão de projeto | Backlog |
| RF15 | RF15.1, RF15.2 | Avaliação | "Saber a qualidade da comida antes de decidir comer no RU"; decisão de projeto | MVP |
| RF16 | — | Avaliação | "Saber a qualidade da comida antes de decidir comer no RU" | Release 2 |
| RF17 | — | Transversal | Experiência geral do usuário (item "Design do site" do Documento de Visão) | MVP |
| RNF01–RNF06 | — | Transversal | Métrica de eficiência e requisitos de sistema (entrega como PWA) | MVP / Release 2 |
| RNF07–RNF08 | RNF07.1 a RNF07.4 | Transversal | Decisão de projeto | MVP |

---

## 7. Resumo por Release

| Release | Requisitos Funcionais |
|---|---|
| **MVP** (entregue) | RF01, RF02, RF03 (RF03.1 e RF03.2), RF04, RF05, RF06, RF07, RF08, RF09, RF15, RF17 |
| **Release 2** (entrega final) | RF11, RF12, RF13, RF16, RF18, RF19, RF20, RF21, RF22; RF03.3 e RF03.4; ampliações de comportamentos do MVP nas RN04 e RN05 (RF07) e no RNF03 |
| **Backlog** | RF10, RF14, RF23 |

Todos os requisitos não funcionais (RNF01–RNF08) e todos os requisitos inversos (RI01–RI10) aplicam-se transversalmente a partir do MVP, ainda que alguns (ex.: RNF06 quanto a detecção, check-in e previsão; RNF03 e RNF07 quanto às regras de localização e retenção; RI03, RI05, RI09) só se manifestem completamente a partir da entrada em vigor das funcionalidades de fila na Release 2.

---

## Anexo A — Parâmetros configuráveis

Valores ajustáveis pela equipe sem alterar os requisitos.

| Parâmetro | Valor inicial | Usado em |
|---|---|---|
| Horário do café da manhã | 7h00 às 9h30 | RF07.3 (RN05), RF11, RF13, RF15.1, RF20.3 |
| Horário do almoço | 11h00 às 14h30 | RF07.3 (RN05), RF11, RF13, RF15.1, RF20.3 |
| Horário do jantar | 17h00 às 19h30 | RF07.3 (RN05), RF11, RF13, RF15.1, RF20.3 |
| Estrutura dos horários | Campus × refeição × dia da semana. Os dias e as refeições servidos vêm do PDF | RF06.2, RF07.1, RF07.3 (RN05) |
| Coordenadas e raio de confirmação do check-in por RU | A definir pela equipe para cada RU, com validação em campo. No Darcy Ribeiro, o RU e o Restaurante Executivo ficam no mesmo prédio e o GPS não os distingue (L11) | RF12 |
| Coordenadas e raio de detecção de campus | A definir pela equipe, por campus; raio bem menor que a metade da distância até o campus mais próximo; na Fazenda Água Limpa, ponto próximo às instalações do RU | RF20.1 |
| Tempo parado para nova detecção de campus | 30 minutos | RF20.1 |
| Tempo limite da leitura de localização | 5 segundos | RN03 (RF12, RF20.2) |
| Precisão mínima da posição | A definir pela equipe | RN03 (RF12, RF20.2) |
| Idade máxima da posição | A definir pela equipe | RN03 (RF12, RF20.2) |
| Faixa de horário da previsão | 15 minutos | RF13, RN06 |
| Janela de histórico da previsão | 4 semanas, mesmo dia da semana | RN06, RN08, RNF07.3 |
| Mínimo de dados para exibir a previsão | Check-ins em 3 dias distintos | RF13, RN06 |
| Cortes dos níveis de fila | 25%, 50% e 75% da média da faixa mais cheia | RN06 |
| Tempo até a primeira pergunta de saída da fila | 15 minutos após o check-in | RF21.1 |
| Intervalo da segunda pergunta de saída da fila | 10 minutos | RF21.2 |
| Expiração da pergunta de saída da fila | 60 minutos após o check-in | RF21.2 |
| Pontos médios das respostas de saída da fila | "até 5 min": 2,5 min; "5 a 10 min": 7,5 min | RN07 |
| Mínimo de dados para exibir a espera estimada | 3 tempos de espera em 2 dias distintos, na janela de 4 semanas | RN08, RF22.2 |
| Prazo de manutenção do vínculo com a conta (check-ins, tentativas e respostas) | 4 semanas, a mesma janela da previsão | RNF07.3 |
| Validade do link de confirmação de e-mail | 24 horas | RF02.1 a RF02.3 |
| Validade do link de redefinição de senha | 1 hora | RF04.2 |
| Limite de solicitações de redefinição | 3 por hora por matrícula/SIAPE | RF04.1 |
| Bloqueio de login | 5 tentativas em 10 minutos, bloqueio de 10 minutos | RF03.2 |
| Janela de validação do prefixo da matrícula de estudante | Dinâmica: de `101` (2010, 1º semestre) até o código do semestre corrente do sistema (ex.: `262` no 2º semestre de 2026), recalculada automaticamente a cada semestre | RN01 (RF01.3) |

---

## Anexo B — Regras de negócio

Regras citadas pelos requisitos funcionais. Onde há uma versão do MVP e outra da Release 2, as duas estão identificadas. Os valores ajustáveis estão no Anexo A.

#### RN01 — Formato da matrícula e do SIAPE

- **Estudante:** matrícula com exatamente 9 dígitos numéricos, extraída do e-mail institucional. Matrícula de 8 dígitos (anterior a 2010) é rejeitada (L10).
- **Prefixo (3 primeiros dígitos, ano/semestre de ingresso):** os 2 primeiros dígitos correspondem aos 2 últimos de um ano entre 2010 e o ano corrente, e o 3º dígito é `1` ou `2`. O intervalo válido vai de `101` (2010, 1º semestre) até o código do semestre corrente, calculado a partir da data do sistema (ex.: `262` no 2º semestre de 2026). Nenhum código fora do intervalo, inclusive "futuro", é aceito. O ano e o semestre correntes usados no cálculo são parâmetros configuráveis (Anexo A).
- **Seis dígitos finais:** são rejeitados se formarem uma sequência inteira crescente (`123456`), uma sequência inteira decrescente (`654321`) ou se todos forem iguais (`111111`).
- **Professor/Servidor:** SIAPE/matrícula funcional com exatamente 7 dígitos numéricos.
- **Outros formatos**, inclusive com pontuação, são rejeitados com mensagem específica.
- **No login (RF03.1):** 9 dígitos indicam matrícula e 7 indicam SIAPE. Um identificador com outra quantidade de dígitos é rejeitado antes de consultar a base, com mensagem de formato inválido.
- O sistema confere apenas o formato (L01).

#### RN02 — Apelido

- Tem de 3 a 20 caracteres, sem espaços, e é único entre os usuários, sem distinção de maiúsculas e minúsculas. É definido apenas no cadastro e não pode ser alterado.
- **Estudante:** o apelido é digitado.
- **Professor/Servidor:** o apelido é extraído do texto antes do "@" do e-mail institucional (qualquer texto é aceito), com os caracteres não alfanuméricos removidos (como o "." em nome.sobrenome) antes da checagem.
- Se, depois da limpeza, o apelido já estiver em uso ou não tiver de 3 a 20 caracteres, o cadastro automático é rejeitado e o sistema pede que a pessoa digite um apelido (ADR 0002).

#### RN03 — Leitura de localização aceita

A posição do dispositivo só é usada se for lida dentro do tempo limite, com a precisão mínima e a idade máxima do Anexo A. Uma leitura fora desses limites equivale a "localização não lida": na detecção de campus (RF20.2), vale o campus lembrado ou o seletor; no check-in (RF12), ele é rejeitado. As coordenadas não são armazenadas (RI09).

#### RN04 — Campus exibido

- **MVP:** o campus exibido é o último escolhido manualmente e lembrado no aparelho; sem ele, o seletor de campus.
- **Release 2:** a ordem é (1) a escolha manual feita depois da última detecção, que prevalece até a próxima abertura do app, ou volta ao primeiro plano com nova detecção; (2) o campus detectado; (3) o campus lembrado; (4) o seletor de campus, se nenhum dos anteriores existir.
- O campus lembrado é sempre o último escolhido manualmente: o campus detectado não o substitui.

#### RN05 — Refeição padrão

- **MVP:** é a refeição em andamento ou, se nenhuma estiver em andamento, a próxima do dia, conforme os horários do Anexo A.
- **Release 2:** a ordem é (1) a refeição em andamento; (2) senão, a próxima refeição ainda por vir no mesmo dia; (3) senão (todas as refeições do dia já terminaram), a última refeição do dia, até as 23h59, com a avaliação aberta (RF15.1) e, no lugar da previsão e do check-in, a indicação "refeição encerrada"; (4) depois da meia-noite volta a valer o item 2, e o café da manhã do novo dia passa a ser o padrão; (5) se o campus não serve refeições no dia (por exemplo, no domingo), a padrão é a primeira refeição do próximo dia com serviço, com o dia indicado na tela.
- Se o dia a exibir pertencer a uma semana cujo PDF ainda não foi lido com sucesso (RF06, RF18), a tela informa que o cardápio ainda não foi publicado.
- Os dias e as refeições servidos são os do PDF (RF06.2).

#### RN06 — Nível de fila por faixa

- As faixas são de 15 minutos e cobrem o horário da refeição (Anexo A).
- Para cada faixa, calcula-se a média de check-ins confirmados nas últimas 4 semanas, no mesmo dia da semana, campus e refeição, considerando apenas os dias com dados.
- O nível é a razão entre a média da faixa e a média da faixa mais cheia: menos de 25% é **vazia**; de 25% a menos de 50% é **curta**; de 50% a menos de 75% é **moderada**; 75% ou mais é **longa**. A faixa mais cheia é sempre longa e é o pico.
- A previsão só é exibida com check-ins em ao menos 3 dias distintos na janela; do contrário, mostra "dados insuficientes", sem valor de reserva.
- As respostas à pergunta de saída da fila não alteram o nível (ADR 0010).

#### RN07 — Tempo de espera

O tempo de espera de um check-in é o intervalo entre o check-in e a saída da fila, obtida da resposta à pergunta de saída da fila (RF21.2):

- "Saí da fila agora há pouco (até 5 min)": a saída é situada 2,5 minutos antes da hora da resposta.
- "Saí da fila há 5 a 10 min": a saída é situada 7,5 minutos antes da hora da resposta.
- "Saí da fila há mais de 10 min": não gera tempo de espera, porque a saída não pode ser situada no tempo.
- "Ainda estou na fila", sem resposta posterior de saída: gera um tempo de espera igual ao intervalo entre o check-in e a última resposta desse tipo. É um piso: a espera real é pelo menos esse valor (L12).
- "Desisti de comer no RU" e a ausência de resposta não geram tempo de espera.

Cada tempo de espera pertence à faixa de horário em que o check-in foi feito.

#### RN08 — Espera estimada

- A espera estimada de uma faixa é a mediana dos tempos de espera da faixa nas últimas 4 semanas, para o mesmo dia da semana, o mesmo campus e a mesma refeição (a mesma janela da RN06), arredondada para minutos inteiros.
- Só é exibida quando a faixa tem ao menos 3 tempos de espera em ao menos 2 dias distintos dentro da janela e a previsão do RF13 é exibida. Do contrário, a faixa mostra só o nível.
