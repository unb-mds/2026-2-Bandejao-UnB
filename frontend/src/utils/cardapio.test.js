import { describe, it, expect } from 'vitest'
import {
  diasDaSemanaVigente,
  formatarNota,
  refeicaoPadrao,
  resumoRefeicao,
  selecaoPadrao,
} from './cardapio'

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
    const diaAntes = new Date(2026, 8, 27, 12, 0)
    expect(selecaoPadrao(semana, diaAntes)).toEqual({ data: '2026-09-28', refeicao: 'cafe' })
  })

  it('semana sem dias não seleciona nada', () => {
    expect(selecaoPadrao([], aLas('12:00'))).toEqual({ data: null, refeicao: null })
  })
})

describe('resumoRefeicao (formato do GET /api/cardapio/)', () => {
  const categoria = (nome, ...descricoes) => ({
    nome,
    semOpcaoCompativel: false,
    pratos: descricoes.map((descricao) => ({
      descricao,
      marcadores: [],
      contemMarcadorSelecionado: false,
    })),
  })

  it('resume prato principal, acompanhamentos e salada', () => {
    const almoco = [
      categoria('Bebidas', 'Suco de caju'),
      categoria('Prato principal', 'Bife', 'Frango'),
      categoria('Prato principal ovolactovegetariano', 'Omelete'),
      categoria('Guarnição', 'Purê'),
      categoria('Acompanhamentos', 'Arroz', 'Feijão'),
      categoria('Salada', 'Folhas'),
    ]
    expect(resumoRefeicao(almoco)).toEqual([
      { rotulo: 'Prato principal', texto: 'Bife, Frango' },
      { rotulo: 'Acompanham.', texto: 'Arroz, Feijão' },
      { rotulo: 'Salada', texto: 'Folhas' },
    ])
  })

  it.each([
    ['com "— Padrão" no nome', 'Prato principal — Padrão'],
    ['só "Prato principal"', 'Prato principal'],
    ['em maiúsculas, sem acento', 'PRATO PRINCIPAL PADRAO'],
  ])(
    'prato principal: fica com o padrão mesmo se o vegetariano vier antes (%s)',
    (_caso, nomeDoPadrao) => {
      const almoco = [
        categoria('Prato principal — Ovolactovegetariano', 'Omelete'),
        categoria('Prato principal — Vegetariano estrito', 'Tofu'),
        categoria(nomeDoPadrao, 'Bife'),
        categoria('Acompanhamentos', 'Arroz'),
      ]

      expect(resumoRefeicao(almoco)[0]).toEqual({ rotulo: 'Prato principal', texto: 'Bife' })
    },
  )

  it('prato principal: sem o padrão, fica com o primeiro que tiver prato', () => {
    const almoco = [
      categoria('Prato principal — Ovolactovegetariano', 'Omelete'),
      categoria('Acompanhamentos', 'Arroz'),
    ]

    expect(resumoRefeicao(almoco)[0]).toEqual({ rotulo: 'Prato principal', texto: 'Omelete' })
  })

  it('aceita os nomes em maiúsculas e no singular, como nos PDFs', () => {
    const almoco = [
      categoria('PRATO PRINCIPAL PADRÃO', 'Bife'),
      categoria('ACOMPANHAMENTO', 'Arroz'),
      categoria('SALADAS', 'Folhas'),
    ]
    expect(resumoRefeicao(almoco).map((l) => l.texto)).toEqual(['Bife', 'Arroz', 'Folhas'])
  })

  it('no café da manhã usa as primeiras categorias com pratos', () => {
    const cafe = [
      categoria('Bebidas', 'Café'),
      categoria('Vazia'),
      categoria('Complemento — Ovolactovegetariano', 'Pão'),
      categoria('Fruta', 'Mamão'),
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
  const SEMANA = [
    '2026-09-28',
    '2026-09-29',
    '2026-09-30',
    '2026-10-01',
    '2026-10-02',
    '2026-10-03',
    '2026-10-04',
  ]

  it('de segunda a domingo da semana atual (7 abas)', () => {
    expect(diasDaSemanaVigente(new Date(2026, 8, 30, 12))).toEqual(SEMANA)
  })

  it('na segunda já inclui o domingo da mesma semana', () => {
    expect(diasDaSemanaVigente(new Date(2026, 8, 28, 0, 0))).toEqual(SEMANA)
  })

  it('no domingo, mostra a semana corrente com o domingo', () => {
    expect(diasDaSemanaVigente(new Date(2026, 9, 4, 23, 59))).toEqual(SEMANA)
  })

  it('na virada de domingo para segunda, já passa para a semana seguinte', () => {
    expect(diasDaSemanaVigente(new Date(2026, 9, 5, 0, 0))).toEqual([
      '2026-10-05',
      '2026-10-06',
      '2026-10-07',
      '2026-10-08',
      '2026-10-09',
      '2026-10-10',
      '2026-10-11',
    ])
  })
})

describe('selecaoPadrao no domingo', () => {
  const domingo = new Date(2026, 9, 4, 12, 0)

  it('com cardápio no domingo (Darcy), seleciona o domingo', () => {
    const semana = [
      { data: '2026-10-03', refeicoes: [{ tipo: 'almoco' }] },
      { data: '2026-10-04', refeicoes: [{ tipo: 'cafe' }, { tipo: 'almoco' }, { tipo: 'jantar' }] },
    ]
    expect(selecaoPadrao(semana, domingo)).toEqual({ data: '2026-10-04', refeicao: 'almoco' })
  })
})
