import { describe, it, expect } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import { routes } from './index'
import App from '@/App.vue'

async function montarEm(caminho) {
  const router = createRouter({ history: createMemoryHistory(), routes })
  router.push(caminho)
  await router.isReady()
  const wrapper = mount(App, { global: { plugins: [router] } })
  await flushPromises()
  return wrapper
}

describe('roteamento', () => {
  it('a raiz mostra o cardápio sem login', async () => {
    const wrapper = await montarEm('/')
    expect(wrapper.find('h1').text()).toBe('Cardápio')
  })

  it('/cardapio/:campusId passa o campus como prop', async () => {
    const wrapper = await montarEm('/cardapio/gama')
    expect(wrapper.text()).toContain('Campus: gama')
  })

  it.each([
    ['/fila', 'Previsão de pico'],
    ['/avaliacoes', 'Avaliações'],
    ['/login', 'Entrar'],
    ['/cadastro', 'Criar conta'],
    ['/confirmar-email', 'Confirmar e-mail'],
    ['/recuperar-senha', 'Recuperar senha'],
    ['/redefinir-senha', 'Redefinir senha'],
  ])('%s renderiza a tela "%s"', async (caminho, titulo) => {
    const wrapper = await montarEm(caminho)
    expect(wrapper.find('h1').text()).toBe(titulo)
  })

  it('rota inexistente cai no 404', async () => {
    const wrapper = await montarEm('/qualquer-coisa')
    expect(wrapper.find('h1').text()).toBe('Página não encontrada')
  })
})