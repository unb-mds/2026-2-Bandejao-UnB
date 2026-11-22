import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { enableAutoUnmount, flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import FilaPrevisao from './FilaPrevisao.vue'
import { ApiError, apiClient } from '@/services/apiClient'
import { reiniciarSimulacao, simulacao } from '@/services/mock/servidor'

const SEGUNDA_MEIO_DIA = new Date(2026, 8, 28, 12, 0)
const HOJE = '2026-09-28'

let pinia

enableAutoUnmount(afterEach)

async function montar(props = {}) {
  const wrapper = mount(FilaPrevisao, {
    props: { campusId: 1, tipoRefeicao: 'almoco', data: HOJE, ...props },
    global: { plugins: [pinia] },
  })
  await flushPromises()
  return wrapper
}

const faixas = (wrapper) => wrapper.findAll('[data-teste="previsao-faixa"]')
const picos = (wrapper) => wrapper.findAll('[data-teste="previsao-faixa"].faixa--pico')

beforeEach(() => {
  vi.useFakeTimers({ toFake: ['Date'] })
  vi.setSystemTime(SEGUNDA_MEIO_DIA)
  localStorage.clear()
  reiniciarSimulacao()
  pinia = createPinia()
  setActivePinia(pinia)
})

afterEach(() => {
  vi.useRealTimers()
  vi.restoreAllMocks()
})

describe('FilaPrevisao (FE-11, RF13, RN06)', () => {
  it('sem login: mostra as faixas de 15 minutos com o nível de cada uma', async () => {
    const wrapper = await montar()

    expect(faixas(wrapper)).toHaveLength(14)
    expect(faixas(wrapper)[0].text()).toContain('11h às 11h15')
    expect(faixas(wrapper)[0].text()).toContain('Vazia')
    expect(faixas(wrapper).at(-1).text()).toContain('14h15 às 14h30')
  })

  it('empate: todas as faixas de maior movimento aparecem como pico', async () => {
    const wrapper = await montar()

    expect(picos(wrapper)).toHaveLength(3)
    expect(picos(wrapper).map((faixa) => faixa.text())).toEqual([
      expect.stringContaining('12h às 12h15'),
      expect.stringContaining('12h15 às 12h30'),
      expect.stringContaining('12h45 às 13h'),
    ])
    for (const faixa of picos(wrapper)) expect(faixa.text()).toContain('Pico')
    expect(wrapper.get('[data-teste="previsao-pico"]').text()).toBe(
      'Picos previstos: 12h às 12h15, 12h15 às 12h30 e 12h45 às 13h',
    )
  })

  it('um pico só: no singular', async () => {
    const wrapper = await montar({ tipoRefeicao: 'cafe' })

    expect(picos(wrapper)).toHaveLength(1)
    expect(wrapper.get('[data-teste="previsao-pico"]').text()).toBe('Pico previsto: 7h45 às 8h')
  })

  it('faixas que não são pico não levam o selo', async () => {
    const wrapper = await montar()

    const comuns = faixas(wrapper).filter((faixa) => !faixa.classes('faixa--pico'))
    expect(comuns).toHaveLength(11)
    for (const faixa of comuns) expect(faixa.find('.selo-pico').exists()).toBe(false)
  })

  it('dados insuficientes: avisa, sem faixas e sem valor de reserva', async () => {
    const wrapper = await montar({ campusId: 5 })

    const aviso = wrapper.get('[data-teste="previsao-dados-insuficientes"]')
    expect(aviso.text()).toContain('Dados insuficientes')
    expect(aviso.text()).toContain('3 dias diferentes')
    expect(faixas(wrapper)).toHaveLength(0)
    expect(wrapper.find('[data-teste="previsao-pico"]').exists()).toBe(false)
  })

  it('enquanto carrega: "Carregando previsão…"', async () => {
    vi.spyOn(apiClient, 'get').mockReturnValue(new Promise(() => {}))

    const wrapper = await montar()

    expect(wrapper.text()).toContain('Carregando previsão…')
  })

  it('501 (backend sem a rota): "Previsão fora do ar no momento", sem erro', async () => {
    simulacao.definirPrevisaoDisponivel(false)

    const wrapper = await montar()

    const aviso = wrapper.get('[data-teste="previsao-indisponivel"]')
    expect(aviso.text()).toContain('Previsão fora do ar no momento')
    expect(wrapper.find('[data-teste="previsao-erro"]').exists()).toBe(false)
  })

  it('com a tela parada, revalida depois dos 5 minutos sem tirar as faixas da tela', async () => {
    vi.useFakeTimers({ toFake: ['Date', 'setInterval', 'clearInterval'] })
    vi.setSystemTime(SEGUNDA_MEIO_DIA)
    const getOriginal = apiClient.get.bind(apiClient)
    const get = vi.spyOn(apiClient, 'get')
    const wrapper = await montar()
    expect(get).toHaveBeenCalledTimes(1)

    vi.advanceTimersByTime(60 * 1000)
    await flushPromises()
    expect(get).toHaveBeenCalledTimes(1)

    let liberar
    get.mockImplementationOnce(
      (caminho, opcoes) =>
        new Promise((resolver) => {
          liberar = () => resolver(getOriginal(caminho, opcoes))
        }),
    )
    vi.setSystemTime(new Date(SEGUNDA_MEIO_DIA.getTime() + 5 * 60 * 1000))
    vi.advanceTimersByTime(60 * 1000)
    await flushPromises()

    expect(get).toHaveBeenCalledTimes(2)
    expect(faixas(wrapper)).toHaveLength(14)
    expect(wrapper.text()).not.toContain('Carregando previsão…')
    liberar()
    await flushPromises()
    expect(faixas(wrapper)).toHaveLength(14)
  })

  it('rede fora: a revalidação não fica alternando entre "Carregando…" e o erro', async () => {
    vi.useFakeTimers({ toFake: ['Date', 'setInterval', 'clearInterval'] })
    vi.setSystemTime(SEGUNDA_MEIO_DIA)
    const get = vi
      .spyOn(apiClient, 'get')
      .mockRejectedValue(new ApiError(0, { codigo: 'sem_conexao', mensagem: 'Sem internet.' }))
    const wrapper = await montar()
    expect(wrapper.find('[data-teste="previsao-erro"]').exists()).toBe(true)

    for (let minuto = 0; minuto < 3; minuto++) {
      vi.advanceTimersByTime(60 * 1000)
      await flushPromises()
      expect(wrapper.text()).not.toContain('Carregando previsão…')
      expect(wrapper.find('[data-teste="previsao-erro"]').exists()).toBe(true)
    }
    expect(get).toHaveBeenCalledTimes(1)
  })

  it('a revalidação de uma previsão boa falha: as faixas continuam na tela', async () => {
    vi.useFakeTimers({ toFake: ['Date', 'setInterval', 'clearInterval'] })
    vi.setSystemTime(SEGUNDA_MEIO_DIA)
    const get = vi.spyOn(apiClient, 'get')
    const wrapper = await montar()
    expect(faixas(wrapper)).toHaveLength(14)

    get.mockRejectedValue(new ApiError(0, { codigo: 'sem_conexao', mensagem: 'Sem internet.' }))
    vi.setSystemTime(new Date(SEGUNDA_MEIO_DIA.getTime() + 5 * 60 * 1000))
    vi.advanceTimersByTime(60 * 1000)
    await flushPromises()

    expect(get).toHaveBeenCalledTimes(2)
    expect(faixas(wrapper)).toHaveLength(14)
    expect(wrapper.find('[data-teste="previsao-erro"]').exists()).toBe(false)
  })

  it('desmontar para a revalidação', async () => {
    vi.useFakeTimers({ toFake: ['Date', 'setInterval', 'clearInterval'] })
    vi.setSystemTime(SEGUNDA_MEIO_DIA)
    const get = vi.spyOn(apiClient, 'get')
    const wrapper = await montar()

    wrapper.unmount()
    vi.setSystemTime(new Date(SEGUNDA_MEIO_DIA.getTime() + 10 * 60 * 1000))
    vi.advanceTimersByTime(5 * 60 * 1000)

    expect(get).toHaveBeenCalledTimes(1)
  })

  it('falha de conexão: mostra o erro e "Tentar novamente" carrega de novo', async () => {
    const getOriginal = apiClient.get.bind(apiClient)
    let falhar = true
    vi.spyOn(apiClient, 'get').mockImplementation((caminho, opcoes) => {
      if (falhar) {
        falhar = false
        return Promise.reject(new ApiError(0, { codigo: 'sem_conexao', mensagem: 'Sem internet.' }))
      }
      return getOriginal(caminho, opcoes)
    })

    const wrapper = await montar()
    expect(wrapper.get('[data-teste="previsao-erro"]').text()).toContain('Sem internet.')

    await wrapper.get('[data-teste="previsao-erro"] button').trigger('click')
    await flushPromises()

    expect(faixas(wrapper)).toHaveLength(14)
  })

  it('campus inexistente (404): mostra o erro, sem "Tentar novamente"', async () => {
    const wrapper = await montar({ campusId: 99 })

    expect(wrapper.get('[data-teste="previsao-erro"]').text()).toContain('Campus não encontrado.')
    expect(wrapper.find('[data-teste="previsao-erro"] button').exists()).toBe(false)
  })

  it.each([
    ['400 parametros_invalidos', 400, { codigo: 'parametros_invalidos', mensagem: 'Inválido.' }, false],
    ['404 campus_nao_encontrado', 404, { codigo: 'campus_nao_encontrado', mensagem: 'Não há.' }, false],
    ['404 sem codigo (página de proxy)', 404, {}, false],
    ['500', 500, { codigo: 'erro_interno', mensagem: 'Fora do ar.' }, true],
  ])('%s: "Tentar novamente" aparece? %s', async (_caso, status, dados, comBotao) => {
    vi.spyOn(apiClient, 'get').mockRejectedValueOnce(new ApiError(status, dados))

    const wrapper = await montar()

    expect(wrapper.find('[data-teste="previsao-erro"]').exists()).toBe(true)
    expect(wrapper.find('[data-teste="previsao-erro"] button').exists()).toBe(comBotao)
  })

  it('os estados ficam numa região aria-live fixa; a lista de faixas fica fora dela', async () => {
    simulacao.definirPrevisaoDisponivel(false)
    const wrapper = await montar()

    const regiao = wrapper.get('[aria-live="polite"]')
    expect(regiao.find('[data-teste="previsao-indisponivel"]').exists()).toBe(true)

    simulacao.definirPrevisaoDisponivel(true)
    const comFaixas = await montar({ tipoRefeicao: 'cafe' })
    const regiaoComFaixas = comFaixas.get('[aria-live="polite"]')
    expect(regiaoComFaixas.find('[data-teste="previsao-pico"]').exists()).toBe(true)
    expect(regiaoComFaixas.find('ol').exists()).toBe(false)
  })

  it('título com a refeição e "hoje"; outro dia aparece com dia e data', async () => {
    const wrapper = await montar()
    expect(wrapper.get('#titulo-previsao').text()).toBe('Previsão · Almoço, hoje')

    await wrapper.setProps({ data: '2026-09-29', tipoRefeicao: 'jantar' })
    await flushPromises()

    expect(wrapper.get('#titulo-previsao').text()).toBe('Previsão · Jantar, ter 29/09')
  })

  it('trocar refeição ou dia pede a previsão certa', async () => {
    const get = vi.spyOn(apiClient, 'get')
    const wrapper = await montar()

    await wrapper.setProps({ tipoRefeicao: 'jantar', data: '2026-09-29' })
    await flushPromises()

    expect(get.mock.calls.map(([caminho]) => caminho)).toEqual([
      '/fila/previsao/?campus=1&refeicao=almoco&data=2026-09-28',
      '/fila/previsao/?campus=1&refeicao=jantar&data=2026-09-29',
    ])
    expect(faixas(wrapper)).toHaveLength(10)
  })

  it('as faixas ficam numa lista com rótulo para o leitor de tela', async () => {
    const wrapper = await montar()

    expect(wrapper.get('ol').attributes('aria-label')).toBe(
      'Nível previsto da fila a cada 15 minutos',
    )
  })
})
