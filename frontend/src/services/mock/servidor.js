/**
 * Backend simulado. Responde às mesmas rotas e com os mesmos formatos que a
 * API Django deverá expor (ver frontend/README.md → "Contrato da API"),
 * aplicando as regras de negócio do MVP: cadastro (RF01), confirmação de
 * e-mail (RF02), login com bloqueio (RF03), recuperação de senha (RF04),
 * cardápio (RF06/RF07) e avaliações (RF15).
 *
 * Nos pontos em que o sistema real enviaria um e-mail, a resposta traz o
 * campo `linkSimulado`, que a interface mostra apenas em modo de simulação.
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

/** Estado volátil (some ao recarregar), como no servidor real após reinício. */
const sessoes = new Map() // token → id do usuário
const tentativasLogin = new Map() // e-mail → [instantes das falhas]
const bloqueiosLogin = new Map() // e-mail → instante de fim do bloqueio
const pedidosRecuperacao = new Map() // e-mail → [instantes]

const ok = (dados, status = 200) => ({ status, dados })
const erro = (status, detail, extra = {}) => ({ status, dados: { detail, ...extra } })

function gerarToken() {
  return globalThis.crypto?.randomUUID?.() ?? `${Date.now()}-${Math.random().toString(36).slice(2)}`
}

const normalizarEmail = (email = '') => email.trim().toLowerCase()

function usuarioPorEmail(email) {
  return banco.estado.usuarios.find((u) => u.email === normalizarEmail(email))
}

function usuarioDaSessao(token) {
  const id = token ? sessoes.get(token) : null
  return id ? banco.estado.usuarios.find((u) => u.id === id) : null
}

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
    expiraEm: new Date(agora.getTime() + validade).toISOString(),
  })
  banco.salvar()
  const rota = tipo === 'confirmacao' ? '/confirmar-email' : '/redefinir-senha'
  return `${rota}?token=${encodeURIComponent(token)}`
}

function consumirLink(tipo, token, agora) {
  const { estado } = banco
  const link = estado.links.find((l) => l.tipo === tipo && l.token === token)
  if (!link) return null
  estado.links = estado.links.filter((l) => l !== link)
  banco.salvar()
  return new Date(link.expiraEm) > agora ? link : null
}

// ─── Cadastro e autenticação ──────────────────────────────────────────────

