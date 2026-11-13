import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useAuthStore } from './auth'
import { apiClient } from '@/services/apiClient'
import { CONTA_DEMO } from '@/services/mock/banco'
import { reiniciarSimulacao, simulacao } from '@/services/mock/servidor'

/**
 * Integração: authStore + apiClient + servidor simulado (Plano de Testes,
 * "Integração" do front). Os corpos seguem o contrato OpenAPI v1 (BE-03).
 */

// Segunda-feira, 28/09/2026, 12h — almoço em andamento.
const SEGUNDA_MEIO_DIA = new Date(2026, 8, 28, 12, 0)
const ALMOCO_HOJE = { campus: 'gama', data: '2026-09-28', refeicao: 'almoco' }

beforeEach(() => {
  vi.useFakeTimers({ toFake: ['Date'] })
  vi.setSystemTime(SEGUNDA_MEIO_DIA)
  reiniciarSimulacao()
  setActivePinia(createPinia())
})

afterEach(() => {
  vi.useRealTimers()
})

describe('authStore com o servidor simulado', () => {
  it('login guarda só apelido, tipo e avisoPrivacidadePendente', async () => {
    const auth = useAuthStore()

    await auth.entrar(CONTA_DEMO.matricula, CONTA_DEMO.senha)

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
    await auth.entrar(CONTA_DEMO.matricula, CONTA_DEMO.senha)

    simulacao.expirarSessao()
    const falha = await apiClient.post('/avaliacoes/', { ...ALMOCO_HOJE, nota: 4 }).catch((e) => e)

    expect(falha.status).toBe(401)
    expect(falha.codigo).toBe('nao_autenticado')
    expect(auth.estaAutenticado).toBe(false)
    expect(auth.usuario).toBeNull()
  })

  it('403 de CSRF não limpa o authStore', async () => {
    const auth = useAuthStore()
    await auth.entrar(CONTA_DEMO.matricula, CONTA_DEMO.senha)

    document.cookie = 'csrftoken=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/'
    const falha = await apiClient.post('/avaliacoes/', { ...ALMOCO_HOJE, nota: 4 }).catch((e) => e)

    expect(falha.status).toBe(403)
    expect(auth.estaAutenticado).toBe(true)
  })

  it('escrita logada passa quando o apiClient manda o CSRF', async () => {
    const auth = useAuthStore()
    await auth.entrar(CONTA_DEMO.matricula, CONTA_DEMO.senha)

    const resposta = await apiClient.post('/avaliacoes/', { ...ALMOCO_HOJE, nota: 4 })

    expect(resposta.nota).toBe(4)
  })

  it('sair encerra a sessão no servidor (DELETE /sessao/) e limpa a store', async () => {
    const auth = useAuthStore()
    await auth.entrar(CONTA_DEMO.matricula, CONTA_DEMO.senha)

    await auth.sair()

    expect(auth.estaAutenticado).toBe(false)
    const falha = await apiClient.get('/sessao/').catch((e) => e)
    expect(falha.codigo).toBe('nao_autenticado')
  })

  it('login com senha errada mostra o codigo do contrato', async () => {
    const auth = useAuthStore()
    const falha = await auth.entrar(CONTA_DEMO.matricula, 'errada123').catch((e) => e)
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

    const pendente = await auth.entrar('241987650', 'senhaforte').catch((e) => e)
    expect(pendente.codigo).toBe('conta_nao_confirmada')

    const reenvio = await auth.reenviarConfirmacao({ matriculaSiape: '241987650' })
    const token = new URL(reenvio.linkSimulado, 'http://x').searchParams.get('token')
    await auth.confirmarEmail(token)

    await auth.entrar('241987650', 'senhaforte')
    expect(auth.apelido).toBe('novo_aluno')
  })
})
