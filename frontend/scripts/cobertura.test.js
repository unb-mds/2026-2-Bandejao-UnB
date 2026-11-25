// @vitest-environment node
import { mkdtempSync, rmSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ARQUIVOS_CRITICOS, MODULOS } from './mutacao.mjs'
import { MINIMO_COBERTURA, coberturaDoRelatorio, principal } from './cobertura.mjs'

const RAIZ_NO_CI = '/home/runner/work/2026-2-Bandejao-UnB/2026-2-Bandejao-UnB/frontend'

/** Entrada do coverage-summary.json (reporter `json-summary` do Vitest) para um arquivo. */
function entrada(total, cobertas) {
  return {
    lines: { total, covered: cobertas, skipped: 0, pct: total ? (cobertas / total) * 100 : 100 },
    statements: { total, covered: cobertas, skipped: 0, pct: 0 },
    functions: { total: 0, covered: 0, skipped: 0, pct: 100 },
    branches: { total: 0, covered: 0, skipped: 0, pct: 100 },
  }
}

/** Relatório com os arquivos dados (caminho a partir de frontend/ -> [total, cobertas]). */
function relatorio(arquivos, raiz = RAIZ_NO_CI) {
  return {
    total: entrada(1000, 900),
    ...Object.fromEntries(
      Object.entries(arquivos).map(([arquivo, [total, cobertas]]) => [
        `${raiz}/${arquivo}`,
        entrada(total, cobertas),
      ]),
    ),
  }
}

/** Todos os arquivos críticos com a mesma cobertura (100 linhas, `cobertas` cobertas). */
function todosCriticos(cobertas) {
  return Object.fromEntries(ARQUIVOS_CRITICOS.map((arquivo) => [arquivo, [100, cobertas]]))
}

describe('coberturaDoRelatorio', () => {
  it('lista os arquivos críticos agrupados por módulo, na ordem do MODULOS', () => {
    const { arquivos, ausentes } = coberturaDoRelatorio(relatorio(todosCriticos(100)))

    expect(ausentes).toEqual([])
    expect(arquivos.map((a) => a.arquivo)).toEqual(ARQUIVOS_CRITICOS)
    const modulosNaOrdem = [...new Set(arquivos.map((a) => a.modulo))]
    expect(modulosNaOrdem).toEqual(Object.keys(MODULOS))
  })

  it('ignora o total e os arquivos que não são críticos', () => {
    const { arquivos } = coberturaDoRelatorio(
      relatorio({ ...todosCriticos(100), 'src/views/HomeView.vue': [10, 0] }),
    )

    expect(arquivos.map((a) => a.arquivo)).not.toContain('src/views/HomeView.vue')
    expect(arquivos).toHaveLength(ARQUIVOS_CRITICOS.length)
  })

  it('guarda as linhas cobertas e o total de cada arquivo', () => {
    const { arquivos } = coberturaDoRelatorio(
      relatorio({ ...todosCriticos(100), 'src/stores/fila.js': [214, 200] }),
    )

    const fila = arquivos.find((a) => a.arquivo === 'src/stores/fila.js')
    expect(fila).toMatchObject({ modulo: 'fila', total: 214, cobertas: 200 })
  })

  it('trunca a porcentagem em duas casas, sem arredondar para cima', () => {
    const { arquivos } = coberturaDoRelatorio(
      relatorio({ ...todosCriticos(100), 'src/stores/fila.js': [3, 2] }),
    )

    expect(arquivos.find((a) => a.arquivo === 'src/stores/fila.js').pct).toBe(66.66)
  })

  it('acha o arquivo qualquer que seja a raiz do checkout (CI ou máquina local)', () => {
    const { ausentes } = coberturaDoRelatorio(
      relatorio(todosCriticos(100), '/home/alana/bandejao/frontend'),
    )

    expect(ausentes).toEqual([])
  })

  it('aceita caminho com barra invertida (Windows)', () => {
    const doWindows = Object.fromEntries(
      Object.entries(relatorio(todosCriticos(100), 'C:/Users/alana/bandejao/frontend')).map(
        ([caminho, dados]) => [caminho.replaceAll('/', '\\'), dados],
      ),
    )

    expect(coberturaDoRelatorio(doWindows).ausentes).toEqual([])
  })

  it('arquivo crítico fora do relatório vai para `ausentes`', () => {
    const arquivos = todosCriticos(100)
    delete arquivos['src/router/index.js']

    expect(coberturaDoRelatorio(relatorio(arquivos)).ausentes).toEqual(['src/router/index.js'])
  })

  it('arquivo crítico sem nenhuma linha também é ausente: 0 de 0 não prova nada', () => {
    const { ausentes, arquivos } = coberturaDoRelatorio(
      relatorio({ ...todosCriticos(100), 'src/stores/gamificacao.js': [0, 0] }),
    )

    expect(ausentes).toEqual(['src/stores/gamificacao.js'])
    expect(arquivos.map((a) => a.arquivo)).not.toContain('src/stores/gamificacao.js')
  })

  it('pasta com o nome grudado no começo (meusrc/) não conta: o final casa a partir de uma barra', () => {
    const arquivos = todosCriticos(100)
    delete arquivos['src/stores/auth.js']
    const { ausentes } = coberturaDoRelatorio(
      relatorio({ ...arquivos, 'meusrc/stores/auth.js': [100, 100] }),
    )

    expect(ausentes).toEqual(['src/stores/auth.js'])
  })

  it.each([
    ['sem `covered`', { total: 100 }],
    ['`covered` texto', { total: 100, covered: 'abc' }],
    ['`covered` negativo', { total: 100, covered: -1 }],
    ['`covered` maior que o total', { total: 100, covered: 101 }],
    ['`total` fracionado', { total: 10.5, covered: 5 }],
  ])('linhas malformadas (%s) são ausentes, não NaN%%', (_caso, linhas) => {
    const dados = relatorio(todosCriticos(100))
    dados[`${RAIZ_NO_CI}/src/stores/fila.js`].lines = linhas

    const { ausentes, arquivos } = coberturaDoRelatorio(dados)

    expect(ausentes).toEqual(['src/stores/fila.js'])
    expect(arquivos.every((a) => Number.isFinite(a.pct))).toBe(true)
  })
})

