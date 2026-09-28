import { afterEach, beforeEach, describe, it, expect, vi } from 'vitest'
import { banco, tratarRequisicaoSimulada } from './servidor'
import { CONTA_DEMO } from './banco'

const post = (caminho, corpo, token) =>
  tratarRequisicaoSimulada({ metodo: 'POST', caminho, corpo, token })
const get = (caminho, token) => tratarRequisicaoSimulada({ metodo: 'GET', caminho, token })
const tokenDoLink = (link) => new URL(link, 'http://x').searchParams.get('token')

// Segunda-feira, 28/09/2026, 12h — almoço em andamento.
const SEGUNDA_MEIO_DIA = new Date(2026, 8, 28, 12, 0)

beforeEach(() => {
  vi.useFakeTimers({ toFake: ['Date'] })
  vi.setSystemTime(SEGUNDA_MEIO_DIA)
  banco.reiniciar()
})

afterEach(() => {
  vi.useRealTimers()
})

async function entrarComDemo() {
  const resposta = await post('/login/', { email: CONTA_DEMO.email, senha: CONTA_DEMO.senha })
  return resposta.dados.token
}

describe('cadastro e confirmação de e-mail (RF01, RF02)', () => {
  const ESTUDANTE = {
    tipo: 'estudante',
    email: '241987650@aluno.unb.br',
    senha: 'senhaforte',
    apelido: 'novo_aluno',
    aceitouPrivacidade: true,
  }

  it('cria a conta pendente e só permite login depois de confirmar', async () => {
    const cadastro = await post('/cadastro/', ESTUDANTE)
    expect(cadastro.status).toBe(201)
    expect(cadastro.dados.pendente).toBe(true)

    const antes = await post('/login/', { email: ESTUDANTE.email, senha: ESTUDANTE.senha })
    expect(antes.status).toBe(403)
    expect(antes.dados.codigo).toBe('email_nao_confirmado')

    const confirmacao = await post('/confirmar-email/', {
      token: tokenDoLink(cadastro.dados.linkSimulado),
    })
    expect(confirmacao.status).toBe(200)

    const depois = await post('/login/', { email: ESTUDANTE.email, senha: ESTUDANTE.senha })
    expect(depois.status).toBe(200)
    expect(depois.dados.usuario).toEqual({ apelido: 'novo_aluno', tipo: 'estudante' })
  })

  it('o link de confirmação é de uso único', async () => {
    const { dados } = await post('/cadastro/', ESTUDANTE)
    const token = tokenDoLink(dados.linkSimulado)
    await post('/confirmar-email/', { token })
    expect((await post('/confirmar-email/', { token })).status).toBe(410)
  })

  it('cadastro não confirmado em 24h é excluído e libera o e-mail', async () => {
    await post('/cadastro/', ESTUDANTE)
    vi.setSystemTime(new Date(SEGUNDA_MEIO_DIA.getTime() + 25 * 60 * 60 * 1000))
    expect((await post('/cadastro/', ESTUDANTE)).status).toBe(201)
  })

  it('rejeita matrícula ou e-mail repetidos sem dizer qual', async () => {
    await post('/cadastro/', ESTUDANTE)
    const repetido = await post('/cadastro/', { ...ESTUDANTE, apelido: 'outro_nick' })
    expect(repetido.status).toBe(422)
    expect(repetido.dados.detail).toBe('Matrícula/SIAPE ou e-mail já cadastrados.')
  })

  it('exige o aceite do aviso de privacidade', async () => {
    const resposta = await post('/cadastro/', { ...ESTUDANTE, aceitouPrivacidade: false })
    expect(resposta.status).toBe(422)
  })

  it('professor/servidor: apelido vem do e-mail; se estiver em uso, pede um manual', async () => {
    const servidor = {
      tipo: 'servidor',
      siape: '1234567',
      email: 'maria.silva@unb.br',
      senha: 'senhaforte',
      aceitouPrivacidade: true,
    }
    const primeiro = await post('/cadastro/', servidor)
    expect(primeiro.status).toBe(201)

    const colisao = await post('/cadastro/', {
      ...servidor,
      siape: '7654321',
      email: 'mariasilva@unb.br',
    })
    expect(colisao.status).toBe(409)
    expect(colisao.dados.codigo).toBe('apelido_manual')

    const manual = await post('/cadastro/', {
      ...servidor,
      siape: '7654321',
      email: 'mariasilva@unb.br',
      apelido: 'profa_maria',
    })
    expect(manual.status).toBe(201)
  })
})

