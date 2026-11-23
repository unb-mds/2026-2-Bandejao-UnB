import { defineConfig, globalIgnores } from 'eslint/config'
import globals from 'globals'
import js from '@eslint/js'
import pluginVue from 'eslint-plugin-vue'
import pluginVitest from '@vitest/eslint-plugin'
import pluginOxlint from 'eslint-plugin-oxlint'
import skipFormatting from 'eslint-config-prettier/flat'

export default defineConfig([
  {
    name: 'app/files-to-lint',
    files: ['**/*.{vue,js,mjs,jsx}'],
  },

  globalIgnores(['**/dist/**', '**/dist-ssr/**', '**/coverage/**']),

  {
    languageOptions: {
      globals: {
        ...globals.browser,
      },
    },
  },

  {
    // Scripts do CI (mutação): rodam no Node.
    name: 'app/scripts-node',
    files: ['scripts/**/*.{js,mjs}', '*.config.{js,mjs}'],
    languageOptions: {
      globals: {
        ...globals.node,
      },
    },
  },

  js.configs.recommended,
  ...pluginVue.configs['flat/essential'],

  {
    // Os testes ficam ao lado do código (`*.test.js`): o padrão `__tests__/` do
    // modelo do Vite não pegava nenhum, e as regras do Vitest não rodavam.
    ...pluginVitest.configs.recommended,
    files: ['src/**/*.test.js', 'src/**/__tests__/*', 'scripts/**/*.test.js'],
    rules: {
      ...pluginVitest.configs.recommended.rules,
      // Teste sem asserção passa sem testar nada (Plano de Testes, checklist da IA).
      'vitest/expect-expect': 'error',
    },
  },

  {
    // SAST do Vue (Plano de Testes 4): `v-html` abre caminho para XSS.
    name: 'app/seguranca-vue',
    files: ['**/*.vue'],
    rules: {
      'vue/no-v-html': 'error',
    },
  },

  ...pluginOxlint.buildFromOxlintConfigFile('.oxlintrc.json'),

  skipFormatting,
])
