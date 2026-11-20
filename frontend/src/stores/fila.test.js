import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useFilaStore } from './fila'
import { useAuthStore } from './auth'
import { apiClient } from '@/services/apiClient'
import { CONTA_DEMO } from '@/services/mock/banco'
import { reiniciarSimulacao, simulacao } from '@/services/mock/servidor'

/**
 * filaStore + apiClient + servidor simulado (fluxo 4a do front). Cada
 * desfecho do POST /api/checkins/ e, em todos eles, a regra do RI09: as
 * coordenadas vão só no corpo e não ficam guardadas em lugar nenhum da store.
 */

// Segunda-feira, 09/11/2026, 12h — almoço em andamento.
const SEGUNDA_MEIO_DIA = new Date(2026, 10, 9, 12, 0)
const SEGUNDA_16H = new Date(2026, 10, 9, 16, 0)

// Valores fáceis de achar em qualquer lugar do estado.
const COORDENADAS = { latitude: -15.7631234, longitude: -47.8701234 }
const CHECKIN_ALMOCO = { campusId: 'darcy', tipoRefeicao: 'almoco', coordenadas: COORDENADAS }

async function entrarComAvisoAceito() {
  const auth = useAuthStore()
  await auth.entrar(CONTA_DEMO.email, CONTA_DEMO.senha)
  await auth.registrarCienciaPrivacidade()
  return auth
}

/** Nenhum número das coordenadas aparece no estado serializado da store. */
function esperarSemCoordenadas(fila) {
  const estado = JSON.stringify(fila.$state)
  expect(estado).not.toContain('15.7631234')
  expect(estado).not.toContain('47.8701234')
  expect(estado).not.toMatch(/latitude|longitude|coordenadas/)
}

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

