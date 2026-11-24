import { fileURLToPath } from 'node:url'
import { mergeConfig, defineConfig, configDefaults } from 'vitest/config'
import viteConfig from './vite.config.js'

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
        // crítico. Os da gamificação entram aqui no PR que os criar (a
        // gamificacaoStore e o PontosAviso entraram na FE-10). O resto é
        // medido, sem meta.
        thresholds: Object.fromEntries(
          [
            'src/services/apiClient.js',
            'src/stores/auth.js',
            'src/stores/cardapio.js',
            'src/stores/avaliacoes.js',
            'src/stores/fila.js',
            'src/stores/gamificacao.js',
            'src/components/PontosAviso.vue',
            'src/services/leituraPosicao.js',
            'src/utils/cardapio.js',
            'src/router/index.js',
          ].map((arquivo) => [arquivo, { lines: 70 }]),
        ),
      },
    },
  }),
)
