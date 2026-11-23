import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { repassarPontos, useGamificacaoStore } from './gamificacao'
import { useAuthStore } from './auth'
import { useAvaliacoesStore } from './avaliacoes'
import { ApiError, apiClient } from '@/services/apiClient'
import { CONTA_DEMO } from '@/services/mock/banco'
import { banco, reiniciarSimulacao, simulacao } from '@/services/mock/servidor'

const bloco = (contribuicao, avaliacaoLiberada = 0) => ({
  total: contribuicao + avaliacaoLiberada,
  contribuicao,
  avaliacaoLiberada,
})

beforeEach(() => {
  setActivePinia(createPinia())
})

afterEach(() => {
  vi.restoreAllMocks()
})

describe('gamificacaoStore: pontos recebidos (FE-10, RF24.2)', () => {
  it('começa sem pontos e sem aviso', () => {
    const gamificacao = useGamificacaoStore()

    expect(gamificacao.ultimosPontos).toBeNull()
    expect(gamificacao.aviso).toBeNull()
    expect(gamificacao.progressoDesatualizado).toBe(false)
  })

  it('total maior que 0: guarda o bloco, abre o aviso e marca o progresso como desatualizado', () => {
    const gamificacao = useGamificacaoStore()

    gamificacao.registrarPontos(bloco(10, 5))

    expect(gamificacao.ultimosPontos).toEqual({ total: 15, contribuicao: 10, avaliacaoLiberada: 5 })
    expect(gamificacao.aviso).toEqual({ id: 1, total: 15 })
    expect(gamificacao.progressoDesatualizado).toBe(true)
  })

  it('guarda só os três campos do contrato', () => {
    const gamificacao = useGamificacaoStore()

    gamificacao.registrarPontos({ ...bloco(10), bonusSemana: 20, extra: 'x' })

    expect(gamificacao.ultimosPontos).toEqual({ total: 10, contribuicao: 10, avaliacaoLiberada: 0 })
  })

  it('total 0: guarda o bloco, sem aviso e sem mexer no progresso', () => {
    const gamificacao = useGamificacaoStore()

    gamificacao.registrarPontos(bloco(0))

    expect(gamificacao.ultimosPontos).toEqual({ total: 0, contribuicao: 0, avaliacaoLiberada: 0 })
    expect(gamificacao.aviso).toBeNull()
    expect(gamificacao.progressoDesatualizado).toBe(false)
  })

  it('total 0 depois de um aviso não fecha o aviso aberto', () => {
    const gamificacao = useGamificacaoStore()

    gamificacao.registrarPontos(bloco(10))
    gamificacao.registrarPontos(bloco(0))

    expect(gamificacao.aviso).toEqual({ id: 1, total: 10 })
  })

  it('cada contribuição que pontua abre um aviso novo, mesmo com o mesmo total', () => {
    const gamificacao = useGamificacaoStore()

    gamificacao.registrarPontos(bloco(10))
    gamificacao.registrarPontos(bloco(10))

    expect(gamificacao.aviso).toEqual({ id: 2, total: 10 })
  })

  it.each([
    [undefined],
    [null],
    [{}],
    [{ total: 10 }],
    [{ total: 10, contribuicao: 10 }],
    [{ total: -5, contribuicao: 0, avaliacaoLiberada: 0 }],
    [{ total: '10', contribuicao: 10, avaliacaoLiberada: 0 }],
    [{ total: 1.5, contribuicao: 1.5, avaliacaoLiberada: 0 }],
    [{ total: 10, contribuicao: null, avaliacaoLiberada: 0 }],
    [{ total: 10, contribuicao: 10, avaliacaoLiberada: -1 }],
  ])('bloco fora do contrato (%o): ignora e registra no console', (pontos) => {
    const gamificacao = useGamificacaoStore()
    const log = vi.spyOn(console, 'error').mockImplementation(() => {})

    gamificacao.registrarPontos(pontos)

    expect(gamificacao.ultimosPontos).toBeNull()
    expect(gamificacao.aviso).toBeNull()
    expect(log).toHaveBeenCalledTimes(1)
  })

  it('bloco fora do contrato depois de um válido não apaga o que já estava', () => {
    const gamificacao = useGamificacaoStore()
    vi.spyOn(console, 'error').mockImplementation(() => {})
    gamificacao.registrarPontos(bloco(10))

    gamificacao.registrarPontos({ total: 'dez' })

    expect(gamificacao.ultimosPontos).toEqual(bloco(10))
    expect(gamificacao.aviso).toEqual({ id: 1, total: 10 })
  })

  it('fecharAviso() fecha o aviso aberto', () => {
    const gamificacao = useGamificacaoStore()
    gamificacao.registrarPontos(bloco(10))

    gamificacao.fecharAviso()

    expect(gamificacao.aviso).toBeNull()
  })

  it('fecharAviso(id) de um aviso antigo não fecha o novo', () => {
    const gamificacao = useGamificacaoStore()
    gamificacao.registrarPontos(bloco(10))
    gamificacao.registrarPontos(bloco(15))

    gamificacao.fecharAviso(1)

    expect(gamificacao.aviso).toEqual({ id: 2, total: 15 })
  })

  it('limpar() apaga os pontos, o aviso e o progresso desatualizado', () => {
    const gamificacao = useGamificacaoStore()
    gamificacao.registrarPontos(bloco(10))

    gamificacao.limpar()

    expect(gamificacao.ultimosPontos).toBeNull()
    expect(gamificacao.aviso).toBeNull()
    expect(gamificacao.progressoDesatualizado).toBe(false)
  })
})

