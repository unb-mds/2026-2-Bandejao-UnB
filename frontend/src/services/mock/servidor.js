/**
 * Backend simulado, só para desenvolvimento e testes (o build de produção
 * não o inclui; ver apiClient). Nas rotas que o MVP usa — cadastro,
 * confirmação, reenvio e sessão — segue o contrato OpenAPI v1 da BE-03
 * (backend/openapi.yaml): mesmas rotas, nomes de campos, status HTTP e
 * valores de `codigo`. Erros vêm como `{ codigo, mensagem }`.
 *
 * Também imita o navegador e o Django na sessão (ADR 0007):
 * - o cookie de sessão é "HttpOnly": fica guardado aqui e o apiClient não o vê;
 * - o cookie `csrftoken` é gravado em `document.cookie` no login, e escritas
 *   com sessão sem o cabeçalho `X-CSRFToken` certo recebem 403 (como o DRF).
 *
 * Nos pontos em que o sistema real enviaria um e-mail, a resposta traz o
 * campo extra `linkSimulado` (fora do contrato), que a interface mostra
 * apenas em modo de simulação. Recuperação de senha, cardápio e avaliações
 * ainda têm o formato do MVP: entram no contrato nas tarefas FE-08, FE-09 e
 * FE-E2.
 */
import { campusValido } from '@/constants/campi'
import { REFEICOES, horaInicio } from '@/constants/refeicoes'
import { hojeISO, minutosAgora, minutosDoDia } from '@/utils/datas'
import { banco, resumoSenha } from './banco'
import { montarCardapioSemana, refeicaoExiste } from './cardapios'
import { APELIDOS_SEMENTE, avaliacoesSemente } from './sementes'
import {
  analisarEmailEstudante,
  analisarEmailServidor,
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

/** Estado volátil (some ao recarregar), como no servidor real após reinício. */
const sessoes = new Map() // id da sessão → id do usuário (django_session)
const tentativasLogin = new Map() // matrícula/SIAPE → [instantes das falhas]
const bloqueiosLogin = new Map() // matrícula/SIAPE → instante de fim do bloqueio
const pedidosRecuperacao = new Map() // e-mail → [instantes]

/** "Cookie HttpOnly" sessionid deste navegador: o JavaScript da página não o lê. */
let cookieSessao = null
/** Valor do csrftoken que o servidor gravou por último. */
let csrfAtual = null

const ok = (dados, status = 200) => ({ status, dados })
const erro = (status, codigo, mensagem, extra = {}) => ({
  status,
  dados: { codigo, mensagem, ...extra },
})
const naoAutenticado = () =>
  erro(401, 'nao_autenticado', 'É preciso entrar na conta para continuar.')

function gerarToken() {
  return globalThis.crypto?.randomUUID?.() ?? `${Date.now()}-${Math.random().toString(36).slice(2)}`
}

function gravarCookieCsrf(valor) {
  csrfAtual = valor
  if (typeof document !== 'undefined') {
    document.cookie = `csrftoken=${encodeURIComponent(valor)}; path=/; SameSite=Lax`
  }
}

const normalizarEmail = (email = '') => String(email).trim().toLowerCase()

function usuarioPorEmail(email) {
  return banco.estado.usuarios.find((u) => u.email === normalizarEmail(email))
}

function usuarioPorMatriculaSiape(matriculaSiape = '') {
  const valor = String(matriculaSiape).trim()
  return valor ? banco.estado.usuarios.find((u) => u.identificador === valor) : null
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
    // Mensagem única, sem revelar qual dos dois já existe (RI01).
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
      'Este link de confirmação expirou, já foi usado ou é inválido.',
    )
  }
  usuario.confirmado = true
  banco.salvar()
  return ok(null)
}

function reenviarConfirmacao({ matriculaSiape, token }, agora) {
  if (!matriculaSiape && !token) {
    return dadosInvalidos('Informe a matrícula/SIAPE ou abra de novo o link recebido.')
  }
  let usuario
  if (matriculaSiape) {
    usuario = usuarioPorMatriculaSiape(matriculaSiape)
  } else {
    const link = banco.estado.links.find((l) => l.tipo === 'confirmacao' && l.token === token)
    usuario = link && banco.estado.usuarios.find((u) => u.id === link.usuarioId)
  }

  // Mesma resposta exista ou não uma conta pendente (RF02.2).
  const resposta = {
    mensagem:
      'Se houver um cadastro pendente, enviamos um novo link de confirmação para o e-mail institucional.',
  }
  if (usuario && !usuario.confirmado) {
    usuario.ultimoEnvio = agora.toISOString() // renova o prazo de 24h (RF02)
    resposta.linkSimulado = criarLink('confirmacao', usuario, VALIDADE_CONFIRMACAO, agora)
  }
  return ok(resposta)
}

