import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import ContatoEquipe from './ContatoEquipe.vue'
import { CANAL_CONTATO, EMAIL_CONTATO } from '@/constants/contato'

/**
 * Canal de contato para reclamações (RNF08, Visão 9.1, ADR 0012): o endereço
 * da equipe, visível e clicável, sem login.
 */
describe('ContatoEquipe', () => {
  it('o canal é o e-mail da equipe (ADR 0012)', () => {
    expect(EMAIL_CONTATO).toBe('equipe@bandejaounb.com.br')
    expect(CANAL_CONTATO).toBe('mailto:equipe@bandejaounb.com.br')
  })

  it('mostra o endereço por extenso, com link mailto', () => {
    const wrapper = mount(ContatoEquipe)

    const link = wrapper.get('a')
    expect(link.attributes('href')).toBe(CANAL_CONTATO)
    expect(link.text()).toBe(EMAIL_CONTATO)
  })

  it('diz para que serve: reclamações e pedido de exclusão da conta', () => {
    const texto = mount(ContatoEquipe).text()

    expect(texto).toContain('reclamações')
    expect(texto).toContain('exclusão da conta')
  })

  it('o mailto não abre em outra aba', () => {
    expect(mount(ContatoEquipe).get('a').attributes('target')).toBeUndefined()
  })
})
