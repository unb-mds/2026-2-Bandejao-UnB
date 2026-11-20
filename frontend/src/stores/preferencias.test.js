import { beforeEach, describe, expect, it } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { usePreferenciasStore } from './preferencias'

const CHAVE = 'bandejao:preferencias'

beforeEach(() => {
  localStorage.clear()
  setActivePinia(createPinia())
})

describe('preferenciasStore: "Agora não" do aviso de localização (RF19)', () => {
  it('começa sem "Agora não" no primeiro acesso', () => {
    expect(usePreferenciasStore().avisoLocalizacaoAdiado).toBe(false)
  })

  it('guarda o "Agora não" no localStorage', () => {
    usePreferenciasStore().adiarAvisoLocalizacao()

    expect(JSON.parse(localStorage.getItem(CHAVE)).avisoLocalizacaoAdiado).toBe(true)
  })

  it('o "Agora não" vale na próxima abertura do app', () => {
    usePreferenciasStore().adiarAvisoLocalizacao()

    setActivePinia(createPinia())

    expect(usePreferenciasStore().avisoLocalizacaoAdiado).toBe(true)
  })

  it('não apaga as outras preferências ao guardar o "Agora não"', () => {
    const preferencias = usePreferenciasStore()
    preferencias.escolherCampus('gama')
    preferencias.adiarAvisoLocalizacao()

    setActivePinia(createPinia())

    expect(usePreferenciasStore().campusId).toBe('gama')
  })

  it('ignora um valor salvo que não seja booleano', () => {
    localStorage.setItem(CHAVE, JSON.stringify({ avisoLocalizacaoAdiado: 'sim' }))

    expect(usePreferenciasStore().avisoLocalizacaoAdiado).toBe(false)
  })
})
