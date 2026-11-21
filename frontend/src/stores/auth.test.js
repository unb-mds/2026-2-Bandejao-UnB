import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useAuthStore } from './auth'
import { ApiError, apiClient } from '@/services/apiClient'
import { CONTA_DEMO } from '@/services/mock/banco'
import { reiniciarSimulacao, simulacao } from '@/services/mock/servidor'

/**
 * Integração: authStore + apiClient + servidor simulado (Plano de Testes,
 * "Integração" do front). Os corpos seguem o contrato OpenAPI v1 (BE-03).
 */

// Segunda-feira, 28/09/2026, 12h — almoço em andamento.
const SEGUNDA_MEIO_DIA = new Date(2026, 8, 28, 12, 0)
const ALMOCO_HOJE = { campus: 3, data: '2026-09-28', refeicao: 'almoco' }

beforeEach(() => {
  vi.useFakeTimers({ toFake: ['Date'] })
  vi.setSystemTime(SEGUNDA_MEIO_DIA)
  reiniciarSimulacao()
  setActivePinia(createPinia())
})

afterEach(() => {
  vi.useRealTimers()
  vi.restoreAllMocks()
})

describe('authStore com o servidor simulado', () => {
  it('a primeira escrita sem sessão (cadastro) já funciona: o apiClient busca o csrftoken', async () => {
    document.cookie = 'csrftoken=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/'
    const auth = useAuthStore()

    const criado = await auth.cadastrar({
      tipoUsuario: 'estudante',
      emailInstitucional: '241987650@aluno.unb.br',
      senha: 'senhaforte',
      apelido: 'novo_aluno',
      aceitePrivacidade: true,
    })

    expect(criado.status).toBe('pendente')
  })

  it('login guarda só apelido, tipo e avisoPrivacidadePendente', async () => {
    const auth = useAuthStore()

    await auth.entrar(CONTA_DEMO.email, CONTA_DEMO.senha)

    expect(auth.estaAutenticado).toBe(true)
    expect(auth.usuario).toEqual({
      apelido: CONTA_DEMO.apelido,
      tipo: 'estudante',
      avisoPrivacidadePendente: true,
    })
    expect(auth).not.toHaveProperty('token')
  })

  it('401 numa rota logada limpa o authStore (sessão expirada no servidor)', async () => {
    const auth = useAuthStore()
    await auth.entrar(CONTA_DEMO.email, CONTA_DEMO.senha)

    simulacao.expirarSessao()
    const falha = await apiClient.post('/avaliacoes/', { ...ALMOCO_HOJE, nota: 4 }).catch((e) => e)

    expect(falha.status).toBe(401)
    expect(falha.codigo).toBe('nao_autenticado')
    expect(auth.estaAutenticado).toBe(false)
    expect(auth.usuario).toBeNull()
  })

  it('403 de CSRF não limpa o authStore', async () => {
    const auth = useAuthStore()
    await auth.entrar(CONTA_DEMO.email, CONTA_DEMO.senha)

    // Cookie com um token que o servidor não reconhece (ex.: velho, de outra aba).
    document.cookie = 'csrftoken=token-velho; path=/'
    const falha = await apiClient.post('/avaliacoes/', { ...ALMOCO_HOJE, nota: 4 }).catch((e) => e)

    expect(falha.status).toBe(403)
    expect(falha.codigo).toBe('csrf_invalido')
    expect(auth.estaAutenticado).toBe(true)
  })

  it('escrita logada passa quando o apiClient manda o CSRF', async () => {
    const auth = useAuthStore()
    await auth.entrar(CONTA_DEMO.email, CONTA_DEMO.senha)

    // POST /privacidade/aceite/: escrita que exige sessão e responde 204.
    await expect(apiClient.post('/privacidade/aceite/')).resolves.toBeNull()
  })

  it('sair encerra a sessão no servidor (DELETE /sessao/) e limpa a store', async () => {
    const auth = useAuthStore()
    await auth.entrar(CONTA_DEMO.email, CONTA_DEMO.senha)

    await auth.sair()

    expect(auth.estaAutenticado).toBe(false)
    const falha = await apiClient.get('/sessao/').catch((e) => e)
    expect(falha.codigo).toBe('nao_autenticado')
  })

  it('sair com a sessão já expirada (401) resolve e limpa a store', async () => {
    const auth = useAuthStore()
    await auth.entrar(CONTA_DEMO.email, CONTA_DEMO.senha)
    simulacao.expirarSessao()

    await expect(auth.sair()).resolves.toBeUndefined()

    expect(auth.estaAutenticado).toBe(false)
  })

  it('sair com outro erro (ex.: 403 de CSRF) rejeita, mas limpa a store', async () => {
    const auth = useAuthStore()
    await auth.entrar(CONTA_DEMO.email, CONTA_DEMO.senha)
    document.cookie = 'csrftoken=token-velho; path=/'

    const falha = await auth.sair().catch((e) => e)

    expect(falha.codigo).toBe('csrf_invalido')
    expect(auth.estaAutenticado).toBe(false)
  })

  it('reenvio sem conta pendente: 200 sem corpo, só a mensagem do front', async () => {
    const auth = useAuthStore()

    const reenvio = await auth.reenviarConfirmacao({ emailInstitucional: '251000001@aluno.unb.br' })

    expect(reenvio.mensagem).toMatch(/novo link de confirmação/)
    expect(reenvio.linkSimulado).toBeUndefined()
  })

  it('login com senha errada mostra o codigo do contrato', async () => {
    const auth = useAuthStore()
    const falha = await auth.entrar(CONTA_DEMO.email, 'errada123').catch((e) => e)
    expect(falha.status).toBe(401)
    expect(falha.codigo).toBe('credenciais_invalidas')
    expect(auth.estaAutenticado).toBe(false)
  })

  it('cadastro, confirmação, reenvio e login usam os nomes do contrato', async () => {
    const auth = useAuthStore()

    const criado = await auth.cadastrar({
      tipoUsuario: 'estudante',
      emailInstitucional: '241987650@aluno.unb.br',
      senha: 'senhaforte',
      apelido: 'novo_aluno',
      aceitePrivacidade: true,
    })
    expect(criado).toMatchObject({
      emailInstitucional: '241987650@aluno.unb.br',
      status: 'pendente',
    })

    const pendente = await auth.entrar('241987650@aluno.unb.br', 'senhaforte').catch((e) => e)
    expect(pendente.codigo).toBe('conta_nao_confirmada')

    const reenvio = await auth.reenviarConfirmacao({ emailInstitucional: '241987650@aluno.unb.br' })
    // O backend responde 200 sem corpo: a mensagem vem da própria store.
    expect(reenvio.mensagem).toMatch(/novo link de confirmação/)
    // `linkSimulado` só existe no modo demonstração.
    const token = new URL(reenvio.linkSimulado, 'http://x').searchParams.get('token')
    await auth.confirmarEmail(token)

    await auth.entrar('241987650@aluno.unb.br', 'senhaforte')
    expect(auth.apelido).toBe('novo_aluno')
  })
})

