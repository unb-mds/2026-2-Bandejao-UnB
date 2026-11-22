/**
 * Backend simulado, só para desenvolvimento e testes (o build de produção
 * não o inclui; ver apiClient). Nas rotas que o MVP usa — cadastro,
 * confirmação, reenvio e sessão — segue o contrato OpenAPI v1 da BE-03
 * (backend/openapi.yaml): mesmas rotas, nomes de campos, status HTTP e
 * valores de `codigo`. Erros vêm como `{ codigo, mensagem }`.
 *
 * Também imita o navegador e o Django na sessão (ADR 0007, #112):
 * - o cookie de sessão é "HttpOnly": fica guardado aqui e o apiClient não o vê;
 * - o cookie `csrftoken` é gravado em `document.cookie` por `GET /csrf/` e
 *   trocado no login; toda escrita, com ou sem sessão, sem o cabeçalho
 *   `X-CSRFToken` certo recebe 403 `csrf_invalido`.
 *
 * Nos pontos em que o sistema real enviaria um e-mail, a resposta traz o
 * campo extra `linkSimulado` (fora do contrato), que a interface mostra
 * apenas em modo de simulação. O aviso de privacidade e o check-in seguem o
 * contrato da BE-09; como o raio do RU não é publicado, o simulado confirma
 * toda localização, a não ser que `simulacao.definirLocalizacaoConfirmada(false)`.
 * O `GET /cardapio/` segue o contrato da BE-11 (#214), mais o campo
 * `semServico` proposto na revisão da FE-08 (#219); o resumo do dia responde
 * 501, como o backend, depois de `simulacao.definirResumoDoDiaDisponivel(false)`.
 * As avaliações seguem o contrato da BE-13 (FE-09): `POST /avaliacoes/` e
 * `GET /refeicoes/{refeicaoId}/avaliacoes/`, com o `refeicaoId` do resumo do
 * dia; as duas respondem 501, como o backend hoje, depois de
 * `simulacao.definirAvaliacoesDisponiveis(false)`. Recuperação de senha, a
 * semana do cardápio (`/cardapio/<campus>/`) e as listas de avaliação da
 * HomeView (`GET /avaliacoes/` e o resumo da semana) ainda têm o formato do
 * MVP: entram no contrato na FE-E2.
 */
import {
  ORDEM_REFEICOES,
  REFEICOES,
  mensagemForaDoHorario,
} from '@/constants/refeicoes'
import { refeicaoPadrao } from '@/utils/cardapio'
import { hojeISO, minutosAgora, minutosDoDia } from '@/utils/datas'
import { banco, resumoSenha } from './banco'
import { CAMPI_DO_BANCO, idDoCampus, montarCardapioSemana, refeicaoExiste } from './cardapios'
import { IDS_MARCADORES } from '@/constants/marcadores'
import { MENSAGEM_CAMPUS_INEXISTENTE } from '@/constants/campi'
import { APELIDOS_SEMENTE, avaliacoesSemente } from './sementes'
import { previsaoSimulada } from './previsao'
import {
  analisarEmailEstudante,
  analisarEmailServidor,
  ehEmailInstitucional,
  validarApelido,
  validarSenha,
  validarSiape,
} from './validacoes'

const MINUTO = 60 * 1000
const HORA = 60 * MINUTO
const VALIDADE_CONFIRMACAO = 24 * HORA
const VALIDADE_REDEFINICAO = HORA
const LIMITE_TENTATIVAS_LOGIN = 5
const JANELA_BLOQUEIO_LOGIN = 10 * MINUTO
const LIMITE_RECUPERACOES_POR_HORA = 3
const METODOS_DE_ESCRITA = new Set(['POST', 'PUT', 'PATCH', 'DELETE'])
/** Limites por IP do backend (`LimiteDeTaxaConfig`, #123). Aqui, "IP" = este navegador. */
const LIMITES_POR_IP = { cadastro: 40, reenvio: 10, login: 60 }
const LIMITE_REENVIOS_POR_CONTA = 3

/**
 * Estado volátil, só do simulado: some ao recarregar a página. No Django, a
 * sessão (django_session), o bloqueio do login (`bloqueado_ate`) e os
 * contadores de limite ficam no banco.
 */
const sessoes = new Map() // id da sessão → id do usuário
const tentativasLogin = new Map() // e-mail → [instantes das falhas]
const bloqueiosLogin = new Map() // e-mail → instante de fim do bloqueio
const pedidosRecuperacao = new Map() // e-mail → [instantes]
const pedidosPorRota = new Map() // rota com limite → [instantes]
const reenviosPorConta = new Map() // id do usuário → [instantes]

/** Se o check-in simulado confirma a localização (o raio real fica só no backend). */
let localizacaoConfirmada = true
let resumoDoDiaDisponivel = true
let previsaoDisponivel = true
/** `false`: comentários e envio de avaliação respondem 501, como o backend sem a BE-13. */
let avaliacoesDisponiveis = true

/** "Cookie HttpOnly" sessionid deste navegador: o JavaScript da página não o lê. */
let cookieSessao = null

const ok = (dados, status = 200) => ({ status, dados })
const erro = (status, codigo, mensagem, extra = {}) => ({
  status,
  dados: { codigo, mensagem, ...extra },
})
const csrfInvalido = () =>
  erro(
    403,
    'csrf_invalido',
    'Não foi possível confirmar a origem do pedido. Recarregue a página e tente de novo.',
  )
const naoAutenticado = () =>
  erro(401, 'nao_autenticado', 'É preciso entrar na conta para continuar.')