describe('filaStore.confirmarCheckin', () => {
  it('manda as coordenadas só no corpo do POST /checkins/, com o id do campus no backend', async () => {
    await entrarComAvisoAceito()
    const post = vi.spyOn(apiClient, 'post')
    const fila = useFilaStore()

    await fila.confirmarCheckin(CHECKIN_ALMOCO)

    const [caminho, corpo] = post.mock.calls.at(-1)
    expect(caminho).toBe('/checkins/')
    expect(corpo).toEqual({ campus: 1, tipoRefeicao: 'almoco', coordenadas: COORDENADAS })
  })

  it('não repassa campos extras que vierem junto com as coordenadas', async () => {
    await entrarComAvisoAceito()
    const post = vi.spyOn(apiClient, 'post')
    const fila = useFilaStore()

    await fila.confirmarCheckin({
      ...CHECKIN_ALMOCO,
      coordenadas: { ...COORDENADAS, accuracy: 12, altitude: 1100 },
    })

    expect(post.mock.calls.at(-1)[1].coordenadas).toEqual(COORDENADAS)
  })

  it('201: confirmado, guarda o check-in e os pontos, sem coordenadas', async () => {
    await entrarComAvisoAceito()
    const fila = useFilaStore()

    const resultado = await fila.confirmarCheckin(CHECKIN_ALMOCO)

    expect(resultado.desfecho).toBe('confirmado')
    expect(resultado.checkin).toMatchObject({
      campus: 1,
      tipoRefeicao: 'almoco',
      data: '2026-11-09',
    })
    // Até a BE-14 o bloco volta zerado.
    expect(resultado.pontos).toEqual({ total: 0, contribuicao: 0, avaliacaoLiberada: 0 })
    expect(fila.ultimoCheckin).toEqual(resultado.checkin)
    expect(fila.ultimosPontos).toEqual(resultado.pontos)
    esperarSemCoordenadas(fila)
  })

  it('422 fora_do_horario: recusado com a mensagem do servidor, que traz a janela', async () => {
    vi.setSystemTime(SEGUNDA_16H)
    await entrarComAvisoAceito()
    const fila = useFilaStore()

    const resultado = await fila.confirmarCheckin(CHECKIN_ALMOCO)

    expect(resultado).toEqual({
      desfecho: 'recusado',
      codigo: 'fora_do_horario',
      mensagem: 'O check-in do almoço só vale das 11h00 às 14h30.',
    })
    expect(fila.ultimoCheckin).toBeNull()
    esperarSemCoordenadas(fila)
  })

  it('422 fora_do_horario sem mensagem: monta a janela pelo horário da refeição', async () => {
    await entrarComAvisoAceito()
    vi.spyOn(apiClient, 'post').mockImplementationOnce(async () => {
      const { ApiError } = await import('@/services/apiClient')
      throw new ApiError(422, { codigo: 'fora_do_horario' })
    })
    const fila = useFilaStore()

    const resultado = await fila.confirmarCheckin({ ...CHECKIN_ALMOCO, tipoRefeicao: 'jantar' })

    expect(resultado.mensagem).toBe('O check-in do jantar só vale das 17h00 às 19h30.')
  })

  it('422 checkin_duplicado: recusado com mensagem própria', async () => {
    await entrarComAvisoAceito()
    const fila = useFilaStore()
    await fila.confirmarCheckin(CHECKIN_ALMOCO)

    const resultado = await fila.confirmarCheckin(CHECKIN_ALMOCO)

    expect(resultado).toEqual({
      desfecho: 'recusado',
      codigo: 'checkin_duplicado',
      mensagem: 'Você já fez check-in nesta refeição hoje.',
    })
    esperarSemCoordenadas(fila)
  })

  it('422 localizacao_nao_confirmada: recusado com mensagem própria', async () => {
    await entrarComAvisoAceito()
    simulacao.definirLocalizacaoConfirmada(false)
    const fila = useFilaStore()

    const resultado = await fila.confirmarCheckin(CHECKIN_ALMOCO)

    expect(resultado).toEqual({
      desfecho: 'recusado',
      codigo: 'localizacao_nao_confirmada',
      mensagem:
        'Não foi possível confirmar que você está no RU. O check-in só vale dentro do restaurante.',
    })
    expect(fila.ultimoCheckin).toBeNull()
    esperarSemCoordenadas(fila)
  })

  it('403 aviso_privacidade_pendente: pede o aviso de novo, sem guardar nada', async () => {
    await useAuthStore().entrar(CONTA_DEMO.email, CONTA_DEMO.senha)
    const fila = useFilaStore()

    const resultado = await fila.confirmarCheckin(CHECKIN_ALMOCO)

    expect(resultado.desfecho).toBe('aviso_privacidade_pendente')
    expect(fila.ultimoCheckin).toBeNull()
    esperarSemCoordenadas(fila)
  })

  it('400 dados_invalidos: erro genérico de check-in', async () => {
    await entrarComAvisoAceito()
    const fila = useFilaStore()

    const resultado = await fila.confirmarCheckin({
      ...CHECKIN_ALMOCO,
      coordenadas: { latitude: 95, longitude: COORDENADAS.longitude },
    })

    expect(resultado).toEqual({
      desfecho: 'erro',
      codigo: 'dados_invalidos',
      mensagem: 'Não foi possível registrar o check-in. Tente de novo.',
    })
    esperarSemCoordenadas(fila)
  })

  it('401 (sessão perdida): limpa o authStore e não guarda nada', async () => {
    const auth = await entrarComAvisoAceito()
    simulacao.expirarSessao()
    const fila = useFilaStore()

    const resultado = await fila.confirmarCheckin(CHECKIN_ALMOCO)

    expect(resultado.desfecho).toBe('nao_autenticado')
    expect(auth.estaAutenticado).toBe(false)
    esperarSemCoordenadas(fila)
  })

  it('sem conexão: erro com a mensagem do apiClient', async () => {
    await entrarComAvisoAceito()
    const { ApiError } = await import('@/services/apiClient')
    vi.spyOn(apiClient, 'post').mockRejectedValueOnce(
      new ApiError(0, { codigo: 'sem_conexao', mensagem: 'Sem internet.' }),
    )
    const fila = useFilaStore()

    const resultado = await fila.confirmarCheckin(CHECKIN_ALMOCO)

    expect(resultado).toEqual({
      desfecho: 'erro',
      codigo: 'sem_conexao',
      mensagem: 'Sem internet.',
    })
    esperarSemCoordenadas(fila)
  })

  it('campus sem id no backend: erro sem chamar a API', async () => {
    await entrarComAvisoAceito()
    const post = vi.spyOn(apiClient, 'post')
    const fila = useFilaStore()

    const resultado = await fila.confirmarCheckin({ ...CHECKIN_ALMOCO, campusId: 'inexistente' })

    expect(resultado.desfecho).toBe('erro')
    expect(post).not.toHaveBeenCalled()
  })

  it('enviandoCheckin fica verdadeiro só durante o envio', async () => {
    await entrarComAvisoAceito()
    const fila = useFilaStore()

    const envio = fila.confirmarCheckin(CHECKIN_ALMOCO)
    expect(fila.enviandoCheckin).toBe(true)
    await envio

    expect(fila.enviandoCheckin).toBe(false)
  })

  it('o estado da store nunca tem coordenadas, nem durante o envio', async () => {
    await entrarComAvisoAceito()
    const fila = useFilaStore()

    const envio = fila.confirmarCheckin(CHECKIN_ALMOCO)
    expect(fila.enviandoCheckin).toBe(true)
    esperarSemCoordenadas(fila)
    await envio

    expect(fila.ultimoCheckin).not.toBeNull()
    esperarSemCoordenadas(fila)
  })
})
