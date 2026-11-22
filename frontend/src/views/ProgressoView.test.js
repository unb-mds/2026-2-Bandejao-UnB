import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { enableAutoUnmount, flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createMemoryHistory, createRouter } from 'vue-router'
import { instalarGuardas, routes } from '@/router'
import { useAuthStore } from '@/stores/auth'
import { useGamificacaoStore } from '@/stores/gamificacao'
import { ApiError, apiClient } from '@/services/apiClient'
import { CONTA_DEMO } from '@/services/mock/banco'
import { banco, reiniciarSimulacao, simulacao } from '@/services/mock/servidor'
import App from '@/App.vue'

const SEGUNDA = new Date(2026, 8, 28, 12, 0)

let pinia

enableAutoUnmount(afterEach)

async function montarEm(caminho = '/progresso') {
  const router = createRouter({ history: createMemoryHistory(), routes })
  instalarGuardas(router)
  router.push(caminho)
  await router.isReady()
  const wrapper = mount(App, { global: { plugins: [pinia, router] }, attachTo: document.body })
  await flushPromises()
  await vi.waitFor(() => expect(wrapper.find('h1').text()).toBe('Meu progresso'))
  await flushPromises()
  return { wrapper, router }
}

async function entrar() {
  await useAuthStore().entrar(CONTA_DEMO.email, CONTA_DEMO.senha)
}

function darCheckins(quantidade, campus = 1) {
  for (let i = 0; i < quantidade; i++) {
    banco.estado.checkins.push({
      id: 3000 + i,
      usuarioId: 1,
      campus,
      tipoRefeicao: 'almoco',
      data: '2026-09-28',
    })
  }
}

const interruptor = (wrapper) => wrapper.get('[data-teste="adesao-interruptor"]')

function adiado() {
  let resolver
  const promessa = new Promise((resolve) => {
    resolver = resolve
  })
  return { promessa, resolver }
}

function trocarGet(caminhoAlvo, resposta) {
  const getOriginal = apiClient.get.bind(apiClient)
  return vi
    .spyOn(apiClient, 'get')
    .mockImplementation((caminho, opcoes) =>
      caminho === caminhoAlvo ? resposta() : getOriginal(caminho, opcoes),
    )
}

async function montarComInterruptor() {
  const montado = await montarEm()
  await vi.waitFor(() =>
    expect(montado.wrapper.find('[data-teste="adesao-interruptor"]').exists()).toBe(true),
  )
  return montado
}

beforeEach(() => {
  vi.useFakeTimers({ toFake: ['Date'] })
  vi.setSystemTime(SEGUNDA)
  localStorage.clear()
  localStorage.setItem(
    'bandejao:preferencias',
    JSON.stringify({ campusId: 1, avisoLocalizacaoAdiado: true }),
  )
  reiniciarSimulacao()
  pinia = createPinia()
  setActivePinia(pinia)
})

afterEach(() => {
  vi.useRealTimers()
  vi.restoreAllMocks()
  document.body.innerHTML = ''
})

