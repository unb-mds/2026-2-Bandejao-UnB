import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useAvaliacoesStore } from './avaliacoes'
import { useAuthStore } from './auth'
import { useGamificacaoStore } from './gamificacao'
import { ApiError, apiClient } from '@/services/apiClient'
import { CONTA_DEMO } from '@/services/mock/banco'
import { reiniciarSimulacao, simulacao } from '@/services/mock/servidor'

/** avaliacoesStore com o servidor simulado (Plano de Testes 3.1; módulo crítico). */

// Segunda-feira, 28/09/2026, 12h — almoço em andamento.
const SEGUNDA_MEIO_DIA = new Date(2026, 8, 28, 12, 0)
const ALMOCO_HOJE = { campus: 3, data: '2026-09-28', refeicao: 'almoco' }

beforeEach(() => {
  vi.useFakeTimers({ toFake: ['Date'] })
  vi.setSystemTime(SEGUNDA_MEIO_DIA)
  reiniciarSimulacao()
  setActivePinia(createPinia())
})

afterEach(() => {
  vi.useRealTimers()
  vi.restoreAllMocks()
})

// MVP: a `HomeView` (/inicio) ainda lê a semana e a refeição no formato
// antigo. Sai na FE-E2.
describe('avaliacoesStore (formato do MVP, usado pela HomeView)', () => {
  it('carrega as avaliações de uma refeição e guarda pela refeição', async () => {
    const avaliacoes = useAvaliacoesStore()

    const daRefeicao = await avaliacoes.carregar(ALMOCO_HOJE)

    expect(daRefeicao.quantidade).toEqual(expect.any(Number))
    expect(avaliacoes.daRefeicao(ALMOCO_HOJE)).toBe(daRefeicao)
    expect(avaliacoes.daRefeicao({ ...ALMOCO_HOJE, refeicao: 'jantar' })).toBeNull()
  })

  it('carrega o resumo da semana do campus', async () => {
    const avaliacoes = useAvaliacoesStore()

    const resumo = await avaliacoes.carregarResumo(3)

    expect(resumo).not.toBeNull()
    expect(avaliacoes.resumoPorCampus[3]).toBe(resumo)
  })

  it('erro ao carregar fica em `erro` e devolve o que já havia', async () => {
    const avaliacoes = useAvaliacoesStore()

    expect(await avaliacoes.carregar({ campus: 3 })).toBeNull()
    expect(avaliacoes.erro).toBe('Informe campus, data e refeição.')

    expect(await avaliacoes.carregarResumo('executivo')).toBeNull()
    expect(avaliacoes.erro).toBe('Campus não encontrado.')
  })

  it('limparCache esquece as avaliações carregadas (login e logout)', async () => {
    const avaliacoes = useAvaliacoesStore()
    await avaliacoes.carregar(ALMOCO_HOJE)

    avaliacoes.limparCache()

    expect(avaliacoes.daRefeicao(ALMOCO_HOJE)).toBeNull()
  })
})

