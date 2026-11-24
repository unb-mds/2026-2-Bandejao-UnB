/**
 * Seleção dos alvos e escore da mutação do front (FE-17, #189, ADR 0013).
 *
 * O modo `--incremental` do Stryker só reaproveita o resultado de uma rodada
 * anterior; ele não sabe o que mudou no PR. Como no backend (BE-19), quem
 * escolhe os arquivos é este script, e o Stryker recebe a lista em `--mutate`.
 *
 * Comandos (de qualquer pasta; os caminhos são resolvidos a partir de
 * `frontend/`):
 *
 *   node scripts/mutacao.mjs alvos origin/develop
 *       Imprime um arquivo crítico por linha para o que o PR mudou em
 *       relação à base. Sem saída quando o PR não mexe em arquivo crítico,
 *       em teste que chegue a um, nem na configuração da mutação. Saída 2 se
 *       o `git diff` falhar.
 *
 *   node scripts/mutacao.mjs escore reports/mutation/mutation.json [--minimo 50] [--por-modulo]
 *       Calcula o escore a partir do relatório JSON do Stryker. Sem
 *       `--por-modulo` (o PR), o mínimo vale para o conjunto dos mutantes
 *       rodados; com ele (a rodada semanal), vale para cada módulo crítico, e
 *       todos precisam estar no relatório. Saída 0: no mínimo. Saída 1:
 *       abaixo. Saída 2: não dá para medir (relatório ausente ou ilegível,
 *       nada avaliado, módulo faltando) ou uso inválido (`--minimo` sem um
 *       número de 0 a 100, comando desconhecido).
 *
 * Só usa a biblioteca padrão do Node.
 */
import { execFileSync } from 'node:child_process'
import { readFileSync, statSync } from 'node:fs'
import { join, posix } from 'node:path'
import { fileURLToPath } from 'node:url'

/**
 * Módulos críticos do front (Plano de Testes, seção 2), com os caminhos a
 * partir de `frontend/`. As validações do cadastro ficam na CadastroView e
 * entram pelos testes do fluxo da conta, não por mutação da view inteira.
 */
export const MODULOS = {
  auth: ['src/stores/auth.js', 'src/router/index.js'],
  cardapio: ['src/stores/cardapio.js', 'src/utils/cardapio.js'],
  avaliacao: ['src/stores/avaliacoes.js'],
  fila: [
    'src/stores/fila.js',
    'src/services/leituraPosicao.js',
    'src/components/CheckinBotao.vue',
    'src/components/FilaPrevisao.vue',
  ],
  gamificacao: ['src/stores/gamificacao.js', 'src/components/PontosAviso.vue'],
  api: ['src/services/apiClient.js'],
}

export const ARQUIVOS_CRITICOS = Object.values(MODULOS).flat()

/**
 * Mudanças que alteram como a mutação roda sem tocar em arquivo crítico.
 * Caminhos a partir da raiz do repositório; os que terminam em `/` valem
 * para a pasta inteira. O servidor simulado entra aqui pelo mesmo motivo dos
 * fixtures e do `conftest.py` no backend: os testes de todas as stores
 * críticas dependem dele. Um `setupFiles` do Vitest, se for criado, também
 * precisa entrar nesta lista.
 *
 * Um PR que mexe nelas e em nenhum arquivo crítico muta um alvo fixo, pequeno
 * e conhecido, para a configuração nova ser exercitada antes do merge. Com
 * outro alvo no PR, o alvo fixo não entra: o Stryker já roda com a
 * configuração nova, e um arquivo bem testado a mais só diluiria o escore do
 * que mudou.
 */
export const CONFIGURACAO_DA_MUTACAO = [
  'frontend/stryker.config.mjs',
  'frontend/vitest.config.js',
  'frontend/vite.config.js',
  'frontend/package.json',
  'frontend/package-lock.json',
  'frontend/scripts/mutacao.mjs',
  'frontend/src/services/mock/',
  '.github/workflows/frontend-ci.yml',
]

/** Pequeno e sempre com mutantes: é também o canário da configuração. */
export const ALVO_DA_CONFIGURACAO = 'src/utils/cardapio.js'

// Mortos (inclusive por tempo esgotado) sobre os avaliados. CompileError,
// RuntimeError, Ignored e Pending não entram na conta, como no Stryker.
const DETECTADOS = new Set(['Killed', 'Timeout'])
const NAO_DETECTADOS = new Set(['Survived', 'NoCoverage'])

// `frontend/`, para os caminhos não dependerem da pasta de onde o script roda.
const RAIZ_DO_FRONT = fileURLToPath(new URL('..', import.meta.url))

const LEITURA_PADRAO = {
  // Arquivo, não pasta: `@/router` tem que cair no `src/router/index.js`.
  existe: (arquivo) => {
    try {
      return statSync(join(RAIZ_DO_FRONT, arquivo)).isFile()
    } catch {
      return false
    }
  },
  ler: (arquivo) => {
    try {
      return readFileSync(join(RAIZ_DO_FRONT, arquivo), 'utf8')
    } catch {
      return null
    }
  },
}

