# CONTEXT.md — Sistema de Monitoramento do RU (UnB)

Glossário do domínio. Sem detalhes de implementação — apenas conceitos e suas relações.

## Termos

**Campus**
Unidade física da UnB. Campi com RU: Darcy Ribeiro, Ceilândia, Gama, Planaltina. Cada `Campus` possui exatamente um `RU` — não há RUs compartilhados entre campi.

**RU (Restaurante Universitário)**
Unidade de restaurante universitário vinculada a um `Campus`. Cada RU possui seu próprio `Cardápio` e sua própria `Fila`. Cada RU tem seus próprios **dias de funcionamento** (ex.: Darcy Ribeiro funciona todos os dias da semana, incluindo sábado e domingo; os demais RUs funcionam apenas de segunda a sexta) — só existe `Cardápio` para os dias em que o RU opera.

**Cardápio**
Conjunto de `Refeição` oferecidas por um RU em uma data específica. O *padrão* de refeições (café da manhã, almoço, jantar) se repete toda semana, mas o *conteúdo* (os itens servidos) muda a cada dia. A UnB publica um cardápio semanal em PDF por campus.

**Refeição**
Um dos períodos de alimentação de um `Cardápio` (ex.: café da manhã, almoço, jantar). Contém uma lista de `ItemCardápio`.

**ItemCardápio**
Um alimento específico oferecido dentro de uma `Refeição`, classificado por uma `Categoria`.

**Categoria (de item)**
Classificação de um `ItemCardápio` dentro de uma `Refeição`. Lista fechada, igual em todos os RUs e datas: guarnição, salada, sobremesa, bebida/refresco, prato principal, prato vegetariano, prato ovolactovegetariano, prato vegetariano estrito.

**Usuário**
Pessoa com conta no sistema, com um `Papel`: Aluno (login via matrícula) ou Servidor (login via matrícula funcional para professores, ou SIAPE para os demais). Só um `Usuário` autenticado pode criar um `Relato`. O campus visualizado na tela é livre — não é vinculado à conta, qualquer `Usuário` ou `Visitante` pode ver/reportar em qualquer RU.

**Visitante**
Pessoa que acessa o sistema sem login. Pode visualizar a `Fila` e o `Cardápio` semanal de qualquer campus, mas não pode criar `Relato`.

**Relato**
Reporte de um `Usuário` autenticado sobre o estado da fila de um RU em um instante específico. Contém um `Nível de Fila`, um instante de criação, e a localização GPS do usuário no momento do relato — **obrigatória**, usada para confirmar que o usuário está fisicamente no campus do RU. Um `Relato` só é aceito se o GPS confirmar presença no campus. Válido por 15 minutos a partir da criação.

**Cooldown de Votação**
Regra que impede um `Usuário` de criar um novo `Relato` para o mesmo RU antes de 15 minutos desde seu último `Relato` naquele RU. Conceitualmente distinto da validade do `Relato` (que rege quanto tempo ele conta na agregação da `Fila`), ainda que hoje ambos usem 15 minutos.

**Nível de Fila**
Escala ordenada de 4 valores usada em um `Relato`: Vazia, Curta, Moderada, Longa (nomes provisórios). As faixas concretas (nº de pessoas ou tempo de espera correspondente a cada nível) ainda não são definidas — tendem a ser relativas a cada RU, já que os campi têm portes diferentes.

**Fila**
Estado da fila física de entrada de um RU em um dado momento, calculado como a média ponderada dos níveis de todos os `Relato` válidos (dentro dos 15 min) daquele RU, com peso maior para os relatos mais recentes. O resultado (um valor contínuo) é exibido ao `Usuário`/`Visitante` arredondado para o `Nível de Fila` discreto mais próximo.

**Avaliação**
Reação de um `Usuário` autenticado a uma `Refeição` específica (de um `Cardápio`, em um dia e período determinados — ex.: o almoço de uma quarta-feira). Composta por uma nota em estrelas e um comentário opcional em texto. O nome completo do `Usuário` autor é exibido junto da `Avaliação` (mecanismo anti-spam/anti-abuso, análogo ao iFood). Cada `Usuário` pode ter no máximo uma `Avaliação` por `Refeição`, podendo editá-la ou apagá-la depois. A nota de uma `Avaliação` é independente da nota de `Avaliação`s de outras `Refeição`s do mesmo dia — a nota do café da manhã não afeta a do almoço, por exemplo.

**Check-in**
Confirmação de um `Usuário` autenticado, via botão no app ("Estou no RU"), de que está fisicamente presente no RU. Ação independente do `Relato`: o `Relato` mede a fila *antes* de entrar, o `Check-in` confirma que a pessoa *de fato entrou*. Alimenta, junto com outros fatores, a `Previsão de Pico`.

**Previsão de Pico**
Estimativa de horários de maior movimento em um RU, calculada a partir do histórico de `Check-in` e de `Relato` (detalhes do cálculo são decisão de implementação, fora deste glossário).

**Alérgeno**
Classificação de risco alergênico de um `ItemCardápio`. Lista fechada baseada nos 14 alérgenos de declaração obrigatória da RDC nº 26/2015 (Anvisa). Um `ItemCardápio` pode ter zero ou mais `Alérgeno`s associados.

**Preferência Alimentar**
Conjunto de filtros — por `Categoria` alimentar e/ou `Alérgeno` a evitar — usado para destacar/ocultar `ItemCardápio`s do `Cardápio`. Qualquer `Visitante` pode aplicar filtros pontualmente, sem persistência entre visitas. Para `Usuário` autenticado, a `Preferência Alimentar` fica salva no perfil e é aplicada automaticamente nas próximas visitas.
