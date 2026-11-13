import { afterEach, beforeEach, describe, it, expect, vi } from 'vitest'
import { reiniciarSimulacao, tratarRequisicaoSimulada } from './servidor'
import { CONTA_DEMO } from './banco'

/**
 * Servidor simulado conferido contra o contrato OpenAPI v1 (BE-03,
 * backend/openapi.yaml) nas rotas que o MVP usa: cadastro, confirmação,
 * reenvio e sessão. Mesmas rotas, nomes de campos, status e `codigo`.
 */

/** O "navegador": lê o cookie csrftoken e manda no cabeçalho, como o apiClient. */
const csrf = () => document.cookie.match(/(?:^|; )csrftoken=([^;]*)/)?.[1]
const pedir = (metodo, caminho, corpo, { semCsrf = false } = {}) =>
  tratarRequisicaoSimulada({
    metodo,
    caminho,
    corpo,
    cabecalhos: semCsrf || !csrf() ? {} : { 'X-CSRFToken': csrf() },
  })
const post = (caminho, corpo, opcoes) => pedir('POST', caminho, corpo, opcoes)
const get = (caminho) => pedir('GET', caminho)
const del = (caminho) => pedir('DELETE', caminho)
const tokenDoLink = (link) => new URL(link, 'http://x').searchParams.get('token')
const confirmar = (link) => post(`/confirmar-email/${tokenDoLink(link)}/`)
const entrar = (matriculaSiape, senha) => post('/sessao/', { matriculaSiape, senha })

// Segunda-feira, 28/09/2026, 12h — almoço em andamento.
const SEGUNDA_MEIO_DIA = new Date(2026, 8, 28, 12, 0)

beforeEach(() => {
  vi.useFakeTimers({ toFake: ['Date'] })
  vi.setSystemTime(SEGUNDA_MEIO_DIA)
  reiniciarSimulacao()
})

afterEach(() => {
  vi.useRealTimers()
})

const entrarComDemo = () => entrar(CONTA_DEMO.matricula, CONTA_DEMO.senha)