describe('login (RF03)', () => {
  it('erro genérico para senha errada e para conta inexistente', async () => {
    const senhaErrada = await post('/login/', { email: CONTA_DEMO.email, senha: 'errada123' })
    const inexistente = await post('/login/', { email: 'ninguem@aluno.unb.br', senha: 'errada123' })
    expect(senhaErrada.status).toBe(401)
    expect(senhaErrada.dados.detail).toBe(inexistente.dados.detail)
  })

  it('bloqueia por 10 minutos após 5 tentativas erradas', async () => {
    const email = 'bloqueio@aluno.unb.br'
    for (let i = 0; i < 4; i++)
      expect((await post('/login/', { email, senha: 'x' })).status).toBe(401)
    expect((await post('/login/', { email, senha: 'x' })).status).toBe(429)
    expect((await post('/login/', { email, senha: 'x' })).status).toBe(429)

    vi.setSystemTime(new Date(SEGUNDA_MEIO_DIA.getTime() + 11 * 60 * 1000))
    expect((await post('/login/', { email, senha: 'x' })).status).toBe(401)
  })
})

describe('recuperação de senha (RF04)', () => {
  it('responde igual exista ou não a conta, e troca a senha pelo link', async () => {
    const existente = await post('/recuperar-senha/', { email: CONTA_DEMO.email })
    const inexistente = await post('/recuperar-senha/', { email: 'ninguem@aluno.unb.br' })
    expect(existente.dados.detail).toBe(inexistente.dados.detail)

    const token = tokenDoLink(existente.dados.linkSimulado)
    expect((await post('/redefinir-senha/', { token, senha: 'novasenha1' })).status).toBe(200)
    expect(
      (await post('/login/', { email: CONTA_DEMO.email, senha: CONTA_DEMO.senha })).status,
    ).toBe(401)
    expect((await post('/login/', { email: CONTA_DEMO.email, senha: 'novasenha1' })).status).toBe(
      200,
    )
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
  })

  it('a segunda avaliação da mesma refeição edita a primeira', async () => {
    const token = await entrarComDemo()
    const antes = (await get(consulta, token)).dados.quantidade

    expect((await post('/avaliacoes/', { ...ALMOCO_HOJE, nota: 2 }, token)).status).toBe(201)
    expect(
      (await post('/avaliacoes/', { ...ALMOCO_HOJE, nota: 5, comentario: 'Mudei de ideia' }, token))
        .status,
    ).toBe(200)

    const { dados } = await get(consulta, token)
    expect(dados.quantidade).toBe(antes + 1)
    expect(dados.minha).toEqual({ nota: 5, comentario: 'Mudei de ideia' })
    expect(dados.avaliacoes[0]).toMatchObject({
      apelido: CONTA_DEMO.apelido,
      comentario: 'Mudei de ideia',
    })
  })

  it('não expõe e-mail nem matrícula na lista pública (RI10)', async () => {
    const token = await entrarComDemo()
    await post('/avaliacoes/', { ...ALMOCO_HOJE, nota: 4, comentario: 'Bom' }, token)
    const texto = JSON.stringify((await get(consulta)).dados)
    expect(texto).not.toContain(CONTA_DEMO.email)
    expect(texto).not.toContain('231034567')
  })

  it('não permite avaliar outro dia nem antes do início da refeição', async () => {
    const token = await entrarComDemo()
    const amanha = await post(
      '/avaliacoes/',
      { ...ALMOCO_HOJE, data: '2026-09-29', nota: 4 },
      token,
    )
    expect(amanha.dados.codigo).toBe('fora_do_dia')

    const jantar = await post(
      '/avaliacoes/',
      { ...ALMOCO_HOJE, refeicao: 'jantar', nota: 4 },
      token,
    )
    expect(jantar.dados.codigo).toBe('antes_do_inicio')
  })

  it('valida nota e tamanho do comentário', async () => {
    const token = await entrarComDemo()
    expect((await post('/avaliacoes/', { ...ALMOCO_HOJE, nota: 0 }, token)).status).toBe(422)
    const longo = await post(
      '/avaliacoes/',
      { ...ALMOCO_HOJE, nota: 3, comentario: 'x'.repeat(501) },
      token,
    )
    expect(longo.status).toBe(422)
  })

  it('refeição que ainda não começou não tem avaliações', async () => {
    const { dados } = await get('/avaliacoes/?campus=gama&data=2026-09-28&refeicao=jantar')
    expect(dados).toMatchObject({ quantidade: 0, media: null, avaliacoes: [] })
  })
})
