# Monitor de disponibilidade (BD-09)

Como a disponibilidade de `https://bandejaounb.com.br` é acompanhada, o que
cada monitor confere e como o relatório é calculado. A meta vem do RNF02: o
sistema deve estar disponível pelo menos **95% do tempo** das **7h às 19h30**,
nos dias em que há refeição servida.

## Monitores

O serviço usado é o [UptimeRobot](https://uptimerobot.com), no plano gratuito.
Os dois monitores checam a cada **5 minutos**, de fora da VM, como um usuário
faria. A checagem parte de fora da rede da VM, então uma falha de DNS ou de
certificado também é detectada.

| Monitor | Tipo | O que confere | Quando abre um incidente | Papel |
|---|---|---|---|---|
| `Keyword on bandejaounb.com.br/api/campi/` | Keyword | `https://bandejaounb.com.br/api/campi/` responde e a resposta contém `Darcy Ribeiro` (Caddy, backend e banco no ar, com os campi carregados) | a resposta falha ou não traz mais a palavra, por exemplo uma lista vazia `[]` | **medida oficial do RNF02** |
| `bandejaounb.com.br` | HTTP(s) | `https://bandejaounb.com.br` responde com sucesso (Caddy e o PWA no ar, com HTTPS válido) | resposta com erro, tempo esgotado ou falha de HTTPS | diagnóstico |

A medida oficial é o monitor da API porque ele também falha quando o Caddy cai
(a API passa por ele) e quando o banco cai, então cobre a queda que o usuário
sente. O monitor do site ajuda a separar a causa (por exemplo, o PWA fora e a
API no ar), mas não entra na conta do RNF02. Assim há um só número, sem somar
nem comparar dois monitores.

Configuração, para quem precisar recriar os monitores: no da API, o alerta abre
quando a palavra **não existe** na resposta (*Alert when: keyword does not
exist*), com a opção de diferenciar maiúsculas e minúsculas ligada; no do
site, o aviso de certificado só funciona com *Ignore SSL errors* **desmarcado**.
**Não pause o monitor da API** (nem num deploy planejado): o tempo pausado não
aparece como queda e some da conta. Se alguém pausar, anote o tempo pausado como
queda no relatório.

O monitor da API existe por causa do que já aconteceu: o banco de produção
chegou a ficar sem campi, e a API respondia 200 com `[]`. Um monitor que só
olha o código HTTP não pegaria isso. O passo
[3. Subir](deploy/deploy-producao.md?id=_3-subir) do guia de deploy explica o
motivo (sem a fixture, a API responde `[]`); o caso em produção, em 20/11, está
registrado na entrada do PR #211 no `AI-USAGE.md`, e a seção "Validação em
produção" do guia de deploy registra a resposta com os 5 campi depois do
`loaddata`.

## Alertas

- Os dois monitores avisam por **e-mail** quando caem e quando voltam.
- O e-mail de alerta é o da conta do UptimeRobot, e só o dono dessa conta
  recebe e vê o painel.
- Ficam fora do monitor, de propósito: login, fila, avaliação e o leitor do
  cardápio. Eles dependem de sessão e de dados de teste, e a BD-09 pede só a
  disponibilidade do serviço.

## Quando chega um alerta

Quem recebe o e-mail (o dono da conta) **avisa no grupo da equipe** assim que
o alerta chega, com o monitor, o horário e o motivo que o painel mostra. Se
outra pessoa precisar agir, ela usa o próprio acesso à VM e não precisa do
painel. **Durante o incidente, peça no grupo que ninguém faça merge na `main`**:
com o deploy automático, um merge vira deploy no meio da correção.

1. Abra o monitor no painel e leia o motivo do incidente (código HTTP, tempo
   esgotado ou "keyword not found").
2. Entre na VM por SSH (ver
   [Infraestrutura](deploy/deploy-producao.md?id=infraestrutura)) e veja
   os serviços:
   ```bash
   cd ~/2026-2-Bandejao-UnB
   docker compose ps
   docker compose logs --tail 100 backend caddy db
   ```
   (mais comandos em [Ver logs](deploy/deploy-producao.md?id=ver-logs)). O
   `db` entra porque, se o banco cai, o backend continua `healthy` no
   `docker compose ps` (o healthcheck só testa a porta do Gunicorn, não fala
   com o banco) e a API responde erro 500: o estado do banco aparece no `ps` e
   a causa, no log do `db`. Não descarte o banco só porque o backend aparece
   `healthy`.
3. Se um serviço caiu, o `restart: unless-stopped` costuma subir de volta
   sozinho, mas ele só reinicia container que **saiu**. Se não subiu, rode
   `docker compose up -d` (sem `git pull`) e veja
   `docker compose logs --tail 100 <serviço>`. Se o container está de pé mas
   com erro (o backend respondendo 500, por exemplo), ele não é reiniciado
   sozinho: use `docker compose restart <serviço>`. Se a causa for o banco
   (passo 2), reinicie o `db` e não o backend. Se o erro for de configuração
   (`.env`), veja os casos de `--force-recreate` em
   [Atualizar](deploy/deploy-producao.md?id=atualizar). Não siga o resto de
   "Atualizar" no meio de um incidente: ele faz `git pull` e coloca código novo
   em produção.
4. Se a API responde `[]`, confirme que a tabela de campi está vazia:
   ```bash
   docker compose logs backend | grep "Tabela CAMPUS vazia"
   docker compose exec backend python manage.py shell -c "from apps.cardapio.models import Campus; print(Campus.objects.count())"
   ```
   Se a API traz campi, mas não o `Darcy Ribeiro` (campus renomeado), **não**
   rode o `loaddata`: troque a palavra do monitor. Só com a tabela vazia rode o
   `loaddata`, sabendo que ele regrava campi **e marcadores** com os valores da fixture e desfaz ajustes feitos no banco,
   como as coordenadas medidas em campo na BD-06 (ver o aviso no passo
   [3. Subir](deploy/deploy-producao.md?id=_3-subir) do guia de deploy).
5. Anote o incidente na tabela de incidentes do
   [relatório](operacao/relatorio-disponibilidade-parcial.md), mesmo que caia fora do
   período dele (a coluna "No período?" separa).

## Como o relatório é calculado

O UptimeRobot monitora 24 horas por dia, mas a meta do RNF02 vale só na janela
das 7h às 19h30 dos dias de refeição. Por isso o relatório não usa o
percentual geral do painel e sim o **log de incidentes** do monitor da API
(a medida oficial, ver [Monitores](#monitores)).

**Antes de calcular, confira o fuso da conta:** em *Account details → Timezone*
do UptimeRobot, a conta deve estar em `America/Sao_Paulo` (UTC−3). O log de
incidentes mostra os horários no fuso da conta. Se ela estiver em UTC, a
janela de 7h às 19h30 de Brasília vira 10h00 às 22h30 no painel, e o relatório
sai errado sem aviso. Anote no relatório qual fuso estava ativo.

- janela de um dia de refeição: 7h00 às 19h30 (horário de Brasília), ou seja,
  **750 minutos**;
- indisponibilidade do dia: soma dos minutos de incidentes do monitor da API
  que caem dentro da janela (um incidente que atravessa o limite conta só a
  parte de dentro);
- disponibilidade do dia (informativa): `(1 − minutos fora do ar ÷ 750) × 100`,
  em %;
- disponibilidade do período: `(1 − soma dos minutos fora do ar ÷ (750 × dias
  de refeição do período)) × 100`, em %. **É esse o número que se compara com
  a meta de 95%.**
- **Regra de decisão, sem arredondar:** a meta é atingida se a soma dos minutos
  que contam for **no máximo 37,5 × dias de refeição**. Assim, um 94,996% não
  vira "95%" por arredondamento.
- Um incidente **ainda aberto** no fechamento termina na hora do fechamento.

A meta vale para o **período**, e não dia a dia: um dia com 60 minutos fora do
ar não reprova o período sozinho. A margem de 5% equivale, em média, a **37,5
minutos de queda por dia de refeição**. Como a checagem é de 5 em 5 minutos, o
tempo fora do ar é medido nesse passo, e uma queda curta entre duas checagens
pode passar despercebida, e o início e o fim de cada incidente têm erro de até
cerca de 5 minutos, **para mais ou para menos**.

O critério dos dias de refeição, o que não conta e onde fica a evidência estão
no [relatório parcial de disponibilidade](operacao/relatorio-disponibilidade-parcial.md).

## Limites conhecidos

- Os links entre pastas deste guia (`deploy/...`, `operacao/...`) seguem o
  formato do site da documentação (docsify). Abertos direto pelo GitHub, dão
  404: leia pelo site.
- A granularidade é de 5 minutos (o plano gratuito não oferece menos).
- O monitor mede se o serviço **responde**, não se o cardápio mostrado está
  atualizado. A atualização depende do leitor do PDF (RF06), que tem alerta
  próprio (ADR 0006).
- Há uma só conta de alerta. Se ela ficar fora do ar ou sem ser lida, ninguém
  é avisado.
- O monitor de palavra-chave procura `Darcy Ribeiro`. Se o nome desse campus
  mudar (no admin ou na fixture), ele abre um falso incidente até a palavra do
  monitor ser trocada.
- O monitor da API não pega uma falha só do PWA com o Caddy e a API no ar
  (por exemplo, uma publicação do front quebrada). O monitor do site mostra o
  HTTP, mas não vê o conteúdo da página.