describe('POST /cadastro/ e confirmação de e-mail (RF01, RF02)', () => {
  const ESTUDANTE = {
    tipoUsuario: 'estudante',
    emailInstitucional: '241987650@aluno.unb.br',
    senha: 'senhaforte',
    apelido: 'novo_aluno',
    aceitePrivacidade: true,
  }
  const SERVIDOR = {
    tipoUsuario: 'professor_servidor',
    matriculaSiape: '1234567',
    emailInstitucional: 'maria.silva@unb.br',
    senha: 'senhaforte',
    aceitePrivacidade: true,
  }

  it('201 { emailInstitucional, status: pendente } e só entra depois de confirmar', async () => {
    const cadastro = await post('/cadastro/', ESTUDANTE)
    expect(cadastro.status).toBe(201)
    expect(cadastro.dados).toMatchObject({
      emailInstitucional: '241987650@aluno.unb.br',
      status: 'pendente',
    })

    const antes = await entrar('241987650', ESTUDANTE.senha)
    expect(antes.status).toBe(403)
    expect(antes.dados.codigo).toBe('conta_nao_confirmada')

    expect((await confirmar(cadastro.dados.linkSimulado)).status).toBe(200)

    const depois = await entrar('241987650', ESTUDANTE.senha)
    expect(depois.status).toBe(200)
    expect(depois.dados).toEqual({
      apelido: 'novo_aluno',
      tipo: 'estudante',
      avisoPrivacidadePendente: true,
    })
  })

  it('o link é de uso único: 410 token_invalido_ou_expirado', async () => {
    const { dados } = await post('/cadastro/', ESTUDANTE)
    await confirmar(dados.linkSimulado)
    const repetido = await confirmar(dados.linkSimulado)
    expect(repetido.status).toBe(410)
    expect(repetido.dados.codigo).toBe('token_invalido_ou_expirado')
  })

  it('cadastro não confirmado em 24h é excluído e libera o e-mail', async () => {
    await post('/cadastro/', ESTUDANTE)
    vi.setSystemTime(new Date(SEGUNDA_MEIO_DIA.getTime() + 25 * 60 * 60 * 1000))
    expect((await post('/cadastro/', ESTUDANTE)).status).toBe(201)
  })

  it('rejeita matrícula ou e-mail repetidos sem dizer qual (422 dados_invalidos)', async () => {
    await post('/cadastro/', ESTUDANTE)
    const repetido = await post('/cadastro/', { ...ESTUDANTE, apelido: 'outro_nick' })
    expect(repetido.status).toBe(422)
    expect(repetido.dados).toEqual({
      codigo: 'dados_invalidos',
      mensagem: 'Matrícula/SIAPE ou e-mail já cadastrados.',
    })
  })

  it('exige aceitePrivacidade', async () => {
    const resposta = await post('/cadastro/', { ...ESTUDANTE, aceitePrivacidade: false })
    expect(resposta.status).toBe(422)
    expect(resposta.dados.codigo).toBe('dados_invalidos')
  })

  it('recusa os nomes antigos (tipo, email, aceitouPrivacidade)', async () => {
    const antigo = await post('/cadastro/', {
      tipo: 'estudante',
      email: '241987650@aluno.unb.br',
      senha: 'senhaforte',
      apelido: 'novo_aluno',
      aceitouPrivacidade: true,
    })
    expect(antigo.status).toBe(422)
  })

  it('professor_servidor: apelido do e-mail em uso dá 409 apelido_indisponivel com sugestão', async () => {
    expect((await post('/cadastro/', SERVIDOR)).status).toBe(201)

    const outro = {
      ...SERVIDOR,
      matriculaSiape: '7654321',
      emailInstitucional: 'mariasilva@unb.br',
    }
    const colisao = await post('/cadastro/', outro)
    expect(colisao.status).toBe(409)
    expect(colisao.dados.codigo).toBe('apelido_indisponivel')
    expect(colisao.dados.mensagem).toEqual(expect.any(String))
    expect(colisao.dados.apelidoSugerido).toBe('mariasilva1')

    const manual = await post('/cadastro/', { ...outro, apelido: 'profa_maria' })
    expect(manual.status).toBe(201)
  })

  it('professor_servidor entra pelo SIAPE', async () => {
    const { dados } = await post('/cadastro/', SERVIDOR)
    await confirmar(dados.linkSimulado)
    const sessao = await entrar('1234567', SERVIDOR.senha)
    expect(sessao.status).toBe(200)
    expect(sessao.dados.tipo).toBe('professor_servidor')
  })
})

describe('POST /reenviar-confirmacao/ (RF02.2)', () => {
  it('aceita matriculaSiape e devolve a mesma resposta exista ou não a conta', async () => {
    await post('/cadastro/', {
      tipoUsuario: 'estudante',
      emailInstitucional: '241987650@aluno.unb.br',
      senha: 'senhaforte',
      apelido: 'novo_aluno',
      aceitePrivacidade: true,
    })
    const existe = await post('/reenviar-confirmacao/', { matriculaSiape: '241987650' })
    const naoExiste = await post('/reenviar-confirmacao/', { matriculaSiape: '251000001' })
    expect(existe.status).toBe(200)
    expect(naoExiste.status).toBe(200)
    expect(existe.dados.mensagem).toBe(naoExiste.dados.mensagem)
    expect((await confirmar(existe.dados.linkSimulado)).status).toBe(200)
  })

  it('aceita o token do link expirado', async () => {
    const { dados } = await post('/cadastro/', {
      tipoUsuario: 'estudante',
      emailInstitucional: '241987650@aluno.unb.br',
      senha: 'senhaforte',
      apelido: 'novo_aluno',
      aceitePrivacidade: true,
    })
    const reenvio = await post('/reenviar-confirmacao/', { token: tokenDoLink(dados.linkSimulado) })
    expect(reenvio.status).toBe(200)
    expect(reenvio.dados.linkSimulado).toEqual(expect.any(String))
  })

  it('sem matriculaSiape nem token: 422 dados_invalidos', async () => {
    const resposta = await post('/reenviar-confirmacao/', {})
    expect(resposta.status).toBe(422)
    expect(resposta.dados.codigo).toBe('dados_invalidos')
  })
})