describe('ProgressoView: usuário logado (FE-12, RF26.2)', () => {
  it('mostra a patente, os pontos totais e quanto falta para a próxima', async () => {
    await entrar()
    darCheckins(16)

    const { wrapper } = await montarEm()

    await vi.waitFor(() =>
      expect(wrapper.find('[data-teste="progresso-patente"]').exists()).toBe(true),
    )
    expect(wrapper.get('#titulo-patente').text()).toBe('Rato de RU')
    expect(wrapper.get('[data-teste="progresso-pontos"]').text()).toBe('160 pontos')
    expect(wrapper.get('[data-teste="progresso-falta"]').text()).toBe(
      'Faltam 290 pontos para Veterano',
    )
    expect(wrapper.get('[role="progressbar"]').attributes('aria-valuenow')).toBe('3')
  })

  it('na última patente: "Você chegou à patente máxima", sem barra', async () => {
    await entrar()
    darCheckins(150)

    const { wrapper } = await montarEm()

    await vi.waitFor(() =>
      expect(wrapper.find('[data-teste="progresso-falta"]').exists()).toBe(true),
    )
    expect(wrapper.get('#titulo-patente').text()).toBe('Lenda do RU')
    expect(wrapper.get('[data-teste="progresso-falta"]').text()).toBe(
      'Você chegou à patente máxima.',
    )
    expect(wrapper.find('[role="progressbar"]').exists()).toBe(false)
  })

  it('o aviso do ranking explica o que fica público, sem citar a Bandeja de Ouro', async () => {
    await entrar()

    const { wrapper } = await montarEm()

    await vi.waitFor(() =>
      expect(wrapper.find('[data-teste="adesao-interruptor"]').exists()).toBe(true),
    )
    const aviso = wrapper.get('[data-teste="adesao-aviso"]').text()
    expect(aviso).toContain('apelido')
    expect(aviso).toContain('patente')
    expect(aviso).toContain('ranking do semestre')
    expect(aviso).not.toContain('comentários')
    expect(aviso).not.toMatch(/bandeja/i)
    expect(wrapper.get('#titulo-adesao').text()).toBe('Participar do ranking')
    expect(interruptor(wrapper).attributes('aria-checked')).toBe('false')
    expect(interruptor(wrapper).attributes('role')).toBe('switch')
  })

  it('501 (backend sem a regra): "Progresso ainda não disponível", sem o interruptor', async () => {
    await entrar()
    simulacao.definirGamificacaoDisponivel(false)

    const { wrapper } = await montarEm()

    await vi.waitFor(() =>
      expect(wrapper.find('[data-teste="progresso-indisponivel"]').exists()).toBe(true),
    )
    expect(wrapper.find('[data-teste="adesao-interruptor"]').exists()).toBe(false)
    expect(wrapper.find('[data-teste="botao-sair"]').exists()).toBe(true)
  })

  it('falha ao carregar: mostra o erro e "Tentar novamente" carrega de novo', async () => {
    await entrar()
    const getOriginal = apiClient.get.bind(apiClient)
    let falhar = true
    vi.spyOn(apiClient, 'get').mockImplementation((caminho, opcoes) => {
      if (caminho === '/gamificacao/progresso/' && falhar) {
        falhar = false
        return Promise.reject(
          new ApiError(0, { codigo: 'sem_conexao', mensagem: 'Sem internet.' }),
        )
      }
      return getOriginal(caminho, opcoes)
    })

    const { wrapper } = await montarEm()
    await vi.waitFor(() =>
      expect(wrapper.find('[data-teste="progresso-erro"]').exists()).toBe(true),
    )
    expect(wrapper.text()).toContain('Sem internet.')

    await wrapper.get('[data-teste="progresso-erro"] button').trigger('click')
    await flushPromises()

    expect(wrapper.find('[data-teste="progresso-patente"]').exists()).toBe(true)
  })

  it('"Sair da conta" encerra a sessão e sai da tela', async () => {
    await entrar()
    const del = vi.spyOn(apiClient, 'delete')
    const { wrapper, router } = await montarEm()
    await vi.waitFor(() =>
      expect(wrapper.find('[data-teste="botao-sair"]').exists()).toBe(true),
    )

    await wrapper.get('[data-teste="botao-sair"]').trigger('click')
    await flushPromises()

    expect(del).toHaveBeenCalledWith('/sessao/')
    expect(useAuthStore().estaAutenticado).toBe(false)
    expect(useGamificacaoStore().progresso.dados).toBeNull()
    await vi.waitFor(() => expect(router.currentRoute.value.name).not.toBe('progresso'))
  })
})

describe('ProgressoView: barra até a próxima patente (FE-12)', () => {
  it.each([
    [
      '0 pontos',
      { pontosTotais: 0, faltaParaProxima: 150 },
      '0',
      'Faltam 150 pontos para Rato de RU',
    ],
    [
      'exatamente 150 pontos',
      { patente: 'RATO_DE_RU', pontosTotais: 150, faltaParaProxima: 300 },
      '0',
      'Faltam 300 pontos para Veterano',
    ],
    [
      '149 pontos',
      { pontosTotais: 149, faltaParaProxima: 1 },
      '99',
      'Faltam 1 ponto para Rato de RU',
    ],
    [
      'falta maior que a faixa',
      { pontosTotais: 0, faltaParaProxima: 400 },
      '0',
      'Faltam 400 pontos para Rato de RU',
    ],
  ])('%s', async (_caso, troca, valor, texto) => {
    await entrar()
    trocarGet('/gamificacao/progresso/', () =>
      Promise.resolve({
        patente: 'CALOURO_DE_BANDEJA',
        sequencia: 0,
        diasNaSemana: 0,
        minimoDias: 3,
        participaRanking: false,
        ...troca,
      }),
    )

    const { wrapper } = await montarComInterruptor()

    expect(wrapper.get('[role="progressbar"]').attributes('aria-valuenow')).toBe(valor)
    expect(wrapper.get('[data-teste="progresso-falta"]').text()).toBe(texto)
  })
})