describe('avaliacoesStore: resumo do dia (GET /api/avaliacoes/resumo/)', () => {
  it('carrega as notas de todas as refeições do dia numa chamada só', async () => {
    const avaliacoes = useAvaliacoesStore()
    const get = vi.spyOn(apiClient, 'get')

    const resumo = await avaliacoes.carregarResumoDoDia(1, '2026-09-28')

    expect(get).toHaveBeenCalledWith('/avaliacoes/resumo/?campus=1&data=2026-09-28')
    expect(resumo.map((r) => r.tipo)).toEqual(['cafe', 'almoco', 'jantar'])
    expect(avaliacoes.daResumoDoDia(1, '2026-09-28')).toEqual(resumo)
    expect(avaliacoes.daResumoDoDia(1, '2026-09-29')).toBeNull()
  })

  it('resumo do dia em 501: devolve null, fica "indisponível" e não mexe no erro da tela', async () => {
    const avaliacoes = useAvaliacoesStore()
    simulacao.definirResumoDoDiaDisponivel(false)
    const log = vi.spyOn(console, 'error')

    expect(await avaliacoes.carregarResumoDoDia(1, '2026-09-28')).toBeNull()

    expect(avaliacoes.erro).toBeNull()
    expect(avaliacoes.situacaoDoResumoDoDia(1, '2026-09-28')).toBe('indisponivel')
    expect(log).not.toHaveBeenCalled()
  })

  it('501 que chega depois de carregar() não aparece como erro nas Avaliações', async () => {
    const avaliacoes = useAvaliacoesStore()
    simulacao.definirResumoDoDiaDisponivel(false)

    const resumo = avaliacoes.carregarResumoDoDia(1, '2026-09-28')
    await avaliacoes.carregar(ALMOCO_HOJE)
    await resumo

    expect(avaliacoes.erro).toBeNull()
  })

  it('outra falha do resumo do dia é registrada no console, sem mexer no erro da tela', async () => {
    const avaliacoes = useAvaliacoesStore()
    vi.spyOn(apiClient, 'get').mockRejectedValueOnce(
      new ApiError(500, { codigo: 'erro_interno', mensagem: 'Fora do ar.' }),
    )
    const log = vi.spyOn(console, 'error').mockImplementation(() => {})

    expect(await avaliacoes.carregarResumoDoDia(1, '2026-09-28')).toBeNull()

    expect(avaliacoes.erro).toBeNull()
    expect(avaliacoes.situacaoDoResumoDoDia(1, '2026-09-28')).toBe('erro')
    expect(log).toHaveBeenCalledTimes(1)
  })
})

/**
 * Contrato da BE-13 (FE-09): GET /api/refeicoes/{refeicaoId}/avaliacoes/ e
 * POST /api/avaliacoes/ (sempre upsert: avaliar de novo edita).
 */
