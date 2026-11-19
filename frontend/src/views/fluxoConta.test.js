import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createMemoryHistory, createRouter } from 'vue-router'
import { carregarSessaoAoAbrir, exigirCampus, routes } from '@/router'
import { usePreferenciasStore } from '@/stores/preferencias'
import { ApiError, apiClient } from '@/services/apiClient'
import { reiniciarSimulacao } from '@/services/mock/servidor'
import App from '@/App.vue'

/**
 * Desfechos do fluxo 4b (C4 do front): cadastro, confirmação de e-mail e
 * login, com as telas de verdade e o servidor simulado no contrato v1.
 */

// Segunda-feira, 28/09/2026, 12h.
const AGORA = new Date(2026, 8, 28, 12, 0)
const SENHA = 'senhaforte'
const ALUNO = { matricula: '241987650', email: '241987650@aluno.unb.br', apelido: 'novo_aluno' }
const CHAVE_DO_SIMULADO = 'bandejao:backend-simulado:v2'

async function montarEm(caminho, { campus = null } = {}) {
  const pinia = createPinia()
  setActivePinia(pinia)
  if (campus) usePreferenciasStore().escolherCampus(campus)

  const router = createRouter({ history: createMemoryHistory(), routes })
  router.beforeEach(carregarSessaoAoAbrir)
  router.beforeEach(exigirCampus)
  router.push(caminho)
  await router.isReady()
  const wrapper = mount(App, { global: { plugins: [pinia, router] }, attachTo: document.body })
  await flushPromises()
  return { wrapper, router }
}

/** Campo pelo rótulo visível, como a pessoa o encontra na tela. */
function campo(wrapper, rotulo) {
  const label = wrapper.findAll('label').find((l) => l.text() === rotulo)
  if (!label) throw new Error(`Campo "${rotulo}" não está na tela`)
  return wrapper.find(`[id="${label.attributes('for')}"]`)
}

function botao(wrapper, texto) {
  const encontrado = wrapper.findAll('button').find((b) => b.text().includes(texto))
  if (!encontrado) throw new Error(`Botão "${texto}" não está na tela`)
  return encontrado
}

async function esperarRota(router, nome) {
  await vi.waitFor(() => expect(router.currentRoute.value.name).toBe(nome))
  await flushPromises()
}

async function enviar(wrapper) {
  await wrapper.find('form').trigger('submit')
  await flushPromises()
}

/** Cadastro direto na API simulada, para os testes que começam depois dele. */
function cadastrarAluno() {
  return apiClient.post('/cadastro/', {
    tipoUsuario: 'estudante',
    emailInstitucional: ALUNO.email,
    senha: SENHA,
    apelido: ALUNO.apelido,
    aceitePrivacidade: true,
  })
}

const tokenDoLink = (link) => new URL(link, 'http://x').searchParams.get('token')

beforeEach(() => {
  vi.useFakeTimers({ toFake: ['Date'] })
  vi.setSystemTime(AGORA)
  localStorage.clear()
  reiniciarSimulacao()
  setActivePinia(createPinia())
})

afterEach(() => {
  vi.useRealTimers()
  document.body.innerHTML = ''
})

