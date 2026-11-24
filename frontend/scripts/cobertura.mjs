/**
 * Cobertura de linhas por módulo crítico do front (FE-19, #191, ADR 0013).
 *
 * O Vitest já reprova o job `testes (front)` quando um arquivo crítico fica
 * abaixo de 70% (`coverage.thresholds`, `vitest.config.js`), mas só diz qual
 * arquivo caiu. Este script lê o `coverage-summary.json` e escreve a tabela
 * de todos os arquivos críticos, por módulo, para o resumo do run: é o
 * relatório que a FE-19 anexa à issue. Os arquivos são os mesmos da mutação
 * (`ARQUIVOS_CRITICOS`, `mutacao.mjs`).
 *
 * Comando (de qualquer pasta):
 *
 *   node scripts/cobertura.mjs resumo coverage/coverage-summary.json [--minimo 70]
 *       Imprime a tabela em Markdown. Saída 0: todos os arquivos críticos no
 *       mínimo. Saída 1: algum abaixo. Saída 2: não dá para medir (relatório
 *       ausente ou ilegível, arquivo crítico fora do relatório ou sem
 *       linhas) ou uso inválido (`--minimo` sem um número de 0 a 100,
 *       comando desconhecido).
 *
 * Só usa a biblioteca padrão do Node.
 */
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { MODULOS, lerMinimo } from './mutacao.mjs'

const MINIMO_PADRAO = 70

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
 * `src/outra/auth.js`.
 */
export function coberturaDoRelatorio(relatorio) {
  const entradas = Object.entries(relatorio)
    .filter(([chave]) => chave !== 'total')
    .map(([chave, dados]) => [normalizar(chave), dados])
  const arquivos = []
  const ausentes = []
  for (const [modulo, lista] of Object.entries(MODULOS)) {
    for (const arquivo of lista) {
      const achado = entradas.find(([chave]) => chave.endsWith(`/${arquivo}`))
      const linhas = achado?.[1]?.lines
      if (!linhas?.total) {
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

const linha = (modulo, arquivo, cobertas, total, pct) =>
  `| ${modulo} | ${arquivo} | ${cobertas}/${total} | ${pct.toFixed(2)}% |`

function comandoResumo(caminho, minimo) {
  let resultado
  try {
    resultado = coberturaDoRelatorio(JSON.parse(readFileSync(caminho, 'utf8')))
  } catch (falha) {
    console.error(`Não dá para medir: ${falha.message}`)
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
    console.error(
      `Não dá para medir: arquivos críticos fora do relatório ou sem linhas: ${ausentes.join(', ')}.`,
    )
    return 2
  }
  const abaixo = arquivos.filter((a) => a.pct < minimo)
  for (const a of abaixo) {
    console.error(`::error::Cobertura de ${a.arquivo} abaixo de ${minimo}%: ${a.pct}%`)
  }
  return abaixo.length ? 1 : 0
}

/** Ponto de entrada; devolve o código de saída (exportado para os testes). */
export function principal([comando, ...argumentos]) {
  if (comando === 'resumo' && argumentos[0]) {
    const minimo = lerMinimo(argumentos, MINIMO_PADRAO)
    if (minimo === null) {
      console.error('--minimo inválido: use um número de 0 a 100.')
      return 2
    }
    return comandoResumo(argumentos[0], minimo)
  }
  console.error('Uso: cobertura.mjs resumo <coverage-summary.json> [--minimo N]')
  return 2
}

if (process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1]) {
  process.exitCode = principal(process.argv.slice(2))
}