const limiteExcedido = () =>
  erro(429, 'limite_excedido', 'Muitos pedidos seguidos. Tente de novo mais tarde.')

/** 32 caracteres alfanuméricos, como o segredo do CSRF do Django. */
function gerarToken() {
  const aleatorio = () =>
    globalThis.crypto?.randomUUID?.().replaceAll('-', '') ??
    Array.from({ length: 32 }, () => Math.floor(Math.random() * 36).toString(36)).join('')
  return aleatorio()
}

function lerCookieCsrf() {
  if (typeof document === 'undefined') return null
  const par = document.cookie.split('; ').find((item) => item.startsWith('csrftoken='))
  return par ? decodeURIComponent(par.slice('csrftoken='.length)) || null : null
}

function gravarCookieCsrf(valor) {
  if (typeof document !== 'undefined') {
    document.cookie = `csrftoken=${encodeURIComponent(valor)}; path=/; SameSite=Lax`
  }
}

/** Conta o pedido na janela de 1 hora e diz se passou do limite. */
function passouDoLimite(mapa, chave, limite, agora) {
  const recentes = (mapa.get(chave) ?? []).filter((t) => agora - t < HORA)
  recentes.push(agora)
  mapa.set(chave, recentes)
  return recentes.length > limite
}

const normalizarEmail = (email = '') => String(email).trim().toLowerCase()

function usuarioPorEmail(email) {
  return banco.estado.usuarios.find((u) => u.email === normalizarEmail(email))
}

function usuarioDaSessao() {
  const id = cookieSessao ? sessoes.get(cookieSessao) : null
  return id ? banco.estado.usuarios.find((u) => u.id === id) : null
}

/** Corpo do schema `Sessao`: nunca matrícula/SIAPE ou e-mail (RI10). */
const corpoSessao = (usuario) => ({
  apelido: usuario.apelido,
  tipo: usuario.tipo,
  avisoPrivacidadePendente: !usuario.aceitouAvisoAtualizado,
})

/** RF02: cadastro pendente não confirmado em 24h é excluído. */
function removerPendentesExpirados(agora) {
  const { estado } = banco
  const antes = estado.usuarios.length
  estado.usuarios = estado.usuarios.filter(
    (u) => u.confirmado || agora - new Date(u.ultimoEnvio) < VALIDADE_CONFIRMACAO,
  )
  if (estado.usuarios.length !== antes) banco.salvar()
}

function criarLink(tipo, usuario, validade, agora) {
  const { estado } = banco
  // Um novo link invalida os anteriores do mesmo tipo para a mesma conta.
  estado.links = estado.links.filter((l) => !(l.tipo === tipo && l.usuarioId === usuario.id))
  const token = gerarToken()
  estado.links.push({
    token,
    tipo,
    usuarioId: usuario.id,
    usado: false,
    expiraEm: new Date(agora.getTime() + validade).toISOString(),
  })
  banco.salvar()
  const rota = tipo === 'confirmacao' ? '/confirmar-email' : '/redefinir-senha'
  return `${rota}?token=${encodeURIComponent(token)}`
}

/** Usa o link uma vez só. Fica marcado como usado para o reenvio por token. */
function consumirLink(tipo, token, agora) {
  const link = banco.estado.links.find((l) => l.tipo === tipo && l.token === token)
  if (!link || link.usado) return null
  link.usado = true
  banco.salvar()
  return new Date(link.expiraEm) > agora ? link : null
}

// ─── Cadastro (POST /api/cadastro/) ───────────────────────────────────────

const dadosInvalidos = (mensagem) => erro(422, 'dados_invalidos', mensagem)

function sugerirApelido(base, emUso) {
  const raiz = (base.length >= 3 ? base : base.padEnd(3, '0')).slice(0, 18)
  for (let n = 1; ; n++) if (!emUso(`${raiz}${n}`)) return `${raiz}${n}`
}

function cadastrar(corpo, agora) {
  const {
    tipoUsuario,
    emailInstitucional = '',
    senha = '',
    apelido = '',
    matriculaSiape = '',
    aceitePrivacidade,
  } = corpo
  if (tipoUsuario !== 'estudante' && tipoUsuario !== 'professor_servidor') {
    return dadosInvalidos('Escolha se você é aluno, professor ou servidor.')
  }
  if (aceitePrivacidade !== true) {
    return dadosInvalidos('É preciso aceitar o aviso de privacidade para criar a conta.')
  }

  let identificador
  let apelidoFinal
  if (tipoUsuario === 'estudante') {
    const analise = analisarEmailEstudante(emailInstitucional, agora)
    if (analise.erro) return dadosInvalidos(analise.erro)
    identificador = analise.matricula
    apelidoFinal = apelido.trim()
  } else {
    const erroSiape = validarSiape(matriculaSiape)
    if (erroSiape) return dadosInvalidos(erroSiape)
    const analise = analisarEmailServidor(emailInstitucional)
    if (analise.erro) return dadosInvalidos(analise.erro)
    identificador = matriculaSiape
    apelidoFinal = apelido.trim() || analise.apelido
  }

  const erroSenha = validarSenha(senha)
  if (erroSenha) return dadosInvalidos(erroSenha)

  const emailNormalizado = normalizarEmail(emailInstitucional)
  const { usuarios } = banco.estado
  if (usuarios.some((u) => u.email === emailNormalizado || u.identificador === identificador)) {
    // Mensagem única, sem revelar qual dos dois já existe (RF01.5).
    return dadosInvalidos('Matrícula/SIAPE ou e-mail já cadastrados.')
  }

  const apelidoEmUso = (valor) =>
    usuarios.some((u) => u.apelido.toLowerCase() === valor.toLowerCase()) ||
    APELIDOS_SEMENTE.some((a) => a.toLowerCase() === valor.toLowerCase())

  const erroApelido = validarApelido(apelidoFinal)
  if (
    tipoUsuario === 'professor_servidor' &&
    !apelido.trim() &&
    (erroApelido || apelidoEmUso(apelidoFinal))
  ) {
    return erro(
      409,
      'apelido_indisponivel',
      `Não foi possível usar "${apelidoFinal}" como apelido. Escolha um apelido para exibir nas suas avaliações.`,
      { apelidoSugerido: sugerirApelido(apelidoFinal, apelidoEmUso) },
    )
  }
  if (erroApelido) return dadosInvalidos(erroApelido)
  if (apelidoEmUso(apelidoFinal))
    return dadosInvalidos('Este apelido já está em uso. Escolha outro.')

  const usuario = {
    id: banco.novoId(),
    tipo: tipoUsuario,
    email: emailNormalizado,
    identificador,
    apelido: apelidoFinal,
    senha: resumoSenha(senha),
    confirmado: false,
    criadoEm: agora.toISOString(),
    ultimoEnvio: agora.toISOString(),
  }
  usuarios.push(usuario)
  const linkSimulado = criarLink('confirmacao', usuario, VALIDADE_CONFIRMACAO, agora)
  return ok({ emailInstitucional: usuario.email, status: 'pendente', linkSimulado }, 201)
}