function cadastrar(corpo, agora) {
  const { tipo, email = '', senha = '', apelido = '', siape = '', aceitouPrivacidade } = corpo
  if (tipo !== 'estudante' && tipo !== 'servidor') {
    return erro(422, 'Escolha se você é aluno, professor ou servidor.')
  }
  if (!aceitouPrivacidade) {
    return erro(422, 'É preciso aceitar o aviso de privacidade para criar a conta.')
  }

  let identificador
  let apelidoFinal
  if (tipo === 'estudante') {
    const analise = analisarEmailEstudante(email, agora)
    if (analise.erro) return erro(422, analise.erro)
    identificador = analise.matricula
    apelidoFinal = apelido.trim()
  } else {
    const erroSiape = validarSiape(siape)
    if (erroSiape) return erro(422, erroSiape)
    const analise = analisarEmailServidor(email)
    if (analise.erro) return erro(422, analise.erro)
    identificador = siape
    apelidoFinal = apelido.trim() || analise.apelido
  }

  const erroSenha = validarSenha(senha)
  if (erroSenha) return erro(422, erroSenha)

  const emailNormalizado = normalizarEmail(email)
  const { usuarios } = banco.estado
  if (usuarios.some((u) => u.email === emailNormalizado || u.identificador === identificador)) {
    // Mensagem única, sem revelar qual dos dois já existe (C4 4b / RF03).
    return erro(422, 'Matrícula/SIAPE ou e-mail já cadastrados.')
  }

  const apelidoEmUso = (valor) =>
    usuarios.some((u) => u.apelido.toLowerCase() === valor.toLowerCase()) ||
    APELIDOS_SEMENTE.some((a) => a.toLowerCase() === valor.toLowerCase())

  const erroApelido = validarApelido(apelidoFinal)
  if (tipo === 'servidor' && !apelido.trim() && (erroApelido || apelidoEmUso(apelidoFinal))) {
    return erro(
      409,
      `Não foi possível usar "${apelidoFinal}" como apelido. Escolha um apelido para exibir nas suas avaliações.`,
      { codigo: 'apelido_manual' },
    )
  }
  if (erroApelido) return erro(422, erroApelido)
  if (apelidoEmUso(apelidoFinal)) return erro(422, 'Este apelido já está em uso. Escolha outro.')

  const usuario = {
    id: banco.novoId(),
    tipo,
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
  return ok({ email: usuario.email, pendente: true, linkSimulado }, 201)
}

function confirmarEmail({ token = '' }, agora) {
  const link = consumirLink('confirmacao', token, agora)
  const usuario = link && banco.estado.usuarios.find((u) => u.id === link.usuarioId)
  if (!usuario) {
    return erro(410, 'Este link de confirmação expirou, já foi usado ou é inválido.')
  }
  usuario.confirmado = true
  banco.salvar()
  return ok({ confirmado: true })
}

function reenviarConfirmacao({ email = '' }, agora) {
  const usuario = usuarioPorEmail(email)
  const resposta = {
    detail:
      'Se houver um cadastro pendente para este e-mail, enviamos um novo link de confirmação.',
  }
  if (usuario && !usuario.confirmado) {
    usuario.ultimoEnvio = agora.toISOString() // renova o prazo de 24h (RF02)
    resposta.linkSimulado = criarLink('confirmacao', usuario, VALIDADE_CONFIRMACAO, agora)
  }
  return ok(resposta)
}

function entrar({ email = '', senha = '' }, agora) {
  const chave = normalizarEmail(email)
  const fimBloqueio = bloqueiosLogin.get(chave)
  if (fimBloqueio && fimBloqueio > agora) {
    const minutos = Math.ceil((fimBloqueio - agora) / MINUTO)
    return erro(429, `Muitas tentativas. Tente novamente em ${minutos} min.`, {
      codigo: 'bloqueado',
    })
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
      return erro(429, 'Muitas tentativas. Tente novamente em 10 min.', { codigo: 'bloqueado' })
    }
    // Mensagem genérica: não indica se a conta existe (RF03).
    return erro(401, 'E-mail ou senha incorretos.')
  }

  tentativasLogin.delete(chave)
  if (!usuario.confirmado) {
    return erro(
      403,
      'Confirme seu e-mail antes de entrar. Enviamos um link para a sua caixa de entrada.',
      {
        codigo: 'email_nao_confirmado',
      },
    )
  }

  const token = gerarToken()
  sessoes.set(token, usuario.id)
  return ok({ token, usuario: { apelido: usuario.apelido, tipo: usuario.tipo } })
}

function sair(token) {
  sessoes.delete(token)
  return ok({})
}

