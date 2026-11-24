// Mutação do front (FE-17, RNF06, ADR 0013, Plano de Testes 3.7 e 5.2).
// Por padrão muta todos os arquivos críticos (rodada semanal). No PR, o job
// `mutacao` passa só os alterados em `--mutate` (scripts/mutacao.mjs).
import { ARQUIVOS_CRITICOS } from './scripts/mutacao.mjs'

/** @type {import('@stryker-mutator/api/core').PartialStrykerOptions} */
export default {
  testRunner: 'vitest',
  vitest: { configFile: 'vitest.config.js' },
  // O vitest-runner sempre mede a cobertura por teste: cada mutante roda só
  // os testes que passam por ele.
  coverageAnalysis: 'perTest',
  mutate: ARQUIVOS_CRITICOS,
  // `break`: a rodada falha abaixo de 50% (meta do RNF06) no conjunto mutado.
  thresholds: { high: 80, low: 60, break: 50 },
  reporters: ['clear-text', 'progress', 'html', 'json'],
  // Relatórios em reports/mutation/ (mutation.html e mutation.json).
  htmlReporter: { fileName: 'reports/mutation/mutation.html' },
  jsonReporter: { fileName: 'reports/mutation/mutation.json' },
  tempDirName: '.stryker-tmp',
  cleanTempDir: 'always',
}