// ─── Confirmação e reenvio ────────────────────────────────────────────────

function confirmarEmail(token, agora) {
  const link = consumirLink('confirmacao', token, agora)
  const usuario = link && banco.estado.usuarios.find((u) => u.id === link.usuarioId)
  if (!usuario) {
    return erro(
      410,
      'token_invalido_ou_expirado',
      'Este link de confirmação é inválido, expirou ou já foi usado. Peça um novo link.',
    )
  }
  usuario.confirmado = true
  banco.salvar()
  return ok(null)
}

function reenviarConfirmacao({ emailInstitucional, token }, agora) {
  if (!emailInstitucional && !token) {
    return dadosInvalidos('Informe o seu e-mail institucional ou abra o link recebido.')
  }
  // Como o backend: vale o e-mail; se ele não achar conta, o token é tentado.
  // O domínio não é conferido: um e-mail fora do padrão só não acha conta.
  let usuario = emailInstitucional ? usuarioPorEmail(emailInstitucional) : null
  if (!usuario && token) {
    const link = banco.estado.links.find((l) => l.tipo === 'confirmacao' && l.token === token)
    usuario = link && banco.estado.usuarios.find((u) => u.id === link.usuarioId)
  }

  // Como o backend: 200 sem corpo, exista ou não uma conta pendente (RF02.2).
  // Só o `linkSimulado` do modo demonstração aparece quando há o que reenviar.
  if (usuario && !usuario.confirmado) {
    // Limite por conta: silencioso, responde igual sem mandar outro link (#123).
    if (passouDoLimite(reenviosPorConta, usuario.id, LIMITE_REENVIOS_POR_CONTA, agora)) {
      return ok(null)
    }
    usuario.ultimoEnvio = agora.toISOString() // renova o prazo de 24h (RF02)
    return ok({ linkSimulado: criarLink('confirmacao', usuario, VALIDADE_CONFIRMACAO, agora) })
  }
  return ok(null)
}

// ─── Sessão (/api/sessao/: POST entra, GET quem sou, DELETE sai) ──────────

function entrar({ emailInstitucional, senha }, agora) {
  if (
    typeof emailInstitucional !== 'string' ||
    typeof senha !== 'string' ||
    !emailInstitucional.trim() ||
    !senha
  ) {
    return dadosInvalidos('Informe o seu e-mail institucional e a senha.')
  }
  const chave = normalizarEmail(emailInstitucional)
  // Não conta como tentativa (RN01).
  if (!ehEmailInstitucional(chave)) {
    return dadosInvalidos('Informe o seu e-mail institucional da UnB (@aluno.unb.br ou @unb.br).')
  }
  const fimBloqueio = bloqueiosLogin.get(chave)
  if (fimBloqueio && fimBloqueio > agora) {
    const minutos = Math.ceil((fimBloqueio - agora) / MINUTO)
    return erro(429, 'login_bloqueado', `Muitas tentativas. Tente de novo em ${minutos} min.`)
  }

  const usuario = usuarioPorEmail(chave)
  if (!usuario || usuario.senha !== resumoSenha(senha)) {
    const recentes = (tentativasLogin.get(chave) ?? []).filter(
      (t) => agora - t < JANELA_BLOQUEIO_LOGIN,
    )
    recentes.push(agora)
    tentativasLogin.set(chave, recentes)
    if (recentes.length >= LIMITE_TENTATIVAS_LOGIN) {
      bloqueiosLogin.set(chave, new Date(agora.getTime() + JANELA_BLOQUEIO_LOGIN))
      tentativasLogin.delete(chave)
      return erro(429, 'login_bloqueado', 'Muitas tentativas. Tente de novo em 10 min.')
    }
    // Mensagem genérica: não indica se a conta existe (RF03.1).
    return erro(401, 'credenciais_invalidas', 'E-mail ou senha incorretos.')
  }

  tentativasLogin.delete(chave)
  if (!usuario.confirmado) {
    return erro(
      403,
      'conta_nao_confirmada',
      'Confirme seu e-mail antes de entrar. Se o link venceu, peça um novo.',
    )
  }

  // Como o Django: nova sessão e novo csrftoken a cada login.
  if (cookieSessao) sessoes.delete(cookieSessao)
  cookieSessao = gerarToken()
  sessoes.set(cookieSessao, usuario.id)
  gravarCookieCsrf(gerarToken())
  return ok(corpoSessao(usuario))
}

