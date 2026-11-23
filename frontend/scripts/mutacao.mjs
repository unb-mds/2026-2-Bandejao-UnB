/**
 * Seleção dos alvos e escore da mutação do front (FE-17, #189, ADR 0013).
 *
 * O modo `--incremental` do Stryker só reaproveita o resultado de uma rodada
 * anterior; ele não sabe o que mudou no PR. Como no backend (BE-19), quem
 * escolhe os arquivos é este script, e o Stryker recebe a lista em `--mutate`.
 *
 * Comandos (rodar de dentro de `frontend/`):
 *
 *   node scripts/mutacao.mjs alvos origin/develop
 *       Imprime um arquivo crítico por linha para o que o PR mudou em
 *       relação à base. Sem saída quando o PR não mexe em arquivo crítico
 *       nem na configuração da mutação. Saída 2 se o `git diff` falhar.
 *
 *   node scripts/mutacao.mjs escore reports/mutation/mutation.json [--minimo 50] [--por-modulo]
 *       Calcula o escore a partir do relatório JSON do Stryker. Sem
 *       `--por-modulo` (o PR), o mínimo vale para o conjunto dos mutantes
 *       rodados; com ele (a rodada semanal), vale para cada módulo crítico.
 *       Saída 0: no mínimo. Saída 1: abaixo. Saída 2: não dá para medir.
 *
 * Só usa a biblioteca padrão do Node.
 */
import { execFileSync } from 'node:child_process'
import { existsSync, readFileSync } from 'node:fs'
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
 * Mudanças que alteram como a mutação roda sem tocar em arquivo crítico. Um
 * PR que mexe nelas e em nenhum arquivo crítico muta um alvo fixo, pequeno e
 * conhecido, para a configuração nova ser exercitada antes do merge. Com
 * outro alvo no PR, o alvo fixo não entra: o Stryker já roda com a
 * configuração nova, e um arquivo bem testado a mais só diluiria o escore do
 * que mudou. Caminhos a partir da raiz do repositório.
 */
export const CONFIGURACAO_DA_MUTACAO = [
  'frontend/stryker.config.mjs',
  'frontend/vitest.config.js',
  'frontend/vite.config.js',
  'frontend/package.json',
  'frontend/package-lock.json',
  'frontend/scripts/mutacao.mjs',
  '.github/workflows/frontend-ci.yml',
]

/** Pequeno e sempre com mutantes: é também o canário da configuração. */
export const ALVO_DA_CONFIGURACAO = 'src/utils/cardapio.js'

// Mortos (inclusive por tempo esgotado) sobre os avaliados. CompileError,
// RuntimeError, Ignored e Pending não entram na conta, como no Stryker.
const DETECTADOS = new Set(['Killed', 'Timeout'])
const NAO_DETECTADOS = new Set(['Survived', 'NoCoverage'])

function normalizar(caminho) {
  return caminho.replaceAll('\\', '/')
}

/** `src/x/y.test.js` -> o arquivo crítico que ele testa (`y.js` ou `y.vue`). */
function arquivoTestado(caminho) {
  const base = caminho.replace(/\.test\.js$/, '')
  return [`${base}.js`, `${base}.vue`].find((arquivo) => ARQUIVOS_CRITICOS.includes(arquivo))
}

/**
 * Arquivos críticos a mutar, a partir dos arquivos alterados no PR (caminhos
 * a partir da raiz do repositório, como o `git diff` devolve). `existe`
 * recebe o caminho a partir de `frontend/` e tira os arquivos apagados.
 */
export function alvosDoPr(alterados, existe = (arquivo) => existsSync(arquivo)) {
  const alvos = new Set()
  let configuracaoMudou = false
  for (const alterado of alterados.map(normalizar)) {
    if (CONFIGURACAO_DA_MUTACAO.includes(alterado)) {
      configuracaoMudou = true
      continue
    }
    if (!alterado.startsWith('frontend/')) continue
    const caminho = alterado.slice('frontend/'.length)
    const alvo = ARQUIVOS_CRITICOS.includes(caminho) ? caminho : arquivoTestado(caminho)
    if (alvo) alvos.add(alvo)
  }
  const existentes = [...alvos].filter((alvo) => existe(alvo)).sort()
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

/** Escore do conjunto e de cada módulo crítico presente no relatório do Stryker. */
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
  const modulos = Object.entries(MODULOS)
    .map(([modulo, arquivos]) => {
      const presentes = arquivos.filter((arquivo) => arquivo in statusPorArquivo)
      if (!presentes.length) return null
      return { modulo, ...contar(presentes.flatMap((arquivo) => statusPorArquivo[arquivo])) }
    })
    .filter(Boolean)
    .sort((a, b) => a.modulo.localeCompare(b.modulo))
  return { conjunto: contar(Object.values(statusPorArquivo).flat()), modulos }
}

// --- Linha de comando --------------------------------------------------------

function comandoAlvos(base) {
  let saida
  try {
    // A partir da raiz do repositório, para os caminhos baterem com a lista.
    saida = execFileSync('git', ['diff', '--name-only', `${base}...HEAD`], {
      cwd: fileURLToPath(new URL('../..', import.meta.url)),
      encoding: 'utf8',
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

  if (!medidos.length || medidos.some((m) => m.escore === null)) {
    console.error('Não dá para medir: há módulo sem nenhum mutante avaliado.')
    return 2
  }
  const abaixo = medidos.filter((m) => m.escore < minimo)
  for (const m of abaixo) {
    console.error(`::error::Escore de mutação de ${m.modulo} abaixo de ${minimo}%: ${m.escore}%`)
  }
  return abaixo.length ? 1 : 0
}

function principal([comando, ...argumentos]) {
  if (comando === 'alvos' && argumentos[0]) return comandoAlvos(argumentos[0])
  if (comando === 'escore' && argumentos[0]) {
    const indice = argumentos.indexOf('--minimo')
    const minimo = indice >= 0 ? Number(argumentos[indice + 1]) : 50
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