describe('/sessao/ (RF03, ADR 0007)', () => {
  it('POST grava a sessão e o csrftoken; GET diz quem sou; DELETE sai com 204', async () => {
    expect((await entrarComDemo()).status).toBe(200)
    expect(csrf()).toEqual(expect.any(String))

    const quemSou = await get('/sessao/')
    expect(quemSou.status).toBe(200)
    expect(quemSou.dados).toEqual({
      apelido: CONTA_DEMO.apelido,
      tipo: 'estudante',
      avisoPrivacidadePendente: true,
    })

    expect((await del('/sessao/')).status).toBe(204)
    expect((await get('/sessao/')).status).toBe(401)
  })

  it('GET e DELETE sem sessão: 401 nao_autenticado', async () => {
    for (const resposta of [await get('/sessao/'), await del('/sessao/')]) {
      expect(resposta.status).toBe(401)
      expect(resposta.dados.codigo).toBe('nao_autenticado')
    }
  })

  it('a sessão nunca devolve matrícula/SIAPE nem e-mail (RI10)', async () => {
    const texto = JSON.stringify((await entrarComDemo()).dados)
    expect(texto).not.toContain(CONTA_DEMO.matricula)
    expect(texto).not.toContain('@')
  })

  it('erro genérico (401 credenciais_invalidas) para senha errada e conta inexistente', async () => {
    const senhaErrada = await entrar(CONTA_DEMO.matricula, 'errada123')
    const inexistente = await entrar('251000001', 'errada123')
    expect(senhaErrada.status).toBe(401)
    expect(senhaErrada.dados).toEqual(inexistente.dados)
    expect(senhaErrada.dados.codigo).toBe('credenciais_invalidas')
  })

  it('bloqueia por 10 minutos após 5 tentativas erradas (429 login_bloqueado)', async () => {
    for (let i = 0; i < 4; i++) expect((await entrar('251000002', 'x')).status).toBe(401)
    const bloqueado = await entrar('251000002', 'x')
    expect(bloqueado.status).toBe(429)
    expect(bloqueado.dados.codigo).toBe('login_bloqueado')
    expect((await entrar('251000002', 'x')).status).toBe(429)

    vi.setSystemTime(new Date(SEGUNDA_MEIO_DIA.getTime() + 11 * 60 * 1000))
    expect((await entrar('251000002', 'x')).status).toBe(401)
  })

  it('escrita logada sem X-CSRFToken: 403 (não é 401, não desloga)', async () => {
    await entrarComDemo()
    const semCsrf = await post('/sessao/', {}, { semCsrf: true })
    expect(semCsrf.status).toBe(403)
    expect((await get('/sessao/')).status).toBe(200)
  })
})

describe('recuperação de senha (RF04, fora do contrato v1)', () => {
  it('responde igual exista ou não a conta, e troca a senha pelo link', async () => {
    const existente = await post('/recuperar-senha/', { email: CONTA_DEMO.email })
    const inexistente = await post('/recuperar-senha/', { email: 'ninguem@aluno.unb.br' })
    expect(existente.dados.mensagem).toBe(inexistente.dados.mensagem)

    const token = tokenDoLink(existente.dados.linkSimulado)
    expect((await post('/redefinir-senha/', { token, senha: 'novasenha1' })).status).toBe(200)
    expect((await entrar(CONTA_DEMO.matricula, CONTA_DEMO.senha)).status).toBe(401)
    expect((await entrar(CONTA_DEMO.matricula, 'novasenha1')).status).toBe(200)
  })

  it('redefinir a senha encerra a sessão aberta', async () => {
    await entrarComDemo()
    const { dados } = await post('/recuperar-senha/', { email: CONTA_DEMO.email })
    await post('/redefinir-senha/', { token: tokenDoLink(dados.linkSimulado), senha: 'novasenha1' })
    expect((await get('/sessao/')).status).toBe(401)
  })

  it('aceita no máximo 3 solicitações por hora', async () => {
    const email = 'limite@aluno.unb.br'
    for (let i = 0; i < 3; i++)
      expect((await post('/recuperar-senha/', { email })).status).toBe(200)
    expect((await post('/recuperar-senha/', { email })).status).toBe(429)
  })

  it('o link de redefinição vale 1 hora', async () => {
    const { dados } = await post('/recuperar-senha/', { email: CONTA_DEMO.email })
    vi.setSystemTime(new Date(SEGUNDA_MEIO_DIA.getTime() + 61 * 60 * 1000))
    const resposta = await post('/redefinir-senha/', {
      token: tokenDoLink(dados.linkSimulado),
      senha: 'novasenha1',
    })
    expect(resposta.status).toBe(410)
  })
})

