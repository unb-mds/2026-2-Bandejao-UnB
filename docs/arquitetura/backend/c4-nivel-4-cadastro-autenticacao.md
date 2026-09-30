# Arquitetura C4 — Nível 4 (Cadastro/Autenticação) — Bandejão

> Detalha, em diagrama de classes, o componente **Cadastro/Autenticação**,
> desenhado no Nível 3 do backend (ver `c4-nivel-3-backend.md`). Cobre o
> Épico Login por inteiro: cadastro em duas etapas (RF01), confirmação de
> e-mail (RF02), login (RF03) e recuperação de senha (RF04).
>
> Referências: ADR 0002 — *Matrícula e apelido extraídos do e-mail
> institucional*, ADR 0007 — *Sessão autenticada por cookie HttpOnly* e
> ADR 0008 — *Matrícula/SIAPE em texto claro* (`docs/arquitetura/adr/`).
>
> O componente faz parte da Release 2. No protótipo da Release 1, as telas
> de cadastro, login e recuperação de senha funcionam sobre um backend
> simulado dentro do frontend, que reproduz os desfechos descritos aqui.

## Nível 4 — Diagrama de Classes do Cadastro/Autenticação

É o componente com mais regras de negócio isoladas e testáveis do backend,
o que pesa bastante para a meta de 60% de cobertura em módulos críticos
(RNF06, que cita "cadastro e autenticação" nominalmente).