describe('carregarSessao: a sessão volta ao abrir o app (ADR 0007)', () => {
  /** Reabrir o app: stores novas, mas o cookie de sessão continua no navegador. */
  function reabrirApp() {
    setActivePinia(createPinia())
    return useAuthStore()
  }

  it('com o cookie de sessão válido, a store volta a ter o usuário', async () => {
    await useAuthStore().entrar(CONTA_DEMO.email, CONTA_DEMO.senha)

    const auth = reabrirApp()
    expect(auth.sessaoCarregada).toBe(false)
    expect(auth.estaAutenticado).toBe(false)

    await auth.carregarSessao()

    expect(auth.sessaoCarregada).toBe(true)
    expect(auth.usuario).toEqual({
      apelido: CONTA_DEMO.apelido,
      tipo: 'estudante',
      avisoPrivacidadePendente: true,
    })
  })

  it('sem sessão (401), fica como visitante, não rejeita e não avisa no console', async () => {
    const auth = useAuthStore()
    const aviso = vi.spyOn(console, 'warn')

    await expect(auth.carregarSessao()).resolves.toBeUndefined()

    expect(auth.sessaoCarregada).toBe(true)
    expect(auth.estaAutenticado).toBe(false)
    expect(aviso).not.toHaveBeenCalled()
  })

  it('500 ao abrir: fica como visitante, e o erro vai para o console', async () => {
    const auth = useAuthStore()
    const aviso = vi.spyOn(console, 'warn').mockImplementation(() => {})
    const falha = new ApiError(500, { codigo: 'erro_interno' })
    vi.spyOn(apiClient, 'get').mockImplementationOnce(() => Promise.reject(falha))

    await expect(auth.carregarSessao()).resolves.toBeUndefined()

    expect(auth.estaAutenticado).toBe(false)
    expect(aviso).toHaveBeenCalledWith(expect.any(String), falha)
  })

  it('sem conexão, fica como visitante e não rejeita (o app abre do mesmo jeito)', async () => {
    const auth = useAuthStore()
    vi.spyOn(console, 'warn').mockImplementation(() => {})
    vi.spyOn(apiClient, 'get').mockImplementationOnce(() =>
      Promise.reject(new ApiError(0, { codigo: 'sem_conexao' })),
    )

    await expect(auth.carregarSessao()).resolves.toBeUndefined()

    expect(auth.sessaoCarregada).toBe(true)
    expect(auth.estaAutenticado).toBe(false)
  })

  it('chamadas ao mesmo tempo fazem um GET /api/sessao/ só', async () => {
    const auth = useAuthStore()
    const espiao = vi.spyOn(apiClient, 'get')

    await Promise.all([auth.carregarSessao(), auth.carregarSessao()])

    expect(espiao).toHaveBeenCalledTimes(1)
    expect(espiao).toHaveBeenCalledWith('/sessao/', { avisarSessaoPerdida: false })
  })
})

