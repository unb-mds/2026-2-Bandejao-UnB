import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { enableAutoUnmount, flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createMemoryHistory, createRouter } from 'vue-router'
import { routes } from '@/router'
import { useAuthStore } from '@/stores/auth'
import { usePreferenciasStore } from '@/stores/preferencias'
import { CONTA_DEMO } from '@/services/mock/banco'
import { reiniciarSimulacao } from '@/services/mock/servidor'
import { ApiError, apiClient } from '@/services/apiClient'
import { EMAIL_CONTATO } from '@/constants/contato'
import App from '@/App.vue'
import BarraLateral from './BarraLateral.vue'

async function montar(componente, caminho = '/campus/1', { logado = false, campus = 1 } = {}) {
  const pinia = createPinia()
  setActivePinia(pinia)
  if (campus) usePreferenciasStore().escolherCampus(campus)
  if (logado) await useAuthStore().entrar(CONTA_DEMO.email, CONTA_DEMO.senha)
  const router = createRouter({ history: createMemoryHistory(), routes })
  router.push(caminho)
  await router.isReady()
  const wrapper = mount(componente, {
    global: { plugins: [pinia, router] },
    attachTo: document.body,
  })
  await flushPromises()
  return { wrapper, router }
}

beforeEach(() => {
  localStorage.clear()
  reiniciarSimulacao()
})

enableAutoUnmount(afterEach)

afterEach(() => {
  vi.restoreAllMocks()
  document.body.innerHTML = ''
})

describe('BarraLateral (FE-23, desktop)', () => {
  it('leva aos mesmos destinos da navegação do topo, com "Fila do RU" por extenso', async () => {
    const { wrapper } = await montar(BarraLateral)

    const links = wrapper
      .get('nav')
      .findAll('a')
      .map((link) => [link.text(), link.attributes('href')])
    expect(links).toEqual([
      ['Início', '/inicio'],
      ['Cardápio', '/cardapio'],
      ['Fila do RU', '/fila'],
      ['Avaliações', '/avaliacoes'],
      ['Ranking', '/ranking'],
    ])
  })

  it('o Ranking (RF27) é alcançado por clique, no ranking do campus lembrado', async () => {
    const { wrapper, router } = await montar(BarraLateral, '/inicio')

    await wrapper
      .get('nav')
      .findAll('a')
      .find((link) => link.text() === 'Ranking')
      .trigger('click')
    await vi.waitFor(() => expect(router.currentRoute.value.path).toBe('/ranking/1'))
    expect(
      wrapper
        .findAll('nav a')
        .filter((link) => link.attributes('aria-current'))
        .map((l) => l.text()),
    ).toEqual(['Ranking'])
  })

  it('marca a página atual: na tela do campus, o Cardápio', async () => {
    const { wrapper } = await montar(BarraLateral, '/campus/1')

    const atual = wrapper.findAll('nav a').filter((link) => link.attributes('aria-current'))
    expect(atual.map((link) => link.text())).toEqual(['Cardápio'])
  })

  it('mostra o campus lembrado, com o atalho para trocar', async () => {
    const { wrapper } = await montar(BarraLateral)

    const campus = wrapper.get('.atalho--campus')
    await expect.poll(() => campus.text()).toContain('Darcy Ribeiro')
    expect(campus.attributes('href')).toBe('/campus')
  })

  it('sem login: "Visitante" leva ao login e não há "Sair da conta"', async () => {
    const { wrapper } = await montar(BarraLateral)

    const conta = wrapper.get('.atalho--conta')
    expect(conta.text()).toContain('Visitante')
    expect(conta.text()).toContain('Acessar conta')
    expect(conta.attributes('href')).toBe('/login')
    expect(wrapper.text()).not.toContain('Sair da conta')
  })

  it('com login: o apelido leva a "Meu progresso"', async () => {
    const { wrapper } = await montar(BarraLateral, '/campus/1', { logado: true })

    const conta = wrapper.get('.atalho--conta')
    expect(conta.text()).toContain(CONTA_DEMO.apelido)
    expect(conta.attributes('href')).toBe('/progresso')
  })

  it('"Sair da conta" com o servidor confirmando: sai e volta à raiz, como o BotaoSair (RF03.3)', async () => {
    const { wrapper, router } = await montar(BarraLateral, '/progresso', { logado: true })

    await wrapper.get('.sair').trigger('click')

    await vi.waitFor(() => expect(router.currentRoute.value.path).toBe('/campus/1'))
    expect(useAuthStore().estaAutenticado).toBe(false)
    expect(wrapper.find('[data-teste="sair-aviso-lateral"]').exists()).toBe(false)
  })

  it('"Sair da conta" sem confirmação do servidor: avisa na lateral, com role="alert" (RF03.3)', async () => {
    const { wrapper, router } = await montar(BarraLateral, '/progresso', { logado: true })
    vi.spyOn(apiClient, 'delete').mockRejectedValueOnce(
      new ApiError(500, { codigo: 'erro_interno', mensagem: 'Erro no servidor.' }),
    )
    vi.spyOn(console, 'error').mockImplementation(() => {})

    await wrapper.get('.sair').trigger('click')

    await vi.waitFor(() =>
      expect(wrapper.find('[data-teste="sair-aviso-lateral"]').exists()).toBe(true),
    )
    const aviso = wrapper.get('[data-teste="sair-aviso-lateral"]')
    expect(aviso.attributes('role')).toBe('alert')
    expect(aviso.text()).toContain('o servidor não confirmou')
    expect(router.currentRoute.value.path).toBe('/progresso')
  })

  it('sem campus escolhido: o atalho convida a escolher', async () => {
    const { wrapper } = await montar(BarraLateral, '/avaliacoes', { campus: null })

    expect(wrapper.get('.atalho--campus').text()).toContain('Escolher campus')
  })

  it('com campus escolhido e falha na busca dos campi: texto neutro, não "Escolher campus"', async () => {
    const getOriginal = apiClient.get.bind(apiClient)
    vi.spyOn(apiClient, 'get').mockImplementation((caminho, opcoes) =>
      caminho.startsWith('/campi/')
        ? Promise.reject(new ApiError(0, { codigo: 'sem_conexao', mensagem: 'Sem internet.' }))
        : getOriginal(caminho, opcoes),
    )

    const { wrapper } = await montar(BarraLateral)

    const campus = wrapper.get('.atalho--campus')
    expect(campus.text()).not.toContain('Escolher campus')
    expect(campus.text()).toContain('Trocar campus')
  })

  it('tem o canal de contato (RNF08)', async () => {
    const { wrapper } = await montar(BarraLateral)

    expect(wrapper.get('.contato').text()).toContain(EMAIL_CONTATO)
  })
})

