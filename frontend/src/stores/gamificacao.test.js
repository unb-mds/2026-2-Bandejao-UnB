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

  it('501 (BE-16 ainda sem a regra): "indisponivel", sem erro', async () => {
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
    vi.spyOn(apiClient, 'get').mockResolvedValueOnce({
      patente: 'CALOURO_DE_BANDEJA',
      pontosTotais: 0,
      faltaParaProxima: 150,
      sequencia: 0,
      diasNaSemana: 0,
      minimoDias: 3,
      participaRanking: false,
      ...troca,
    })
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
    const post = vi.spyOn(apiClient, 'post')

    const primeiro = gamificacao.alterarAdesao(true)
    const segundo = await gamificacao.alterarAdesao(true)
    await primeiro

    expect(segundo).toEqual({ desfecho: 'ignorado' })
    expect(post).toHaveBeenCalledTimes(1)
  })
})