describe('cardápio (RF06, RF07)', () => {
  it('devolve a semana vigente do campus', async () => {
    const { status, dados } = await get('/cardapio/darcy/')
    expect(status).toBe(200)
    expect(dados.publicado).toBe(true)
    expect(dados.dias[0].data).toBe('2026-09-28')
    expect(dados.dias.at(-1).refeicoes.map((r) => r.tipo)).toEqual(['almoco']) // sábado
  })

  it('indica cardápio não publicado', async () => {
    const { dados } = await get('/cardapio/fal/')
    expect(dados).toMatchObject({ publicado: false, dias: [] })
  })

  it('campus inexistente é 404', async () => {
    expect((await get('/cardapio/executivo/')).status).toBe(404)
  })
})

describe('avaliações (RF15)', () => {
  const ALMOCO_HOJE = { campus: 'gama', data: '2026-09-28', refeicao: 'almoco' }
  const consulta = `/avaliacoes/?campus=gama&data=2026-09-28&refeicao=almoco`

  it('visitante não pode avaliar', async () => {
    const resposta = await post('/avaliacoes/', { ...ALMOCO_HOJE, nota: 5 })
    expect(resposta.status).toBe(401)
    expect(resposta.dados.codigo).toBe('nao_autenticado')
  })

  it('a segunda avaliação da mesma refeição edita a primeira', async () => {
    await entrarComDemo()
    const antes = (await get(consulta)).dados.quantidade

    expect((await post('/avaliacoes/', { ...ALMOCO_HOJE, nota: 2 })).status).toBe(201)
    expect(
      (await post('/avaliacoes/', { ...ALMOCO_HOJE, nota: 5, comentario: 'Mudei de ideia' }))
        .status,
    ).toBe(200)

    const { dados } = await get(consulta)
    expect(dados.quantidade).toBe(antes + 1)
    expect(dados.minha).toEqual({ nota: 5, comentario: 'Mudei de ideia' })
    expect(dados.avaliacoes[0]).toMatchObject({
      apelido: CONTA_DEMO.apelido,
      comentario: 'Mudei de ideia',
    })
  })

  it('não expõe e-mail nem matrícula na lista pública (RI10)', async () => {
    await entrarComDemo()
    await post('/avaliacoes/', { ...ALMOCO_HOJE, nota: 4, comentario: 'Bom' })
    await del('/sessao/')
    const texto = JSON.stringify((await get(consulta)).dados)
    expect(texto).not.toContain(CONTA_DEMO.email)
    expect(texto).not.toContain('231034567')
  })

  it('não permite avaliar outro dia nem antes do início da refeição', async () => {
    await entrarComDemo()
    const amanha = await post('/avaliacoes/', { ...ALMOCO_HOJE, data: '2026-09-29', nota: 4 })
    expect(amanha.dados.codigo).toBe('fora_do_dia')

    const jantar = await post('/avaliacoes/', { ...ALMOCO_HOJE, refeicao: 'jantar', nota: 4 })
    expect(jantar.dados.codigo).toBe('antes_do_inicio')
  })

  it('valida nota e tamanho do comentário', async () => {
    await entrarComDemo()
    expect((await post('/avaliacoes/', { ...ALMOCO_HOJE, nota: 0 })).status).toBe(422)
    const longo = await post('/avaliacoes/', {
      ...ALMOCO_HOJE,
      nota: 3,
      comentario: 'x'.repeat(501),
    })
    expect(longo.status).toBe(422)
  })

  it('refeição que ainda não começou não tem avaliações', async () => {
    const { dados } = await get('/avaliacoes/?campus=gama&data=2026-09-28&refeicao=jantar')
    expect(dados).toMatchObject({ quantidade: 0, media: null, avaliacoes: [] })
  })
})
