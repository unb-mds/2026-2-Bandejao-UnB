/**
 * Cobertura de linhas por módulo crítico do front (FE-19, #191, ADR 0013).
 *
 * O Vitest já reprova o job `testes (front)` quando um arquivo crítico fica
 * abaixo da meta (`coverage.thresholds`, `vitest.config.js`), e o log dele
 * lista a cobertura de todo o front, misturada. Este script lê o
 * `coverage-summary.json` e escreve só os arquivos críticos, agrupados por
 * módulo, no resumo do run. Os arquivos são os de cada módulo do `MODULOS`
 * (`mutacao.mjs`), os mesmos da mutação.
 *
 * O Vitest sozinho não pega arquivo crítico ausente: uma chave de
 * `thresholds` que não casa com nenhum arquivo é avaliada sobre 0 de 0
 * linhas, que conta como 100%. Quem fecha esse buraco é este script, que sai
 * com 2 quando um arquivo crítico não está no relatório.
 *
 * Comando, na pasta `frontend/` (o caminho do relatório é relativo à pasta
 * atual):
 *
 *   node scripts/cobertura.mjs resumo coverage/coverage-summary.json [--minimo 70]
 *       Imprime a tabela em Markdown. Saída 0: todos os arquivos críticos no
 *       mínimo. Saída 1: algum abaixo. Saída 2: não dá para medir (relatório
 *       ausente ou ilegível, arquivo crítico fora do relatório ou sem
 *       linhas) ou uso inválido (`--minimo` sem um número de 0 a 100,
 *       comando desconhecido).
 *
 * O motivo de cada reprovação sai no stdout (vai para o resumo do run, junto
 * da tabela) e no stderr como `::error::` (vira anotação no GitHub).
 *
 * Só usa a biblioteca padrão do Node.
 */
import { readFileSync, realpathSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { MODULOS, lerMinimo } from './mutacao.mjs'

/**
 * Meta de linhas de cada arquivo crítico (RNF06). É a única fonte: o
 * `vitest.config.js` monta o `coverage.thresholds` com ela e o workflow usa o
 * padrão do script.
 */
export const MINIMO_COBERTURA = 70

const normalizar = (caminho) => caminho.replaceAll('\\', '/')

/** Duas casas truncadas, como o escore da mutação (Plano de Testes 5.2). */
const truncar = (cobertas, total) => Math.floor((cobertas / total) * 10_000) / 100

/**
 * Cobertura de linhas de cada arquivo crítico presente no relatório e os
 * críticos que não dá para medir (`ausentes`: fora do relatório ou sem
 * nenhuma linha, porque 0 de 0 não prova nada).
 *
 * As chaves do `coverage-summary.json` são caminhos absolutos, que mudam
 * entre o CI e a máquina de cada um; o arquivo é achado pelo final do
 * caminho, a partir de uma barra, para `src/stores/auth.js` não casar com
 * `frontend/meusrc/stores/auth.js`. Linhas malformadas (sem `covered` ou
 * `total` inteiros, ou `covered` fora de 0 a `total`) também são ausentes:
 * virariam `NaN%` e aprovariam sem medir.
 */
export function coberturaDoRelatorio(relatorio) {
  if (relatorio === null || typeof relatorio !== 'object' || Array.isArray(relatorio)) {
    throw new Error('o relatório não é um objeto do coverage-summary.json')
  }
  const entradas = Object.entries(relatorio)
    .filter(([chave]) => chave !== 'total')
    .map(([chave, dados]) => [normalizar(chave), dados])
  const arquivos = []
  const ausentes = []
  for (const [modulo, lista] of Object.entries(MODULOS)) {
    for (const arquivo of lista) {
      const achado = entradas.find(([chave]) => chave.endsWith(`/${arquivo}`))
      const linhas = achado?.[1]?.lines
      if (!linhasValidas(linhas)) {
        ausentes.push(arquivo)
        continue
      }
      arquivos.push({
        modulo,
        arquivo,
        cobertas: linhas.covered,
        total: linhas.total,
        pct: truncar(linhas.covered, linhas.total),
      })
    }
  }
  return { arquivos, ausentes }
}

function linhasValidas(linhas) {
  return (
    Number.isInteger(linhas?.total) &&
    Number.isInteger(linhas.covered) &&
    linhas.total > 0 &&
    linhas.covered >= 0 &&
    linhas.covered <= linhas.total
  )
}

/** Motivo de não medir: no resumo do run (stdout) e como anotação (stderr). */
function naoMedido(motivo) {
  console.log(`\n**Não medido:** ${motivo}`)
  console.error(`::error::Não dá para medir: ${motivo}`)
}

const linha = (modulo, arquivo, cobertas, total, pct) =>
  `| ${modulo} | ${arquivo} | ${cobertas}/${total} | ${pct.toFixed(2)}% |`

function comandoResumo(caminho, minimo) {
  let resultado
  try {
    resultado = coberturaDoRelatorio(JSON.parse(readFileSync(caminho, 'utf8')))
  } catch (falha) {
    naoMedido(falha.message)
    return 2
  }
  const { arquivos, ausentes } = resultado

  console.log('| Módulo | Arquivo | Linhas | Cobertura |')
  console.log('|---|---|---|---|')
  for (const a of arquivos)
    console.log(linha(a.modulo, `\`${a.arquivo}\``, a.cobertas, a.total, a.pct))
  const cobertas = arquivos.reduce((soma, a) => soma + a.cobertas, 0)
  const total = arquivos.reduce((soma, a) => soma + a.total, 0)
  if (total) console.log(linha('**conjunto**', '', cobertas, total, truncar(cobertas, total)))

  if (ausentes.length) {
    naoMedido(
      `${ausentes.map((a) => `\`${a}\``).join(', ')} (fora do relatório, sem linhas ou com linhas malformadas).`,
    )
    // Ausente vence abaixo: sem medir tudo, o veredito não é "só cobertura baixa".
    return 2
  }
  const abaixo = arquivos.filter((a) => a.pct < minimo)
  for (const a of abaixo) {
    const pct = `${a.pct.toFixed(2)}%`
    console.log(`\n**Abaixo de ${minimo}%:** \`${a.arquivo}\` (${pct})`)
    console.error(`::error::Cobertura de ${a.arquivo} abaixo de ${minimo}%: ${pct}`)
  }
  return abaixo.length ? 1 : 0
}

/** Ponto de entrada; devolve o código de saída (exportado para os testes). */
export function principal([comando, ...argumentos]) {
  if (comando === 'resumo' && argumentos[0]) {
    const minimo = lerMinimo(argumentos, MINIMO_COBERTURA)
    if (minimo === null) {
      console.error('--minimo inválido: use um número de 0 a 100.')
      return 2
    }
    return comandoResumo(argumentos[0], minimo)
  }
  console.error('Uso: cobertura.mjs resumo <coverage-summary.json> [--minimo N]')
  return 2
}

// `realpathSync`: chamado por um link simbólico, o argv[1] não é o caminho real
// do módulo, e sem isso o script não rodaria e sairia com 0.
if (process.argv[1] && fileURLToPath(import.meta.url) === realpathSync(process.argv[1])) {
  process.exitCode = principal(process.argv.slice(2))
}