```mermaid
classDiagram
  class TipoUsuario {
    <<enumeration>>
    ESTUDANTE
    PROFESSOR_SERVIDOR
  }

  class CadastroView {
    +post(request) Response
  }
  class ConfirmacaoEmailView {
    +post(request) Response
  }
  class ReenvioConfirmacaoView {
    +post(request) Response
  }
  class LoginView {
    +post(request) Response
  }
  class LogoutView {
    +post(request) Response
  }
  class SessaoView {
    +get(request) Response
  }
  class SolicitarRecuperacaoSenhaView {
    +post(request) Response
  }
  class RedefinirSenhaView {
    +post(token: str, request) Response
  }

  class CadastroService {
    +registrar(tipoUsuario: TipoUsuario, dados: dict) Usuario
  }

  class IdentificadorExtractor {
    <<interface>>
    +extrair(dados: dict) IdentificadorExtraido
  }
  class EstudanteIdentificadorExtractor {
    +extrair(dados: dict) IdentificadorExtraido
  }
  class ProfessorServidorIdentificadorExtractor {
    +extrair(dados: dict) IdentificadorExtraido
  }
  class IdentificadorExtraido {
    +identificador: str
    +apelidoSugerido: str
  }

  class MatriculaValidator {
    +validarFormato(matricula: str) bool
    +validarPrefixoAnoSemestre(matricula: str) bool
    +validarSequenciaDigitos(matricula: str) bool
  }
  class SiapeValidator {
    +validarFormato(siape: str) bool
  }
  class EmailInstitucionalValidator {
    +validarFormatoEstudante(email: str) bool
    +validarFormatoProfessorServidor(email: str) bool
  }

  class ApelidoResolver {
    +resolverManual(apelidoDigitado: str) str
    +resolverExtraido(textoAntesDoArroba: str) str
    -limparCaracteresNaoAlfanumericos(texto: str) str
    +validarDisponibilidade(apelido: str) bool
  }
  class ApelidoIndisponivelError

  class SenhaValidator {
    +validar(senha: str) bool
  }
  class PasswordHasher {
    +hash(senha: str) str
    +verificar(senha: str, hash: str) bool
  }

  class UsuarioRepository {
    +existeMatriculaOuSiape(identificador: str) bool
    +existeEmail(email: str) bool
    +buscarPorIdentificador(identificador: str) Usuario
    +salvar(usuario: Usuario) Usuario
    +excluirPendenteExpirada(usuario: Usuario) void
  }
  class IdentificadorJaCadastradoError
  class EmailJaCadastradoError

  class Usuario {
    +id: int
    +tipoUsuario: TipoUsuario
    +matriculaSiape: str
    +email: str
    +apelido: str
    +senhaHash: str
    +status: StatusUsuario
    +criadoEm: datetime
  }
  class StatusUsuario {
    <<enumeration>>
    PENDENTE
    ATIVO
    SUSPENSO
    REMOVIDO
  }

  class ConfirmacaoEmailService {
    +enviarLink(usuario: Usuario) void
    +confirmar(token: str) void
    +reenviar(identificador: str) void
  }
  class SolicitacaoReenvioTracker {
    +podeReenviar(identificador: str) bool
    -MAX_POR_HORA: int = 3
  }
  class Token {
    +usuarioId: int
    +tipo: TipoToken
    +tokenHash: str
    +criadoEm: datetime
    +expiraEm: datetime
    +usadoEm: datetime
  }
  class TipoToken {
    <<enumeration>>
    CONFIRMACAO_EMAIL
    REDEFINICAO_SENHA
  }
  class TokenExpiradoOuInvalidoError

  class ExclusaoCadastroPendenteJob {
    +executar() void
  }

  class LoginService {
    +autenticar(request, identificador: str, senha: str) Usuario
    +encerrar(request) void
  }
  class TentativaLoginTracker {
    +registrarTentativa(identificador: str, sucesso: bool) void
    +estaBloqueado(identificador: str) bool
    -MAX_TENTATIVAS: int = 5
    -JANELA: timedelta = 10min
    -BLOQUEIO: timedelta = 10min
  }
  class UsuarioPendenteError
  class UsuarioInativoError
  class CredenciaisInvalidasError
  class SessaoDjango {
    <<django.contrib.sessions>>
    +usuarioId: int
    +expiraEm: datetime
  }

  class RecuperacaoSenhaService {
    +solicitar(identificador: str) void
    +redefinir(token: str, novaSenha: str) void
  }
  class SolicitacaoRedefinicaoTracker {
    +podeSolicitar(identificador: str) bool
    -MAX_POR_HORA: int = 3
  }

  class EmailSvc["Serviço de E-mail (externo)"] {
    <<external>>
  }

  CadastroView --> CadastroService : registrar()
  ConfirmacaoEmailView --> ConfirmacaoEmailService : confirmar()
  ReenvioConfirmacaoView --> ConfirmacaoEmailService : reenviar()
  LoginView --> LoginService : autenticar()
  LogoutView --> LoginService : encerrar()
  SessaoView ..> SessaoDjango : lê apelido e tipo do usuário logado
  SolicitarRecuperacaoSenhaView --> RecuperacaoSenhaService : solicitar()
  RedefinirSenhaView --> RecuperacaoSenhaService : redefinir()

  IdentificadorExtractor <|.. EstudanteIdentificadorExtractor
  IdentificadorExtractor <|.. ProfessorServidorIdentificadorExtractor
  IdentificadorExtractor --> IdentificadorExtraido : produz

  CadastroService --> IdentificadorExtractor : escolhe estratégia por TipoUsuario
  CadastroService --> MatriculaValidator : valida (Estudante)
  CadastroService --> SiapeValidator : valida (Professor/Servidor)
  CadastroService --> EmailInstitucionalValidator : valida formato
  CadastroService --> ApelidoResolver : resolve/valida apelido
  ApelidoResolver ..> ApelidoIndisponivelError : lança se indisponível
  CadastroService --> SenhaValidator : valida senha
  SenhaValidator --> PasswordHasher : gera hash
  CadastroService --> UsuarioRepository : verifica duplicidade / salva
  UsuarioRepository ..> IdentificadorJaCadastradoError : lança se já em uso
  UsuarioRepository ..> EmailJaCadastradoError : lança se já em uso
  CadastroService --> Usuario : cria (pendente)
  CadastroService --> ConfirmacaoEmailService : dispara envio de link

  ConfirmacaoEmailService --> Token : gera/consome (CONFIRMACAO_EMAIL)
  ConfirmacaoEmailService --> SolicitacaoReenvioTracker : limita reenvios a 3/hora
  ConfirmacaoEmailService ..> TokenExpiradoOuInvalidoError : lança se inválido/expirado
  ConfirmacaoEmailService --> UsuarioRepository : marca confirmada
  ConfirmacaoEmailService ..> EmailSvc : envia link [SMTP]
  ExclusaoCadastroPendenteJob --> UsuarioRepository : exclui pendentes expiradas

  LoginService --> TentativaLoginTracker : verifica bloqueio / registra tentativa
  LoginService --> UsuarioRepository : busca conta
  LoginService --> PasswordHasher : verifica senha
  LoginService ..> UsuarioPendenteError : lança se usuário pendente
  LoginService ..> UsuarioInativoError : lança se suspenso ou removido (mensagem genérica)
  LoginService ..> CredenciaisInvalidasError : lança em erro (mensagem genérica)
  LoginService --> SessaoDjango : cria em sucesso, apaga no logout (cookie HttpOnly, ADR 0007)

  RecuperacaoSenhaService --> SolicitacaoRedefinicaoTracker : limita 3/hora
  RecuperacaoSenhaService --> Token : gera/consome (REDEFINICAO_SENHA)
  RecuperacaoSenhaService --> UsuarioRepository : busca conta / atualiza senha
  RecuperacaoSenhaService --> PasswordHasher : gera hash da nova senha
  RecuperacaoSenhaService ..> EmailSvc : envia link [SMTP]

  UsuarioRepository ..> Usuario : grava/lê
  Usuario --> TipoUsuario : tem
  Usuario --> StatusUsuario : tem
  Token --> TipoToken : tem
```

### Notas do diagrama

- **`IdentificadorExtractor` é uma estratégia por `TipoUsuario`** — a
  distinção entre Estudante e Professor/Servidor do RF01/ADR 0002 (quem
  digita o quê, e o que é extraído do e-mail) fica isolada nas duas
  implementações, em vez de virar um emaranhado de `if tipo == ...` dentro
  do `CadastroService`. Isso deixa mais fácil testar as duas regras da ADR
  0002 separadamente: para Estudante, a matrícula vem do e-mail e o apelido
  é digitado; para Professor/Servidor, é o inverso.
