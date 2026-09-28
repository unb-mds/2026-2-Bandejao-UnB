import { describe, it, expect } from 'vitest'
import {
  filtrarCategorias,
  formatarNota,
  refeicaoPadrao,
  resumoRefeicao,
  selecaoPadrao,
} from './cardapio'

const p = (nome, ...marcadores) => ({ nome, marcadores })
const CATEGORIAS = [
  { rotulo: 'Bebidas', dieta: 'todas', pratos: [p('Suco de caju')] },
  {
    rotulo: 'Prato Principal — Padrão',
    dieta: 'padrao',
    pratos: [p('Bife', 'suino'), p('Frango')],
  },
  {
    rotulo: 'Prato Principal — Ovolactovegetariano',
    dieta: 'ovolacto',
    pratos: [p('Omelete', 'ovo', 'leite')],
  },
  { rotulo: 'Prato Principal — Vegetariano Estrito', dieta: 'vegano', pratos: [p('Tofu', 'soja')] },
  { rotulo: 'Guarnição', dieta: 'todas', pratos: [p('Purê', 'leite')] },
  { rotulo: 'Acompanhamentos', dieta: 'todas', pratos: [p('Arroz'), p('Feijão')] },
  { rotulo: 'Salada', dieta: 'todas', pratos: [p('Folhas')] },
]

const rotulos = (categorias) => categorias.map((c) => c.rotulo)
const aLas = (hhmm) => {
  const [h, m] = hhmm.split(':').map(Number)
  return new Date(2026, 8, 28, h, m)
}

describe('filtrarCategorias — dieta (RF09)', () => {
  it('sem filtro exibe todas as linhas', () => {
    expect(filtrarCategorias(CATEGORIAS)).toHaveLength(CATEGORIAS.length)
  })

  it('ovolactovegetariano oculta só a linha padrão', () => {
    const visiveis = rotulos(filtrarCategorias(CATEGORIAS, { dieta: 'ovolacto' }))
    expect(visiveis).not.toContain('Prato Principal — Padrão')
    expect(visiveis).toContain('Prato Principal — Ovolactovegetariano')
    expect(visiveis).toContain('Prato Principal — Vegetariano Estrito')
    expect(visiveis).toContain('Salada')
  })

  it('vegetariano estrito mantém só a linha vegana e as comuns', () => {
    const visiveis = rotulos(filtrarCategorias(CATEGORIAS, { dieta: 'vegano' }))
    expect(visiveis).toEqual([
      'Bebidas',
      'Prato Principal — Vegetariano Estrito',
      'Guarnição',
      'Acompanhamentos',
      'Salada',
    ])
  })
})

describe('filtrarCategorias — marcadores (RF08)', () => {
  it('oculta os pratos que contêm um marcador selecionado', () => {
    const [, padrao] = filtrarCategorias(CATEGORIAS, { marcadores: ['suino'] })
    expect(padrao.pratos.map((prato) => prato.nome)).toEqual(['Frango'])
  })

  it('mantém a categoria vazia para exibir "sem opção compatível"', () => {
    const guarnicao = filtrarCategorias(CATEGORIAS, { marcadores: ['leite'] }).find(
      (c) => c.rotulo === 'Guarnição',
    )
    expect(guarnicao.pratos).toEqual([])
  })

  it('combina dieta e marcadores', () => {
    const resultado = filtrarCategorias(CATEGORIAS, { dieta: 'vegano', marcadores: ['soja'] })
    const vegana = resultado.find((c) => c.dieta === 'vegano')
    expect(vegana.pratos).toEqual([])
    expect(resultado.some((c) => c.dieta === 'padrao')).toBe(false)
  })

  it('não altera os dados originais', () => {
    filtrarCategorias(CATEGORIAS, { marcadores: ['suino', 'leite'] })
    expect(CATEGORIAS[1].pratos).toHaveLength(2)
  })
})

describe('refeicaoPadrao (RF07)', () => {
  const TODAS = ['cafe', 'almoco', 'jantar']

  it.each([
    ['06:00', 'cafe'],
    ['08:00', 'cafe'],
    ['10:00', 'almoco'],
    ['12:30', 'almoco'],
    ['15:00', 'jantar'],
    ['18:00', 'jantar'],
    ['22:00', 'jantar'],
  ])('às %s exibe %s', (hora, esperado) => {
    expect(refeicaoPadrao(TODAS, aLas(hora))).toBe(esperado)
  })

  it('só considera as refeições servidas no dia', () => {
    expect(refeicaoPadrao(['cafe', 'almoco'], aLas('18:00'))).toBe('almoco')
    expect(refeicaoPadrao([], aLas('12:00'))).toBeNull()
  })
})

describe('selecaoPadrao', () => {
  const semana = [
    { data: '2026-09-28', refeicoes: [{ tipo: 'cafe' }, { tipo: 'almoco' }, { tipo: 'jantar' }] },
    { data: '2026-09-29', refeicoes: [{ tipo: 'cafe' }, { tipo: 'almoco' }] },
  ]

  it('seleciona hoje e a refeição em andamento', () => {
    expect(selecaoPadrao(semana, aLas('12:00'))).toEqual({ data: '2026-09-28', refeicao: 'almoco' })
  })

  it('sem cardápio hoje, seleciona o próximo dia disponível', () => {
    const domingo = new Date(2026, 8, 27, 12, 0)
    expect(selecaoPadrao(semana, domingo)).toEqual({ data: '2026-09-28', refeicao: 'cafe' })
  })

  it('semana sem dias não seleciona nada', () => {
    expect(selecaoPadrao([], aLas('12:00'))).toEqual({ data: null, refeicao: null })
  })
})

describe('resumoRefeicao', () => {
  it('resume prato principal, acompanhamentos e salada', () => {
    expect(resumoRefeicao(CATEGORIAS)).toEqual([
      { rotulo: 'Prato principal', texto: 'Bife, Frango' },
      { rotulo: 'Acompanham.', texto: 'Arroz, Feijão' },
      { rotulo: 'Salada', texto: 'Folhas' },
    ])
  })

  it('no café da manhã usa as primeiras categorias', () => {
    const cafe = [
      { rotulo: 'Bebidas', dieta: 'todas', pratos: [p('Café')] },
      { rotulo: 'Complemento — Ovolactovegetariano', dieta: 'ovolacto', pratos: [p('Pão')] },
      { rotulo: 'Fruta', dieta: 'todas', pratos: [p('Mamão')] },
    ]
    expect(resumoRefeicao(cafe).map((l) => l.rotulo)).toEqual(['Bebidas', 'Complemento', 'Fruta'])
  })
})

describe('formatarNota', () => {
  it('usa vírgula decimal e traço quando não há nota', () => {
    expect(formatarNota(4.2857)).toBe('4,3')
    expect(formatarNota(null)).toBe('–')
  })
})