describe('CadastroView: desfechos do envio', () => {
  async function preencherAluno(wrapper) {
    await botao(wrapper, 'Aluno').trigger('click')
    await campo(wrapper, 'Apelido (nick)').setValue(ALUNO.apelido)
    await campo(wrapper, 'E-mail institucional').setValue(ALUNO.email)
    await campo(wrapper, 'Senha').setValue(SENHA)
    await wrapper.find('input[type="checkbox"]').setValue(true)
  }

  it('201: vai para "verifique seu e-mail" com o e-mail da resposta', async () => {
    const { wrapper, router } = await montarEm('/cadastro')
    await preencherAluno(wrapper)

    await enviar(wrapper)

    await esperarRota(router, 'confirmar-email')
    expect(router.currentRoute.value.query.email).toBe(ALUNO.email)
    expect(wrapper.text()).toContain('Verifique seu e-mail')
  })

  it('409: pede o apelido num campo a mais e mantém os outros campos preenchidos', async () => {
    await apiClient.post('/cadastro/', {
      tipoUsuario: 'professor_servidor',
      matriculaSiape: '1234567',
      emailInstitucional: 'maria.silva@unb.br',
      senha: SENHA,
      aceitePrivacidade: true,
    })
    const { wrapper, router } = await montarEm('/cadastro')
    await botao(wrapper, 'Servidor').trigger('click')
    expect(wrapper.findAll('label').some((l) => l.text() === 'Apelido (nick)')).toBe(false)
    await campo(wrapper, 'SIAPE').setValue('7654321')
    await campo(wrapper, 'E-mail institucional').setValue('mariasilva@unb.br')
    await campo(wrapper, 'Senha').setValue(SENHA)
    await wrapper.find('input[type="checkbox"]').setValue(true)

    await enviar(wrapper)

    await vi.waitFor(() => expect(wrapper.find('[role="alert"]').exists()).toBe(true))
    expect(router.currentRoute.value.name).toBe('cadastro')
    expect(campo(wrapper, 'Apelido (nick)').element.value).toBe('mariasilva1')
    expect(campo(wrapper, 'SIAPE').element.value).toBe('7654321')
    expect(campo(wrapper, 'E-mail institucional').element.value).toBe('mariasilva@unb.br')
    expect(campo(wrapper, 'Senha').element.value).toBe(SENHA)

    await campo(wrapper, 'Apelido (nick)').setValue('profa_maria')
    await enviar(wrapper)

    await esperarRota(router, 'confirmar-email')
  })

  it('422 de conta repetida: mensagem que não diz qual campo já existe (RF01.5)', async () => {
    await cadastrarAluno()
    const { wrapper, router } = await montarEm('/cadastro')
    await preencherAluno(wrapper)
    await campo(wrapper, 'Apelido (nick)').setValue('outro_nick')

    await enviar(wrapper)

    await vi.waitFor(() =>
      expect(wrapper.find('[role="alert"]').text()).toBe(
        'Matrícula/SIAPE ou e-mail já cadastrados.',
      ),
    )
    expect(router.currentRoute.value.name).toBe('cadastro')
  })
})

describe('ConfirmarEmailView: token na query string', () => {
  it('token válido: "conta confirmada"', async () => {
    const { linkSimulado } = await cadastrarAluno()

    const { wrapper } = await montarEm(`/confirmar-email?token=${tokenDoLink(linkSimulado)}`)

    await vi.waitFor(() => expect(wrapper.text()).toContain('Conta confirmada!'))
  })

  it('token já usado: "link inválido" e o reenvio pelo próprio token', async () => {
    const { linkSimulado } = await cadastrarAluno()
    const token = tokenDoLink(linkSimulado)
    await apiClient.post(`/confirmar-email/${token}/`)

    const { wrapper } = await montarEm(`/confirmar-email?token=${token}`)

    await vi.waitFor(() => expect(wrapper.text()).toContain('Peça um novo link abaixo.'))
    // No link inválido, o reenvio não pede nada: usa o próprio token.
    await enviar(wrapper)

    await vi.waitFor(() => expect(wrapper.text()).toContain('novo link de confirmação'))
  })

  it('erro que não é do token (sem conexão): oferece tentar de novo', async () => {
    const { linkSimulado } = await cadastrarAluno()
    const espiao = vi.spyOn(apiClient, 'post').mockImplementationOnce(() =>
      Promise.reject(new ApiError(0, { codigo: 'sem_conexao' })),
    )
    const { wrapper } = await montarEm(`/confirmar-email?token=${tokenDoLink(linkSimulado)}`)

    await vi.waitFor(() => expect(wrapper.text()).toContain('Não conseguimos confirmar agora.'))
    espiao.mockRestore()
    await botao(wrapper, 'Tentar de novo').trigger('click')

    await vi.waitFor(() => expect(wrapper.text()).toContain('Conta confirmada!'))
  })
})