function normalizar(caminho) {
  return caminho.replaceAll('\\', '/')
}

function eConfiguracao(caminho) {
  return CONFIGURACAO_DA_MUTACAO.some((gatilho) =>
    gatilho.endsWith('/') ? caminho.startsWith(gatilho) : caminho === gatilho,
  )
}

/**
 * `src/x/y.test.js` ou `src/x/y.qualquer.test.js` -> o arquivo crítico de
 * mesmo nome (`y.js` ou `y.vue`), cortando o nome no primeiro ponto.
 */
function arquivoTestadoPeloNome(caminho) {
  const pasta = posix.dirname(caminho)
  const nome = posix.basename(caminho).split('.')[0]
  return [`${pasta}/${nome}.js`, `${pasta}/${nome}.vue`].find((arquivo) =>
    ARQUIVOS_CRITICOS.includes(arquivo),
  )
}

// `import x from '...'`, `import '...'`, `export ... from '...'` e `import('...')`.
const IMPORTS = /(?:\bfrom\s*|\bimport\s*\(?\s*)['"]([^'"]+)['"]/g

/** Caminho importado -> arquivo do projeto (a partir de `frontend/`), ou null. */
function resolverImport(origem, especificador, { existe }) {
  let base
  if (especificador.startsWith('@/')) base = `src/${especificador.slice(2)}`
  else if (especificador.startsWith('.')) base = posix.join(posix.dirname(origem), especificador)
  else return null // pacote do node_modules
  return [base, `${base}.js`, `${base}.vue`, `${base}/index.js`].find(existe) ?? null
}

/**
 * Arquivos críticos alcançados a partir de um arquivo, seguindo os imports
 * (estáticos e `import()` dinâmicos, como os das rotas) dentro do projeto.
 */
function criticosAlcancados(inicio, leitura) {
  const vistos = new Set([inicio])
  const fila = [inicio]
  const criticos = new Set()
  while (fila.length) {
    const atual = fila.shift()
    if (ARQUIVOS_CRITICOS.includes(atual)) criticos.add(atual)
    const conteudo = leitura.ler(atual)
    if (!conteudo) continue
    for (const [, especificador] of conteudo.matchAll(IMPORTS)) {
      const destino = resolverImport(atual, especificador, leitura)
      if (destino && !vistos.has(destino)) {
        vistos.add(destino)
        fila.push(destino)
      }
    }
  }
  return criticos
}

/**
 * Arquivos críticos a mutar, a partir dos arquivos alterados no PR (caminhos
 * a partir da raiz do repositório, como o `git diff` devolve):
 * - arquivo crítico alterado: ele mesmo;
 * - teste alterado: o arquivo crítico de mesmo nome; sem correspondência por
 *   nome, os arquivos críticos que ele importa, direta ou indiretamente (no
 *   backend, um teste sem correspondência muta o app inteiro);
 * - configuração da mutação: o alvo fixo, só se não houver outro alvo.
 *
 * `leitura.existe` e `leitura.ler` recebem caminhos a partir de `frontend/`;
 * arquivo apagado no PR não vira alvo.
 */
export function alvosDoPr(alterados, leitura = LEITURA_PADRAO) {
  const alvos = new Set()
  let configuracaoMudou = false
  for (const alterado of alterados.map(normalizar)) {
    if (eConfiguracao(alterado)) {
      configuracaoMudou = true
      continue
    }
    if (!alterado.startsWith('frontend/')) continue
    const caminho = alterado.slice('frontend/'.length)
    if (ARQUIVOS_CRITICOS.includes(caminho)) {
      alvos.add(caminho)
    } else if (caminho.startsWith('src/') && caminho.endsWith('.test.js')) {
      const peloNome = arquivoTestadoPeloNome(caminho)
      if (peloNome) alvos.add(peloNome)
      else criticosAlcancados(caminho, leitura).forEach((alvo) => alvos.add(alvo))
    }
  }
  const existentes = [...alvos].filter((alvo) => leitura.existe(alvo)).sort()
  if (configuracaoMudou && existentes.length === 0) return [ALVO_DA_CONFIGURACAO]
  return existentes
}

function contar(status) {
  const detectados = status.filter((s) => DETECTADOS.has(s)).length
  const avaliados = detectados + status.filter((s) => NAO_DETECTADOS.has(s)).length
  // Duas casas truncadas, como o escore do backend (Plano de Testes 5.1).
  const escore = avaliados ? Math.floor((detectados / avaliados) * 10_000) / 100 : null
  return { detectados, avaliados, escore }
}

/**
 * Escore do conjunto e de cada módulo crítico presente no relatório do
 * Stryker, e os módulos que não aparecem nele (`ausentes`).
 */
export function escoreDoRelatorio(relatorio) {
  if (!relatorio?.files || typeof relatorio.files !== 'object') {
    throw new Error('Relatório do Stryker sem a lista de arquivos (files).')
  }
  const statusPorArquivo = Object.fromEntries(
    Object.entries(relatorio.files).map(([arquivo, dados]) => [
      normalizar(arquivo),
      (dados.mutants ?? []).map((mutante) => mutante.status),
    ]),
  )
  const modulos = []
  const ausentes = []
  for (const [modulo, arquivos] of Object.entries(MODULOS)) {
    const presentes = arquivos.filter((arquivo) => arquivo in statusPorArquivo)
    if (presentes.length) {
      modulos.push({ modulo, ...contar(presentes.flatMap((arquivo) => statusPorArquivo[arquivo])) })
    } else {
      ausentes.push(modulo)
    }
  }
  modulos.sort((a, b) => a.modulo.localeCompare(b.modulo))
  return { conjunto: contar(Object.values(statusPorArquivo).flat()), modulos, ausentes }
}

// --- Linha de comando --------------------------------------------------------

function comandoAlvos(base) {
  let saida
  try {
    // A partir da raiz do repositório, para os caminhos baterem com a lista.
    saida = execFileSync('git', ['diff', '--name-only', `${base}...HEAD`], {
      cwd: join(RAIZ_DO_FRONT, '..'),
      encoding: 'utf8',
      stdio: ['ignore', 'pipe', 'pipe'],
    })
  } catch (falha) {
    console.error(`Não foi possível comparar com ${base}: ${falha.message}`)
    return 2
  }
  for (const alvo of alvosDoPr(saida.split('\n').filter(Boolean))) console.log(alvo)
  return 0
}

function linha(rotulo, { detectados, avaliados, escore }) {
  const texto = escore === null ? 'sem mutantes avaliados' : `${escore.toFixed(2)}%`
  return `| ${rotulo} | ${detectados} | ${avaliados} | ${texto} |`
}

function comandoEscore(caminho, { minimo, porModulo }) {
  let resultado
  try {
    resultado = escoreDoRelatorio(JSON.parse(readFileSync(caminho, 'utf8')))
  } catch (falha) {
    console.error(`Não dá para medir: ${falha.message}`)
    return 2
  }
  const medidos = porModulo ? resultado.modulos : [{ modulo: 'conjunto', ...resultado.conjunto }]
  console.log('| Módulo | Mortos | Avaliados | Escore |')
  console.log('|---|---|---|---|')
  for (const medido of medidos) console.log(linha(medido.modulo, medido))
  if (porModulo) console.log(linha('**geral**', resultado.conjunto))

  if (porModulo && resultado.ausentes.length) {
    console.error(`Não dá para medir: módulos fora do relatório: ${resultado.ausentes.join(', ')}.`)
    return 2
  }
  const semAvaliados = medidos.filter((m) => m.escore === null).map((m) => m.modulo)
  if (semAvaliados.length) {
    const onde = porModulo ? `nos módulos ${semAvaliados.join(', ')}` : 'no conjunto'
    console.error(`Não dá para medir: nenhum mutante avaliado ${onde}.`)
    return 2
  }
  const abaixo = medidos.filter((m) => m.escore < minimo)
  for (const m of abaixo) {
    console.error(`::error::Escore de mutação de ${m.modulo} abaixo de ${minimo}%: ${m.escore}%`)
  }
  return abaixo.length ? 1 : 0
}

/** Valor do `--minimo` (padrão 50), ou null se for inválido. */
function lerMinimo(argumentos) {
  const indice = argumentos.indexOf('--minimo')
  if (indice < 0) return 50
  const valor = argumentos[indice + 1]
  // Sem `Number('')` (que dá 0) nem outra opção no lugar do número.
  if (valor === undefined || valor.trim() === '' || valor.startsWith('--')) return null
  const minimo = Number(valor)
  return Number.isFinite(minimo) && minimo >= 0 && minimo <= 100 ? minimo : null
}

/** Ponto de entrada; devolve o código de saída (exportado para os testes). */
export function principal([comando, ...argumentos]) {
  if (comando === 'alvos' && argumentos[0]) return comandoAlvos(argumentos[0])
  if (comando === 'escore' && argumentos[0]) {
    const minimo = lerMinimo(argumentos)
    if (minimo === null) {
      console.error('--minimo inválido: use um número de 0 a 100.')
      return 2
    }
    return comandoEscore(argumentos[0], { minimo, porModulo: argumentos.includes('--por-modulo') })
  }
  console.error(
    'Uso: mutacao.mjs alvos <base> | escore <relatorio.json> [--minimo N] [--por-modulo]',
  )
  return 2
}

if (process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1]) {
  process.exitCode = principal(process.argv.slice(2))
}
