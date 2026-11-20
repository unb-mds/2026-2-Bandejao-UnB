import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { usePreferenciasStore } from './preferencias'

const CHAVE = 'bandejao:preferencias'

beforeEach(() => {
  localStorage.clear()
  setActivePinia(createPinia())
})

afterEach(() => {
  vi.restoreAllMocks()
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

describe('preferenciasStore: localização permitida sem Permissions API (RF19)', () => {
  it('começa sem a marca de permitida', () => {
    expect(usePreferenciasStore().localizacaoPermitida).toBe(false)
  })

  it('guarda que a pessoa permitiu, para a próxima abertura', () => {
    usePreferenciasStore().registrarLocalizacaoPermitida()

    setActivePinia(createPinia())

    expect(usePreferenciasStore().localizacaoPermitida).toBe(true)
  })
})

describe('preferenciasStore: armazenamento com problema', () => {
  it('localStorage corrompido volta aos padrões e registra o problema', () => {
    const aviso = vi.spyOn(console, 'warn').mockImplementation(() => {})
    localStorage.setItem(CHAVE, '{não é json')

    const preferencias = usePreferenciasStore()

    expect(preferencias.campusId).toBeNull()
    expect(preferencias.avisoLocalizacaoAdiado).toBe(false)
    expect(aviso).toHaveBeenCalled()
  })

  it('setItem lançando exceção não quebra o "Agora não" nesta visita', () => {
    const aviso = vi.spyOn(console, 'warn').mockImplementation(() => {})
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new DOMException('cota excedida', 'QuotaExceededError')
    })
    const preferencias = usePreferenciasStore()

    preferencias.adiarAvisoLocalizacao()
    preferencias.escolherCampus('gama')

    expect(preferencias.avisoLocalizacaoAdiado).toBe(true)
    expect(aviso).toHaveBeenCalledOnce()
  })
})
