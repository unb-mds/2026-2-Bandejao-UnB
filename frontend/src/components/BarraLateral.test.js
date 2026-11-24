import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import { enableAutoUnmount, flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createMemoryHistory, createRouter } from 'vue-router'
import { routes } from '@/router'
import { useAuthStore } from '@/stores/auth'
import { usePreferenciasStore } from '@/stores/preferencias'
import { CONTA_DEMO } from '@/services/mock/banco'
import { reiniciarSimulacao } from '@/services/mock/servidor'
import { EMAIL_CONTATO } from '@/constants/contato'
import App from '@/App.vue'
import BarraLateral from './BarraLateral.vue'

async function montar(componente, caminho = '/campus/1', { logado = false } = {}) {
  const pinia = createPinia()
  setActivePinia(pinia)
  usePreferenciasStore().escolherCampus(1)
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
    ])
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

  it('com login: o apelido leva a "Meu progresso", e "Sair da conta" sai', async () => {
    const { wrapper } = await montar(BarraLateral, '/campus/1', { logado: true })

    const conta = wrapper.get('.atalho--conta')
    expect(conta.text()).toContain(CONTA_DEMO.apelido)
    expect(conta.attributes('href')).toBe('/progresso')

    await wrapper.get('.sair').trigger('click')
    await flushPromises()
    expect(useAuthStore().estaAutenticado).toBe(false)
    expect(wrapper.get('.atalho--conta').text()).toContain('Visitante')
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

  it.each(['/boas-vindas', '/campus'])('%s: tela de entrada, sem a lateral', async (caminho) => {
    const { wrapper } = await montar(App, caminho)
    expect(wrapper.find('.barra-lateral').exists()).toBe(false)
    expect(wrapper.find('.aside-conta').exists()).toBe(false)
  })

  it.each(['/login', '/cadastro', '/recuperar-senha'])(
    '%s: tela de conta, com o lado verde e sem a lateral',
    async (caminho) => {
      const { wrapper } = await montar(App, caminho)
      expect(wrapper.find('.barra-lateral').exists()).toBe(false)
      expect(wrapper.find('.aside-conta').exists()).toBe(true)
    },
  )
})