describe('ProgressoView: sessão expirada (FE-12)', () => {
  it('401 ao pedir o progresso: aparece o convite, sem o cartão de erro', async () => {
    await entrar()
    trocarGet('/gamificacao/progresso/', () => {
      useAuthStore().limpar()
      return Promise.reject(new ApiError(401, { codigo: 'nao_autenticado' }))
    })

    const { wrapper } = await montarEm()

    await vi.waitFor(() => expect(wrapper.text()).toContain('Entre para ver seu progresso'))
    expect(wrapper.find('[data-teste="progresso-erro"]').exists()).toBe(false)
  })

  it('401 ao mudar a adesão: depois de entrar de novo, o erro antigo não aparece', async () => {
    await entrar()
    const { wrapper } = await montarComInterruptor()
    vi.spyOn(apiClient, 'post').mockImplementationOnce(() => {
      useAuthStore().limpar()
      return Promise.reject(new ApiError(401, { codigo: 'nao_autenticado' }))
    })

    await interruptor(wrapper).trigger('click')
    await flushPromises()
    await entrar()
    await vi.waitFor(() =>
      expect(wrapper.find('[data-teste="adesao-interruptor"]').exists()).toBe(true),
    )

    expect(wrapper.find('[data-teste="adesao-erro"]').exists()).toBe(false)
  })
})

describe('ProgressoView: sair da conta (FE-12, RF03.3)', () => {
  it('o servidor não confirma: avisa, sem sair da tela', async () => {
    await entrar()
    const { wrapper, router } = await montarEm()
    await vi.waitFor(() =>
      expect(wrapper.find('[data-teste="botao-sair"]').exists()).toBe(true),
    )
    vi.spyOn(apiClient, 'delete').mockRejectedValueOnce(
      new ApiError(500, { codigo: 'erro_interno', mensagem: 'Erro no servidor.' }),
    )

    await wrapper.get('[data-teste="botao-sair"]').trigger('click')
    await flushPromises()

    const aviso = wrapper.get('[data-teste="sair-aviso"]')
    expect(aviso.attributes('role')).toBe('alert')
    expect(aviso.text()).toContain('o servidor não confirmou')
    expect(router.currentRoute.value.name).toBe('progresso')
    expect(useAuthStore().estaAutenticado).toBe(false)
  })

  it('enquanto sai, o botão fica desativado e um segundo clique não pede de novo', async () => {
    await entrar()
    const { wrapper } = await montarEm()
    await vi.waitFor(() =>
      expect(wrapper.find('[data-teste="botao-sair"]').exists()).toBe(true),
    )
    const del = vi.spyOn(apiClient, 'delete').mockReturnValue(new Promise(() => {}))

    await wrapper.get('[data-teste="botao-sair"]').trigger('click')
    await wrapper.get('[data-teste="botao-sair"]').trigger('click')

    expect(wrapper.get('[data-teste="botao-sair"]').attributes('disabled')).toBeDefined()
    expect(del).toHaveBeenCalledTimes(1)
  })
})

describe('ProgressoView: visitante (FE-12, RF05)', () => {
  it('mostra o ConviteLogin, sem pedir o progresso e sem o botão de sair', async () => {
    const get = vi.spyOn(apiClient, 'get')

    const { wrapper, router } = await montarEm()

    expect(router.currentRoute.value.name).toBe('progresso')
    expect(wrapper.text()).toContain('Entre para ver seu progresso')
    expect(wrapper.find('a[href^="/login"]').exists()).toBe(true)
    expect(get.mock.calls.map(([caminho]) => caminho)).not.toContain('/gamificacao/progresso/')
    expect(wrapper.find('[data-teste="adesao-interruptor"]').exists()).toBe(false)
    expect(wrapper.find('[data-teste="botao-sair"]').exists()).toBe(false)
  })
})