describe('LoginView', () => {
  async function entrarPelaTela(wrapper, matricula = ALUNO.matricula, senha = SENHA) {
    await campo(wrapper, 'Matrícula ou SIAPE').setValue(matricula)
    await campo(wrapper, 'Senha').setValue(senha)
    await enviar(wrapper)
  }

  async function cadastrarEConfirmar() {
    const { linkSimulado } = await cadastrarAluno()
    await apiClient.post(`/confirmar-email/${tokenDoLink(linkSimulado)}/`)
  }

  it('com campus lembrado, o login leva à tela do campus (RF03.4)', async () => {
    await cadastrarEConfirmar()
    const { wrapper, router } = await montarEm('/login', { campus: 'darcy' })

    await entrarPelaTela(wrapper)

    await esperarRota(router, 'inicio')
    expect(wrapper.find(`[aria-label="Perfil de ${ALUNO.apelido}"]`).exists()).toBe(true)
  })

  it('sem campus lembrado, o login leva à escolha do campus', async () => {
    await cadastrarEConfirmar()
    const { wrapper, router } = await montarEm('/login')

    await entrarPelaTela(wrapper)

    await esperarRota(router, 'campus')
    expect(router.currentRoute.value.name).toBe('campus')
  })

  it('conta pendente: mostra o erro e o reenvio do link (RF02)', async () => {
    await cadastrarAluno()
    const { wrapper } = await montarEm('/login')

    await entrarPelaTela(wrapper)

    await vi.waitFor(() => expect(wrapper.text()).toContain('Confirme seu e-mail antes de entrar.'))
    await botao(wrapper, 'Reenviar link de confirmação').trigger('click')
    await vi.waitFor(() =>
      expect(wrapper.find('[role="status"]').text()).toContain('novo link de confirmação'),
    )
  })

  it('senha errada: mensagem genérica, sem dizer se a conta existe', async () => {
    await cadastrarEConfirmar()
    const { wrapper, router } = await montarEm('/login')

    await entrarPelaTela(wrapper, ALUNO.matricula, 'errada123')

    await vi.waitFor(() =>
      expect(wrapper.find('[role="alert"]').text()).toContain('Matrícula/SIAPE ou senha incorretas.'),
    )
    expect(router.currentRoute.value.name).toBe('login')
  })
})

describe('nada do formulário fica salvo no aparelho (front 4b, RI09)', () => {
  it('depois de cadastrar e entrar, o localStorage não tem senha, e-mail nem matrícula', async () => {
    const cadastro = await montarEm('/cadastro', { campus: 'darcy' })
    await botao(cadastro.wrapper, 'Aluno').trigger('click')
    await campo(cadastro.wrapper, 'Apelido (nick)').setValue(ALUNO.apelido)
    await campo(cadastro.wrapper, 'E-mail institucional').setValue(ALUNO.email)
    await campo(cadastro.wrapper, 'Senha').setValue(SENHA)
    await cadastro.wrapper.find('input[type="checkbox"]').setValue(true)
    await enviar(cadastro.wrapper)
    await esperarRota(cadastro.router, 'confirmar-email')
    cadastro.wrapper.unmount()

    const reenvio = await apiClient.post('/reenviar-confirmacao/', {
      matriculaSiape: ALUNO.matricula,
    })
    await apiClient.post(`/confirmar-email/${tokenDoLink(reenvio.linkSimulado)}/`)
    const login = await montarEm('/login')
    await campo(login.wrapper, 'Matrícula ou SIAPE').setValue(ALUNO.matricula)
    await campo(login.wrapper, 'Senha').setValue(SENHA)
    await enviar(login.wrapper)
    await esperarRota(login.router, 'inicio')

    // O banco do servidor simulado (só em desenvolvimento) faz o papel do backend.
    const doApp = Object.keys(localStorage).filter((chave) => chave !== CHAVE_DO_SIMULADO)
    expect(doApp.length).toBeGreaterThan(0) // as preferências continuam lá
    for (const chave of doApp) {
      const valor = localStorage.getItem(chave)
      expect(valor).not.toContain(SENHA)
      expect(valor).not.toContain(ALUNO.email)
      expect(valor).not.toContain(ALUNO.matricula)
    }
  })
})