function quemSou() {
  const usuario = usuarioDaSessao()
  return usuario ? ok(corpoSessao(usuario)) : naoAutenticado()
}

function sair() {
  if (!usuarioDaSessao()) return naoAutenticado()
  sessoes.delete(cookieSessao)
  cookieSessao = null
  return ok(null, 204)
}

// ─── Recuperação de senha (fora do contrato v1; ligada à API na FE-E2) ────

function solicitarRecuperacao({ email = '' }, agora) {
  const chave = normalizarEmail(email)
  const resposta = {
    mensagem: 'Se houver uma conta com este e-mail, enviaremos um link para redefinir a senha.',
  }

  const recentes = (pedidosRecuperacao.get(chave) ?? []).filter((t) => agora - t < HORA)
  if (recentes.length >= LIMITE_RECUPERACOES_POR_HORA) {
    return erro(
      429,
      'limite_de_pedidos',
      'Limite de 3 solicitações por hora atingido. Tente novamente mais tarde.',
    )
  }
  recentes.push(agora)
  pedidosRecuperacao.set(chave, recentes)

  const usuario = usuarioPorEmail(chave)
  if (usuario?.confirmado) {
    resposta.linkSimulado = criarLink('redefinicao', usuario, VALIDADE_REDEFINICAO, agora)
  }
  return ok(resposta)
}

function redefinirSenha({ token = '', senha = '' }, agora) {
  const erroSenha = validarSenha(senha)
  if (erroSenha) return dadosInvalidos(erroSenha)
  const link = consumirLink('redefinicao', token, agora)
  const usuario = link && banco.estado.usuarios.find((u) => u.id === link.usuarioId)
  if (!usuario) {
    return erro(
      410,
      'token_invalido_ou_expirado',
      'Este link de redefinição expirou, já foi usado ou é inválido.',
    )
  }

  usuario.senha = resumoSenha(senha)
  banco.salvar()
  // A senha anterior deixa de valer e as sessões ativas são encerradas (RF04).
  for (const [sessao, id] of sessoes) if (id === usuario.id) sessoes.delete(sessao)
  return ok({ redefinida: true })
}

// ─── Cardápio e avaliações ────────────────────────────────────────────────

function listarCampi() {
  return ok(structuredClone(CAMPI_DO_BANCO))
}

function obterCardapio(valor, agora) {
  const campus = idDoCampus(valor)
  if (!campus) return erro(404, 'campus_nao_encontrado', 'Campus não encontrado.')
  return ok(montarCardapioSemana(campus, agora))
}

const AVISO_SUJEITO_A_ALTERACAO =
  'Cardápio sujeito a alteração. A ausência de marcador não garante que o prato esteja livre do ingrediente.'

const DIETA_DA_LINHA = {
  todas: null,
  padrao: 'padrao',
  ovolacto: 'ovolacto',
  vegano: 'vegetariano_estrito',
}

const DIETAS_ACEITAS = {
  sem_filtro: null,
  ovolactovegetariano: [null, 'ovolacto', 'vegetariano_estrito'],
  vegetariano_estrito: [null, 'vegetariano_estrito'],
}

function ehDataISO(valor) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(valor ?? '')) return false
  const data = new Date(`${valor}T00:00:00Z`)
  return !Number.isNaN(data.getTime()) && data.toISOString().startsWith(valor)
}
const dataNaFaixa = (valor) => ehDataISO(valor) && valor >= '2000-01-01' && valor <= '2099-12-31'
const PARAMETROS_DO_CARDAPIO = ['campus', 'semana', 'dia', 'refeicao', 'marcadores', 'dieta']
const parametrosInvalidos = (mensagem = 'Parâmetros do cardápio inválidos.') =>
  erro(400, 'parametros_invalidos', mensagem)

function filtrarRefeicao(refeicao, { dieta, marcadores }) {
  const linhas = DIETAS_ACEITAS[dieta]
  const desativado = refeicao.alergenosIndisponiveis
  return refeicao.categorias
    .filter((categoria) => !linhas || linhas.includes(DIETA_DA_LINHA[categoria.dieta]))
    .map((categoria) => {
      const pratos = categoria.pratos.map((prato) => ({
        descricao: prato.nome,
        marcadores: [...prato.marcadores],
        contemMarcadorSelecionado:
          !desativado && prato.marcadores.some((m) => marcadores.includes(m)),
      }))
      return {
        nome: categoria.rotulo,
        pratos,
        semOpcaoCompativel:
          pratos.length > 0 && pratos.every((prato) => prato.contemMarcadorSelecionado),
      }
    })
}