describe('avaliacoesStore: avaliações de uma refeição (contrato da BE-13)', () => {
  const HOJE = '2026-09-28'

  /** refeicaoId do almoço de hoje no Gama, como o resumo do dia devolve. */
  async function idDoAlmoco(avaliacoes = useAvaliacoesStore()) {
    const resumo = await avaliacoes.carregarResumoDoDia(3, HOJE)
    return resumo.find((r) => r.tipo === 'almoco').refeicaoId
  }

  async function entrar() {
    await useAuthStore().entrar(CONTA_DEMO.email, CONTA_DEMO.senha)
  }

  it('carrega média, quantidade e comentários pelo refeicaoId', async () => {
    const avaliacoes = useAvaliacoesStore()
    const refeicaoId = await idDoAlmoco(avaliacoes)
    const get = vi.spyOn(apiClient, 'get')

    const dados = await avaliacoes.carregarAvaliacoesDaRefeicao(refeicaoId)

    expect(get).toHaveBeenCalledWith(`/refeicoes/${refeicaoId}/avaliacoes/`)
    expect(dados.resumoAvaliacoes).toEqual({
      media: expect.any(Number),
      quantidade: expect.any(Number),
    })
    expect(dados.comentarios[0]).toEqual({
      apelido: expect.any(String),
      nota: expect.any(Number),
      comentario: expect.any(String),
      criadaEm: expect.any(String),
    })
    expect(avaliacoes.avaliacoesDaRefeicao(refeicaoId)).toEqual(dados)
    expect(avaliacoes.situacaoDaRefeicao(refeicaoId)).toBe('carregado')
  })

  it('refeição em 501 (backend sem a BE-13): situação "indisponivel", sem erro no console', async () => {
    const avaliacoes = useAvaliacoesStore()
    const refeicaoId = await idDoAlmoco(avaliacoes)
    simulacao.definirAvaliacoesDisponiveis(false)
    const log = vi.spyOn(console, 'error')

    expect(await avaliacoes.carregarAvaliacoesDaRefeicao(refeicaoId)).toBeNull()

    expect(avaliacoes.situacaoDaRefeicao(refeicaoId)).toBe('indisponivel')
    expect(log).not.toHaveBeenCalled()
  })

  it('outra falha ao carregar: situação "erro" com a mensagem da API', async () => {
    const avaliacoes = useAvaliacoesStore()
    vi.spyOn(apiClient, 'get').mockRejectedValueOnce(
      new ApiError(0, { codigo: 'sem_conexao', mensagem: 'Sem internet.' }),
    )

    expect(await avaliacoes.carregarAvaliacoesDaRefeicao(42)).toBeNull()

    expect(avaliacoes.situacaoDaRefeicao(42)).toBe('erro')
    expect(avaliacoes.erroDaRefeicao(42)).toBe('Sem internet.')
  })

  it('avaliar (criar): POST /avaliacoes/ com refeicaoId, nota e comentário', async () => {
    await entrar()
    const avaliacoes = useAvaliacoesStore()
    const refeicaoId = await idDoAlmoco(avaliacoes)
    const post = vi.spyOn(apiClient, 'post')

    const resultado = await avaliacoes.avaliar({
      refeicaoId,
      campus: 3,
      data: HOJE,
      nota: 4,
      comentario: 'Bom',
    })

    expect(post).toHaveBeenCalledWith('/avaliacoes/', { refeicaoId, nota: 4, comentario: 'Bom' })
    expect(resultado).toMatchObject({
      desfecho: 'criada',
      avaliacao: { refeicaoId, nota: 4, comentario: 'Bom', editadaEm: null },
      pontos: { total: 0, contribuicao: 0, avaliacaoLiberada: 0 },
    })
    expect(avaliacoes.minhaAvaliacao(refeicaoId, CONTA_DEMO.apelido)).toEqual({
      nota: 4,
      comentario: 'Bom',
    })
  })

  it('avaliar repassa o bloco pontos à gamificacaoStore (RF24.2)', async () => {
    await entrar()
    const avaliacoes = useAvaliacoesStore()
    const refeicaoId = await idDoAlmoco(avaliacoes)
    vi.spyOn(apiClient, 'post').mockResolvedValueOnce({
      avaliacao: { id: 9, refeicaoId, nota: 5, comentario: '', criadaEm: HOJE, editadaEm: null },
      pontos: { total: 5, contribuicao: 5, avaliacaoLiberada: 0 },
    })

    await avaliacoes.avaliar({ refeicaoId, campus: 3, data: HOJE, nota: 5 })

    expect(useGamificacaoStore().ultimosPontos).toEqual({
      total: 5,
      contribuicao: 5,
      avaliacaoLiberada: 0,
    })
    expect(useGamificacaoStore().aviso).toMatchObject({ total: 5 })
  })

  it('avaliação com pontos zerados não abre o aviso de pontos', async () => {
    await entrar()
    const avaliacoes = useAvaliacoesStore()
    const refeicaoId = await idDoAlmoco(avaliacoes)

    await avaliacoes.avaliar({ refeicaoId, campus: 3, data: HOJE, nota: 4 })

    expect(useGamificacaoStore().ultimosPontos).toMatchObject({ total: 0 })
    expect(useGamificacaoStore().aviso).toBeNull()
  })

  it('falha no envio da avaliação não passa nada à gamificacaoStore', async () => {
    await entrar()
    const avaliacoes = useAvaliacoesStore()
    const refeicaoId = await idDoAlmoco(avaliacoes)
    vi.spyOn(apiClient, 'post').mockRejectedValueOnce(
      new ApiError(500, { codigo: 'erro_interno', mensagem: 'Fora do ar.' }),
    )
    vi.spyOn(console, 'error').mockImplementation(() => {})

    await avaliacoes.avaliar({ refeicaoId, campus: 3, data: HOJE, nota: 4 })

    expect(useGamificacaoStore().ultimosPontos).toBeNull()
  })

  it('avaliar recarrega os comentários e o resumo do dia (média nova)', async () => {
    await entrar()
    const avaliacoes = useAvaliacoesStore()
    const refeicaoId = await idDoAlmoco(avaliacoes)
    const antes = (await avaliacoes.carregarAvaliacoesDaRefeicao(refeicaoId)).resumoAvaliacoes
      .quantidade

    await avaliacoes.avaliar({ refeicaoId, campus: 3, data: HOJE, nota: 5, comentario: 'Top' })

    const dados = avaliacoes.avaliacoesDaRefeicao(refeicaoId)
    expect(dados.resumoAvaliacoes.quantidade).toBe(antes + 1)
    expect(dados.comentarios[0]).toMatchObject({ apelido: CONTA_DEMO.apelido, comentario: 'Top' })
    const doResumo = avaliacoes.daResumoDoDia(3, HOJE).find((r) => r.refeicaoId === refeicaoId)
    expect(doResumo.quantidade).toBe(antes + 1)
  })

  it('avaliar de novo (editar): desfecho "editada", sem duplicar', async () => {
    await entrar()
    const avaliacoes = useAvaliacoesStore()
    const refeicaoId = await idDoAlmoco(avaliacoes)
    const alvo = { refeicaoId, campus: 3, data: HOJE }
    await avaliacoes.avaliar({ ...alvo, nota: 2, comentario: '' })
    const depoisDaPrimeira = avaliacoes.avaliacoesDaRefeicao(refeicaoId).resumoAvaliacoes.quantidade

    const resultado = await avaliacoes.avaliar({ ...alvo, nota: 5, comentario: 'Mudei de ideia' })

    expect(resultado.desfecho).toBe('editada')
    expect(resultado.avaliacao.editadaEm).toEqual(expect.any(String))
    expect(avaliacoes.avaliacoesDaRefeicao(refeicaoId).resumoAvaliacoes.quantidade).toBe(
      depoisDaPrimeira,
    )
    expect(avaliacoes.minhaAvaliacao(refeicaoId, CONTA_DEMO.apelido)).toEqual({
      nota: 5,
      comentario: 'Mudei de ideia',
    })
  })

  it('minhaAvaliacao acha a do próprio apelido nos comentários (depois de recarregar a página)', async () => {
    await entrar()
    const primeira = useAvaliacoesStore()
    const refeicaoId = await idDoAlmoco(primeira)
    await primeira.avaliar({ refeicaoId, campus: 3, data: HOJE, nota: 3, comentario: 'Ok' })
    // Store nova: só o que vem do servidor.
    setActivePinia(createPinia())
    const avaliacoes = useAvaliacoesStore()

    await avaliacoes.carregarAvaliacoesDaRefeicao(refeicaoId)

    expect(avaliacoes.minhaAvaliacao(refeicaoId, CONTA_DEMO.apelido)).toEqual({
      nota: 3,
      comentario: 'Ok',
    })
    expect(avaliacoes.minhaAvaliacao(refeicaoId, 'outra_pessoa')).toBeNull()
    expect(avaliacoes.minhaAvaliacao(refeicaoId, null)).toBeNull()
  })

  it.each([
    ['janela_avaliacao_fechada', 'indisponivel', { data: '2026-09-29' }],
    ['nota_invalida', 'erro', { nota: 0 }],
    ['comentario_muito_longo', 'erro', { comentario: 'x'.repeat(501) }],
  ])('422 %s: desfecho "%s" com a mensagem por codigo', async (codigo, desfecho, mudanca) => {
    await entrar()
    const avaliacoes = useAvaliacoesStore()
    const refeicaoId = await idDoAlmoco(avaliacoes)
    let alvo = { refeicaoId, campus: 3, data: HOJE, nota: 4, comentario: '', ...mudanca }
    if (mudanca.data) {
      const outroDia = await avaliacoes.carregarResumoDoDia(3, mudanca.data)
      alvo = { ...alvo, refeicaoId: outroDia.find((r) => r.tipo === 'almoco').refeicaoId }
    }

    const resultado = await avaliacoes.avaliar(alvo)

    expect(resultado).toEqual({
      desfecho,
      codigo,
      mensagem: {
        janela_avaliacao_fechada:
          'A avaliação desta refeição está fechada. Só dá para avaliar refeições de hoje que já começaram, até 23h59.',
        nota_invalida: 'Escolha uma nota de 1 a 5 estrelas.',
        comentario_muito_longo: 'O comentário pode ter no máximo 500 caracteres.',
      }[codigo],
    })
  })

  it('404 refeicao_nao_encontrada: indisponível', async () => {
    await entrar()
    const avaliacoes = useAvaliacoesStore()

    const resultado = await avaliacoes.avaliar({ refeicaoId: 999, campus: 3, data: HOJE, nota: 4 })

    expect(resultado).toEqual({
      desfecho: 'indisponivel',
      codigo: 'refeicao_nao_encontrada',
      mensagem: 'Esta refeição não está no cardápio, então não pode ser avaliada.',
    })
  })

  it('501 (backend sem a BE-13): indisponível com mensagem própria', async () => {
    await entrar()
    const avaliacoes = useAvaliacoesStore()
    const refeicaoId = await idDoAlmoco(avaliacoes)
    simulacao.definirAvaliacoesDisponiveis(false)

    const resultado = await avaliacoes.avaliar({ refeicaoId, campus: 3, data: HOJE, nota: 4 })

    expect(resultado).toEqual({
      desfecho: 'indisponivel',
      codigo: null,
      mensagem: 'As avaliações ainda não estão disponíveis. Tente de novo mais tarde.',
    })
  })

  it('sem sessão (401): desfecho "nao_autenticado"', async () => {
    const avaliacoes = useAvaliacoesStore()
    const refeicaoId = await idDoAlmoco(avaliacoes)

    const resultado = await avaliacoes.avaliar({ refeicaoId, campus: 3, data: HOJE, nota: 4 })

    expect(resultado.desfecho).toBe('nao_autenticado')
  })

  it('sem conexão: erro com a mensagem do apiClient, e nada muda', async () => {
    await entrar()
    const avaliacoes = useAvaliacoesStore()
    const refeicaoId = await idDoAlmoco(avaliacoes)
    vi.spyOn(apiClient, 'post').mockRejectedValueOnce(
      new ApiError(0, { codigo: 'sem_conexao', mensagem: 'Sem internet.' }),
    )

    const resultado = await avaliacoes.avaliar({ refeicaoId, campus: 3, data: HOJE, nota: 4 })

    expect(resultado).toEqual({
      desfecho: 'erro',
      codigo: 'sem_conexao',
      mensagem: 'Sem internet.',
    })
    expect(avaliacoes.minhaAvaliacao(refeicaoId, CONTA_DEMO.apelido)).toBeNull()
  })

  it('limparCache esquece as avaliações próprias e os comentários (login e logout)', async () => {
    await entrar()
    const avaliacoes = useAvaliacoesStore()
    const refeicaoId = await idDoAlmoco(avaliacoes)
    await avaliacoes.avaliar({ refeicaoId, campus: 3, data: HOJE, nota: 4 })

    avaliacoes.limparCache()

    expect(avaliacoes.avaliacoesDaRefeicao(refeicaoId)).toBeNull()
    expect(avaliacoes.minhaAvaliacao(refeicaoId, CONTA_DEMO.apelido)).toBeNull()
  })
})

