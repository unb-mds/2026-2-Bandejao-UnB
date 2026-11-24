import { fileURLToPath } from 'node:url'
import { mergeConfig, defineConfig, configDefaults } from 'vitest/config'
import viteConfig from './vite.config.js'
import { ARQUIVOS_CRITICOS } from './scripts/mutacao.mjs'

export default mergeConfig(
  viteConfig,
  defineConfig({
    test: {
      environment: 'jsdom',
      // .stryker-tmp: cópias do projeto que o Stryker cria durante a mutação.
      exclude: [...configDefaults.exclude, 'e2e/**', '.stryker-tmp/**'],
      root: fileURLToPath(new URL('./', import.meta.url)),
      coverage: {
        provider: 'v8',
        include: ['src/**/*.{js,vue}'],
        exclude: ['src/**/*.test.js', 'src/services/mock/**'],
        reporter: ['text-summary', 'text', 'html', 'json-summary'],
        // Meta do RNF06 (Plano de Testes 1 e 2): 70% de linhas em cada arquivo
        // crítico. A lista é a mesma da mutação (scripts/mutacao.mjs), para a
        // cobertura e a mutação não divergirem: um arquivo crítico novo entra
        // nas duas portas de uma vez (FE-19). O resto é medido, sem meta.
        thresholds: Object.fromEntries(
          ARQUIVOS_CRITICOS.map((arquivo) => [arquivo, { lines: 70 }]),
        ),
      },
    },
  }),
)
