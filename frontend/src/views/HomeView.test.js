import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createMemoryHistory, createRouter } from 'vue-router'
import { instalarGuardas, routes } from '@/router'
import { reiniciarSimulacao } from '@/services/mock/servidor'
import { ApiError, apiClient } from '@/services/apiClient'
import { CONTA_DEMO } from '@/services/mock/banco'
import { useAuthStore } from '@/stores/auth'
import App from '@/App.vue'

const DOMINGO_MEIO_DIA = new Date(2026, 9, 4, 12, 0)

let router

async function montarHome(campusId, { logado = false } = {}) {
  localStorage.setItem(
    'bandejao:preferencias',
    JSON.stringify({ campusId, avisoLocalizacaoAdiado: true }),
  )
  const pinia = createPinia()
  setActivePinia(pinia)
  if (logado) await useAuthStore().entrar(CONTA_DEMO.email, CONTA_DEMO.senha)
  router = createRouter({ history: createMemoryHistory(), routes })
  instalarGuardas(router)
  router.push('/inicio')
  await router.isReady()
  const wrapper = mount(App, { global: { plugins: [pinia, router] }, attachTo: document.body })
  await flushPromises()
  await vi.waitFor(() =>
    expect(wrapper.find('.cartao-hoje').text()).not.toContain('Carregando cardápio'),
  )
  return wrapper
}

beforeEach(() => {
  vi.useFakeTimers({ toFake: ['Date'] })
  vi.setSystemTime(DOMINGO_MEIO_DIA)
  localStorage.clear()
  reiniciarSimulacao()
})

afterEach(() => {
  vi.useRealTimers()
  vi.restoreAllMocks()
  document.body.innerHTML = ''
})

function trocarGet(trecho, resposta) {
  const getOriginal = apiClient.get.bind(apiClient)
  return vi
    .spyOn(apiClient, 'get')
    .mockImplementation((caminho, opcoes) =>
      caminho.startsWith(trecho) ? resposta(caminho) : getOriginal(caminho, opcoes),
    )
}

const cardapioDaApi = (troca = {}) => ({
  campus: 1,
  data: '2026-10-04',
  refeicao: 'almoco',
  refeicaoEncerrada: false,
  status: 'publicado',
  avisoSujeitoAAlteracao: 'Cardápio sujeito a alteração.',
  alergenosIndisponivel: false,
  filtroMarcadorDesativado: false,
  semServico: false,
  categorias: [],
  ...troca,
})

const prato = (descricao) => ({ descricao, marcadores: [], contemMarcadorSelecionado: false })

describe('HomeView: cartão "Cardápio de hoje" pelo GET /api/cardapio/ (#251)', () => {
  it('pede a refeição de hoje com campus e dia, e nunca a rota da semana do MVP', async () => {
    const get = vi.spyOn(apiClient, 'get')

    await montarHome(1)

    const caminhos = get.mock.calls.map(([caminho]) => caminho)
    expect(caminhos).toContain('/cardapio/?campus=1&dia=2026-10-04')
    expect(caminhos.some((caminho) => /^\/cardapio\/\d+\/$/.test(caminho))).toBe(false)
  })

  it('mostra o resumo da refeição que o backend resolveu, no formato da API', async () => {
    trocarGet('/cardapio/', () =>
      Promise.resolve(
        cardapioDaApi({
          refeicao: 'jantar',
          categorias: [
            { nome: 'Prato principal', semOpcaoCompativel: false, pratos: [prato('Frango')] },
            { nome: 'Acompanhamentos', semOpcaoCompativel: false, pratos: [prato('Arroz')] },
            { nome: 'Salada', semOpcaoCompativel: false, pratos: [prato('Alface')] },
          ],
        }),
      ),
    )

    const wrapper = await montarHome(1)
    const cartao = wrapper.get('.cartao-hoje')

    expect(cartao.text()).toContain('Jantar')
    expect(cartao.findAll('.hoje-rotulo').map((rotulo) => rotulo.text())).toEqual([
      'Prato principal',
      'Acompanham.',
      'Salada',
    ])
    expect(cartao.findAll('.hoje-texto').map((texto) => texto.text())).toEqual([
      'Frango',
      'Arroz',
      'Alface',
    ])
  })

  it('semana não publicada: "Cardápio ainda não publicado."', async () => {
    const wrapper = await montarHome(5)

    expect(wrapper.get('.cartao-hoje').text()).toContain('Cardápio ainda não publicado.')
  })

  it('o backend devolve outro dia (o próximo com serviço): não há refeições hoje', async () => {
    trocarGet('/cardapio/', () =>
      Promise.resolve(
        cardapioDaApi({
          data: '2026-10-05',
          categorias: [
            { nome: 'Prato principal', semOpcaoCompativel: false, pratos: [prato('Frango')] },
          ],
        }),
      ),
    )

    const wrapper = await montarHome(1)
    const cartao = wrapper.get('.cartao-hoje')

    expect(cartao.text()).toContain('Não há refeições servidas hoje neste campus.')
    expect(cartao.find('.hoje-linhas').exists()).toBe(false)
    expect(cartao.find('.horario').exists()).toBe(false)
  })

  it('sem serviço hoje e a semana do próximo dia sem PDF: "sem refeições hoje", não "não publicado"', async () => {
    // O backend pula para o próximo dia com serviço, e a semana dele ainda não foi publicada.
    trocarGet('/cardapio/', () =>
      Promise.resolve(cardapioDaApi({ data: '2026-10-05', status: 'nao_publicado' })),
    )

    const wrapper = await montarHome(1)
    const cartao = wrapper.get('.cartao-hoje')

    expect(cartao.text()).toContain('Não há refeições servidas hoje neste campus.')
    expect(cartao.text()).not.toContain('Cardápio ainda não publicado.')
  })

  it('erro da API: mostra a mensagem do pedido da refeição', async () => {
    trocarGet('/cardapio/', () =>
      Promise.reject(new ApiError(500, { codigo: 'erro_interno', mensagem: 'Fora do ar.' })),
    )

    const wrapper = await montarHome(1)

    expect(wrapper.get('.cartao-hoje').text()).toContain('Fora do ar.')
  })

  it('a nota do cartão vem do resumo do dia (GET /api/avaliacoes/resumo/)', async () => {
    trocarGet('/avaliacoes/resumo/?campus=1&data=', () =>
      Promise.resolve([{ refeicaoId: 7, tipo: 'almoco', media: 4.4, quantidade: 5 }]),
    )

    const wrapper = await montarHome(1)

    await vi.waitFor(() => expect(wrapper.get('.hoje-nota span').text()).toBe('4,4'))
  })
})