describe('ProgressoView: mudança de adesão (FE-12, RF27.1)', () => {
  it('ligar o interruptor: POST, recarrega o progresso e o ranking e o interruptor fica ligado', async () => {
    await entrar()
    darCheckins(2)
    const gamificacao = useGamificacaoStore()
    await gamificacao.carregarRanking(1)
    const { wrapper } = await montarEm()
    await vi.waitFor(() =>
      expect(wrapper.find('[data-teste="adesao-interruptor"]').exists()).toBe(true),
    )
    const post = vi.spyOn(apiClient, 'post')
    const get = vi.spyOn(apiClient, 'get')

    await interruptor(wrapper).trigger('click')
    await flushPromises()

    expect(post).toHaveBeenCalledWith('/gamificacao/adesao/')
    expect(get.mock.calls.map(([caminho]) => caminho).sort()).toEqual([
      '/gamificacao/progresso/',
      '/ranking/1/',
    ])
    expect(interruptor(wrapper).attributes('aria-checked')).toBe('true')
    expect(gamificacao.rankingDe(1).dados.linhas.map((l) => l.apelido)).toContain(
      CONTA_DEMO.apelido,
    )
  })

  it('desligar: DELETE e o interruptor volta a desligado', async () => {
    await entrar()
    await useGamificacaoStore().alterarAdesao(true)
    const { wrapper } = await montarEm()
    await vi.waitFor(() =>
      expect(interruptor(wrapper).attributes('aria-checked')).toBe('true'),
    )
    const del = vi.spyOn(apiClient, 'delete')

    await interruptor(wrapper).trigger('click')
    await flushPromises()

    expect(del).toHaveBeenCalledWith('/gamificacao/adesao/')
    expect(interruptor(wrapper).attributes('aria-checked')).toBe('false')
  })

  it('confirmada a adesão, o interruptor continua na tela enquanto o progresso recarrega', async () => {
    await entrar()
    const { wrapper } = await montarComInterruptor()
    const recarga = adiado()
    trocarGet('/gamificacao/progresso/', () => recarga.promessa)

    await interruptor(wrapper).trigger('click')
    await flushPromises()

    expect(interruptor(wrapper).attributes('aria-checked')).toBe('true')
    expect(interruptor(wrapper).attributes('disabled')).toBeDefined()
    expect(wrapper.text()).not.toContain('Carregando progresso…')
  })

  it('confirmada a adesão e o recarregamento falha: o interruptor fica ligado, sem erro', async () => {
    await entrar()
    const { wrapper } = await montarComInterruptor()
    trocarGet('/gamificacao/progresso/', () =>
      Promise.reject(
        new ApiError(500, { codigo: 'erro_interno', mensagem: 'Erro no servidor.' }),
      ),
    )

    await interruptor(wrapper).trigger('click')
    await flushPromises()

    expect(interruptor(wrapper).attributes('aria-checked')).toBe('true')
    expect(wrapper.find('[data-teste="adesao-erro"]').exists()).toBe(false)
    expect(wrapper.find('[data-teste="progresso-erro"]').exists()).toBe(false)
  })

  it('falha ao desligar: continua ligado com o erro, e a nova tentativa apaga o erro', async () => {
    await entrar()
    await useGamificacaoStore().alterarAdesao(true)
    const { wrapper } = await montarComInterruptor()
    vi.spyOn(apiClient, 'delete').mockRejectedValueOnce(
      new ApiError(0, { codigo: 'sem_conexao', mensagem: 'Sem internet.' }),
    )

    await interruptor(wrapper).trigger('click')
    await flushPromises()
    expect(interruptor(wrapper).attributes('aria-checked')).toBe('true')
    expect(wrapper.get('[data-teste="adesao-erro"]').text()).toBe('Sem internet.')

    await interruptor(wrapper).trigger('click')
    await flushPromises()
    expect(interruptor(wrapper).attributes('aria-checked')).toBe('false')
    expect(wrapper.find('[data-teste="adesao-erro"]').exists()).toBe(false)
  })

  it('enquanto salva, o interruptor fica desativado', async () => {
    await entrar()
    const { wrapper } = await montarEm()
    await vi.waitFor(() =>
      expect(wrapper.find('[data-teste="adesao-interruptor"]').exists()).toBe(true),
    )
    vi.spyOn(apiClient, 'post').mockReturnValue(new Promise(() => {}))

    await interruptor(wrapper).trigger('click')

    expect(interruptor(wrapper).attributes('disabled')).toBeDefined()
    expect(wrapper.text()).toContain('Salvando…')
  })

  it('falha ao mudar: mostra o erro e o interruptor continua como estava', async () => {
    await entrar()
    const { wrapper } = await montarEm()
    await vi.waitFor(() =>
      expect(wrapper.find('[data-teste="adesao-interruptor"]').exists()).toBe(true),
    )
    vi.spyOn(apiClient, 'post').mockRejectedValueOnce(
      new ApiError(0, { codigo: 'sem_conexao', mensagem: 'Sem internet.' }),
    )

    await interruptor(wrapper).trigger('click')
    await flushPromises()

    expect(wrapper.get('[data-teste="adesao-erro"]').text()).toBe('Sem internet.')
    expect(interruptor(wrapper).attributes('aria-checked')).toBe('false')
  })
})