/** Casos da revisão do PR #223. */
describe('avaliacoesStore: respostas inesperadas e rascunho', () => {
  const HOJE = '2026-09-28'

  async function preparar() {
    await useAuthStore().entrar(CONTA_DEMO.email, CONTA_DEMO.senha)
    const avaliacoes = useAvaliacoesStore()
    const resumo = await avaliacoes.carregarResumoDoDia(3, HOJE)
    const refeicaoId = resumo.find((r) => r.tipo === 'almoco').refeicaoId
    return { avaliacoes, refeicaoId, alvo: { refeicaoId, campus: 3, data: HOJE, nota: 4 } }
  }

  it.each([
    ['sem corpo', null],
    ['sem o bloco avaliacao', { pontos: { total: 0 } }],
  ])(
    '2xx %s: não rejeita, devolve erro "resposta_invalida" e registra no console',
    async (_caso, corpo) => {
      const { avaliacoes, refeicaoId, alvo } = await preparar()
      vi.spyOn(apiClient, 'post').mockResolvedValueOnce(corpo)
      const log = vi.spyOn(console, 'error').mockImplementation(() => {})

      const resultado = await avaliacoes.avaliar(alvo)

      expect(resultado).toEqual({
        desfecho: 'erro',
        codigo: 'resposta_invalida',
        mensagem:
          'Não deu para confirmar se a avaliação foi salva. Recarregue a página para conferir.',
      })
      expect(log).toHaveBeenCalledTimes(1)
      expect(avaliacoes.minhaAvaliacao(refeicaoId, null)).toBeNull()
    },
  )

  it('2xx com a recarga falhando: "criada" com atualizada=false e os dados anteriores mantidos', async () => {
    const { avaliacoes, refeicaoId, alvo } = await preparar()
    const antes = await avaliacoes.carregarAvaliacoesDaRefeicao(refeicaoId)
    const get = vi.spyOn(apiClient, 'get')
    get.mockRejectedValue(new ApiError(0, { codigo: 'sem_conexao', mensagem: 'Sem internet.' }))
    vi.spyOn(console, 'error').mockImplementation(() => {})

    const resultado = await avaliacoes.avaliar(alvo)

    expect(resultado).toMatchObject({ desfecho: 'criada', atualizada: false })
    expect(avaliacoes.avaliacoesDaRefeicao(refeicaoId)).toEqual(antes)
    expect(avaliacoes.situacaoDaRefeicao(refeicaoId)).toBe('carregado')
    expect(avaliacoes.erroDaRefeicao(refeicaoId)).toBeNull()
    expect(avaliacoes.minhaAvaliacao(refeicaoId, null)).toEqual({ nota: 4, comentario: '' })
  })

  it('2xx com a recarga ok: atualizada=true', async () => {
    const { avaliacoes, alvo } = await preparar()

    expect(await avaliacoes.avaliar(alvo)).toMatchObject({ desfecho: 'criada', atualizada: true })
  })

  it('400 dados_invalidos: mensagem genérica e registro no console', async () => {
    const { avaliacoes, alvo } = await preparar()
    vi.spyOn(apiClient, 'post').mockRejectedValueOnce(
      new ApiError(400, { codigo: 'dados_invalidos', mensagem: 'refeicaoId: inteiro.' }),
    )
    const log = vi.spyOn(console, 'error').mockImplementation(() => {})

    const resultado = await avaliacoes.avaliar(alvo)

    expect(resultado).toEqual({
      desfecho: 'erro',
      codigo: 'dados_invalidos',
      mensagem: 'Não foi possível enviar a avaliação. Tente de novo.',
    })
    expect(log).toHaveBeenCalledTimes(1)
  })

  it('código inesperado (403 csrf_invalido): mensagem da API e registro no console', async () => {
    const { avaliacoes, alvo } = await preparar()
    vi.spyOn(apiClient, 'post').mockRejectedValueOnce(
      new ApiError(403, { codigo: 'csrf_invalido', mensagem: 'Recarregue a página.' }),
    )
    const log = vi.spyOn(console, 'error').mockImplementation(() => {})

    const resultado = await avaliacoes.avaliar(alvo)

    expect(resultado).toEqual({
      desfecho: 'erro',
      codigo: 'csrf_invalido',
      mensagem: 'Recarregue a página.',
    })
    expect(log).toHaveBeenCalledTimes(1)
  })

  it('falha de rede ou 5xx no POST não vai para o console (não é erro do app)', async () => {
    const { avaliacoes, alvo } = await preparar()
    vi.spyOn(apiClient, 'post').mockRejectedValueOnce(new ApiError(503, {}))
    const log = vi.spyOn(console, 'error')

    expect((await avaliacoes.avaliar(alvo)).desfecho).toBe('erro')
    expect(log).not.toHaveBeenCalled()
  })

  it('GET dos comentários com 5xx ou 404 vai para o console; o 501 não', async () => {
    const avaliacoes = useAvaliacoesStore()
    const log = vi.spyOn(console, 'error').mockImplementation(() => {})
    vi.spyOn(apiClient, 'get').mockRejectedValueOnce(new ApiError(500, {}))

    await avaliacoes.carregarAvaliacoesDaRefeicao(42)
    await avaliacoes.carregarAvaliacoesDaRefeicao(999)

    expect(log).toHaveBeenCalledTimes(2)
  })

  it('rascunho: guardarRascunho e retomarRascunho (uma vez só), e sobrevive ao limparCache', () => {
    const avaliacoes = useAvaliacoesStore()

    avaliacoes.guardarRascunho(7, { nota: 3, comentario: 'quase' })
    avaliacoes.limparCache()

    expect(avaliacoes.retomarRascunho(7)).toEqual({ nota: 3, comentario: 'quase', editando: false })
    expect(avaliacoes.retomarRascunho(7)).toBeNull()
  })

  it('rascunho guarda se era a edição de uma avaliação existente', () => {
    const avaliacoes = useAvaliacoesStore()

    avaliacoes.guardarRascunho(7, { nota: 2, comentario: 'mudei de ideia', editando: true })

    expect(avaliacoes.retomarRascunho(7)).toEqual({
      nota: 2,
      comentario: 'mudei de ideia',
      editando: true,
    })
  })
})