function solicitarRecuperacao({ email = '' }, agora) {
  const chave = normalizarEmail(email)
  const resposta = {
    detail: 'Se houver uma conta com este e-mail, enviaremos um link para redefinir a senha.',
  }

  const recentes = (pedidosRecuperacao.get(chave) ?? []).filter((t) => agora - t < HORA)
  if (recentes.length >= LIMITE_RECUPERACOES_POR_HORA) {
    return erro(429, 'Limite de 3 solicitações por hora atingido. Tente novamente mais tarde.')
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
  if (erroSenha) return erro(422, erroSenha)
  const link = consumirLink('redefinicao', token, agora)
  const usuario = link && banco.estado.usuarios.find((u) => u.id === link.usuarioId)
  if (!usuario) return erro(410, 'Este link de redefinição expirou, já foi usado ou é inválido.')

  usuario.senha = resumoSenha(senha)
  banco.salvar()
  // A senha anterior deixa de valer e as sessões ativas são encerradas (RF04).
  for (const [tokenSessao, id] of sessoes) if (id === usuario.id) sessoes.delete(tokenSessao)
  return ok({ redefinida: true })
}

// ─── Cardápio e avaliações ────────────────────────────────────────────────

function obterCardapio(campus, agora) {
  if (!campusValido(campus)) return erro(404, 'Campus não encontrado.')
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

function listarAvaliacoes(parametros, token, agora) {
  const { campus, data, refeicao } = parametros
  if (!campusValido(campus) || !REFEICOES[refeicao] || !data) {
    return erro(400, 'Informe campus, data e refeição.')
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

  const usuario = usuarioDaSessao(token)
  const minha = usuario ? reais.find((a) => a.usuarioId === usuario.id) : null
  return ok({
    media: quantidade ? soma / quantidade : null,
    quantidade,
    avaliacoes: lista,
    minha: minha ? { nota: minha.nota, comentario: minha.comentario } : null,
  })
}

function resumoSemana({ campus }, agora) {
  if (!campusValido(campus)) return erro(404, 'Campus não encontrado.')
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

function avaliar(corpo, token, agora) {
  const usuario = usuarioDaSessao(token)
  if (!usuario)
    return erro(401, 'Faça login para avaliar refeições.', { codigo: 'nao_autenticado' })

  const { campus, data, refeicao, nota, comentario = '' } = corpo
  if (
    !campusValido(campus) ||
    !REFEICOES[refeicao] ||
    !refeicaoExiste(campus, data, refeicao, agora)
  ) {
    return erro(404, 'Refeição não encontrada no cardápio.')
  }
  if (!Number.isInteger(nota) || nota < 1 || nota > 5)
    return erro(422, 'Escolha uma nota de 1 a 5 estrelas.')
  if (comentario.length > 500) return erro(422, 'O comentário pode ter no máximo 500 caracteres.')
  if (data !== hojeISO(agora)) {
    return erro(422, 'Só é possível avaliar refeições do dia de hoje.', { codigo: 'fora_do_dia' })
  }
  const inicio = REFEICOES[refeicao].inicio
  if (minutosAgora(agora) < minutosDoDia(inicio)) {
    return erro(422, `A avaliação abre às ${horaInicio(refeicao)}, quando a refeição começa.`, {
      codigo: 'antes_do_inicio',
    })
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
  ['GET', /^\/cardapio\/([\w-]+)\/$/, ({ agora }, [campus]) => obterCardapio(campus, agora)],
  ['GET', /^\/avaliacoes\/resumo\/$/, ({ parametros, agora }) => resumoSemana(parametros, agora)],
  [
    'GET',
    /^\/avaliacoes\/$/,
    ({ parametros, token, agora }) => listarAvaliacoes(parametros, token, agora),
  ],
  ['POST', /^\/avaliacoes\/$/, ({ corpo, token, agora }) => avaliar(corpo, token, agora)],
  ['POST', /^\/cadastro\/$/, ({ corpo, agora }) => cadastrar(corpo, agora)],
  ['POST', /^\/confirmar-email\/$/, ({ corpo, agora }) => confirmarEmail(corpo, agora)],
  ['POST', /^\/reenviar-confirmacao\/$/, ({ corpo, agora }) => reenviarConfirmacao(corpo, agora)],
  ['POST', /^\/login\/$/, ({ corpo, agora }) => entrar(corpo, agora)],
  ['POST', /^\/logout\/$/, ({ token }) => sair(token)],
  ['POST', /^\/recuperar-senha\/$/, ({ corpo, agora }) => solicitarRecuperacao(corpo, agora)],
  ['POST', /^\/redefinir-senha\/$/, ({ corpo, agora }) => redefinirSenha(corpo, agora)],
]

const ATRASO_MS = import.meta.env.MODE === 'test' ? 0 : 250

export async function tratarRequisicaoSimulada({ metodo, caminho, corpo, token }) {
  if (ATRASO_MS) await new Promise((resolver) => setTimeout(resolver, ATRASO_MS))

  const agora = new Date()
  removerPendentesExpirados(agora)

  const url = new URL(caminho, 'http://simulado')
  const parametros = Object.fromEntries(url.searchParams)
  for (const [verbo, padrao, tratar] of ROTAS) {
    const encontrado = verbo === metodo && padrao.exec(url.pathname)
    if (encontrado) {
      return tratar(
        { corpo: structuredClone(corpo ?? {}), parametros, token, agora },
        encontrado.slice(1),
      )
    }
  }
  return erro(404, 'Rota não encontrada.')
}

export { banco }
