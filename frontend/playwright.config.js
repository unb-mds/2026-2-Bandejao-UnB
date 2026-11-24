import { defineConfig } from '@playwright/test'

/**
 * Testes de ponta a ponta (FE-18, Plano de Testes 3.5): o PWA de produção,
 * a API e o MySQL sobem com o e2e/docker-compose.yml, e o Playwright usa o
 * app como uma pessoa usaria. Um fluxo por marco (M1 a M4) e os testes de
 * qualidade da FE-16, cada um no celular e no desktop (FE-20).
 */
export default defineConfig({
  testDir: './e2e',
  testMatch: '**/*.spec.js',
  globalSetup: './e2e/apoio/preparar.js',
  // Cada fluxo usa contas e dados próprios, então os projetos rodam juntos. O
  // teste de qualidade da FE-16 reusa a conta do M4 só para ler: entrar não
  // encerra as outras sessões, e ele não muda pontos nem a adesão.
  fullyParallel: true,
  forbidOnly: Boolean(process.env.CI),
  // Sem segunda tentativa: o banco só é limpo uma vez por rodada, então uma
  // tentativa nova do M2, do M3 ou do M4 falharia pelo que a primeira gravou
  // (check-in feito, avaliação enviada, adesão ligada), e não pela causa real.
  retries: 0,
  reporter: process.env.CI ? [['github'], ['html', { open: 'never' }]] : 'list',
  use: {
    baseURL: process.env.E2E_URL ?? 'http://localhost:8080',
    // O relógio do backend começa no almoço de Brasília (docker-compose).
    timezoneId: 'America/Sao_Paulo',
    locale: 'pt-BR',
    // O trace da tentativa que falhou (no CI, no artefato e2e-relatorio).
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  projects: [
    {
      name: 'celular',
      use: { viewport: { width: 360, height: 800 }, isMobile: true, hasTouch: true },
    },
    {
      name: 'desktop',
      use: { viewport: { width: 1366, height: 768 } },
    },
  ],
})
