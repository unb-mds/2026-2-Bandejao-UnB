# ADR 0006 — Alerta de falha do Leitor de Cardápio por e-mail, com limite de avisos

**Status:** Aceita, com ponto em aberto (destinatário do alerta)
**Data:** 2026-09-27
**Projeto:** Bandejão (Grupo 6, MDS, FCTE/UnB)

## Contexto

O Leitor de Cardápio (RF06) lê o PDF semanal do site do RU, cujo formato
pode mudar sem aviso (L05) e cuja leitura dos ícones de marcador é o ponto
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
dia, quantidade enviada, horário do último envio). O desenho está em
`c4-nivel-4-leitor-cardapio.md`.

## Consequências

- A equipe é avisada de forma ativa, sem precisar consultar log ou banco.
- O alerta passa a depender do Serviço de E-mail, cujo provedor ainda não foi
  escolhido (Nível 2). Se o serviço de e-mail estiver fora do ar quando a
  leitura falhar, o aviso se perde. Na implementação, a falha no envio do
  alerta não deve derrubar o processo de leitura nem impedir que o fallback
  do RF06 seja aplicado.
- O limite de 3 avisos por dia e o intervalo de 6 horas são valores iniciais,
  escolhidos na mesma ordem de grandeza dos limites já usados no projeto
  (por exemplo, 3 solicitações de redefinição de senha por hora, RF04). Vale
  revisá-los depois de algumas semanas de uso real; sugere-se tratá-los como
  parâmetros configuráveis, como os do Anexo A do Documento de Requisitos.
- O contador precisa ser persistido (tabela `ContadorAlerta`), porque o
  disparo do Leitor é feito por cron do SO (ADR 0003) e o processo não
  mantém memória entre execuções.
- Como a decisão só cobre o envio, o alerta não deixa histórico próprio além
  do contador. Se a equipe quiser consultar depois quais falhas ocorreram,
  será preciso registrar os alertas em tabela; isso não foi decidido.

## Pontos em aberto

- **Destinatário do alerta.** Não foi definido para qual endereço os avisos
  serão enviados (e-mail de grupo do projeto, lista de endereços etc.). A
  equipe optou por tratar esse ponto depois. Uma possibilidade é tratá-lo como
  mais um parâmetro configurável. A ADR deve ser atualizada quando isso for
  decidido.
- **Provedor do Serviço de E-mail.** Continua em aberto, como já registrado no
  Nível 2 (`c4-niveis-1-2.md`).

## Alternativas consideradas

**Log da aplicação** e **registro no banco**: descartadas como canal único
por serem passivas. Nada impede que a equipe também as adote como
complemento.

## Relacionadas

- Requisitos: RF06, RF02, RF04, RNF08, L03, L05.
- `docs/adr/0003-leitor-pdf-como-modulo-do-backend.md` (módulo do Leitor de
  Cardápio e disparo por cron).
- `docs/adr/0004-acesso-direto-da-equipe-ao-banco.md` (canal passivo de
  consulta que esta decisão complementa).
