// @vitest-environment node
import { existsSync, mkdtempSync, rmSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import configDoVitest from '../vitest.config.js'
import {
  ALVO_DA_CONFIGURACAO,
  ARQUIVOS_CRITICOS,
  MODULOS,
  alvosDoPr,
  escoreDoRelatorio,
  principal,
} from './mutacao.mjs'
import { MINIMO_COBERTURA } from './cobertura.mjs'

const raiz = fileURLToPath(new URL('..', import.meta.url))
const existe = (arquivo) => existsSync(`${raiz}/${arquivo}`)
// Todo arquivo existe e nenhum é lido: só a correspondência por nome conta.
const semNada = { existe: () => true, ler: () => null }

/** Projeto de mentira para o grafo de imports: caminho -> conteúdo. */
function projeto(arquivos) {
  return { existe: (arquivo) => arquivo in arquivos, ler: (arquivo) => arquivos[arquivo] ?? null }
}

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

  // As metas são montadas a partir do ARQUIVOS_CRITICOS (FE-19): os dois testes
  // abaixo passam por construção e servem de trava contra quem voltar a
  // escrever a lista à mão no vitest.config.js.
  it('trava: todo arquivo com meta de cobertura no vitest.config.js também é mutado', () => {
    // Só as chaves de arquivo: opções globais (`perFile`, `lines`) não são arquivos.
    const comMeta = Object.keys(configDoVitest.test.coverage.thresholds).filter((chave) =>
      chave.startsWith('src/'),
    )
    expect(comMeta.length).toBeGreaterThan(0)
    expect(comMeta.filter((arquivo) => !ARQUIVOS_CRITICOS.includes(arquivo))).toEqual([])
  })

  it('trava: todo arquivo mutado tem a meta de linhas do cobertura.mjs no vitest.config.js', () => {
    const metas = configDoVitest.test.coverage.thresholds
    expect(MINIMO_COBERTURA).toBe(70)
    expect(
      ARQUIVOS_CRITICOS.filter((arquivo) => metas[arquivo]?.lines !== MINIMO_COBERTURA),
    ).toEqual([])
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

  it('teste com mais de um ponto no nome aponta para o arquivo antes do primeiro ponto', () => {
    expect(alvosDoPr(['frontend/src/utils/cardapio.propriedades.test.js'], semNada)).toEqual([
      'src/utils/cardapio.js',
    ])
  })

  it('teste sem correspondência por nome muta os arquivos críticos que ele importa', () => {
    const arquivos = {
      'src/views/HomeView.test.js':
        "import HomeView from './HomeView.vue'\nimport { mount } from '@vue/test-utils'",
      'src/views/HomeView.vue':
        "import { useAuthStore } from '@/stores/auth'\nimport { formatarNota } from '../utils/cardapio'",
      'src/stores/auth.js': "import { apiClient } from '@/services/apiClient.js'",
      'src/services/apiClient.js': "const simulado = () => import('./mock/servidor')",
      'src/services/mock/servidor.js': '',
      'src/utils/cardapio.js': "import { hojeISO } from './datas'",
      'src/utils/datas.js': '',
    }

    expect(alvosDoPr(['frontend/src/views/HomeView.test.js'], projeto(arquivos))).toEqual([
      'src/services/apiClient.js',
      'src/stores/auth.js',
      'src/utils/cardapio.js',
    ])
  })

  it('segue também o import() dinâmico das rotas e não entra em laço', () => {
    const arquivos = {
      'src/router/rotas.test.js': "import { routes } from './rotas'",
      'src/router/rotas.js':
        "export const routes = [{ component: () => import('@/views/FilaView.vue') }]",
      'src/views/FilaView.vue':
        "import { useFilaStore } from '@/stores/fila'\nimport { routes } from '@/router/rotas'",
      'src/stores/fila.js': '',
    }

    expect(alvosDoPr(['frontend/src/router/rotas.test.js'], projeto(arquivos))).toEqual([
      'src/stores/fila.js',
    ])
  })

  it('teste que não chega a nenhum arquivo crítico não gera alvo', () => {
    const arquivos = {
      'src/components/AvisoLocalizacao.test.js': "import Aviso from './AvisoLocalizacao.vue'",
      'src/components/AvisoLocalizacao.vue':
        "import { usePreferenciasStore } from '@/stores/preferencias'",
      'src/stores/preferencias.js': '',
    }

    expect(
      alvosDoPr(['frontend/src/components/AvisoLocalizacao.test.js'], projeto(arquivos)),
    ).toEqual([])
  })

  it('no projeto de verdade, o teste do fluxo da conta chega à authStore e às guardas', () => {
    const alvos = alvosDoPr(['frontend/src/views/fluxoConta.test.js'])

    expect(alvos).toContain('src/stores/auth.js')
    expect(alvos).toContain('src/router/index.js')
    expect(alvos).toContain('src/services/apiClient.js')
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

  it.each(['frontend/src/services/mock/servidor.js', 'frontend/src/services/mock/banco.js'])(
    'o servidor simulado (%s) conta como configuração, como os fixtures no backend',
    (arquivo) => {
      expect(alvosDoPr([arquivo], semNada)).toEqual([ALVO_DA_CONFIGURACAO])
    },
  )

  it('arquivo crítico apagado no PR não vira alvo', () => {
    const naoExiste = { existe: (arquivo) => arquivo !== 'src/stores/fila.js', ler: () => null }
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

describe('linha de comando (principal)', () => {
  let pasta
  let saida
  let erros

  /** Grava um relatório do Stryker com os status dados por arquivo e devolve o caminho. */
  function gravar(arquivos, nome = 'relatorio.json') {
    const caminho = join(pasta, nome)
    writeFileSync(caminho, JSON.stringify(relatorio(arquivos)))
    return caminho
  }

  /** Um arquivo de cada módulo crítico, todos com o mesmo escore. */
  function todosOsModulos(status) {
    return Object.fromEntries(Object.values(MODULOS).map((arquivos) => [arquivos[0], status]))
  }

  beforeEach(() => {
    pasta = mkdtempSync(join(tmpdir(), 'mutacao-'))
    saida = vi.spyOn(console, 'log').mockImplementation(() => {})
    erros = vi.spyOn(console, 'error').mockImplementation(() => {})
  })

  afterEach(() => {
    rmSync(pasta, { recursive: true, force: true })
    vi.restoreAllMocks()
  })

  const textoDe = (espiao) => espiao.mock.calls.flat().join('\n')

  it('sai com 0 quando o escore é exatamente o mínimo', () => {
    const caminho = gravar({ 'src/stores/fila.js': ['Killed', 'Survived'] })

    expect(principal(['escore', caminho, '--minimo', '50'])).toBe(0)
    expect(textoDe(saida)).toContain('50.00%')
  })

  it('sai com 1 abaixo do mínimo', () => {
    const caminho = gravar({ 'src/stores/fila.js': ['Killed', 'Survived', 'Survived'] })

    expect(principal(['escore', caminho, '--minimo', '50'])).toBe(1)
  })

  it('sem --minimo, o mínimo é 50', () => {
    const caminho = gravar({ 'src/stores/fila.js': ['Killed', 'Survived', 'Survived'] })

    expect(principal(['escore', caminho])).toBe(1)
  })

  it.each([
    ['sem valor', ['--minimo']],
    ['texto', ['--minimo', 'abc']],
    ['outra opção no lugar', ['--minimo', '--por-modulo']],
    ['acima de 100', ['--minimo', '101']],
    ['negativo', ['--minimo', '-1']],
  ])('--minimo inválido (%s) sai com 2 em vez de aprovar', (_caso, opcoes) => {
    const caminho = gravar({ 'src/stores/fila.js': ['Survived'] })

    expect(principal(['escore', caminho, ...opcoes])).toBe(2)
    expect(textoDe(erros)).toMatch(/--minimo/)
  })

  it('arquivo ausente sai com 2', () => {
    expect(principal(['escore', join(pasta, 'nao-existe.json')])).toBe(2)
  })

  it('JSON inválido sai com 2', () => {
    const caminho = join(pasta, 'quebrado.json')
    writeFileSync(caminho, '{ não é json')

    expect(principal(['escore', caminho])).toBe(2)
  })

  it('relatório sem files sai com 2', () => {
    const caminho = join(pasta, 'sem-files.json')
    writeFileSync(caminho, '{}')

    expect(principal(['escore', caminho])).toBe(2)
  })

  it('conjunto sem nenhum mutante avaliado sai com 2, falando do conjunto', () => {
    const caminho = gravar({ 'src/stores/fila.js': ['CompileError'] })

    expect(principal(['escore', caminho])).toBe(2)
    expect(textoDe(erros)).toMatch(/conjunto/)
  })

  it('--por-modulo com todos os módulos no mínimo sai com 0', () => {
    const caminho = gravar(todosOsModulos(['Killed', 'Survived']))

    expect(principal(['escore', caminho, '--por-modulo'])).toBe(0)
  })

  it('--por-modulo sai com 1 se um módulo fica abaixo, mesmo com o geral acima', () => {
    const arquivos = todosOsModulos(['Killed', 'Killed', 'Killed', 'Killed'])
    arquivos[MODULOS.api[0]] = ['Survived']
    const caminho = gravar(arquivos)

    expect(principal(['escore', caminho, '--por-modulo'])).toBe(1)
    expect(textoDe(erros)).toMatch(/api/)
  })

  it('--por-modulo sai com 2 se falta algum módulo no relatório, e diz qual', () => {
    const arquivos = todosOsModulos(['Killed'])
    delete arquivos[MODULOS.gamificacao[0]]
    const caminho = gravar(arquivos)

    expect(principal(['escore', caminho, '--por-modulo'])).toBe(2)
    expect(textoDe(erros)).toMatch(/gamificacao/)
  })

  it('alvos com uma base que não existe sai com 2', () => {
    expect(principal(['alvos', 'origin/branch-que-nao-existe-fe17'])).toBe(2)
  })

  it('sem comando, sai com 2 e mostra o uso', () => {
    expect(principal([])).toBe(2)
    expect(textoDe(erros)).toMatch(/Uso:/)
  })
})