// ─── Sessão (/api/sessao/: POST entra, GET quem sou, DELETE sai) ──────────

function entrar({ matriculaSiape = '', senha = '' }, agora) {
  const chave = String(matriculaSiape).trim()
  const fimBloqueio = bloqueiosLogin.get(chave)
  if (fimBloqueio && fimBloqueio > agora) {
    const minutos = Math.ceil((fimBloqueio - agora) / MINUTO)
    return erro(429, 'login_bloqueado', `Muitas tentativas. Tente novamente em ${minutos} min.`)
  }

  const usuario = usuarioPorMatriculaSiape(chave)
  if (!usuario || usuario.senha !== resumoSenha(senha)) {
    const recentes = (tentativasLogin.get(chave) ?? []).filter(
      (t) => agora - t < JANELA_BLOQUEIO_LOGIN,
    )
    recentes.push(agora)
    tentativasLogin.set(chave, recentes)
    if (recentes.length >= LIMITE_TENTATIVAS_LOGIN) {
      bloqueiosLogin.set(chave, new Date(agora.getTime() + JANELA_BLOQUEIO_LOGIN))
      tentativasLogin.delete(chave)
      return erro(429, 'login_bloqueado', 'Muitas tentativas. Tente novamente em 10 min.')
    }
    // Mensagem genérica: não indica se a conta existe (RF03.1).
    return erro(401, 'credenciais_invalidas', 'Matrícula/SIAPE ou senha incorretos.')
  }

  tentativasLogin.delete(chave)
  if (!usuario.confirmado) {
    return erro(
      403,
      'conta_nao_confirmada',
      'Confirme seu e-mail antes de entrar. Enviamos um link para a sua caixa de entrada.',
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

function obterCardapio(campus, agora) {
  if (!campusValido(campus)) return erro(404, 'campus_nao_encontrado', 'Campus não encontrado.')
  return ok(montarCardapioSemana(campus, agora))
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
  const { campus, data, refeicao } = parametros
  if (!campusValido(campus) || !REFEICOES[refeicao] || !data) {
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

function resumoSemana({ campus }, agora) {
  if (!campusValido(campus)) return erro(404, 'campus_nao_encontrado', 'Campus não encontrado.')
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

function avaliar(corpo, agora) {
  const usuario = usuarioDaSessao()
  if (!usuario) return naoAutenticado()

  const { campus, data, refeicao, nota, comentario = '' } = corpo
  if (
    !campusValido(campus) ||
    !REFEICOES[refeicao] ||
    !refeicaoExiste(campus, data, refeicao, agora)
  ) {
    return erro(404, 'refeicao_nao_encontrada', 'Refeição não encontrada no cardápio.')
  }
  if (!Number.isInteger(nota) || nota < 1 || nota > 5)
    return erro(422, 'nota_invalida', 'Escolha uma nota de 1 a 5 estrelas.')
  if (comentario.length > 500) {
    return erro(422, 'comentario_muito_longo', 'O comentário pode ter no máximo 500 caracteres.')
  }
  if (data !== hojeISO(agora)) {
    return erro(422, 'fora_do_dia', 'Só é possível avaliar refeições do dia de hoje.')
  }
  const inicio = REFEICOES[refeicao].inicio
  if (minutosAgora(agora) < minutosDoDia(inicio)) {
    return erro(
      422,
      'antes_do_inicio',
      `A avaliação abre às ${horaInicio(refeicao)}, quando a refeição começa.`,
    )
  }

  // Uma avaliação por usuário e refeição; a segunda tentativa edita (RF15).
  const existente = banco.estado.avaliacoes.find(
    (a) =>
      a.usuarioId === usuario.id &&
      a.campus === campus &&
      a.data === data &&
      a.refeicao === refeicao,
  )
  const texto = comentario.trim()
  if (existente) {
    Object.assign(existente, { nota, comentario: texto, atualizadaEm: agora.toISOString() })
  } else {
    banco.estado.avaliacoes.push({
      id: banco.novoId(),
      usuarioId: usuario.id,
      campus,
      data,
      refeicao,
      nota,
      comentario: texto,
      atualizadaEm: agora.toISOString(),
    })
  }
  banco.salvar()
  return ok({ nota, comentario: texto, editada: Boolean(existente) }, existente ? 200 : 201)
}

// ─── Roteamento ───────────────────────────────────────────────────────────

const ROTAS = [
  ['POST', /^\/cadastro\/$/, ({ corpo, agora }) => cadastrar(corpo, agora)],
  [
    'POST',
    /^\/confirmar-email\/([^/]+)\/$/,
    ({ agora }, [token]) => confirmarEmail(decodeURIComponent(token), agora),
  ],
  ['POST', /^\/reenviar-confirmacao\/$/, ({ corpo, agora }) => reenviarConfirmacao(corpo, agora)],
  ['GET', /^\/sessao\/$/, () => quemSou()],
  ['POST', /^\/sessao\/$/, ({ corpo, agora }) => entrar(corpo, agora)],
  ['DELETE', /^\/sessao\/$/, () => sair()],
  ['POST', /^\/recuperar-senha\/$/, ({ corpo, agora }) => solicitarRecuperacao(corpo, agora)],
  ['POST', /^\/redefinir-senha\/$/, ({ corpo, agora }) => redefinirSenha(corpo, agora)],
  ['GET', /^\/cardapio\/([\w-]+)\/$/, ({ agora }, [campus]) => obterCardapio(campus, agora)],
  ['GET', /^\/avaliacoes\/resumo\/$/, ({ parametros, agora }) => resumoSemana(parametros, agora)],
  ['GET', /^\/avaliacoes\/$/, ({ parametros, agora }) => listarAvaliacoes(parametros, agora)],
  ['POST', /^\/avaliacoes\/$/, ({ corpo, agora }) => avaliar(corpo, agora)],
]

const ATRASO_MS = import.meta.env.MODE === 'test' ? 0 : 250

/**
 * Como o `SessionAuthentication` do DRF: o CSRF só é cobrado de quem tem
 * sessão. Quem não tem sessão cai no 401 da própria rota, nunca no 403.
 */
function csrfRecusado(metodo, cabecalhos) {
  if (!METODOS_DE_ESCRITA.has(metodo) || !usuarioDaSessao()) return false
  return !csrfAtual || cabecalhos['X-CSRFToken'] !== csrfAtual
}

export async function tratarRequisicaoSimulada({ metodo, caminho, corpo, cabecalhos = {} }) {
  if (ATRASO_MS) await new Promise((resolver) => setTimeout(resolver, ATRASO_MS))

  const agora = new Date()
  removerPendentesExpirados(agora)

  const url = new URL(caminho, 'http://simulado')
  const parametros = Object.fromEntries(url.searchParams)
  for (const [verbo, padrao, tratar] of ROTAS) {
    const encontrado = verbo === metodo && padrao.exec(url.pathname)
    if (!encontrado) continue
    if (csrfRecusado(metodo, cabecalhos)) {
      // Mesmo corpo que o Django devolve hoje (o `codigo` do 403 entra na BE-05).
      return { status: 403, dados: { detail: 'CSRF Failed: CSRF token missing or incorrect.' } }
    }
    return tratar({ corpo: structuredClone(corpo ?? {}), parametros, agora }, encontrado.slice(1))
  }
  return erro(404, 'rota_nao_encontrada', 'Rota não encontrada.')
}

/** Ganchos para os testes. */
export const simulacao = {
  /** O servidor esqueceu a sessão (expirou ou foi encerrada em outro aparelho). */
  expirarSessao() {
    sessoes.clear()
  },
}

/** Volta ao estado inicial: banco, sessões, cookies e contadores de tentativas. */
export function reiniciarSimulacao() {
  banco.reiniciar()
  sessoes.clear()
  tentativasLogin.clear()
  bloqueiosLogin.clear()
  pedidosRecuperacao.clear()
  cookieSessao = null
  csrfAtual = null
  if (typeof document !== 'undefined') {
    document.cookie = 'csrftoken=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/'
  }
}

export { banco }