describe('repassarPontos', () => {
  it('entrega o bloco à gamificacaoStore', () => {
    repassarPontos(bloco(10), 'do check-in')

    expect(useGamificacaoStore().aviso).toEqual({ id: 1, total: 10 })
  })

  it('se registrar os pontos lançar, não propaga: só registra no console', () => {
    const gamificacao = useGamificacaoStore()
    vi.spyOn(gamificacao, 'registrarPontos').mockImplementation(() => {
      throw new Error('quebrou')
    })
    const log = vi.spyOn(console, 'error').mockImplementation(() => {})

    expect(() => repassarPontos(bloco(10), 'do check-in')).not.toThrow()
    expect(log).toHaveBeenCalledWith('Falha ao registrar os pontos do check-in.', expect.any(Error))
  })
})

describe('gamificacaoStore: progresso, ranking e adesão (FE-12)', () => {
  const SEGUNDA = new Date(2026, 8, 28, 12, 0)

  async function entrar() {
    await useAuthStore().entrar(CONTA_DEMO.email, CONTA_DEMO.senha)
  }

  function darCheckins(quantidade, campus = 1) {
    for (let i = 0; i < quantidade; i++) {
      banco.estado.checkins.push({
        id: 1000 + i,
        usuarioId: 1,
        campus,
        tipoRefeicao: 'almoco',
        data: '2026-09-28',
      })
    }
  }

  const progressoValido = (troca = {}) => ({
    patente: 'CALOURO_DE_BANDEJA',
    pontosTotais: 0,
    faltaParaProxima: 150,
    sequencia: 0,
    diasNaSemana: 0,
    minimoDias: 3,
    participaRanking: false,
    ...troca,
  })

  function adiado() {
    let resolver
    let rejeitar
    const promessa = new Promise((resolve, reject) => {
      resolver = resolve
      rejeitar = reject
    })
    return { promessa, resolver, rejeitar }
  }

  function perderSessao() {
    useAuthStore().limpar()
    return new ApiError(401, { codigo: 'nao_autenticado' })
  }

  beforeEach(() => {
    vi.useFakeTimers({ toFake: ['Date'] })
    vi.setSystemTime(SEGUNDA)
    localStorage.clear()
    reiniciarSimulacao()
    setActivePinia(createPinia())
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('carrega o progresso da conta: patente, pontos, quanto falta e a adesão', async () => {
    await entrar()
    darCheckins(3)
    const gamificacao = useGamificacaoStore()

    await gamificacao.carregarProgresso()

    expect(gamificacao.progresso).toEqual({
      situacao: 'carregado',
      erro: null,
      dados: {
        patente: 'CALOURO_DE_BANDEJA',
        pontosTotais: 30,
        faltaParaProxima: 120,
        sequencia: 0,
        diasNaSemana: 1,
        minimoDias: 3,
        participaRanking: false,
      },
    })
  })

  it('carregado vem do cache; com o progresso desatualizado (pontos novos), pede de novo', async () => {
    await entrar()
    const gamificacao = useGamificacaoStore()
    const get = vi.spyOn(apiClient, 'get')

    await gamificacao.carregarProgresso()
    await gamificacao.carregarProgresso()
    expect(get).toHaveBeenCalledTimes(1)

    gamificacao.registrarPontos(bloco(10))
    await gamificacao.carregarProgresso()

    expect(get).toHaveBeenCalledTimes(2)
    expect(gamificacao.progressoDesatualizado).toBe(false)
  })

  it('dois pedidos ao mesmo tempo saem uma vez só', async () => {
    await entrar()
    const gamificacao = useGamificacaoStore()
    const get = vi.spyOn(apiClient, 'get')

    await Promise.all([gamificacao.carregarProgresso(), gamificacao.carregarProgresso()])

    expect(get).toHaveBeenCalledTimes(1)
  })

  it('501 (backend sem a regra): "indisponivel", sem erro', async () => {
    await entrar()
    simulacao.definirGamificacaoDisponivel(false)
    const gamificacao = useGamificacaoStore()

    await gamificacao.carregarProgresso()

    expect(gamificacao.progresso).toEqual({ situacao: 'indisponivel', dados: null, erro: null })
  })

  it.each([
    ['patente desconhecida', { patente: 'GENERAL' }],
    ['sem participaRanking', { participaRanking: undefined }],
    ['pontos negativos', { pontosTotais: -1 }],
  ])('progresso fora do contrato (%s): erro', async (_caso, troca) => {
    await entrar()
    vi.spyOn(apiClient, 'get').mockResolvedValueOnce(progressoValido(troca))
    vi.spyOn(console, 'error').mockImplementation(() => {})
    const gamificacao = useGamificacaoStore()

    await gamificacao.carregarProgresso()

    expect(gamificacao.progresso.situacao).toBe('erro')
    expect(gamificacao.progresso.erro.mensagem).toEqual(expect.any(String))
  })

  it('sair no meio do carregamento: a resposta antiga não volta para a store', async () => {
    await entrar()
    const gamificacao = useGamificacaoStore()

    const pedido = gamificacao.carregarProgresso()
    gamificacao.limpar()
    await pedido

    expect(gamificacao.progresso).toEqual({ situacao: null, dados: null, erro: null })
  })

  it('sair e entrar com o pedido antigo pendente: pede de novo e não fica preso em "carregando"', async () => {
    await entrar()
    const gamificacao = useGamificacaoStore()
    const antigo = adiado()
    const get = vi.spyOn(apiClient, 'get').mockReturnValueOnce(antigo.promessa)

    gamificacao.carregarProgresso()
    gamificacao.limpar()
    const novo = gamificacao.carregarProgresso()
    antigo.resolver(progressoValido({ pontosTotais: 999 }))
    await novo

    expect(get).toHaveBeenCalledTimes(2)
    expect(gamificacao.progresso.situacao).toBe('carregado')
    expect(gamificacao.progresso.dados.pontosTotais).toBe(0)
  })

  it('resposta fora de ordem: um pedido sem forcar que chega depois não desfaz o com forcar', async () => {
    await entrar()
    const gamificacao = useGamificacaoStore()
    const primeiro = adiado()
    const segundo = adiado()
    vi.spyOn(apiClient, 'get')
      .mockReturnValueOnce(primeiro.promessa)
      .mockReturnValueOnce(segundo.promessa)

    const pedidoA = gamificacao.carregarProgresso()
    const pedidoB = gamificacao.carregarProgresso({ forcar: true })
    segundo.resolver(progressoValido({ participaRanking: true }))
    await pedidoB
    primeiro.resolver(progressoValido({ participaRanking: false }))
    await pedidoA

    expect(gamificacao.progresso.dados.participaRanking).toBe(true)
  })

  it('401 no progresso: a sessão acaba e nada fica gravado', async () => {
    await entrar()
    const gamificacao = useGamificacaoStore()
    vi.spyOn(apiClient, 'get').mockImplementationOnce(() => Promise.reject(perderSessao()))

    await gamificacao.carregarProgresso()

    expect(useAuthStore().estaAutenticado).toBe(false)
    expect(gamificacao.progresso).toEqual({ situacao: null, dados: null, erro: null })
  })

  it('ranking do campus: público, com cache por campus', async () => {
    const gamificacao = useGamificacaoStore()
    const get = vi.spyOn(apiClient, 'get')

    await gamificacao.carregarRanking(1)
    await gamificacao.carregarRanking(1)

    expect(get).toHaveBeenCalledTimes(1)
    expect(gamificacao.rankingDe(1).dados).toMatchObject({ campusId: 1, semestre: '2026.2' })
    expect(gamificacao.rankingDe(1).dados.linhas[0]).toEqual({
      posicao: 1,
      apelido: 'bandejeiro_raiz',
      patente: 'VETERANO',
    })
    expect(gamificacao.rankingDe(3)).toBeNull()
  })

  it('ranking de campus inexistente: erro campus_nao_encontrado', async () => {
    const gamificacao = useGamificacaoStore()

    await gamificacao.carregarRanking(99)

    expect(gamificacao.rankingDe(99)).toMatchObject({
      situacao: 'erro',
      erro: { codigo: 'campus_nao_encontrado' },
    })
  })

  it('campusId como texto (vindo da rota) usa a mesma entrada do número', async () => {
    const gamificacao = useGamificacaoStore()
    const get = vi.spyOn(apiClient, 'get')

    await gamificacao.carregarRanking('1')
    await gamificacao.carregarRanking(1)

    expect(get).toHaveBeenCalledTimes(1)
    expect(get).toHaveBeenCalledWith('/ranking/1/')
    expect(gamificacao.rankingDe(1).situacao).toBe('carregado')
    expect(gamificacao.rankingDe('1')).toBe(gamificacao.rankingDe(1))
  })

  it('ranking com 501: "indisponivel", sem erro', async () => {
    simulacao.definirGamificacaoDisponivel(false)
    const gamificacao = useGamificacaoStore()

    await gamificacao.carregarRanking(1)

    expect(gamificacao.rankingDe(1)).toEqual({ situacao: 'indisponivel', dados: null, erro: null })
  })

  it('ranking com forcar: a resposta antiga que chega depois não sobrescreve a nova', async () => {
    const gamificacao = useGamificacaoStore()
    const antigo = adiado()
    const novo = adiado()
    vi.spyOn(apiClient, 'get')
      .mockReturnValueOnce(antigo.promessa)
      .mockReturnValueOnce(novo.promessa)
    const ranking = (apelido) => ({
      campusId: 1,
      semestre: '2026.2',
      linhas: [{ posicao: 1, apelido, patente: 'VETERANO' }],
    })

    const pedidoAntigo = gamificacao.carregarRanking(1)
    const pedidoNovo = gamificacao.carregarRanking(1, { forcar: true })
    novo.resolver(ranking('novo'))
    await pedidoNovo
    antigo.resolver(ranking('antigo'))
    await pedidoAntigo

    expect(gamificacao.rankingDe(1).dados.linhas[0].apelido).toBe('novo')
  })

  it.each([
    ['campusId diferente', { campusId: 2 }],
    ['linhas que não são lista', { linhas: {} }],
    ['posição 0', { linhas: [{ posicao: 0, apelido: 'a', patente: 'VETERANO' }] }],
    ['posição quebrada', { linhas: [{ posicao: 1.5, apelido: 'a', patente: 'VETERANO' }] }],
    ['patente desconhecida', { linhas: [{ posicao: 1, apelido: 'a', patente: 'GENERAL' }] }],
    ['sem apelido', { linhas: [{ posicao: 1, patente: 'VETERANO' }] }],
    ['semestre numérico', { semestre: 20262 }],
  ])('ranking fora do contrato (%s): erro', async (_caso, troca) => {
    vi.spyOn(apiClient, 'get').mockResolvedValueOnce({
      campusId: 1,
      semestre: '2026.2',
      linhas: [],
      ...troca,
    })
    vi.spyOn(console, 'error').mockImplementation(() => {})
    const gamificacao = useGamificacaoStore()

    await gamificacao.carregarRanking(1)

    expect(gamificacao.rankingDe(1).situacao).toBe('erro')
  })

  it('logout limpa os rankings, e um pedido pendente não volta depois', async () => {
    const gamificacao = useGamificacaoStore()
    await gamificacao.carregarRanking(1)
    const pendente = adiado()
    vi.spyOn(apiClient, 'get').mockReturnValueOnce(pendente.promessa)

    const pedido = gamificacao.carregarRanking(3)
    gamificacao.limpar()
    pendente.resolver({ campusId: 3, semestre: '2026.2', linhas: [] })
    await pedido

    expect(gamificacao.rankingDe(1)).toBeNull()
    expect(gamificacao.rankingDe(3)).toBeNull()
  })

  it('entrar no ranking: POST, recarrega o progresso e os rankings já abertos e limpa os comentários', async () => {
    await entrar()
    darCheckins(2, 1)
    const gamificacao = useGamificacaoStore()
    await gamificacao.carregarProgresso()
    await gamificacao.carregarRanking(1)
    const limparCache = vi.spyOn(useAvaliacoesStore(), 'limparCache')
    const post = vi.spyOn(apiClient, 'post')
    const get = vi.spyOn(apiClient, 'get')

    const resultado = await gamificacao.alterarAdesao(true)

    expect(resultado).toEqual({ desfecho: 'ok' })
    expect(post).toHaveBeenCalledWith('/gamificacao/adesao/')
    expect(get.mock.calls.map(([caminho]) => caminho).sort()).toEqual([
      '/gamificacao/progresso/',
      '/ranking/1/',
    ])
    expect(limparCache).toHaveBeenCalledTimes(1)
    expect(gamificacao.progresso.dados.participaRanking).toBe(true)
    expect(gamificacao.rankingDe(1).dados.linhas.map((l) => l.apelido)).toContain(
      CONTA_DEMO.apelido,
    )
    expect(gamificacao.alterandoAdesao).toBe(false)
  })

  it('sair do ranking: DELETE e o apelido some do ranking na hora', async () => {
    await entrar()
    darCheckins(2, 1)
    const gamificacao = useGamificacaoStore()
    await gamificacao.alterarAdesao(true)
    await gamificacao.carregarRanking(1)
    const del = vi.spyOn(apiClient, 'delete')

    await gamificacao.alterarAdesao(false)

    expect(del).toHaveBeenCalledWith('/gamificacao/adesao/')
    expect(gamificacao.progresso.dados.participaRanking).toBe(false)
    expect(gamificacao.rankingDe(1).dados.linhas.map((l) => l.apelido)).not.toContain(
      CONTA_DEMO.apelido,
    )
  })

  it('falha ao mudar a adesão: erro com mensagem, sem recarregar nada', async () => {
    await entrar()
    const gamificacao = useGamificacaoStore()
    await gamificacao.carregarProgresso()
    vi.spyOn(apiClient, 'post').mockRejectedValueOnce(
      new ApiError(0, { codigo: 'sem_conexao', mensagem: 'Sem internet.' }),
    )
    const get = vi.spyOn(apiClient, 'get')

    const resultado = await gamificacao.alterarAdesao(true)

    expect(resultado).toEqual({ desfecho: 'erro', mensagem: 'Sem internet.' })
    expect(gamificacao.erroDaAdesao).toBe('Sem internet.')
    expect(get).not.toHaveBeenCalled()
    expect(gamificacao.progresso.dados.participaRanking).toBe(false)
  })

  it('dois toques seguidos no interruptor: o segundo é ignorado enquanto o primeiro não acaba', async () => {
    await entrar()
    const gamificacao = useGamificacaoStore()
    const pendente = adiado()
    const post = vi.spyOn(apiClient, 'post').mockReturnValueOnce(pendente.promessa)

    const primeiro = gamificacao.alterarAdesao(true)
    const segundo = await gamificacao.alterarAdesao(true)

    expect(segundo).toEqual({ desfecho: 'ignorado' })
    expect(gamificacao.alterandoAdesao).toBe(true)
    pendente.resolver(null)
    expect(await primeiro).toEqual({ desfecho: 'ok' })
    expect(post).toHaveBeenCalledTimes(1)
  })

  it('adesão confirmada: participaRanking muda na hora, sem voltar a "carregando"', async () => {
    await entrar()
    const gamificacao = useGamificacaoStore()
    await gamificacao.carregarProgresso()
    const recarga = adiado()
    vi.spyOn(apiClient, 'get').mockReturnValueOnce(recarga.promessa)

    const mudanca = gamificacao.alterarAdesao(true)
    await vi.waitFor(() => expect(gamificacao.progresso.dados.participaRanking).toBe(true))

    expect(gamificacao.progresso.situacao).toBe('carregado')
    recarga.resolver(progressoValido({ participaRanking: true }))
    expect(await mudanca).toEqual({ desfecho: 'ok' })
  })

  it('adesão confirmada e o recarregamento falha: mantém o novo estado, sem erro, e marca como desatualizado', async () => {
    await entrar()
    const gamificacao = useGamificacaoStore()
    await gamificacao.carregarProgresso()
    vi.spyOn(apiClient, 'get').mockRejectedValueOnce(
      new ApiError(500, { codigo: 'erro_interno', mensagem: 'Erro no servidor.' }),
    )

    const resultado = await gamificacao.alterarAdesao(true)

    expect(resultado).toEqual({ desfecho: 'ok' })
    expect(gamificacao.erroDaAdesao).toBeNull()
    expect(gamificacao.progresso).toMatchObject({
      situacao: 'carregado',
      erro: null,
      dados: { participaRanking: true },
    })
    expect(gamificacao.progressoDesatualizado).toBe(true)
  })

  it('401 na adesão: o erro não passa para quem entrar depois', async () => {
    await entrar()
    const gamificacao = useGamificacaoStore()
    await gamificacao.carregarProgresso()
    vi.spyOn(apiClient, 'post').mockImplementationOnce(() => Promise.reject(perderSessao()))

    await gamificacao.alterarAdesao(true)
    expect(gamificacao.erroDaAdesao).toBeNull()

    await entrar()
    expect(gamificacao.erroDaAdesao).toBeNull()
  })

  it('falha ao sair do ranking: continua dentro, com o erro; a próxima tentativa apaga o erro', async () => {
    await entrar()
    const gamificacao = useGamificacaoStore()
    await gamificacao.alterarAdesao(true)
    vi.spyOn(apiClient, 'delete').mockRejectedValueOnce(
      new ApiError(0, { codigo: 'sem_conexao', mensagem: 'Sem internet.' }),
    )

    await gamificacao.alterarAdesao(false)
    expect(gamificacao.erroDaAdesao).toBe('Sem internet.')
    expect(gamificacao.progresso.dados.participaRanking).toBe(true)

    await gamificacao.alterarAdesao(false)
    expect(gamificacao.erroDaAdesao).toBeNull()
    expect(gamificacao.progresso.dados.participaRanking).toBe(false)
  })
})

/** Ranking do semestre por campus para a RankingView (FE-13, RF27.2, RI12). */
describe('gamificacaoStore: ranking para a RankingView (FE-13)', () => {
  beforeEach(() => reiniciarSimulacao())

  it('carrega o ranking do campus e guarda por campus', async () => {
    const gamificacao = useGamificacaoStore()
    const get = vi.spyOn(apiClient, 'get')

    await gamificacao.carregarRanking(1)
    const ranking = gamificacao.rankingDoCampus(1)

    expect(get).toHaveBeenCalledWith('/ranking/1/')
    expect(ranking).toMatchObject({ campusId: 1, semestre: expect.any(String) })
    expect(ranking.linhas.length).toBeGreaterThan(0)
    expect(ranking.linhas.length).toBeLessThanOrEqual(10)
    expect(gamificacao.rankingDoCampus(1)).toEqual(ranking)
    expect(gamificacao.situacaoDoRanking(1)).toBe('carregado')
    expect(gamificacao.rankingDoCampus(2)).toBeNull()
  })

  it('guarda só posição, apelido e patente de cada linha, nunca pontos (RI12)', async () => {
    vi.spyOn(apiClient, 'get').mockResolvedValueOnce({
      campusId: 3,
      semestre: '2026.2',
      linhas: [{ posicao: 1, apelido: 'ana', patente: 'VETERANO', pontos: 480, email: 'x@y' }],
    })
    const gamificacao = useGamificacaoStore()

    await gamificacao.carregarRanking(3)
    const ranking = gamificacao.rankingDoCampus(3)

    expect(ranking.linhas).toEqual([{ posicao: 1, apelido: 'ana', patente: 'VETERANO' }])
  })

  it('campus sem ninguém no ranking: linhas vazias, situação "carregado"', async () => {
    const gamificacao = useGamificacaoStore()

    await gamificacao.carregarRanking(5)
    const ranking = gamificacao.rankingDoCampus(5)

    expect(ranking.linhas).toEqual([])
    expect(gamificacao.situacaoDoRanking(5)).toBe('carregado')
  })

  it('não pede de novo um ranking já carregado, a não ser com forcar', async () => {
    const gamificacao = useGamificacaoStore()
    await gamificacao.carregarRanking(1)
    const get = vi.spyOn(apiClient, 'get')

    await gamificacao.carregarRanking(1)
    expect(get).not.toHaveBeenCalled()

    await gamificacao.carregarRanking(1, { forcar: true })
    expect(get).toHaveBeenCalledTimes(1)
  })

  it('404 sem o código campus_nao_encontrado (proxy, rota errada): "erro" e console', async () => {
    vi.spyOn(apiClient, 'get').mockRejectedValueOnce(new ApiError(404, {}))
    const log = vi.spyOn(console, 'error').mockImplementation(() => {})
    const gamificacao = useGamificacaoStore()

    await gamificacao.carregarRanking(1)

    expect(gamificacao.situacaoDoRanking(1)).toBe('erro')
    expect(log).toHaveBeenCalledTimes(1)
  })

  it('404 campus_nao_encontrado: situação "nao_encontrado", sem console', async () => {
    const gamificacao = useGamificacaoStore()
    const log = vi.spyOn(console, 'error')

    await gamificacao.carregarRanking(999)

    expect(gamificacao.rankingDoCampus(999)).toBeNull()

    expect(gamificacao.situacaoDoRanking(999)).toBe('nao_encontrado')
    expect(log).not.toHaveBeenCalled()
  })

  it('501 (backend ainda sem o ranking): situação "indisponivel", sem console', async () => {
    simulacao.definirGamificacaoDisponivel(false)
    const gamificacao = useGamificacaoStore()
    const log = vi.spyOn(console, 'error')

    await gamificacao.carregarRanking(1)

    expect(gamificacao.rankingDoCampus(1)).toBeNull()

    expect(gamificacao.situacaoDoRanking(1)).toBe('indisponivel')
    expect(log).not.toHaveBeenCalled()
  })

  it('outra falha: situação "erro" com a mensagem da API', async () => {
    vi.spyOn(apiClient, 'get').mockRejectedValueOnce(
      new ApiError(0, { codigo: 'sem_conexao', mensagem: 'Sem internet.' }),
    )
    vi.spyOn(console, 'error').mockImplementation(() => {})
    const gamificacao = useGamificacaoStore()

    await gamificacao.carregarRanking(1)

    expect(gamificacao.rankingDoCampus(1)).toBeNull()

    expect(gamificacao.situacaoDoRanking(1)).toBe('erro')
    expect(gamificacao.erroDoRanking(1)).toBe('Sem internet.')
  })

  it('resposta sem a lista de linhas: "erro" e registro no console', async () => {
    vi.spyOn(apiClient, 'get').mockResolvedValueOnce({ campusId: 1, semestre: '2026.2' })
    const log = vi.spyOn(console, 'error').mockImplementation(() => {})
    const gamificacao = useGamificacaoStore()

    await gamificacao.carregarRanking(1)

    expect(gamificacao.rankingDoCampus(1)).toBeNull()

    expect(gamificacao.situacaoDoRanking(1)).toBe('erro')
    expect(log).toHaveBeenCalledTimes(1)
  })

  it('uma falha não apaga o ranking que já estava carregado', async () => {
    const gamificacao = useGamificacaoStore()
    await gamificacao.carregarRanking(1)
    const antes = gamificacao.rankingDoCampus(1)
    vi.spyOn(apiClient, 'get').mockRejectedValueOnce(new ApiError(503, {}))
    vi.spyOn(console, 'error').mockImplementation(() => {})

    await gamificacao.carregarRanking(1, { forcar: true })

    expect(gamificacao.rankingDoCampus(1)).toEqual(antes)
  })
})

/** Casos da revisão do PR #242. */
describe('gamificacaoStore: ranking — validação, cache e corridas', () => {
  beforeEach(() => reiniciarSimulacao())

  const respondendo = (corpo) => vi.spyOn(apiClient, 'get').mockResolvedValueOnce(corpo)

  it.each([
    ['linha vazia', { campusId: 1, semestre: '2026.2', linhas: [{}] }],
    ['sem semestre', { campusId: 1, linhas: [] }],
    ['sem campusId', { semestre: '2026.2', linhas: [] }],
    [
      'posição não inteira',
      {
        campusId: 1,
        semestre: '2026.2',
        linhas: [{ posicao: '1', apelido: 'a', patente: 'VETERANO' }],
      },
    ],
    [
      'apelido não texto',
      {
        campusId: 1,
        semestre: '2026.2',
        linhas: [{ posicao: 1, apelido: 7, patente: 'VETERANO' }],
      },
    ],
    [
      'patente fora do Anexo A',
      {
        campusId: 1,
        semestre: '2026.2',
        linhas: [{ posicao: 1, apelido: 'a', patente: 'GENERAL' }],
      },
    ],
  ])('resposta fora do contrato (%s): "erro" e console', async (_caso, corpo) => {
    respondendo(corpo)
    const log = vi.spyOn(console, 'error').mockImplementation(() => {})
    const gamificacao = useGamificacaoStore()

    await gamificacao.carregarRanking(1)

    expect(gamificacao.rankingDoCampus(1)).toBeNull()
    expect(gamificacao.situacaoDoRanking(1)).toBe('erro')
    expect(gamificacao.erroDoRanking(1)).toEqual(expect.any(String))
    expect(log).toHaveBeenCalledTimes(1)
  })

  it('erro que não é da API vai para o console uma vez só', async () => {
    vi.spyOn(apiClient, 'get').mockRejectedValueOnce(new TypeError('quebrou'))
    const log = vi.spyOn(console, 'error').mockImplementation(() => {})
    const gamificacao = useGamificacaoStore()

    await gamificacao.carregarRanking(1)

    expect(log).toHaveBeenCalledTimes(1)
  })

  it('invalidarRanking(campusId): o próximo carregarRanking busca de novo', async () => {
    const gamificacao = useGamificacaoStore()
    await gamificacao.carregarRanking(1)
    const get = vi.spyOn(apiClient, 'get')

    gamificacao.invalidarRanking(1)
    await gamificacao.carregarRanking(1)

    expect(get).toHaveBeenCalledWith('/ranking/1/')
  })

  it('invalidarRanking() sem campus vale para todos; o ranking na tela continua até chegar o novo', async () => {
    const gamificacao = useGamificacaoStore()
    await gamificacao.carregarRanking(1)
    await gamificacao.carregarRanking(3)

    gamificacao.invalidarRanking()

    expect(gamificacao.rankingDoCampus(1)).not.toBeNull()
    const get = vi.spyOn(apiClient, 'get')
    await gamificacao.carregarRanking(1)
    await gamificacao.carregarRanking(3)
    expect(get.mock.calls.map(([caminho]) => caminho)).toEqual(['/ranking/1/', '/ranking/3/'])
  })

  it('limpar() também invalida os rankings', async () => {
    const gamificacao = useGamificacaoStore()
    await gamificacao.carregarRanking(1)
    const get = vi.spyOn(apiClient, 'get')

    gamificacao.limpar()
    await gamificacao.carregarRanking(1)

    expect(get).toHaveBeenCalledTimes(1)
  })

  it('duas buscas com forcar no mesmo campus: vale a resposta da mais nova', async () => {
    const gamificacao = useGamificacaoStore()
    let responderVelha
    const get = vi.spyOn(apiClient, 'get')
    get.mockImplementationOnce(() => new Promise((ok) => (responderVelha = ok)))
    get.mockResolvedValueOnce({
      campusId: 1,
      semestre: '2026.2',
      linhas: [{ posicao: 1, apelido: 'nova', patente: 'VETERANO' }],
    })

    const velha = gamificacao.carregarRanking(1, { forcar: true })
    await gamificacao.carregarRanking(1, { forcar: true })
    responderVelha({
      campusId: 1,
      semestre: '2026.2',
      linhas: [{ posicao: 1, apelido: 'velha', patente: 'VETERANO' }],
    })
    await velha

    expect(gamificacao.rankingDoCampus(1).linhas[0].apelido).toBe('nova')
    expect(gamificacao.situacaoDoRanking(1)).toBe('carregado')
  })

  it('404 campus_nao_encontrado apaga um ranking antigo do campus', async () => {
    const gamificacao = useGamificacaoStore()
    await gamificacao.carregarRanking(1)
    vi.spyOn(apiClient, 'get').mockRejectedValueOnce(
      new ApiError(404, { codigo: 'campus_nao_encontrado' }),
    )

    await gamificacao.carregarRanking(1, { forcar: true })

    expect(gamificacao.rankingDoCampus(1)).toBeNull()
  })
})