function cardapioFiltrado(parametros, agora) {
  const campus = idDoCampus(parametros.campus)
  const dieta = parametros.dieta ?? 'sem_filtro'
  if (/^[1-9]\d*$/.test(parametros.campus ?? '') && !campus) {
    return parametrosInvalidos(MENSAGEM_CAMPUS_INEXISTENTE)
  }
  if (
    !campus ||
    Object.keys(parametros).some((nome) => !PARAMETROS_DO_CARDAPIO.includes(nome)) ||
    !Object.hasOwn(DIETAS_ACEITAS, dieta) ||
    (parametros.refeicao && !REFEICOES[parametros.refeicao]) ||
    (parametros.dia !== undefined && !dataNaFaixa(parametros.dia)) ||
    (parametros.semana !== undefined && !dataNaFaixa(parametros.semana))
  ) {
    return parametrosInvalidos()
  }
  const marcadores = parametros.marcadores === undefined ? [] : parametros.marcadores.split(',')
  if (marcadores.some((nome) => !nome)) return parametrosInvalidos()
  const desconhecido = marcadores.find((nome) => !IDS_MARCADORES.includes(nome))
  if (desconhecido) return parametrosInvalidos(`Marcador desconhecido: ${desconhecido}.`)
  const hoje = hojeISO(agora)
  const semana = montarCardapioSemana(campus, agora)
  const base = {
    campus,
    avisoSujeitoAAlteracao: AVISO_SUJEITO_A_ALTERACAO,
    alergenosIndisponivel: false,
    filtroMarcadorDesativado: false,
    refeicaoEncerrada: false,
    semServico: false,
    categorias: [],
  }
  const naoPublicado = (data) =>
    ok({
      ...base,
      status: 'nao_publicado',
      data,
      refeicao: parametros.refeicao ?? refeicaoPadrao(ORDEM_REFEICOES, agora),
    })

  if (!semana.publicado) return naoPublicado(parametros.dia ?? hoje)
  const pedido = parametros.dia ?? hoje
  const naoServida = (data, tipo, extra = {}) =>
    ok({ ...base, status: 'publicado', data, refeicao: tipo, ...extra })
  const dia =
    semana.dias.find((d) => d.data === pedido) ??
    (parametros.refeicao ? null : semana.dias.find((d) => d.data > pedido))
  if (!dia && parametros.refeicao) return naoServida(pedido, parametros.refeicao)
  if (!dia) {
    return naoServida(pedido, refeicaoPadrao(ORDEM_REFEICOES, agora), { semServico: true })
  }

  const tipos = ORDEM_REFEICOES.filter((tipo) => dia.refeicoes.some((r) => r.tipo === tipo))
  if (parametros.refeicao && !tipos.includes(parametros.refeicao)) {
    return naoServida(dia.data, parametros.refeicao)
  }
  const tipo =
    parametros.refeicao ?? (dia.data === hoje ? refeicaoPadrao(tipos, agora) : tipos[0])
  const refeicao = dia.refeicoes.find((r) => r.tipo === tipo)
  const ultima = tipos.at(-1)
  return ok({
    ...base,
    status: 'publicado',
    data: dia.data,
    refeicao: tipo,
    alergenosIndisponivel: refeicao.alergenosIndisponiveis,
    filtroMarcadorDesativado: refeicao.alergenosIndisponiveis,
    refeicaoEncerrada:
      dia.data === hoje &&
      tipo === ultima &&
      minutosAgora(agora) > minutosDoDia(REFEICOES[ultima].fim),
    categorias: filtrarRefeicao(refeicao, { dieta, marcadores }),
  })
}

const idDaRefeicao = (campus, data, tipo) =>
  Number(`${campus}${data.replaceAll('-', '')}${ORDEM_REFEICOES.indexOf(tipo)}`)

function resumoDoDia(campus, data, agora) {
  const dia = montarCardapioSemana(campus, agora).dias.find((d) => d.data === data)
  if (!dia) return ok([])
  return ok(
    ORDEM_REFEICOES.filter((tipo) => dia.refeicoes.some((r) => r.tipo === tipo)).map((tipo) => {
      const { soma, quantidade } = avaliacoesDaRefeicao(campus, data, tipo, agora)
      return {
        refeicaoId: idDaRefeicao(campus, data, tipo),
        tipo,
        media: quantidade ? soma / quantidade : null,
        quantidade,
      }
    }),
  )
}

function avaliacoesDaRefeicao(campus, data, refeicao, agora) {
  const semente = avaliacoesSemente(campus, data, refeicao, agora)
  const reais = banco.estado.avaliacoes.filter(
    (a) => a.campus === campus && a.data === data && a.refeicao === refeicao,
  )
  const soma = semente.soma + reais.reduce((total, a) => total + a.nota, 0)
  const quantidade = semente.quantidade + reais.length
  return { soma, quantidade, reais, comentarios: semente.comentarios }
}

function listarAvaliacoes(parametros, agora) {
  const { data, refeicao } = parametros
  const campus = idDoCampus(parametros.campus)
  if (!campus || !REFEICOES[refeicao] || !data) {
    return erro(400, 'parametros_invalidos', 'Informe campus, data e refeição.')
  }
  const { soma, quantidade, reais, comentarios } = avaliacoesDaRefeicao(
    campus,
    data,
    refeicao,
    agora,
  )
  const apelidoPorId = new Map(banco.estado.usuarios.map((u) => [u.id, u.apelido]))
  const lista = [
    ...reais.map((a) => ({
      id: a.id,
      apelido: apelidoPorId.get(a.usuarioId) ?? 'usuário removido',
      nota: a.nota,
      comentario: a.comentario,
      criadaEm: a.atualizadaEm,
    })),
    ...comentarios,
  ]
    .filter((a) => a.comentario)
    .sort((a, b) => b.criadaEm.localeCompare(a.criadaEm))

  const usuario = usuarioDaSessao()
  const minha = usuario ? reais.find((a) => a.usuarioId === usuario.id) : null
  return ok({
    media: quantidade ? soma / quantidade : null,
    quantidade,
    avaliacoes: lista,
    minha: minha ? { nota: minha.nota, comentario: minha.comentario } : null,
  })
}