describe('carregarSessao com a rede lenta (tempo limite de 3 s)', () => {
  /** Promessa que só se resolve quando o teste mandar, como uma rede travada. */
  function pedidoTravado() {
    let resolver
    let rejeitar
    const promessa = new Promise((sim, nao) => {
      resolver = sim
      rejeitar = nao
    })
    return { promessa, resolver, rejeitar }
  }

  beforeEach(() => {
    vi.useFakeTimers({ toFake: ['Date', 'setTimeout', 'clearTimeout'] })
    vi.setSystemTime(SEGUNDA_MEIO_DIA)
  })

  /** Abre o app com o `GET /sessao/` travado e deixa passar o tempo limite. */
  async function abrirComRedeTravada() {
    const travado = pedidoTravado()
    vi.spyOn(apiClient, 'get').mockImplementationOnce(() => travado.promessa)
    const auth = useAuthStore()
    const carregando = auth.carregarSessao()
    await vi.advanceTimersByTimeAsync(3000)
    await carregando
    return { auth, travado }
  }

  const OUTRA_PESSOA = {
    apelido: 'outra_pessoa',
    tipo: 'estudante',
    avisoPrivacidadePendente: false,
  }

  it('espera os 3 s inteiros: com 2999 ms a primeira tela ainda não abriu', async () => {
    vi.spyOn(apiClient, 'get').mockImplementationOnce(() => pedidoTravado().promessa)
    const auth = useAuthStore()
    let abriu = false
    auth.carregarSessao().then(() => (abriu = true))

    await vi.advanceTimersByTimeAsync(2999)
    expect(abriu).toBe(false)
    expect(auth.sessaoCarregada).toBe(false)

    await vi.advanceTimersByTimeAsync(1)
    expect(abriu).toBe(true)
  })

  it('depois de 3 s sem resposta, o app segue como visitante', async () => {
    vi.spyOn(apiClient, 'get').mockImplementationOnce(() => pedidoTravado().promessa)
    const auth = useAuthStore()

    const carregando = auth.carregarSessao()
    await vi.advanceTimersByTimeAsync(3000)

    await expect(carregando).resolves.toBeUndefined()
    expect(auth.sessaoCarregada).toBe(true)
    expect(auth.estaAutenticado).toBe(false)
  })

  it('se a resposta chegar depois do tempo limite, o apelido aparece', async () => {
    const travado = pedidoTravado()
    vi.spyOn(apiClient, 'get').mockImplementationOnce(() => travado.promessa)
    const auth = useAuthStore()
    const carregando = auth.carregarSessao()
    await vi.advanceTimersByTimeAsync(3000)
    await carregando

    travado.resolver({ apelido: 'demo', tipo: 'estudante', avisoPrivacidadePendente: false })
    await vi.advanceTimersByTimeAsync(0)

    expect(auth.apelido).toBe('demo')
  })

  it('uma resposta atrasada não desfaz um login feito nesse meio-tempo', async () => {
    const travado = pedidoTravado()
    vi.spyOn(apiClient, 'get').mockImplementationOnce(() => travado.promessa)
    const auth = useAuthStore()
    const carregando = auth.carregarSessao()
    await vi.advanceTimersByTimeAsync(3000)
    await carregando

    await auth.entrar(CONTA_DEMO.email, CONTA_DEMO.senha)
    travado.rejeitar(new ApiError(401, { codigo: 'nao_autenticado' }))
    await vi.advanceTimersByTimeAsync(0)

    expect(auth.apelido).toBe(CONTA_DEMO.apelido)
  })

  it('login nesse meio-tempo vale mais que a resposta atrasada com outra pessoa', async () => {
    const { auth, travado } = await abrirComRedeTravada()

    await auth.entrar(CONTA_DEMO.email, CONTA_DEMO.senha)
    travado.resolver(OUTRA_PESSOA)
    await vi.advanceTimersByTimeAsync(0)

    expect(auth.apelido).toBe(CONTA_DEMO.apelido)
  })

  it('quem saiu nesse meio-tempo continua visitante, mesmo se a resposta trouxer alguém', async () => {
    const { auth, travado } = await abrirComRedeTravada()

    await auth.sair()
    travado.resolver(OUTRA_PESSOA)
    await vi.advanceTimersByTimeAsync(0)

    expect(auth.estaAutenticado).toBe(false)
  })

  it('errar a senha nesse meio-tempo não descarta a sessão que chega atrasada', async () => {
    const { auth, travado } = await abrirComRedeTravada()

    await expect(auth.entrar(CONTA_DEMO.email, 'errada123')).rejects.toMatchObject({ status: 401 })
    travado.resolver({
      apelido: CONTA_DEMO.apelido,
      tipo: 'estudante',
      avisoPrivacidadePendente: true,
    })
    await vi.advanceTimersByTimeAsync(0)

    expect(auth.apelido).toBe(CONTA_DEMO.apelido)
  })
})

