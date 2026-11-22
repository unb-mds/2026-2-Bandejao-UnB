# Monitor de disponibilidade (BD-09)

Como a disponibilidade de `https://bandejaounb.com.br` é acompanhada, o que
cada monitor confere e como o relatório é calculado. A meta vem do RNF02: o
sistema deve estar disponível pelo menos **95% do tempo** das **7h às 19h30**,
nos dias em que há refeição servida.

## Monitores ativos

O serviço usado é o [UptimeRobot](https://uptimerobot.com), no plano gratuito.
Os dois monitores checam a cada **5 minutos**, de fora da VM, como um usuário
faria.

| Monitor | Tipo | O que confere | Quando abre um incidente |
|---|---|---|---|
| `bandejaounb.com.br` | HTTP(s) | `https://bandejaounb.com.br` responde com sucesso (Caddy e o PWA no ar, com HTTPS válido) | resposta com erro, tempo esgotado ou falha de HTTPS |
| `Keyword on bandejaounb.com.br/api/campi/` | Keyword | `https://bandejaounb.com.br/api/campi/` responde e a resposta contém `Darcy Ribeiro` (backend e banco no ar, com os campi carregados) | a resposta falha ou não traz mais a palavra, por exemplo uma lista vazia `[]` |

O segundo monitor existe por causa do que já aconteceu: o banco de produção
chegou a ficar sem campi (ver "Validação em produção" no
[guia de deploy](../deploy/deploy-producao.md)), e a API respondia 200 com
`[]`. Um monitor que só olha o código HTTP não pegaria isso.

## Alertas

- Os dois monitores avisam por **e-mail** quando caem e quando voltam.
- O e-mail de alerta é o da conta do UptimeRobot, de quem a criou (Luís, BD).
- Ficam fora do monitor, de propósito: login, fila, avaliação e o leitor do
  cardápio. Eles dependem de sessão e de dados de teste, e a BD-09 pede só a
  disponibilidade do serviço.

## Quando chega um alerta

1. Abra o monitor no painel e leia o motivo do incidente (código HTTP, tempo
   esgotado ou "keyword not found").
2. Entre na VM e veja os serviços:
   `docker compose ps` e `docker compose logs --tail=100 backend caddy`
   (comandos em "Ver logs", no [guia de deploy](../deploy/deploy-producao.md)).
3. Se um serviço caiu, o `restart: unless-stopped` costuma subir de volta
   sozinho. Se não subiu, siga "Atualizar" no guia.
4. Se a API responde `[]`, confira se os campi estão carregados
   (`loaddata campi marcadores`, passo do guia).
5. Anote o incidente no relatório (horário de início e de fim, motivo).

## Como o relatório é calculado

O UptimeRobot monitora 24 horas por dia, mas a meta do RNF02 vale só na janela
das 7h às 19h30 dos dias de refeição. Por isso o relatório não usa o
percentual geral do painel e sim o **log de incidentes** de cada monitor:

- janela de um dia de refeição: 7h00 às 19h30 (horário de Brasília), ou seja,
  **750 minutos**;
- indisponibilidade do dia: soma dos minutos de incidentes que caem dentro da
  janela (um incidente que atravessa o limite conta só a parte de dentro);
- disponibilidade do dia: `1 − minutos fora do ar ÷ 750`;
- disponibilidade do período: `1 − (soma dos minutos fora do ar) ÷ (750 × dias
  de refeição do período)`.

A margem da meta é de 5%: **37,5 minutos de queda por dia de refeição**. Como a
checagem é de 5 em 5 minutos, o tempo fora do ar é medido nesse passo, e uma
queda curta entre duas checagens pode passar despercebida.

O modelo do relatório está em
[relatório parcial de disponibilidade](relatorio-disponibilidade-parcial.md).

## Limites conhecidos

- A granularidade é de 5 minutos (o plano gratuito não oferece menos).
- O monitor mede se o serviço **responde**, não se o cardápio mostrado está
  atualizado. A atualização depende do leitor do PDF (RF06), que tem alerta
  próprio (ADR 0006).
- Há uma só conta de alerta. Se ela ficar fora do ar ou sem ser lida, ninguém
  é avisado. A equipe pode convidar mais um e-mail depois.
- A checagem parte de fora da rede da VM, então uma falha de DNS ou de
  certificado também é detectada.