describe('HomeView: cartão "Cardápio de hoje" no domingo (#229)', () => {
  it('campus que serve no domingo (Darcy): mostra a refeição de domingo', async () => {
    const wrapper = await montarHome(1)
    const cartao = wrapper.get('.cartao-hoje')

    expect(cartao.find('.hoje-linhas').exists()).toBe(true)
    expect(cartao.text()).toContain('Almoço')
    expect(cartao.text()).not.toContain('Não há refeições servidas hoje')
  })

  it('campus sem serviço no domingo (Gama): mostra que não há refeições hoje', async () => {
    const wrapper = await montarHome(3)
    const cartao = wrapper.get('.cartao-hoje')

    expect(cartao.text()).toContain('Não há refeições servidas hoje neste campus.')
    expect(cartao.find('.hoje-linhas').exists()).toBe(false)
  })
})

describe('HomeView: atalho para o ranking (FE-13)', () => {
  it('o menu do perfil tem "Ranking do campus", levando ao ranking do campus lembrado', async () => {
    const wrapper = await montarHome(3)

    await wrapper.get('.avatar').trigger('click')
    const link = wrapper.findAll('.menu-item').find((i) => i.text().includes('Ranking do campus'))

    expect(link.attributes('href')).toBe('/ranking/3')
  })
})

describe('HomeView: "Sair da conta" no menu (RF03.3)', () => {
  async function clicarEmSair(wrapper) {
    await wrapper.get('.avatar').trigger('click')
    const itens = wrapper.findAll('[role="menuitem"]')
    await itens.find((item) => item.text() === 'Sair da conta').trigger('click')
    await flushPromises()
  }

  it('servidor confirma: sai da conta e continua na Início, sem aviso', async () => {
    const wrapper = await montarHome(1, { logado: true })
    const del = vi.spyOn(apiClient, 'delete')

    await clicarEmSair(wrapper)

    expect(del).toHaveBeenCalledWith('/sessao/')
    expect(useAuthStore().estaAutenticado).toBe(false)
    expect(router.currentRoute.value.name).toBe('inicio')
    expect(wrapper.find('[data-teste="sair-aviso"]').exists()).toBe(false)
    await wrapper.get('.avatar').trigger('click')
    expect(wrapper.text()).toContain('Entrar na conta')
  })

  it('o servidor não confirma: avisa na Início, com role="alert"', async () => {
    const wrapper = await montarHome(1, { logado: true })
    vi.spyOn(apiClient, 'delete').mockRejectedValueOnce(
      new ApiError(500, { codigo: 'erro_interno', mensagem: 'Erro no servidor.' }),
    )
    vi.spyOn(console, 'error').mockImplementation(() => {})

    await clicarEmSair(wrapper)

    const aviso = wrapper.get('[data-teste="sair-aviso"]')
    expect(aviso.attributes('role')).toBe('alert')
    expect(aviso.text()).toContain('o servidor não confirmou')
    expect(useAuthStore().estaAutenticado).toBe(false)
    expect(router.currentRoute.value.name).toBe('inicio')
  })
})
