import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createMemoryHistory, createRouter } from 'vue-router'
import { instalarGuardas, routes } from '@/router'
import { reiniciarSimulacao } from '@/services/mock/servidor'
import { ApiError, apiClient } from '@/services/apiClient'
import { CONTA_DEMO } from '@/services/mock/banco'
import { useAuthStore } from '@/stores/auth'
import { usePreferenciasStore } from '@/stores/preferencias'
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

const getOriginal = apiClient.get.bind(apiClient)

function trocarGet(trecho, resposta) {
  const anterior = vi.isMockFunction(apiClient.get)
    ? apiClient.get.getMockImplementation()
    : getOriginal
  return vi
    .spyOn(apiClient, 'get')
    .mockImplementation((caminho, opcoes) =>
      caminho.startsWith(trecho) ? resposta(caminho) : anterior(caminho, opcoes),
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

  it('refeição de hoje publicada, mas sem pratos: diz que os pratos não foram cadastrados', async () => {
    trocarGet('/cardapio/', () =>
      Promise.resolve(
        cardapioDaApi({
          categorias: [{ nome: 'Prato principal', semOpcaoCompativel: false, pratos: [] }],
        }),
      ),
    )

    const wrapper = await montarHome(1)
    const cartao = wrapper.get('.cartao-hoje')

    expect(cartao.text()).toContain('Almoço')
    expect(cartao.text()).toContain('Os pratos desta refeição ainda não foram cadastrados.')
    expect(cartao.text()).not.toContain('Não há refeições servidas hoje neste campus.')
  })

  it('erro da API: mostra a mensagem do pedido da refeição', async () => {
    trocarGet('/cardapio/', () =>
      Promise.reject(new ApiError(500, { codigo: 'erro_interno', mensagem: 'Fora do ar.' })),
    )

    const wrapper = await montarHome(1)

    expect(wrapper.get('.cartao-hoje').text()).toContain('Fora do ar.')
  })

  it('resumo do dia fora do formato: o cardápio continua no cartão, sem a nota', async () => {
    trocarGet('/avaliacoes/resumo/?campus=1&data=', () => Promise.resolve({ media: 4.4 }))
    vi.spyOn(console, 'error').mockImplementation(() => {})

    const wrapper = await montarHome(1)
    const cartao = wrapper.get('.cartao-hoje')

    expect(cartao.find('.hoje-linhas').exists()).toBe(true)
    expect(cartao.find('.hoje-nota').exists()).toBe(false)
  })

  it('falha no resumo do dia: o cardápio continua no cartão, sem a nota', async () => {
    trocarGet('/avaliacoes/resumo/?campus=1&data=', () =>
      Promise.reject(new ApiError(500, { codigo: 'erro_interno', mensagem: 'Fora do ar.' })),
    )
    vi.spyOn(console, 'error').mockImplementation(() => {})

    const wrapper = await montarHome(1)
    const cartao = wrapper.get('.cartao-hoje')

    expect(cartao.find('.hoje-linhas').exists()).toBe(true)
    expect(cartao.find('.hoje-nota').exists()).toBe(false)
  })

  it('a nota do cartão é a da refeição de hoje no resumo do dia (GET /api/avaliacoes/resumo/)', async () => {
    const resumo = trocarGet('/avaliacoes/resumo/?campus=1&data=', () =>
      Promise.resolve([
        { refeicaoId: 6, tipo: 'cafe', media: 2.1, quantidade: 3 },
        { refeicaoId: 7, tipo: 'almoco', media: 4.4, quantidade: 5 },
      ]),
    )

    const wrapper = await montarHome(1)

    // O dia do pedido é exatamente hoje, e a nota é a do almoço (a refeição do cartão).
    expect(resumo.mock.calls.map(([caminho]) => caminho)).toContain(
      '/avaliacoes/resumo/?campus=1&data=2026-10-04',
    )
    await vi.waitFor(() => expect(wrapper.get('.hoje-nota span').text()).toBe('4,4'))
  })

  it('com nota no resumo, mas sem serviço hoje: o cartão não mostra nota', async () => {
    trocarGet('/avaliacoes/resumo/?campus=3&data=', () =>
      Promise.resolve([{ refeicaoId: 7, tipo: 'almoco', media: 4.4, quantidade: 5 }]),
    )

    // Gama não serve no domingo.
    const wrapper = await montarHome(3)

    expect(wrapper.get('.cartao-hoje').text()).toContain('Não há refeições servidas hoje')
    expect(wrapper.find('.hoje-nota').exists()).toBe(false)
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
  it('trocar de campus com a tela aberta: o cartão passa a ser o do campus novo', async () => {
    const wrapper = await montarHome(1)
    await vi.waitFor(() => expect(wrapper.find('.hoje-nota').exists()).toBe(true))
    expect(wrapper.get('.cartao-hoje').text()).toContain('Almoço')

    // Gama não serve no domingo.
    usePreferenciasStore().escolherCampus(3)
    await flushPromises()

    const cartao = wrapper.get('.cartao-hoje')
    await vi.waitFor(() =>
      expect(cartao.text()).toContain('Não há refeições servidas hoje neste campus.'),
    )
    expect(cartao.find('.hoje-linhas').exists()).toBe(false)
    expect(cartao.find('.hoje-nota').exists()).toBe(false)
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

describe('HomeView: previsão de pico no cartão Fila (FE-22, #269)', () => {
  const faixa = (inicio, fim, ehPico = true) => ({
    inicio,
    fim,
    nivel: ehPico ? 'longa' : 'curta',
    ehPico,
  })

  const cartaoFila = (wrapper) => wrapper.get('.linha-cartoes a[href="/fila"]')

  function prepararCardapio(troca = {}) {
    trocarGet('/cardapio/', () => Promise.resolve(cardapioDaApi(troca)))
  }

  it('pede a previsão do campus, da refeição de hoje e da data correta', async () => {
    prepararCardapio({ refeicao: 'jantar' })
    const get = trocarGet('/fila/previsao/', () =>
      Promise.resolve({
        status: 'disponivel',
        faixas: [faixa('18:30', '18:45')],
      }),
    )

    const wrapper = await montarHome(1)

    await vi.waitFor(() => {
      expect(get.mock.calls.map(([caminho]) => caminho)).toContain(
        '/fila/previsao/?campus=1&refeicao=jantar&data=2026-10-04',
      )
      expect(cartaoFila(wrapper).text()).toContain('18h30 às 18h45')
    })
  })

  it('mostra todos os picos em caso de empate', async () => {
    prepararCardapio()
    trocarGet('/fila/previsao/', () =>
      Promise.resolve({
        status: 'disponivel',
        faixas: [faixa('11:00', '11:15', false), faixa('11:30', '11:45'), faixa('12:00', '12:15')],
      }),
    )

    const wrapper = await montarHome(1)

    await vi.waitFor(() => {
      const texto = cartaoFila(wrapper).text()
      expect(texto).toContain('11h30 às 11h45')
      expect(texto).toContain('12h às 12h15')
      expect(texto).not.toContain('11h às 11h15')
    })
  })

  it('mostra texto de reserva quando os dados são insuficientes', async () => {
    prepararCardapio()
    trocarGet('/fila/previsao/', () =>
      Promise.resolve({
        status: 'dados_insuficientes',
        faixas: [],
      }),
    )

    const wrapper = await montarHome(1)

    await vi.waitFor(() => {
      expect(cartaoFila(wrapper).text()).toContain('Dados insuficientes')
      expect(cartaoFila(wrapper).text()).not.toContain('Na próxima versão')
    })
  })

  it('mostra texto de reserva quando a API falha', async () => {
    prepararCardapio()
    trocarGet('/fila/previsao/', () =>
      Promise.reject(
        new ApiError(500, {
          codigo: 'erro_interno',
          mensagem: 'Fora do ar.',
        }),
      ),
    )

    const wrapper = await montarHome(1)

    await vi.waitFor(() => {
      expect(cartaoFila(wrapper).text()).toContain('Previsão indisponível')
      expect(cartaoFila(wrapper).text()).not.toContain('Na próxima versão')
    })
  })

  it('sem refeição hoje: não pede previsão de outro dia', async () => {
    prepararCardapio({ data: '2026-10-05' })
    const get = vi.spyOn(apiClient, 'get')

    const wrapper = await montarHome(1)

    expect(cartaoFila(wrapper).text()).toContain('Sem refeição hoje')
    expect(get.mock.calls.some(([caminho]) => caminho.startsWith('/fila/previsao/'))).toBe(false)
  })

  it('atualiza a previsão quando o campus muda', async () => {
    prepararCardapio()
    trocarGet('/fila/previsao/', (caminho) =>
      Promise.resolve({
        status: 'disponivel',
        faixas: caminho.includes('campus=3&')
          ? [faixa('12:30', '12:45')]
          : [faixa('11:30', '11:45')],
      }),
    )

    const wrapper = await montarHome(1)

    await vi.waitFor(() => expect(cartaoFila(wrapper).text()).toContain('11h30 às 11h45'))

    usePreferenciasStore().escolherCampus(3)

    await vi.waitFor(() => {
      expect(cartaoFila(wrapper).text()).toContain('12h30 às 12h45')
      expect(cartaoFila(wrapper).text()).not.toContain('11h30 às 11h45')
    })
  })

  it('continua levando à rota fila', async () => {
    const wrapper = await montarHome(1)

    expect(cartaoFila(wrapper).attributes('href')).toBe('/fila')
    expect(router.resolve(cartaoFila(wrapper).attributes('href')).name).toBe('fila')
  })
})
