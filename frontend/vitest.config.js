import { fileURLToPath } from 'node:url'
import { mergeConfig, defineConfig, configDefaults } from 'vitest/config'
import viteConfig from './vite.config.js'
import { ARQUIVOS_CRITICOS } from './scripts/mutacao.mjs'
import { MINIMO_COBERTURA } from './scripts/cobertura.mjs'

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
        // crítico (MINIMO_COBERTURA, scripts/cobertura.mjs). A lista é a mesma
        // da mutação (scripts/mutacao.mjs), para a cobertura e a mutação não
        // divergirem: um arquivo crítico novo entra nas duas portas de uma vez.
        // O resto é medido, sem meta.
        //
        // Atenção: uma chave daqui que não casa com nenhum arquivo é avaliada
        // sobre 0 de 0 linhas, que conta como 100%, sem aviso. Arquivo crítico
        // ausente é pego pelo scripts/cobertura.mjs (saída 2) no job
        // `testes (front)` e pelo teste "todo arquivo crítico existe".
        thresholds: Object.fromEntries(
          ARQUIVOS_CRITICOS.map((arquivo) => [arquivo, { lines: MINIMO_COBERTURA }]),
        ),
      },
    },
  }),
)