describe('aviso de privacidade atualizado (RF11, RNF07.1)', () => {
  it('avisoPrivacidadePendente vem da sessão', async () => {
    const auth = useAuthStore()
    expect(auth.avisoPrivacidadePendente).toBe(false)

    await auth.entrar(CONTA_DEMO.email, CONTA_DEMO.senha)

    expect(auth.avisoPrivacidadePendente).toBe(true)
  })

  it('registrarCienciaPrivacidade: POST /privacidade/aceite/ e a sessão deixa de ter o aviso pendente', async () => {
    const auth = useAuthStore()
    await auth.entrar(CONTA_DEMO.email, CONTA_DEMO.senha)
    const post = vi.spyOn(apiClient, 'post')

    await auth.registrarCienciaPrivacidade()

    expect(post).toHaveBeenCalledWith('/privacidade/aceite/')
    expect(auth.avisoPrivacidadePendente).toBe(false)
    expect(auth.apelido).toBe(CONTA_DEMO.apelido)
  })

  it('registrarCienciaPrivacidade que falha mantém o aviso pendente', async () => {
    const auth = useAuthStore()
    await auth.entrar(CONTA_DEMO.email, CONTA_DEMO.senha)
    vi.spyOn(apiClient, 'post').mockRejectedValueOnce(new ApiError(500))

    await expect(auth.registrarCienciaPrivacidade()).rejects.toBeInstanceOf(ApiError)

    expect(auth.avisoPrivacidadePendente).toBe(true)
  })

  it('marcarAvisoPrivacidadePendente: volta a pedir o aviso (403 do check-in)', async () => {
    const auth = useAuthStore()
    await auth.entrar(CONTA_DEMO.email, CONTA_DEMO.senha)
    await auth.registrarCienciaPrivacidade()

    auth.marcarAvisoPrivacidadePendente()

    expect(auth.avisoPrivacidadePendente).toBe(true)
  })

  it('marcarAvisoPrivacidadePendente sem sessão não cria usuário', () => {
    const auth = useAuthStore()

    auth.marcarAvisoPrivacidadePendente()

    expect(auth.estaAutenticado).toBe(false)
  })
})
