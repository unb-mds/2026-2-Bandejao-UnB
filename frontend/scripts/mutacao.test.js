// @vitest-environment node
import { existsSync, readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'
import {
  ALVO_DA_CONFIGURACAO,
  ARQUIVOS_CRITICOS,
  MODULOS,
  alvosDoPr,
  escoreDoRelatorio,
} from './mutacao.mjs'

const raiz = fileURLToPath(new URL('..', import.meta.url))
const existe = (arquivo) => existsSync(`${raiz}/${arquivo}`)
const semNada = () => true

/** Relatório no formato do mutation-testing-report-schema (reporter `json` do Stryker). */
function relatorio(arquivos) {
  return {
    schemaVersion: '2',
    thresholds: { high: 80, low: 60 },
    files: Object.fromEntries(
      Object.entries(arquivos).map(([arquivo, status]) => [
        arquivo,
        {
          language: 'javascript',
          source: '',
          mutants: status.map((s, i) => ({ id: `${i}`, status: s })),
        },
      ]),
    ),
  }
}

describe('lista dos arquivos críticos', () => {
  it('cobre os módulos críticos do front no Plano de Testes (seção 2)', () => {
    expect(Object.keys(MODULOS)).toEqual([
      'auth',
      'cardapio',
      'avaliacao',
      'fila',
      'gamificacao',
      'api',
    ])
  })

  it('todo arquivo crítico existe', () => {
    expect(ARQUIVOS_CRITICOS.filter((arquivo) => !existe(arquivo))).toEqual([])
  })

  it('todo arquivo crítico com meta de cobertura no vitest.config.js também é mutado', () => {
    const config = readFileSync(`${raiz}/vitest.config.js`, 'utf8')
    const comMeta = [...config.matchAll(/'(src\/[^'*]+\.(?:js|vue))'/g)].map((m) => m[1])
    expect(comMeta.length).toBeGreaterThan(0)
    expect(comMeta.filter((arquivo) => !ARQUIVOS_CRITICOS.includes(arquivo))).toEqual([])
  })

  it('o alvo fixo da configuração é um arquivo crítico', () => {
    expect(ARQUIVOS_CRITICOS).toContain(ALVO_DA_CONFIGURACAO)
  })
})

describe('alvosDoPr', () => {
  it('um PR que não mexe em arquivo crítico não tem nada a mutar', () => {
    expect(
      alvosDoPr(['README.md', 'frontend/src/views/HomeView.vue', 'backend/apps/x.py'], semNada),
    ).toEqual([])
  })

  it('arquivo crítico alterado é mutado (caminho a partir de frontend/)', () => {
    expect(alvosDoPr(['frontend/src/stores/fila.js'], semNada)).toEqual(['src/stores/fila.js'])
  })

  it('teste alterado muta o arquivo que ele cobre, .js ou .vue', () => {
    expect(
      alvosDoPr(
        ['frontend/src/stores/auth.test.js', 'frontend/src/components/CheckinBotao.test.js'],
        semNada,
      ),
    ).toEqual(['src/components/CheckinBotao.vue', 'src/stores/auth.js'])
  })

  it('teste de arquivo que não é crítico não gera alvo', () => {
    expect(alvosDoPr(['frontend/src/components/AvisoLocalizacao.test.js'], semNada)).toEqual([])
  })

  it('sem repetição: código e teste do mesmo arquivo viram um alvo só', () => {
    expect(
      alvosDoPr(['frontend/src/utils/cardapio.js', 'frontend/src/utils/cardapio.test.js'], semNada),
    ).toEqual(['src/utils/cardapio.js'])
  })

  it.each([
    'frontend/stryker.config.mjs',
    'frontend/vitest.config.js',
    'frontend/vite.config.js',
    'frontend/package.json',
    'frontend/package-lock.json',
    'frontend/scripts/mutacao.mjs',
    '.github/workflows/frontend-ci.yml',
  ])('mudança na configuração da mutação (%s) muta o alvo fixo', (arquivo) => {
    expect(alvosDoPr([arquivo], semNada)).toEqual([ALVO_DA_CONFIGURACAO])
  })

  it('com outro arquivo crítico alterado, a configuração não puxa o alvo fixo', () => {
    expect(
      alvosDoPr(['frontend/scripts/mutacao.mjs', 'frontend/src/stores/fila.js'], semNada),
    ).toEqual(['src/stores/fila.js'])
  })

  it('arquivo crítico apagado no PR não vira alvo', () => {
    const naoExiste = (arquivo) => arquivo !== 'src/stores/fila.js'
    expect(alvosDoPr(['frontend/src/stores/fila.js'], naoExiste)).toEqual([])
  })

  it('aceita caminhos com barra invertida (Windows)', () => {
    expect(alvosDoPr(['frontend\\src\\stores\\fila.js'], semNada)).toEqual(['src/stores/fila.js'])
  })
})

describe('escoreDoRelatorio', () => {
  it('escore = (mortos + tempo esgotado) / avaliados, sem os que não rodaram', () => {
    const { conjunto } = escoreDoRelatorio(
      relatorio({
        'src/stores/fila.js': [
          'Killed',
          'Killed',
          'Timeout',
          'Survived',
          'NoCoverage',
          'CompileError',
          'Ignored',
        ],
      }),
    )

    expect(conjunto).toMatchObject({ detectados: 3, avaliados: 5, escore: 60 })
  })

  it('agrupa por módulo crítico', () => {
    const { modulos } = escoreDoRelatorio(
      relatorio({
        'src/stores/fila.js': ['Killed', 'Survived'],
        'src/components/CheckinBotao.vue': ['Killed', 'Killed'],
        'src/stores/auth.js': ['Survived'],
      }),
    )

    expect(modulos).toEqual([
      { modulo: 'auth', detectados: 0, avaliados: 1, escore: 0 },
      { modulo: 'fila', detectados: 3, avaliados: 4, escore: 75 },
    ])
  })

  it('trunca em duas casas, como no backend', () => {
    const { conjunto } = escoreDoRelatorio(
      relatorio({ 'src/stores/fila.js': ['Killed', 'Killed', 'Survived'] }),
    )

    expect(conjunto.escore).toBe(66.66)
  })

  it('sem nenhum mutante avaliado, o escore é nulo (não dá para medir)', () => {
    const { conjunto } = escoreDoRelatorio(relatorio({ 'src/stores/fila.js': ['CompileError'] }))

    expect(conjunto.escore).toBeNull()
  })

  it('relatório sem a lista de arquivos é recusado', () => {
    expect(() => escoreDoRelatorio({})).toThrow(/relatório/i)
  })
})