- **`ApelidoResolver` concentra as três variações da regra de apelido**:
  aceitar o valor digitado (Estudante), extrair e limpar caracteres não
  alfanuméricos do texto antes do "@" (Professor/Servidor), e validar
  disponibilidade/tamanho nos dois casos. A colisão ou o tamanho inválido
  do apelido extraído automaticamente não é tratada como erro fatal do
  cadastro: o RF01 pede que, nesse caso específico, o sistema **peça um
  apelido alternativo digitado manualmente**, em vez de simplesmente
  rejeitar o cadastro — vale essa distinção na hora de implementar
  `ApelidoIndisponivelError` (é recuperável, não é o mesmo tipo de falha que
  matrícula/e-mail duplicados).
- **`MatriculaValidator` tem três métodos separados**, não um só
  `validar()`, porque o RF01 define três checagens compostas e
  independentes: formato (9 dígitos), prefixo de ano/semestre (janela
  dinâmica, recalculada a cada semestre conforme o Anexo A) e sequência dos
  6 dígitos restantes (rejeita crescente, decrescente ou todos iguais).
  Métodos separados tornam cada regra testável isoladamente com casos de
  borda próprios, sem depender de montar uma matrícula "válida no resto"
  só para testar uma das três checagens.
- **`Usuario.matriculaSiape` é armazenada em texto claro, de forma
  recuperável** (ADR 0008), e não como hash irreversível — diferente de
  `senhaHash`. A equipe precisa recuperar a matrícula/SIAPE a partir do
  apelido para tratar matrícula contestada (L01) e para moderação (RNF08), e
  o login precisa buscar o usuário pela matrícula/SIAPE com uma restrição
  `UNIQUE`, o que a criptografia comum impediria. A proteção vem do acesso
  restrito ao banco (ADR 0004), de nunca expor o campo em resposta pública
  (RI10) e de nunca gravá-lo em log. Essa distinção — dado recuperável vs.
  dado irreversível — é proposital e não deve ser "simplificada" para os
  dois usarem o mesmo mecanismo na implementação.
- **Um único `Token`, com `tipo`**, cobre a confirmação de e-mail (24 h) e a
  redefinição de senha (1 h), como no C4 do Banco de Dados. Só o hash do
  token é guardado (`tokenHash`); o token em claro existe apenas no link
  enviado por e-mail (RNF04).
- **A confirmação de e-mail é um `POST`** disparado pela tela aberta a partir
  do link, e não um `GET` no próprio link: provedores de e-mail costumam
  pré-carregar links, e um `GET` que altera estado consumiria o token antes
  de a pessoa clicar.
- **A sessão é a do próprio Django, em cookie HttpOnly** (ADR 0007).
  `LoginService.autenticar` cria a sessão, `encerrar` a apaga (logout), e
  `SessaoView` informa ao PWA quem está logado (apenas apelido e tipo). A
  redefinição de senha encerra todas as sessões da conta, e um usuário
  `SUSPENSO` ou `REMOVIDO` não autentica (`UsuarioInativoError`, com a mesma
  mensagem genérica de credenciais inválidas).
- **`ExclusaoCadastroPendenteJob` é um job separado do `CadastroService`**,
  análogo ao `LerCardapioCommand` do Leitor de Cardápio: o RF02 exige que um
  cadastro pendente não confirmado em 24h seja excluído automaticamente,
  o que é responsabilidade de um processo periódico, não de uma ação
  disparada por requisição HTTP. Roda no mesmo agendador do Leitor de
  Cardápio (cron do SO), cuja frequência será definida no spike SP-02 do
  backlog, junto com a hospedagem.
- **`TentativaLoginTracker`, `SolicitacaoRedefinicaoTracker` e
  `SolicitacaoReenvioTracker` são classes separadas, não uma genérica de
  "rate limiting"**, porque os parâmetros e a
  granularidade são diferentes: bloqueio de login é por identificador, 5
  tentativas em 10 minutos, bloqueio de 10 minutos (RF03); recuperação de
  senha é por identificador, 3 solicitações por hora (RF04); reenvio do link
  de confirmação é por identificador, 3 por hora (RF02). Também evita
  que uma implementação genérica demais esconda esses números do Anexo A
  atrás de uma configuração difícil de rastrear até o requisito.
- **`LoginService` nunca deixa a `LoginView` saber se a matrícula/SIAPE
  existe** — tanto `UsuarioPendenteError` quanto `CredenciaisInvalidasError`
  viram mensagens específicas de propósito diferente (uma convida a
  confirmar o e-mail; a outra é genérica de propósito, para não permitir
  enumeração de contas, RF03) — mas nenhuma das duas revela existência da
  conta a quem não sabe a senha correta.