function resumoSemana(parametros, agora) {
  const campus = idDoCampus(parametros.campus)
  if (parametros.data !== undefined) {
    if (!campus || !ehDataISO(parametros.data)) {
      return erro(400, 'parametros_invalidos', 'Parâmetros do resumo inválidos.')
    }
    if (!resumoDoDiaDisponivel) return { status: 501, dados: null }
    return resumoDoDia(campus, parametros.data, agora)
  }
  if (!campus) return erro(404, 'campus_nao_encontrado', 'Campus não encontrado.')
  const { dias } = montarCardapioSemana(campus, agora)
  let somaSemana = 0
  let quantidadeSemana = 0
  const resumoDias = dias.map((dia) => {
    let soma = 0
    let quantidade = 0
    for (const { tipo } of dia.refeicoes) {
      const parcial = avaliacoesDaRefeicao(campus, dia.data, tipo, agora)
      soma += parcial.soma
      quantidade += parcial.quantidade
    }
    somaSemana += soma
    quantidadeSemana += quantidade
    return { data: dia.data, media: quantidade ? soma / quantidade : null, quantidade }
  })
  return ok({
    media: quantidadeSemana ? somaSemana / quantidadeSemana : null,
    quantidade: quantidadeSemana,
    dias: resumoDias,
  })
}

/** Refeição do simulado pelo `refeicaoId` do resumo do dia, ou null. */
function refeicaoPorId(refeicaoId, agora) {
  if (!Number.isSafeInteger(refeicaoId) || refeicaoId <= 0) return null
  const texto = String(refeicaoId)
  const tipo = ORDEM_REFEICOES[Number(texto.at(-1))]
  const digitos = texto.slice(-9, -1)
  const campus = Number(texto.slice(0, -9))
  if (!tipo || digitos.length !== 8 || !campus) return null
  const data = `${digitos.slice(0, 4)}-${digitos.slice(4, 6)}-${digitos.slice(6, 8)}`
  if (!refeicaoExiste(campus, data, tipo, agora)) return null
  return { refeicaoId, campus, data, tipo }
}

const refeicaoNaoEncontrada = () =>
  erro(404, 'refeicao_nao_encontrada', 'Refeição não encontrada no cardápio.')

/**
 * GET /refeicoes/{refeicaoId}/avaliacoes/ (schema AvaliacoesDaRefeicao).
 * Público. Conta removida aparece como "usuário removido" (RNF07.4) e nada
 * além do apelido sai do autor (RI10).
 */
function avaliacoesDaRefeicaoPorId(refeicaoId, agora) {
  if (!avaliacoesDisponiveis) return { status: 501, dados: null }
  const refeicao = refeicaoPorId(refeicaoId, agora)
  if (!refeicao) return refeicaoNaoEncontrada()
  const { campus, data, tipo } = refeicao
  const { soma, quantidade, reais, comentarios } = avaliacoesDaRefeicao(campus, data, tipo, agora)
  const apelidoPorId = new Map(banco.estado.usuarios.map((u) => [u.id, u.apelido]))
  const publicas = [
    ...reais.map((a) => ({
      apelido: apelidoPorId.get(a.usuarioId) ?? 'usuário removido',
      nota: a.nota,
      comentario: a.comentario,
      criadaEm: a.criadaEm ?? a.atualizadaEm,
    })),
    ...comentarios.map(({ apelido, nota, comentario, criadaEm }) => ({
      apelido,
      nota,
      comentario,
      criadaEm,
    })),
  ].sort((a, b) => b.criadaEm.localeCompare(a.criadaEm))
  return ok({
    resumoAvaliacoes: { media: quantidade ? soma / quantidade : null, quantidade },
    comentarios: publicas,
  })
}

/**
 * POST /avaliacoes/ (contrato da BE-13): sempre upsert. 201 na primeira, 200
 * na edição (não pontua de novo). O bloco `pontos` volta zerado: os 5 pontos
 * só valem com check-in na mesma refeição (Anexo A), e o simulado não liga a
 * avaliação ao check-in; o check-in, que não depende disso, já dá os 10.
 */
function avaliar(corpo, agora) {
  const usuario = usuarioDaSessao()
  if (!usuario) return naoAutenticado()
  if (!avaliacoesDisponiveis) return { status: 501, dados: null }

  const { refeicaoId, nota, comentario = '' } = corpo
  const refeicao = refeicaoPorId(refeicaoId, agora)
  if (!refeicao) return refeicaoNaoEncontrada()
  if (!Number.isInteger(nota) || nota < 1 || nota > 5) {
    return erro(422, 'nota_invalida', 'Escolha uma nota de 1 a 5 estrelas.')
  }
  if (typeof comentario !== 'string' || comentario.length > 500) {
    return erro(422, 'comentario_muito_longo', 'O comentário pode ter no máximo 500 caracteres.')
  }
  const { campus, data, tipo } = refeicao
  const comecou = minutosAgora(agora) >= minutosDoDia(REFEICOES[tipo].inicio)
  if (data !== hojeISO(agora) || !comecou) {
    return erro(
      422,
      'janela_avaliacao_fechada',
      'Só é possível avaliar refeições de hoje que já começaram.',
    )
  }

  const instante = agora.toISOString()
  const texto = comentario.trim()
  const existente = banco.estado.avaliacoes.find(
    (a) =>
      a.usuarioId === usuario.id && a.campus === campus && a.data === data && a.refeicao === tipo,
  )
  let avaliacao = existente
  if (existente) {
    Object.assign(existente, {
      nota,
      comentario: texto,
      editadaEm: instante,
      atualizadaEm: instante,
    })
  } else {
    avaliacao = {
      id: banco.novoId(),
      usuarioId: usuario.id,
      refeicaoId,
      campus,
      data,
      refeicao: tipo,
      nota,
      comentario: texto,
      criadaEm: instante,
      editadaEm: null,
      atualizadaEm: instante,
    }
    banco.estado.avaliacoes.push(avaliacao)
  }
  banco.salvar()
  return ok(
    {
      avaliacao: {
        id: avaliacao.id,
        refeicaoId,
        nota,
        comentario: texto,
        criadaEm: avaliacao.criadaEm ?? instante,
        editadaEm: avaliacao.editadaEm ?? null,
      },
      pontos: { total: 0, contribuicao: 0, avaliacaoLiberada: 0 },
    },
    existente ? 200 : 201,
  )
}