describe('linha de comando (principal)', () => {
  let pasta
  let saida
  let erros

  /** Grava o coverage-summary.json e devolve o caminho. */
  function gravar(arquivos, nome = 'coverage-summary.json') {
    const caminho = join(pasta, nome)
    writeFileSync(caminho, JSON.stringify(relatorio(arquivos)))
    return caminho
  }

  beforeEach(() => {
    pasta = mkdtempSync(join(tmpdir(), 'cobertura-'))
    saida = vi.spyOn(console, 'log').mockImplementation(() => {})
    erros = vi.spyOn(console, 'error').mockImplementation(() => {})
  })

  afterEach(() => {
    rmSync(pasta, { recursive: true, force: true })
    vi.restoreAllMocks()
  })

  const textoDe = (espiao) => espiao.mock.calls.flat().join('\n')

  it('sai com 0 quando todos os arquivos estão no mínimo, e 70% exatos passam', () => {
    const caminho = gravar(todosCriticos(70))

    expect(principal(['resumo', caminho, '--minimo', '70'])).toBe(0)
    expect(textoDe(erros)).toBe('')
  })

  it('sai com 1 quando um arquivo fica abaixo, e nomeia o arquivo', () => {
    const caminho = gravar({ ...todosCriticos(100), 'src/services/apiClient.js': [1000, 699] })

    expect(principal(['resumo', caminho, '--minimo', '70'])).toBe(1)
    expect(textoDe(erros)).toContain(
      '::error::Cobertura de src/services/apiClient.js abaixo de 70%: 69.90%',
    )
  })

  it('o motivo da reprovação também sai no stdout, que vai para o resumo do run', () => {
    const caminho = gravar({ ...todosCriticos(100), 'src/services/apiClient.js': [1000, 699] })

    principal(['resumo', caminho])

    expect(textoDe(saida)).toContain('**Abaixo de 70%:** `src/services/apiClient.js` (69.90%)')
  })

  it('sem --minimo, o mínimo é a meta do vitest.config.js (70)', () => {
    expect(MINIMO_COBERTURA).toBe(70)
    const caminho = gravar({ ...todosCriticos(100), 'src/stores/fila.js': [1000, 699] })

    expect(principal(['resumo', caminho])).toBe(1)
  })

  it('imprime a tabela em Markdown com módulo, arquivo, linhas e cobertura', () => {
    const caminho = gravar({ ...todosCriticos(100), 'src/stores/fila.js': [214, 200] })

    principal(['resumo', caminho])

    const texto = textoDe(saida)
    expect(texto).toContain('| Módulo | Arquivo | Linhas | Cobertura |')
    expect(texto).toContain('| fila | `src/stores/fila.js` | 200/214 | 93.45% |')
  })

  it('fecha a tabela com a linha do conjunto dos arquivos críticos', () => {
    const caminho = gravar(todosCriticos(80))

    principal(['resumo', caminho])

    const linhas = textoDe(saida).split('\n')
    const total = ARQUIVOS_CRITICOS.length * 100
    expect(linhas.at(-1)).toBe(`| **conjunto** |  | ${total * 0.8}/${total} | 80.00% |`)
  })

  it('a tabela sai mesmo quando um arquivo reprova', () => {
    const caminho = gravar({ ...todosCriticos(100), 'src/stores/fila.js': [1000, 100] })

    principal(['resumo', caminho])

    expect(textoDe(saida)).toContain('`src/stores/fila.js`')
  })

  it.each([
    ['sem valor', ['--minimo']],
    ['texto', ['--minimo', 'abc']],
    ['outra opção no lugar', ['--minimo', '--outra']],
    ['acima de 100', ['--minimo', '101']],
    ['negativo', ['--minimo', '-1']],
  ])('--minimo inválido (%s) sai com 2 em vez de aprovar', (_caso, opcoes) => {
    const caminho = gravar(todosCriticos(100))

    expect(principal(['resumo', caminho, ...opcoes])).toBe(2)
    expect(textoDe(erros)).toMatch(/--minimo/)
  })

  it('relatório ausente sai com 2: sem medir, não aprova', () => {
    expect(principal(['resumo', join(pasta, 'nao-existe.json')])).toBe(2)
    expect(textoDe(erros)).toContain('Não dá para medir')
  })

  it('JSON inválido sai com 2 e diz que não dá para medir', () => {
    const caminho = join(pasta, 'quebrado.json')
    writeFileSync(caminho, '{ não é json')

    expect(principal(['resumo', caminho])).toBe(2)
    expect(textoDe(erros)).toContain('::error::Não dá para medir')
    expect(textoDe(saida)).toContain('**Não medido:**')
  })

  it.each([
    ['null', 'null'],
    ['lista', '[]'],
    ['objeto vazio', '{}'],
    ['número', '42'],
  ])('JSON válido com formato errado (%s) sai com 2', (_caso, conteudo) => {
    const caminho = join(pasta, 'formato.json')
    writeFileSync(caminho, conteudo)

    expect(principal(['resumo', caminho])).toBe(2)
    expect(textoDe(erros)).toContain('::error::Não dá para medir')
  })

  it('arquivo ausente e arquivo abaixo ao mesmo tempo: sai com 2 (não medir vence)', () => {
    const arquivos = { ...todosCriticos(100), 'src/stores/fila.js': [1000, 100] }
    delete arquivos['src/router/index.js']
    const caminho = gravar(arquivos)

    expect(principal(['resumo', caminho])).toBe(2)
  })

  it('arquivo crítico fora do relatório sai com 2, e nomeia o arquivo', () => {
    const arquivos = todosCriticos(100)
    delete arquivos['src/components/CheckinBotao.vue']
    const caminho = gravar(arquivos)

    expect(principal(['resumo', caminho])).toBe(2)
    expect(textoDe(erros)).toContain('::error::')
    expect(textoDe(erros)).toContain('src/components/CheckinBotao.vue')
    expect(textoDe(saida)).toContain('**Não medido:** `src/components/CheckinBotao.vue`')
  })

  it.each([
    ['sem comando', []],
    ['sem caminho', ['resumo']],
    ['comando desconhecido', ['outro', 'x.json']],
  ])('%s: sai com 2 e mostra o uso', (_caso, argumentos) => {
    expect(principal(argumentos)).toBe(2)
    expect(textoDe(erros)).toContain('Uso:')
  })
})
