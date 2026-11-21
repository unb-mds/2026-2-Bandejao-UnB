import { afterEach, beforeEach, describe, it, expect, vi } from 'vitest'
import { banco, reiniciarSimulacao, simulacao, tratarRequisicaoSimulada } from './servidor'
import { CONTA_DEMO } from './banco'

/**
 * Servidor simulado conferido contra o contrato OpenAPI v1 (BE-03,
 * backend/openapi.yaml) nas rotas que o MVP usa: cadastro, confirmação,
 * reenvio e sessão. Mesmas rotas, nomes de campos, status e `codigo`.
 */

/**
 * O "navegador": como o apiClient, busca o cookie em GET /csrf/ antes da
 * primeira escrita e manda o valor no cabeçalho X-CSRFToken.
 */
const csrf = () => document.cookie.match(/(?:^|; )csrftoken=([^;]*)/)?.[1]
async function pedir(metodo, caminho, corpo, { semCsrf = false } = {}) {
  if (metodo !== 'GET' && !semCsrf && !csrf()) {
    await tratarRequisicaoSimulada({ metodo: 'GET', caminho: '/csrf/' })
  }
  return tratarRequisicaoSimulada({
    metodo,
    caminho,
    corpo,
    cabecalhos: semCsrf ? {} : { 'X-CSRFToken': csrf() },
  })
}
const post = (caminho, corpo, opcoes) => pedir('POST', caminho, corpo, opcoes)
const get = (caminho) => pedir('GET', caminho)
const del = (caminho) => pedir('DELETE', caminho)
const tokenDoLink = (link) => new URL(link, 'http://x').searchParams.get('token')
const confirmar = (link) => post(`/confirmar-email/${tokenDoLink(link)}/`)
const entrar = (emailInstitucional, senha) => post('/sessao/', { emailInstitucional, senha })

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

const ALUNO_SEM_CONTA = '251000001@aluno.unb.br'
const entrarComDemo = () => entrar(CONTA_DEMO.email, CONTA_DEMO.senha)

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

    const antes = await entrar(ESTUDANTE.emailInstitucional, ESTUDANTE.senha)
    expect(antes.status).toBe(403)
    expect(antes.dados.codigo).toBe('conta_nao_confirmada')

    expect((await confirmar(cadastro.dados.linkSimulado)).status).toBe(200)

    const depois = await entrar(ESTUDANTE.emailInstitucional, ESTUDANTE.senha)
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

  it('professor_servidor entra pelo e-mail @unb.br', async () => {
    const { dados } = await post('/cadastro/', SERVIDOR)
    await confirmar(dados.linkSimulado)
    const sessao = await entrar('maria.silva@unb.br', SERVIDOR.senha)
    expect(sessao.status).toBe(200)
    expect(sessao.dados.tipo).toBe('professor_servidor')
  })
})

