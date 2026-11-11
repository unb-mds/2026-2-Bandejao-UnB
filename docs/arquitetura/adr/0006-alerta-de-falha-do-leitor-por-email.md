# ADR 0006 — Alerta de falha do Leitor de Cardápio por e-mail, com limite de avisos

**Status:** Aceita (pontos em aberto resolvidos em 2026-11-05 pela ADR 0012; abrangência de `FALHA_LEITURA_PDF` ampliada em 2026-11-11 pela ADR 0014)
**Data:** 2026-09-27
**Projeto:** Bandejão (Grupo 6, MDS, FCTE/UnB)

## Contexto

O Leitor de Cardápio (RF06) lê o PDF semanal do site do RU, cujo formato
pode mudar sem aviso (L15) e cuja leitura dos ícones de marcador é o ponto
mais frágil do módulo (L03). O RF06 define comportamentos de contingência
para as falhas:

- falha de leitura do PDF: o sistema mantém o último cardápio válido;
- legenda inválida ou associação de ícone impossível: o cardápio é publicado
  em texto, e a refeição fica marcada como "informação de alérgenos
  indisponível".

Nos dois casos, a equipe precisa ficar sabendo. Sem aviso, o cardápio
desatualizado ou sem alérgenos pode passar dias despercebido. O sistema não
tem tela administrativa (RNF08), e a equipe já acessa o banco diretamente
para moderação (ADR 0004).

Foram consideradas três formas de avisar a equipe:

1. **Log da aplicação** (Python `logging`, no arquivo ou na saída do
   servidor). Custo mínimo, mas é passivo: a equipe só descobre a falha se
   for ler o log.
2. **Registro no banco** (tabela de alertas, consultada pelo mesmo acesso
   direto da ADR 0004). Não cria nenhum canal novo, mas também é passivo.
3. **E-mail para a equipe.** É o único canal que efetivamente avisa alguém,
   e o sistema já tem integração de e-mail para o cadastro (RF02, RF04).

## Decisão

O Leitor de Cardápio avisa a equipe **por e-mail**, usando o mesmo Serviço de
E-mail já usado em RF02 e RF04, com um **limite de avisos** para que uma
falha persistente não vire ruído:

- no máximo **3 avisos por dia**, contados por combinação de **campus + tipo
  de falha** (legenda inválida, associação de ícone falhou, falha de leitura
  do PDF);
- **intervalo mínimo de 6 horas** entre dois avisos da mesma combinação, para
  espalhar os avisos ao longo do dia caso a leitura rode mais de uma vez;
- a contagem é diária e por combinação, e zera quando a leitura daquele
  campus volta a funcionar ou, no mais tardar, no dia seguinte. Assim, uma
  falha que dura vários dias gera pelo menos um aviso por dia, e não fica em
  silêncio depois do terceiro e-mail.

A regra é implementada em `AlertaEquipeService` (métodos `registrarAlerta` e
`deveEnviar`), com o controle de contagem em `ContadorAlerta` (campus, tipo,
dia, quantidade enviada, horário do último envio), gravado na tabela
`CONTADOR_ALERTA`. Os três tipos de falha são os mesmos em todo o sistema:
`LEGENDA_INVALIDA`, `ASSOCIACAO_FALHOU` e `FALHA_LEITURA_PDF` no
`TipoAlerta` do Leitor, e `legenda_invalida`, `associacao_falhou` e
`falha_leitura_pdf` no banco.

`FALHA_LEITURA_PDF` cobre também as falhas da descoberta do PDF na página do
RU (ADR 0014): página fora do ar, título do campus ausente ou repetido, nome
do arquivo que não bate com o campus, dois links para a mesma semana, dias do
PDF fora do intervalo do link, e cardápio da semana ainda não publicado
depois do prazo do Anexo A. A mensagem do alerta diz qual
etapa falhou. Assim, a ADR 0014 não cria um tipo novo. O desenho está em
`c4-nivel-4-leitor-cardapio.md`, e as tabelas, no Nível 4 do banco de dados.

## Consequências

- A equipe é avisada de forma ativa, sem precisar consultar log ou banco.
- O alerta passa a depender do Serviço de E-mail, que é o Brevo (ADR 0012).
  Se o serviço de e-mail estiver fora do ar quando a leitura falhar, ou se o
  limite diário de envio do plano do Brevo já tiver sido atingido (o limite é
  compartilhado com os e-mails de cadastro e de redefinição de senha), o aviso
  se perde. Na implementação, a falha no envio do
  alerta não deve derrubar o processo de leitura nem impedir que o fallback
  do RF06 seja aplicado.
- O limite de 3 avisos por dia e o intervalo de 6 horas são valores iniciais,
  escolhidos na mesma ordem de grandeza dos limites já usados no projeto
  (por exemplo, 3 solicitações de redefinição de senha por hora, RF04). Vale
  revisá-los depois de algumas semanas de uso real; sugere-se tratá-los como
  parâmetros configuráveis, como os do Anexo A do Documento de Requisitos.
- O contador precisa ser persistido (tabela `CONTADOR_ALERTA`), porque o
  disparo do Leitor é feito por cron do SO (ADR 0003) e o processo não
  mantém memória entre execuções.
- Além do e-mail, cada falha fica registrada na tabela
  `ALERTA_LEITURA_CARDAPIO` (campus, refeição quando houver, tipo, mensagem e
  se já foi resolvida), que a equipe consulta e marca como resolvida por
  acesso direto ao banco (ADR 0004). Assim, as falhas ocorridas podem ser
  consultadas depois, mesmo quando o limite de e-mails já foi atingido.

## Pontos resolvidos

Os dois pontos que ficaram em aberto nesta ADR foram decididos em 2026-11-05
(ADR 0012):

- **Destinatário do alerta:** `equipe@bandejaounb.com.br`, endereço da equipe
  encaminhado para `equipe.bandejao@gmail.com`. Ele é um parâmetro
  configurável (variável de ambiente), para poder ser trocado sem mudar o
  código.
- **Provedor do Serviço de E-mail:** Brevo, via SMTP, com remetente
  `nao-responda@bandejaounb.com.br`.

## Alternativas consideradas

**Log da aplicação** e **registro no banco**: descartadas como canal único
por serem passivas. Nada impede que a equipe também as adote como
complemento.

## Relacionadas

- Requisitos: RF06, RF02, RF04, RNF08, L03, L15.
- `docs/arquitetura/adr/0003-leitor-pdf-como-modulo-do-backend.md` (módulo do Leitor de
  Cardápio e disparo por cron).
- `docs/arquitetura/adr/0004-acesso-direto-da-equipe-ao-banco.md` (canal passivo de
  consulta que esta decisão complementa).
- `docs/arquitetura/adr/0012-hospedagem-e-servico-de-email.md` (provedor do
  Serviço de E-mail e destinatário dos alertas).
- `docs/arquitetura/adr/0014-descoberta-do-pdf-de-cada-campus.md` (falhas da
  descoberta do PDF, alertadas como `FALHA_LEITURA_PDF`).