// ─── Roteamento ───────────────────────────────────────────────────────────

function gravarCsrfSeFaltar() {
  // Como o `get_token` do Django: mantém o token que já existe.
  if (!tokenCsrfValido(lerCookieCsrf())) gravarCookieCsrf(gerarToken())
  return ok(null, 204)
}

// ─── Aviso de privacidade e check-in (BE-09) ─────────────────────────────────

/** POST /privacidade/aceite/: sem corpo, 204 (RF11, RNF07.1). */
function registrarAceitePrivacidade(agora) {
  const usuario = usuarioDaSessao()
  if (!usuario) return naoAutenticado()
  usuario.aceitouAvisoAtualizado = true
  usuario.aceiteAvisoEm = agora.toISOString()
  banco.salvar()
  return { status: 204, dados: null }
}

const numeroNaFaixa = (valor, limite) =>
  typeof valor === 'number' && Number.isFinite(valor) && Math.abs(valor) <= limite

function corpoCheckinValido({ campus, tipoRefeicao, coordenadas }) {
  return (
    Number.isInteger(campus) &&
    idDoCampus(campus) === campus &&
    Object.hasOwn(REFEICOES, tipoRefeicao ?? '') &&
    numeroNaFaixa(coordenadas?.latitude, 90) &&
    numeroNaFaixa(coordenadas?.longitude, 180)
  )
}

/**
 * POST /checkins/ na ordem do backend (Fila N4): sessão, formato, aviso de
 * privacidade, horário, duplicidade (por conta, campus, refeição e dia, como o
 * UNIQUE `checkin_unico_por_usuario_campus_tipo_data`) e distância. As coordenadas não são
 * gravadas (RI09): o registro só tem conta, campus, refeição e data.
 */
function registrarCheckin(corpo, agora) {
  const usuario = usuarioDaSessao()
  if (!usuario) return naoAutenticado()
  if (!corpoCheckinValido(corpo)) {
    return erro(400, 'dados_invalidos', 'Não foi possível registrar o check-in.')
  }
  if (!usuario.aceitouAvisoAtualizado) {
    return erro(
      403,
      'aviso_privacidade_pendente',
      'Dê ciência ao aviso de privacidade atualizado antes do check-in.',
    )
  }

  const { campus, tipoRefeicao } = corpo
  const { inicio, fim } = REFEICOES[tipoRefeicao]
  const minutos = minutosAgora(agora)
  if (minutos < minutosDoDia(inicio) || minutos > minutosDoDia(fim)) {
    return erro(422, 'fora_do_horario', mensagemForaDoHorario(tipoRefeicao))
  }

  const data = hojeISO(agora)
  const { estado } = banco
  estado.checkins ??= []
  const repetido = estado.checkins.some(
    (c) =>
      c.usuarioId === usuario.id &&
      c.campus === campus &&
      c.tipoRefeicao === tipoRefeicao &&
      c.data === data,
  )
  if (repetido) {
    return erro(422, 'checkin_duplicado', 'Você já fez check-in nesta refeição hoje.')
  }
  if (!localizacaoConfirmada) {
    return erro(
      422,
      'localizacao_nao_confirmada',
      'Não foi possível confirmar que você está no RU.',
    )
  }

  const checkin = { id: estado.proximoId++, campus, tipoRefeicao, data }
  estado.checkins.push({ ...checkin, usuarioId: usuario.id })
  banco.salvar()
  // Os 10 pontos do check-in confirmado (Anexo A, RN09), como a BE-14 vai
  // devolver; o backend real ainda volta zerado até lá.
  return ok({ checkin, pontos: { total: 10, contribuicao: 10, avaliacaoLiberada: 0 } }, 201)
}

function previsaoDaFila(parametros, agora) {
  const extras = Object.keys(parametros).filter(
    (nome) => !['campus', 'refeicao', 'data'].includes(nome),
  )
  if (
    !/^[1-9]\d*$/.test(parametros.campus ?? '') ||
    !Object.hasOwn(REFEICOES, parametros.refeicao ?? '') ||
    (parametros.data !== undefined && !ehDataISO(parametros.data)) ||
    extras.length
  ) {
    return erro(400, 'parametros_invalidos', 'Parâmetros da previsão inválidos.')
  }
  const campus = idDoCampus(parametros.campus)
  if (!campus) return erro(404, 'campus_nao_encontrado', 'Campus não encontrado.')
  if (!previsaoDisponivel) return { status: 501, dados: null }
  return ok(previsaoSimulada(campus, parametros.refeicao, parametros.data ?? hojeISO(agora)))
}

