import { describe, it, expect } from 'vitest'
import {
  diasDaSemanaVigente,
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

const aLas = (hhmm) => {
  const [h, m] = hhmm.split(':').map(Number)
  return new Date(2026, 8, 28, h, m)
}

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

describe('diasDaSemanaVigente (AbasSemana, RF07.1)', () => {
  it('de segunda a sábado da semana atual', () => {
    expect(diasDaSemanaVigente(new Date(2026, 8, 30, 12))).toEqual([
      '2026-09-28',
      '2026-09-29',
      '2026-09-30',
      '2026-10-01',
      '2026-10-02',
      '2026-10-03',
    ])
  })

  it('no domingo, já mostra a semana seguinte', () => {
    expect(diasDaSemanaVigente(new Date(2026, 9, 4, 12))[0]).toBe('2026-10-05')
  })
})