describe('POST /reenviar-confirmacao/ (RF02.2)', () => {
  it('aceita emailInstitucional e devolve a mesma resposta exista ou não a conta', async () => {
    await post('/cadastro/', {
      tipoUsuario: 'estudante',
      emailInstitucional: '241987650@aluno.unb.br',
      senha: 'senhaforte',
      apelido: 'novo_aluno',
      aceitePrivacidade: true,
    })
    const existe = await post('/reenviar-confirmacao/', {
      emailInstitucional: ' 241987650@Aluno.UnB.br ',
    })
    const naoExiste = await post('/reenviar-confirmacao/', {
      emailInstitucional: '251000001@aluno.unb.br',
    })
    // Como o backend: 200 sem corpo nos dois casos. Só o `linkSimulado`
    // (extra do modo demonstração) aparece quando há conta pendente.
    expect(existe.status).toBe(200)
    expect(naoExiste.status).toBe(200)
    expect(naoExiste.dados).toBeNull()
    expect(Object.keys(existe.dados)).toEqual(['linkSimulado'])
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

  it('e-mail sem conta e token válido: vale o token', async () => {
    const { dados } = await post('/cadastro/', {
      tipoUsuario: 'estudante',
      emailInstitucional: '241987650@aluno.unb.br',
      senha: 'senhaforte',
      apelido: 'novo_aluno',
      aceitePrivacidade: true,
    })
    const reenvio = await post('/reenviar-confirmacao/', {
      emailInstitucional: '251000001@aluno.unb.br',
      token: tokenDoLink(dados.linkSimulado),
    })
    expect(reenvio.status).toBe(200)
    expect(reenvio.dados.linkSimulado).toEqual(expect.any(String))
  })

  it('e-mail fora do domínio só não acha conta: o mesmo 200', async () => {
    const resposta = await post('/reenviar-confirmacao/', { emailInstitucional: 'x@gmail.com' })
    expect(resposta.status).toBe(200)
    expect(resposta.dados).toBeNull()
  })

  it('sem emailInstitucional nem token: 422 dados_invalidos', async () => {
    const resposta = await post('/reenviar-confirmacao/', {})
    expect(resposta.status).toBe(422)
    expect(resposta.dados).toEqual({
      codigo: 'dados_invalidos',
      mensagem: 'Informe o seu e-mail institucional ou abra o link recebido.',
    })
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
    const senhaErrada = await entrar(CONTA_DEMO.email, 'errada123')
    const inexistente = await entrar('251000001@aluno.unb.br', 'errada123')
    expect(senhaErrada.status).toBe(401)
    expect(senhaErrada.dados).toEqual(inexistente.dados)
    expect(senhaErrada.dados).toEqual({
      codigo: 'credenciais_invalidas',
      mensagem: 'E-mail ou senha incorretos.',
    })
  })

  it('maiúsculas e espaços nas pontas do e-mail entram na mesma conta', async () => {
    const sessao = await entrar(` ${CONTA_DEMO.email.toUpperCase()} `, CONTA_DEMO.senha)
    expect(sessao.status).toBe(200)
    expect(sessao.dados.apelido).toBe(CONTA_DEMO.apelido)
  })

  it('e-mail fora do domínio da UnB: 422 dados_invalidos, sem contar tentativa', async () => {
    for (let i = 0; i < 6; i++) {
      const resposta = await entrar('aluno@gmail.com', 'x')
      expect(resposta.status).toBe(422)
      expect(resposta.dados).toEqual({
        codigo: 'dados_invalidos',
        mensagem: 'Informe o seu e-mail institucional da UnB (@aluno.unb.br ou @unb.br).',
      })
    }
    const semSenha = await post('/sessao/', { emailInstitucional: CONTA_DEMO.email })
    expect(semSenha.status).toBe(422)
    expect(semSenha.dados.mensagem).toBe('Informe o seu e-mail institucional e a senha.')
  })

  it('corpo antigo com matriculaSiape: 422 dados_invalidos', async () => {
    const resposta = await post('/sessao/', {
      matriculaSiape: CONTA_DEMO.matricula,
      senha: CONTA_DEMO.senha,
    })
    expect(resposta.status).toBe(422)
    expect(resposta.dados.codigo).toBe('dados_invalidos')
  })

  it('bloqueia por 10 minutos após 5 tentativas erradas (429 login_bloqueado)', async () => {
    const outro = '251000002@aluno.unb.br'
    for (let i = 0; i < 4; i++) expect((await entrar(outro, 'x')).status).toBe(401)
    const bloqueado = await entrar(outro, 'x')
    expect(bloqueado.status).toBe(429)
    expect(bloqueado.dados.codigo).toBe('login_bloqueado')
    expect((await entrar(outro, 'x')).status).toBe(429)

    vi.setSystemTime(new Date(SEGUNDA_MEIO_DIA.getTime() + 11 * 60 * 1000))
    expect((await entrar(outro, 'x')).status).toBe(401)
  })

  it('escrita logada sem X-CSRFToken: 403 csrf_invalido (não é 401, não desloga)', async () => {
    await entrarComDemo()
    const semCsrf = await post('/sessao/', {}, { semCsrf: true })
    expect(semCsrf.status).toBe(403)
    expect(semCsrf.dados.codigo).toBe('csrf_invalido')
    expect((await get('/sessao/')).status).toBe(200)
  })
})

describe('CSRF (ADR 0007, #112)', () => {
  it('GET /csrf/ responde 204 e grava o cookie csrftoken', async () => {
    const resposta = await get('/csrf/')
    expect(resposta.status).toBe(204)
    expect(csrf()).toEqual(expect.any(String))
  })

  it('escrita sem sessão também exige o X-CSRFToken (cadastro e login)', async () => {
    await get('/csrf/')
    for (const caminho of ['/cadastro/', '/sessao/', '/reenviar-confirmacao/']) {
      const resposta = await post(caminho, {}, { semCsrf: true })
      expect(resposta.status).toBe(403)
      expect(resposta.dados).toEqual({
        codigo: 'csrf_invalido',
        mensagem:
          'Não foi possível confirmar a origem do pedido. Recarregue a página e tente de novo.',
      })
    }
  })

  it('depois de um F5, o cookie que ficou no navegador continua valendo', async () => {
    await entrarComDemo()
    const cookieAntesDoF5 = csrf()

    // F5: o módulo do simulado é carregado de novo (estado em memória zerado),
    // mas o cookie csrftoken continua no navegador, como no Django.
    vi.resetModules()
    const recarregado = await import('./servidor')
    const resposta = await recarregado.tratarRequisicaoSimulada({
      metodo: 'POST',
      caminho: '/reenviar-confirmacao/',
      corpo: { emailInstitucional: '251000001@aluno.unb.br' },
      cabecalhos: { 'X-CSRFToken': cookieAntesDoF5 },
    })

    expect(resposta.status).toBe(200)
  })

  it('o cabeçalho precisa ser igual ao cookie', async () => {
    await get('/csrf/')
    const resposta = await tratarRequisicaoSimulada({
      metodo: 'POST',
      caminho: '/reenviar-confirmacao/',
      corpo: { emailInstitucional: '251000001@aluno.unb.br' },
      cabecalhos: { 'X-CSRFToken': 'outro-valor' },
    })
    expect(resposta.status).toBe(403)
  })

  it('o login troca o csrftoken: o valor antigo deixa de valer', async () => {
    await get('/csrf/')
    const antes = csrf()
    await entrarComDemo()
    expect(csrf()).not.toBe(antes)

    const comTokenVelho = await tratarRequisicaoSimulada({
      metodo: 'DELETE',
      caminho: '/sessao/',
      cabecalhos: { 'X-CSRFToken': antes },
    })
    expect(comTokenVelho.status).toBe(403)
  })
})

describe('recuperação de senha (RF04, fora do contrato v1)', () => {
  it('responde igual exista ou não a conta, e troca a senha pelo link', async () => {
    const existente = await post('/recuperar-senha/', { email: CONTA_DEMO.email })
    const inexistente = await post('/recuperar-senha/', { email: 'ninguem@aluno.unb.br' })
    expect(existente.dados.mensagem).toBe(inexistente.dados.mensagem)

    const token = tokenDoLink(existente.dados.linkSimulado)
    expect((await post('/redefinir-senha/', { token, senha: 'novasenha1' })).status).toBe(200)
    expect((await entrar(CONTA_DEMO.email, CONTA_DEMO.senha)).status).toBe(401)
    expect((await entrar(CONTA_DEMO.email, 'novasenha1')).status).toBe(200)
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

describe('campi (GET /campi/, contrato da BE-08)', () => {
  it('devolve id inteiro e nome do banco, em ordem de id', async () => {
    const { status, dados } = await get('/campi/')

    expect(status).toBe(200)
    expect(dados).toEqual([
      { id: 1, nome: 'Darcy Ribeiro' },
      { id: 2, nome: 'Ceilândia' },
      { id: 3, nome: 'Gama' },
      { id: 4, nome: 'Planaltina' },
      { id: 5, nome: 'Fazenda Água Limpa' },
    ])
  })
})

describe('cardápio (RF06, RF07)', () => {
  it('devolve a semana vigente do campus', async () => {
    const { status, dados } = await get('/cardapio/1/')
    expect(status).toBe(200)
    expect(dados.publicado).toBe(true)
    expect(dados.dias[0].data).toBe('2026-09-28')
    expect(dados.dias.at(-1).refeicoes.map((r) => r.tipo)).toEqual(['almoco']) // sábado
  })

  it('indica cardápio não publicado', async () => {
    const { dados } = await get('/cardapio/5/')
    expect(dados).toMatchObject({ publicado: false, dias: [] })
  })

  it('campus inexistente é 404', async () => {
    expect((await get('/cardapio/99/')).status).toBe(404)
    expect((await get('/cardapio/darcy/')).status).toBe(404)
  })
})

describe('GET /cardapio/ (contrato da BE-11, ADR 0005)', () => {
  const categoria = (dados, nome) => dados.categorias.find((c) => c.nome === nome)
  const nomes = (dados) => dados.categorias.map((c) => c.nome)

  it('sem dia nem refeição: hoje e a refeição padrão da RN05', async () => {
    const { status, dados } = await get('/cardapio/?campus=1')

    expect(status).toBe(200)
    expect(dados).toMatchObject({
      campus: 1,
      status: 'publicado',
      data: '2026-09-28',
      refeicao: 'almoco',
      refeicaoEncerrada: false,
      alergenosIndisponivel: false,
      filtroMarcadorDesativado: false,
    })
    expect(dados.avisoSujeitoAAlteracao).toContain('sujeito a alteração')
    expect(categoria(dados, 'Prato Principal — Padrão').pratos[0]).toEqual({
      descricao: 'Bife acebolado',
      marcadores: ['suino'],
      contemMarcadorSelecionado: false,
    })
  })

  it('dieta ovolactovegetariano tira a linha padrão; vegetariano estrito deixa só a dela', async () => {
    const ovolacto = (await get('/cardapio/?campus=1&dieta=ovolactovegetariano')).dados
    const estrito = (await get('/cardapio/?campus=1&dieta=vegetariano_estrito')).dados

    expect(nomes(ovolacto)).not.toContain('Prato Principal — Padrão')
    expect(nomes(ovolacto)).toContain('Prato Principal — Ovolactovegetariano')
    expect(nomes(estrito)).not.toContain('Prato Principal — Ovolactovegetariano')
    expect(nomes(estrito)).toContain('Prato Principal — Vegetariano Estrito')
    expect(nomes(estrito)).toContain('Guarnição')
  })

  it('marcadores sinalizam os pratos, sem escondê-los (RF08)', async () => {
    const { dados } = await get('/cardapio/?campus=1&marcadores=leite_e_derivados,suino')

    const pure = categoria(dados, 'Guarnição')
    expect(pure.pratos[0]).toMatchObject({
      descricao: 'Purê de batata',
      contemMarcadorSelecionado: true,
    })
    expect(pure.semOpcaoCompativel).toBe(true)
    const padrao = categoria(dados, 'Prato Principal — Padrão')
    expect(padrao.pratos.map((p) => p.contemMarcadorSelecionado)).toEqual([true, false])
    expect(padrao.semOpcaoCompativel).toBe(false)
  })

  it('refeição sem informação de alérgenos: filtro de marcadores desativado', async () => {
    const { dados } = await get(
      '/cardapio/?campus=2&dia=2026-09-30&refeicao=jantar&marcadores=leite_e_derivados',
    )

    expect(dados).toMatchObject({ alergenosIndisponivel: true, filtroMarcadorDesativado: true })
    expect(dados.categorias.every((c) => !c.semOpcaoCompativel)).toBe(true)
  })

  it('campus que não publicou: status nao_publicado e sem categorias (RF18)', async () => {
    const { dados } = await get('/cardapio/?campus=5')

    expect(dados).toMatchObject({ status: 'nao_publicado', categorias: [] })
  })

  it('depois da última refeição do dia: a última, encerrada (RN05)', async () => {
    vi.setSystemTime(new Date(2026, 8, 28, 21, 0))

    const { dados } = await get('/cardapio/?campus=1')

    expect(dados).toMatchObject({ refeicao: 'jantar', refeicaoEncerrada: true })
  })

  it('dia sem serviço, sem refeição: passa ao próximo dia com serviço (RN05)', async () => {
    const { dados } = await get('/cardapio/?campus=3&dia=2026-09-27')

    expect(dados).toMatchObject({ status: 'publicado', data: '2026-09-28' })
  })

  it('o fim do horário ainda é da refeição: às 9h30 é café', async () => {
    vi.setSystemTime(new Date(2026, 8, 28, 9, 30))
    expect((await get('/cardapio/?campus=1')).dados.refeicao).toBe('cafe')

    vi.setSystemTime(new Date(2026, 8, 28, 9, 31))
    expect((await get('/cardapio/?campus=1')).dados.refeicao).toBe('almoco')
  })

  it('marcador desconhecido: 400 citando o nome', async () => {
    const resposta = await get('/cardapio/?campus=1&marcadores=ovo,leite')

    expect(resposta.status).toBe(400)
    expect(resposta.dados).toEqual({
      codigo: 'parametros_invalidos',
      mensagem: 'Marcador desconhecido: leite.',
    })
  })

  it('campus inexistente: 400 com a mensagem do backend', async () => {
    const resposta = await get('/cardapio/?campus=99')

    expect(resposta.status).toBe(400)
    expect(resposta.dados).toEqual({
      codigo: 'parametros_invalidos',
      mensagem: 'Não existe campus com esse id.',
    })
  })

  it.each([
    ['sem campus', '/cardapio/'],
    ['campus inexistente', '/cardapio/?campus=99'],
    ['dieta desconhecida', '/cardapio/?campus=1&dieta=todos'],
    ['refeição desconhecida', '/cardapio/?campus=1&refeicao=lanche'],
    ['parâmetro fora do contrato', '/cardapio/?campus=1&_=123'],
    ['item vazio em marcadores', '/cardapio/?campus=1&marcadores=ovo,'],
    ['dia fora da faixa', '/cardapio/?campus=1&dia=1999-12-31'],
  ])('%s: 400 parametros_invalidos', async (_caso, caminho) => {
    const resposta = await get(caminho)

    expect(resposta.status).toBe(400)
    expect(resposta.dados.codigo).toBe('parametros_invalidos')
  })
})

describe('GET /avaliacoes/resumo/?campus=&data= (resumo do dia)', () => {
  it('uma linha por refeição do dia, com nota média e quantidade', async () => {
    const { status, dados } = await get('/avaliacoes/resumo/?campus=1&data=2026-09-28')

    expect(status).toBe(200)
    expect(dados.map((r) => r.tipo)).toEqual(['cafe', 'almoco', 'jantar'])
    expect(dados[0]).toEqual({
      refeicaoId: expect.any(Number),
      tipo: 'cafe',
      media: expect.any(Number),
      quantidade: expect.any(Number),
    })
    expect(dados[2]).toMatchObject({ tipo: 'jantar', media: null, quantidade: 0 })
  })

  it('dia sem refeições: lista vazia', async () => {
    const { dados } = await get('/avaliacoes/resumo/?campus=4&data=2026-10-03')

    expect(dados).toEqual([])
  })
})

describe('avaliações (RF15)', () => {
  const ALMOCO_HOJE = { campus: 3, data: '2026-09-28', refeicao: 'almoco' }
  const consulta = `/avaliacoes/?campus=3&data=2026-09-28&refeicao=almoco`

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
    const { dados } = await get('/avaliacoes/?campus=3&data=2026-09-28&refeicao=jantar')
    expect(dados).toMatchObject({ quantidade: 0, media: null, avaliacoes: [] })
  })
})

describe('limite de taxa por IP (429 limite_excedido, #123)', () => {
  const LIMITE = {
    codigo: 'limite_excedido',
    mensagem: 'Muitos pedidos seguidos. Tente de novo mais tarde.',
  }

  it('cadastro: 40 por hora', async () => {
    for (let i = 0; i < 40; i++) expect((await post('/cadastro/', {})).status).toBe(422)
    const excedido = await post('/cadastro/', {})
    expect(excedido.status).toBe(429)
    expect(excedido.dados).toEqual(LIMITE)

    vi.setSystemTime(new Date(SEGUNDA_MEIO_DIA.getTime() + 61 * 60 * 1000))
    expect((await post('/cadastro/', {})).status).toBe(422)
  })

  it('reenvio de confirmação: 10 por hora', async () => {
    for (let i = 0; i < 10; i++) {
      const reenvio = await post('/reenviar-confirmacao/', { emailInstitucional: ALUNO_SEM_CONTA })
      expect(reenvio.status).toBe(200)
    }
    const excedido = await post('/reenviar-confirmacao/', { emailInstitucional: ALUNO_SEM_CONTA })
    expect(excedido.status).toBe(429)
    expect(excedido.dados).toEqual(LIMITE)
  })

  it('login: 60 por hora, contando também os pedidos inválidos', async () => {
    for (let i = 0; i < 60; i++) expect((await entrar('aluno@gmail.com', 'x')).status).toBe(422)
    const excedido = await entrarComDemo()
    expect(excedido.status).toBe(429)
    expect(excedido.dados).toEqual(LIMITE)
  })

  it('reenvio por conta: depois de 3 links na hora, responde 200 sem mandar outro', async () => {
    await post('/cadastro/', {
      tipoUsuario: 'estudante',
      emailInstitucional: '241987650@aluno.unb.br',
      senha: 'senhaforte',
      apelido: 'novo_aluno',
      aceitePrivacidade: true,
    })
    for (let i = 0; i < 3; i++) {
      const reenvio = await post('/reenviar-confirmacao/', {
        emailInstitucional: '241987650@aluno.unb.br',
      })
      expect(reenvio.dados.linkSimulado).toEqual(expect.any(String))
    }
    const quarto = await post('/reenviar-confirmacao/', {
      emailInstitucional: '241987650@aluno.unb.br',
    })
    expect(quarto.status).toBe(200)
    expect(quarto.dados).toBeNull()
  })
})

describe('POST /privacidade/aceite/ (RF11, RNF07.1)', () => {
  it('sem sessão: 401 nao_autenticado', async () => {
    const resposta = await post('/privacidade/aceite/')

    expect(resposta.status).toBe(401)
    expect(resposta.dados.codigo).toBe('nao_autenticado')
  })

  it('com sessão: 204 sem corpo, e a sessão deixa de ter o aviso pendente', async () => {
    await entrarComDemo()
    expect((await get('/sessao/')).dados.avisoPrivacidadePendente).toBe(true)

    const resposta = await post('/privacidade/aceite/')

    expect(resposta).toEqual({ status: 204, dados: null })
    expect((await get('/sessao/')).dados.avisoPrivacidadePendente).toBe(false)
  })

  it('sem CSRF: 403 csrf_invalido', async () => {
    await entrarComDemo()

    const resposta = await post('/privacidade/aceite/', undefined, { semCsrf: true })

    expect(resposta.status).toBe(403)
    expect(resposta.dados.codigo).toBe('csrf_invalido')
  })
})

describe('POST /checkins/ (RF11, RF12, contrato da BE-09)', () => {
  const COORDENADAS = { latitude: -15.7631234, longitude: -47.8701234 }
  const CHECKIN = { campus: 1, tipoRefeicao: 'almoco', coordenadas: COORDENADAS }

  async function entrarComAviso() {
    await entrarComDemo()
    await post('/privacidade/aceite/')
  }

  it('sem sessão: 401 nao_autenticado', async () => {
    const resposta = await post('/checkins/', CHECKIN)

    expect(resposta.status).toBe(401)
    expect(resposta.dados.codigo).toBe('nao_autenticado')
  })

  it('201 com o check-in e o bloco de pontos zerado (até a BE-14), sem coordenadas', async () => {
    await entrarComAviso()

    const resposta = await post('/checkins/', CHECKIN)

    expect(resposta.status).toBe(201)
    expect(resposta.dados).toEqual({
      checkin: { id: expect.any(Number), campus: 1, tipoRefeicao: 'almoco', data: '2026-09-28' },
      pontos: { total: 0, contribuicao: 0, avaliacaoLiberada: 0 },
    })
  })

  it('não grava as coordenadas no "banco" (RI09)', async () => {
    await entrarComAviso()

    await post('/checkins/', CHECKIN)

    const salvo = JSON.stringify(banco.estado)
    expect(salvo).not.toContain('15.7631234')
    expect(salvo).not.toContain('47.8701234')
  })

  it('aviso pendente: 403 aviso_privacidade_pendente', async () => {
    await entrarComDemo()

    const resposta = await post('/checkins/', CHECKIN)

    expect(resposta.status).toBe(403)
    expect(resposta.dados.codigo).toBe('aviso_privacidade_pendente')
  })

  it.each([
    ['campus inexistente', { ...CHECKIN, campus: 99 }],
    ['campus como texto', { ...CHECKIN, campus: 'darcy' }],
    ['refeição inexistente', { ...CHECKIN, tipoRefeicao: 'ceia' }],
    ['sem coordenadas', { campus: 1, tipoRefeicao: 'almoco' }],
    ['latitude fora da faixa', { ...CHECKIN, coordenadas: { ...COORDENADAS, latitude: 91 } }],
    ['longitude fora da faixa', { ...CHECKIN, coordenadas: { ...COORDENADAS, longitude: -181 } }],
    ['latitude como texto', { ...CHECKIN, coordenadas: { ...COORDENADAS, latitude: '-15.7' } }],
  ])('400 dados_invalidos: %s', async (_caso, corpo) => {
    await entrarComAviso()

    const resposta = await post('/checkins/', corpo)

    expect(resposta.status).toBe(400)
    expect(resposta.dados.codigo).toBe('dados_invalidos')
  })

  it('fora da janela da refeição: 422 fora_do_horario com a janela na mensagem', async () => {
    await entrarComAviso()
    vi.setSystemTime(new Date(2026, 8, 28, 16, 0))

    const resposta = await post('/checkins/', CHECKIN)

    expect(resposta.status).toBe(422)
    expect(resposta.dados).toEqual({
      codigo: 'fora_do_horario',
      mensagem: 'O check-in do almoço só vale das 11h00 às 14h30.',
    })
  })

  it('segundo check-in na mesma refeição e no mesmo campus: 422 checkin_duplicado (RI03)', async () => {
    await entrarComAviso()
    await post('/checkins/', CHECKIN)

    const resposta = await post('/checkins/', CHECKIN)

    expect(resposta.status).toBe(422)
    expect(resposta.dados.codigo).toBe('checkin_duplicado')
  })

  it('mesma refeição em outro campus: 201, como no UNIQUE do backend', async () => {
    await entrarComAviso()
    await post('/checkins/', CHECKIN)

    const resposta = await post('/checkins/', { ...CHECKIN, campus: 2 })

    expect(resposta.status).toBe(201)
    expect(resposta.dados.checkin.campus).toBe(2)
  })

  it('fora do raio do RU: 422 localizacao_nao_confirmada', async () => {
    await entrarComAviso()
    simulacao.definirLocalizacaoConfirmada(false)

    const resposta = await post('/checkins/', CHECKIN)

    expect(resposta.status).toBe(422)
    expect(resposta.dados.codigo).toBe('localizacao_nao_confirmada')
  })

  it('reiniciarSimulacao volta a confirmar a localização', async () => {
    simulacao.definirLocalizacaoConfirmada(false)
    reiniciarSimulacao()
    await entrarComAviso()

    expect((await post('/checkins/', CHECKIN)).status).toBe(201)
  })
})
