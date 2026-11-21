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
    preferencias.escolherCampus(3)
    preferencias.adiarAvisoLocalizacao()

    setActivePinia(createPinia())

    expect(usePreferenciasStore().campusId).toBe(3)
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
    preferencias.escolherCampus(3)

    expect(preferencias.avisoLocalizacaoAdiado).toBe(true)
    expect(aviso).toHaveBeenCalledOnce()
  })
})

describe('preferenciasStore: campus lembrado com o id inteiro da API (RF07.2)', () => {
  it('guarda o id inteiro do campus', () => {
    usePreferenciasStore().escolherCampus(3)

    expect(JSON.parse(localStorage.getItem(CHAVE)).campusId).toBe(3)
  })

  it('aceita o id vindo da rota, como texto', () => {
    const preferencias = usePreferenciasStore()

    preferencias.escolherCampus('4')

    expect(preferencias.campusId).toBe(4)
  })

  it.each([['darcy'], [0], [-1], [1.5], [null]])('ignora um campus inválido (%s)', (valor) => {
    const preferencias = usePreferenciasStore()
    preferencias.escolherCampus(2)

    preferencias.escolherCampus(valor)

    expect(preferencias.campusId).toBe(2)
  })

  it.each([
    ['darcy', 1],
    ['ceilandia', 2],
    ['gama', 3],
    ['planaltina', 4],
    ['fal', 5],
  ])('campus salvo no formato antigo (%s) vira o id %s', (salvo, id) => {
    localStorage.setItem(CHAVE, JSON.stringify({ campusId: salvo }))
    setActivePinia(createPinia())

    expect(usePreferenciasStore().campusId).toBe(id)
  })

  it.each([['executivo'], ['3'], [0], ['toString'], [null]])(
    'campus salvo inválido (%s) vale como "sem campus escolhido"',
    (salvo) => {
      localStorage.setItem(CHAVE, JSON.stringify({ campusId: salvo }))
      setActivePinia(createPinia())

      expect(usePreferenciasStore().campusId).toBeNull()
    },
  )

  it('esquecerCampus limpa o campus lembrado', () => {
    const preferencias = usePreferenciasStore()
    preferencias.escolherCampus(3)

    preferencias.esquecerCampus()

    expect(preferencias.campusId).toBeNull()
    expect(JSON.parse(localStorage.getItem(CHAVE)).campusId).toBeNull()
  })
})

describe('preferenciasStore: filtros com os nomes da API (ADR 0005)', () => {
  it('começa com a dieta "sem filtro" e sem marcadores', () => {
    const preferencias = usePreferenciasStore()

    expect(preferencias.dieta).toBe('sem_filtro')
    expect(preferencias.marcadores).toEqual([])
    expect(preferencias.filtrosAtivos).toBe(0)
  })

  it('filtros salvos com os nomes antigos continuam valendo; o desconhecido sai com aviso', () => {
    localStorage.setItem(
      CHAVE,
      JSON.stringify({ dieta: 'ovolacto', marcadores: ['leite', 'trigo', 'suino', 'peixe'] }),
    )
    setActivePinia(createPinia())
    const aviso = vi.spyOn(console, 'warn').mockImplementation(() => {})

    const preferencias = usePreferenciasStore()
    expect(preferencias.dieta).toBe('ovolactovegetariano')
    expect(preferencias.marcadores).toEqual(['leite_e_derivados', 'trigo_gluten', 'suino'])
    expect(aviso).toHaveBeenCalledTimes(1)
    expect(aviso.mock.calls[0][1]).toEqual(['peixe'])
  })

  it.each([
    ['todos', 'sem_filtro'],
    ['ovolacto', 'ovolactovegetariano'],
    ['vegano', 'vegetariano_estrito'],
  ])('dieta salva com o nome antigo %s vira %s', (antiga, atual) => {
    localStorage.setItem(CHAVE, JSON.stringify({ dieta: antiga }))
    setActivePinia(createPinia())

    expect(usePreferenciasStore().dieta).toBe(atual)
  })

  it('o nome antigo e o novo do mesmo marcador viram um só', () => {
    localStorage.setItem(CHAVE, JSON.stringify({ marcadores: ['leite', 'leite_e_derivados'] }))
    setActivePinia(createPinia())

    expect(usePreferenciasStore().marcadores).toEqual(['leite_e_derivados'])
  })

  it('nome salvo que é propriedade de objeto não vira dieta nem marcador', () => {
    localStorage.setItem(
      CHAVE,
      JSON.stringify({ dieta: 'toString', marcadores: ['constructor', 'ovo'] }),
    )
    setActivePinia(createPinia())
    vi.spyOn(console, 'warn').mockImplementation(() => {})

    const preferencias = usePreferenciasStore()
    expect(preferencias.dieta).toBe('sem_filtro')
    expect(preferencias.marcadores).toEqual(['ovo'])
  })

  it('filtros aplicados ficam lembrados no aparelho', () => {
    usePreferenciasStore().aplicarFiltros('vegetariano_estrito', ['soja'])
    setActivePinia(createPinia())

    const preferencias = usePreferenciasStore()
    expect(preferencias.dieta).toBe('vegetariano_estrito')
    expect(preferencias.marcadores).toEqual(['soja'])
    expect(preferencias.filtrosAtivos).toBe(2)
  })
})