// Terceiro item: nome do limite por IP da rota (LIMITES_POR_IP), se houver.
const ROTAS = [
  ['GET', /^\/csrf\/$/, () => gravarCsrfSeFaltar()],
  ['POST', /^\/cadastro\/$/, ({ corpo, agora }) => cadastrar(corpo, agora), 'cadastro'],
  [
    'POST',
    /^\/confirmar-email\/([^/]+)\/$/,
    ({ agora }, [token]) => confirmarEmail(decodeURIComponent(token), agora),
  ],
  [
    'POST',
    /^\/reenviar-confirmacao\/$/,
    ({ corpo, agora }) => reenviarConfirmacao(corpo, agora),
    'reenvio',
  ],
  ['GET', /^\/sessao\/$/, () => quemSou()],
  ['POST', /^\/sessao\/$/, ({ corpo, agora }) => entrar(corpo, agora), 'login'],
  ['DELETE', /^\/sessao\/$/, () => sair()],
  ['POST', /^\/recuperar-senha\/$/, ({ corpo, agora }) => solicitarRecuperacao(corpo, agora)],
  ['POST', /^\/redefinir-senha\/$/, ({ corpo, agora }) => redefinirSenha(corpo, agora)],
  ['GET', /^\/campi\/$/, () => listarCampi()],
  ['GET', /^\/cardapio\/$/, ({ parametros, agora }) => cardapioFiltrado(parametros, agora)],
  ['GET', /^\/cardapio\/([\w-]+)\/$/, ({ agora }, [campus]) => obterCardapio(campus, agora)],
  ['GET', /^\/avaliacoes\/resumo\/$/, ({ parametros, agora }) => resumoSemana(parametros, agora)],
  ['GET', /^\/avaliacoes\/$/, ({ parametros, agora }) => listarAvaliacoes(parametros, agora)],
  ['POST', /^\/avaliacoes\/$/, ({ corpo, agora }) => avaliar(corpo, agora)],
  [
    'GET',
    /^\/refeicoes\/(\d+)\/avaliacoes\/$/,
    ({ agora }, [id]) => avaliacoesDaRefeicaoPorId(Number(id), agora),
  ],
  ['POST', /^\/privacidade\/aceite\/$/, ({ agora }) => registrarAceitePrivacidade(agora)],
  ['POST', /^\/checkins\/$/, ({ corpo, agora }) => registrarCheckin(corpo, agora)],
  ['GET', /^\/fila\/previsao\/$/, ({ parametros, agora }) => previsaoDaFila(parametros, agora)],
]

const ATRASO_MS = import.meta.env.MODE === 'test' ? 0 : 250

const tokenCsrfValido = (valor) => /^[A-Za-z0-9]{32}([A-Za-z0-9]{32})?$/.test(valor ?? '')

/**
 * Como o backend (`CsrfObrigatorio`, #112): toda escrita cobra o CSRF, com ou
 * sem sessão, e leituras passam direto. Como no Django, compara o cabeçalho
 * com o cookie, sem guardar nada em memória: o cookie sobrevive ao F5.
 */
function csrfRecusado(metodo, cabecalhos) {
  if (!METODOS_DE_ESCRITA.has(metodo)) return false
  const cookie = lerCookieCsrf()
  return !tokenCsrfValido(cookie) || cabecalhos['X-CSRFToken'] !== cookie
}

export async function tratarRequisicaoSimulada({ metodo, caminho, corpo, cabecalhos = {} }) {
  if (ATRASO_MS) await new Promise((resolver) => setTimeout(resolver, ATRASO_MS))

  const agora = new Date()
  removerPendentesExpirados(agora)

  const url = new URL(caminho, 'http://simulado')
  const parametros = Object.fromEntries(url.searchParams)
  for (const [verbo, padrao, tratar, limite] of ROTAS) {
    const encontrado = verbo === metodo && padrao.exec(url.pathname)
    if (!encontrado) continue
    // Mesma ordem do DRF: primeiro o CSRF, depois o limite de taxa.
    if (csrfRecusado(metodo, cabecalhos)) return csrfInvalido()
    if (limite && passouDoLimite(pedidosPorRota, limite, LIMITES_POR_IP[limite], agora)) {
      return limiteExcedido()
    }
    return tratar({ corpo: structuredClone(corpo ?? {}), parametros, agora }, encontrado.slice(1))
  }
  return erro(404, 'nao_encontrado', 'O recurso pedido não existe.')
}

/** Ganchos para os testes. */
export const simulacao = {
  /** O servidor esqueceu a sessão (expirou ou foi encerrada em outro aparelho). */
  expirarSessao() {
    sessoes.clear()
  },
  /** `false`: o check-in recebe 422 `localizacao_nao_confirmada` (fora do raio do RU). */
  definirLocalizacaoConfirmada(confirmada) {
    localizacaoConfirmada = confirmada
  },
  definirAvaliacoesDisponiveis(disponiveis) {
    avaliacoesDisponiveis = disponiveis
  },
  definirResumoDoDiaDisponivel(disponivel) {
    resumoDoDiaDisponivel = disponivel
  },
  definirPrevisaoDisponivel(disponivel) {
    previsaoDisponivel = disponivel
  },
}

/** Volta ao estado inicial: banco, sessões, cookies e contadores de tentativas. */
export function reiniciarSimulacao() {
  banco.reiniciar()
  sessoes.clear()
  tentativasLogin.clear()
  bloqueiosLogin.clear()
  pedidosRecuperacao.clear()
  pedidosPorRota.clear()
  reenviosPorConta.clear()
  localizacaoConfirmada = true
  resumoDoDiaDisponivel = true
  previsaoDisponivel = true
  avaliacoesDisponiveis = true
  cookieSessao = null
  if (typeof document !== 'undefined') {
    document.cookie = 'csrftoken=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/'
  }
}

export { banco }