describe('App: onde a lateral e o lado verde das telas de conta aparecem', () => {
  it.each(['/campus/1', '/inicio', '/avaliacoes', '/progresso'])(
    '%s: com a lateral',
    async (caminho) => {
      const { wrapper } = await montar(App, caminho)
      expect(wrapper.find('.barra-lateral').exists()).toBe(true)
      expect(wrapper.find('.aside-conta').exists()).toBe(false)
    },
  )

  it.each(['/boas-vindas', '/campus'])(
    '%s, sem campus escolhido: tela de entrada, sem a lateral',
    async (caminho) => {
      const { wrapper } = await montar(App, caminho, { campus: null })
      expect(wrapper.find('.barra-lateral').exists()).toBe(false)
      expect(wrapper.find('.aside-conta').exists()).toBe(false)
    },
  )

  it('/campus com campus já escolhido (vindo de "Trocar"): com a lateral, para ter saída', async () => {
    const { wrapper } = await montar(App, '/campus')
    expect(wrapper.find('.barra-lateral').exists()).toBe(true)
  })

  it.each(['/login', '/cadastro', '/recuperar-senha', '/confirmar-email', '/redefinir-senha'])(
    '%s: tela de conta, com o lado verde e sem a lateral',
    async (caminho) => {
      const { wrapper } = await montar(App, caminho)
      expect(wrapper.find('.barra-lateral').exists()).toBe(false)
      expect(wrapper.find('.aside-conta').exists()).toBe(true)
    },
  )
})

describe('AsideConta: o passo marcado', () => {
  const passos = (wrapper) =>
    wrapper.findAll('.aside-conta .passos span').map((s) => s.classes('passo--ativo'))

  it('no login, só o primeiro passo', async () => {
    const { wrapper } = await montar(App, '/login')
    expect(passos(wrapper)).toEqual([true, false, false])
  })

  it('no cadastro, os dois primeiros', async () => {
    const { wrapper } = await montar(App, '/cadastro')
    expect(passos(wrapper)).toEqual([true, true, false])
  })
})
