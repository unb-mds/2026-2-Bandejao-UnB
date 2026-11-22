import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createMemoryHistory, createRouter } from 'vue-router'
import AvaliacaoWidget from './AvaliacaoWidget.vue'
import { useAuthStore } from '@/stores/auth'
import { useAvaliacoesStore } from '@/stores/avaliacoes'
import { apiClient } from '@/services/apiClient'
import { CONTA_DEMO, banco } from '@/services/mock/banco'
import { reiniciarSimulacao, simulacao } from '@/services/mock/servidor'

/**
 * AvaliacaoWidget ligado à API (FE-09, RF15, RF05): criar, editar, motivos de
 * indisponível, média, quantidade e comentários com apelido e "usuário
 * removido". Integração com a avaliacoesStore, o authStore e o servidor
 * simulado (contrato da BE-13).
 */

// Segunda-feira, 28/09/2026, 12h — almoço em andamento.
const SEGUNDA_MEIO_DIA = new Date(2026, 8, 28, 12, 0)
const HOJE = '2026-09-28'
const ALMOCO_HOJE = { campusId: 3, data: HOJE, tipo: 'almoco' }

async function entrar() {
  await useAuthStore().entrar(CONTA_DEMO.email, CONTA_DEMO.senha)
}

const montados = []
async function montar(props = ALMOCO_HOJE) {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', name: 'inicio', component: { template: '<div />' } },
      { path: '/login', name: 'login', component: { template: '<div />' } },
    ],
  })
  await router.push('/')
  const wrapper = mount(AvaliacaoWidget, {
    props,
    global: { plugins: [router] },
    attachTo: document.body,
  })
  montados.push(wrapper)
  await flushPromises()
  return wrapper
}

const texto = (wrapper) => wrapper.text().replace(/\s+/g, ' ')
const indisponivel = (wrapper) => wrapper.find('[data-teste="avaliacao-indisponivel"]')
const formulario = (wrapper) => wrapper.find('[data-teste="avaliacao-formulario"]')

async function escolherNota(wrapper, nota) {
  await wrapper.get(`[data-teste="estrela-${nota}"]`).trigger('click')
}

async function enviar(wrapper) {
  await wrapper.get('[data-teste="avaliacao-formulario"]').trigger('submit')
  await flushPromises()
}

beforeEach(() => {
  vi.useFakeTimers({ toFake: ['Date'] })
  vi.setSystemTime(SEGUNDA_MEIO_DIA)
  localStorage.clear()
  reiniciarSimulacao()
  setActivePinia(createPinia())
})

afterEach(() => {
  montados.splice(0).forEach((wrapper) => wrapper.unmount())
  vi.useRealTimers()
  vi.restoreAllMocks()
})

describe('AvaliacaoWidget — média, quantidade e comentários (RF15.2)', () => {
  it('mostra a média e a quantidade da refeição, sem login', async () => {
    const wrapper = await montar()

    const avaliacoes = useAvaliacoesStore()
    const refeicaoId = avaliacoes.daResumoDoDia(3, HOJE).find((r) => r.tipo === 'almoco').refeicaoId
    const { media, quantidade } = avaliacoes.avaliacoesDaRefeicao(refeicaoId).resumoAvaliacoes
    expect(wrapper.get('[data-teste="avaliacao-media"]').text()).toBe(
      media.toFixed(1).replace('.', ','),
    )
    expect(wrapper.get('[data-teste="avaliacao-quantidade"]').text()).toBe(
      `${quantidade} avaliações`,
    )
  })

  it('mostra os comentários com o apelido do autor', async () => {
    const wrapper = await montar()

    const comentarios = wrapper.findAll('[data-teste="avaliacao-comentario"]')
    expect(comentarios.length).toBeGreaterThan(0)
    expect(comentarios[0].get('[data-teste="comentario-apelido"]').text()).not.toBe('')
  })

  it('autor com conta removida aparece como "usuário removido"', async () => {
    await entrar()
    const avaliacoes = useAvaliacoesStore()
    const resumo = await avaliacoes.carregarResumoDoDia(3, HOJE)
    const refeicaoId = resumo.find((r) => r.tipo === 'almoco').refeicaoId
    await avaliacoes.avaliar({ refeicaoId, campus: 3, data: HOJE, nota: 2, comentario: 'Salgado' })
    banco.estado.usuarios = banco.estado.usuarios.filter((u) => u.apelido !== CONTA_DEMO.apelido)
    avaliacoes.limparCache()

    const wrapper = await montar()

    const primeiro = wrapper.findAll('[data-teste="avaliacao-comentario"]')[0]
    expect(primeiro.text()).toContain('usuário removido')
    expect(primeiro.text()).toContain('Salgado')
    expect(primeiro.get('[data-teste="comentario-apelido"]').attributes('data-removido')).toBe(
      'true',
    )
  })

  it('refeição sem avaliações: "Sem avaliações ainda"', async () => {
    vi.setSystemTime(new Date(2026, 8, 28, 10, 0))
    const wrapper = await montar()

    expect(wrapper.get('[data-teste="avaliacao-resumo"]').text()).toContain('Sem avaliações ainda')
    expect(wrapper.findAll('[data-teste="avaliacao-comentario"]')).toHaveLength(0)
  })

  it('não mostra e-mail nem matrícula (RI10)', async () => {
    await entrar()
    const wrapper = await montar()
    await escolherNota(wrapper, 4)
    await enviar(wrapper)

    expect(wrapper.html()).not.toContain(CONTA_DEMO.email)
    expect(wrapper.html()).not.toContain('231034567')
  })
})

describe('AvaliacaoWidget — criar (RF15.1)', () => {
  it('envia nota e comentário pelo POST /api/avaliacoes/ com o refeicaoId', async () => {
    await entrar()
    const post = vi.spyOn(apiClient, 'post')
    const wrapper = await montar()

    await escolherNota(wrapper, 4)
    await wrapper.get('textarea').setValue('Frango ótimo')
    await enviar(wrapper)

    expect(post).toHaveBeenCalledWith('/avaliacoes/', {
      refeicaoId: expect.any(Number),
      nota: 4,
      comentario: 'Frango ótimo',
    })
    expect(texto(wrapper)).toContain('Avaliação enviada!')
    expect(texto(wrapper)).toContain('Sua nota: 4 estrelas')
  })

  it('depois de enviar, o próprio comentário aparece na lista e a quantidade sobe', async () => {
    await entrar()
    const wrapper = await montar()
    const quantidade = () =>
      Number(wrapper.get('[data-teste="avaliacao-quantidade"]').text().match(/\d+/)[0])
    const antes = quantidade()

    await escolherNota(wrapper, 5)
    await wrapper.get('textarea').setValue('Excelente')
    await enviar(wrapper)

    expect(quantidade()).toBe(antes + 1)
    const primeiro = wrapper.findAll('[data-teste="avaliacao-comentario"]')[0]
    expect(primeiro.text()).toContain(CONTA_DEMO.apelido)
    expect(primeiro.text()).toContain('Excelente')
  })

  it('sem nota, o botão de enviar fica desativado', async () => {
    await entrar()
    const wrapper = await montar()

    expect(wrapper.get('[data-teste="avaliacao-enviar"]').attributes('disabled')).toBeDefined()
  })

  it('o comentário vai até 500 caracteres, com contador', async () => {
    await entrar()
    const wrapper = await montar()

    const campo = wrapper.get('textarea')
    expect(campo.attributes('maxlength')).toBe('500')
    await campo.setValue('abc')
    expect(texto(wrapper)).toContain('3/500')
  })

  it('pontos > 0 na resposta: mostra "+N pontos"', async () => {
    await entrar()
    vi.spyOn(apiClient, 'post').mockResolvedValueOnce({
      avaliacao: {
        id: 9,
        refeicaoId: 1,
        nota: 5,
        comentario: '',
        criadaEm: SEGUNDA_MEIO_DIA.toISOString(),
        editadaEm: null,
      },
      pontos: { total: 5, contribuicao: 0, avaliacaoLiberada: 5 },
    })
    const wrapper = await montar()

    await escolherNota(wrapper, 5)
    await enviar(wrapper)

    expect(texto(wrapper)).toContain('+5 pontos')
  })

  it('pontos zerados (até a BE-14): sem "+N pontos"', async () => {
    await entrar()
    const wrapper = await montar()

    await escolherNota(wrapper, 5)
    await enviar(wrapper)

    expect(texto(wrapper)).not.toMatch(/\+\d+ pontos/)
  })

  it('erro de validação do servidor (422) aparece no formulário', async () => {
    await entrar()
    const { ApiError } = await import('@/services/apiClient')
    vi.spyOn(apiClient, 'post').mockRejectedValueOnce(
      new ApiError(422, { codigo: 'comentario_muito_longo', mensagem: 'x' }),
    )
    const wrapper = await montar()

    await escolherNota(wrapper, 3)
    await enviar(wrapper)

    expect(formulario(wrapper).text()).toContain('O comentário pode ter no máximo 500 caracteres.')
  })
})

describe('AvaliacaoWidget — editar (RF15.1)', () => {
  it('quem já avaliou vê a própria nota e o botão Editar, sem o formulário', async () => {
    await entrar()
    const primeira = await montar()
    await escolherNota(primeira, 2)
    await enviar(primeira)
    primeira.unmount()
    montados.splice(0)
    // Recarregar a página: a store só sabe o que vem do servidor.
    setActivePinia(createPinia())
    await entrar()

    const wrapper = await montar()

    expect(texto(wrapper)).toContain('Sua nota: 2 estrelas')
    expect(formulario(wrapper).exists()).toBe(false)

    // Editar depois de recarregar: o formulário vem com a nota do servidor.
    await wrapper.get('[data-teste="avaliacao-editar"]').trigger('click')
    expect(wrapper.get('[data-teste="estrela-2"]').attributes('aria-checked')).toBe('true')
  })

  it('Editar abre o formulário preenchido e salva pelo mesmo POST (upsert)', async () => {
    await entrar()
    const wrapper = await montar()
    await escolherNota(wrapper, 2)
    await wrapper.get('textarea').setValue('Sem sal')
    await enviar(wrapper)
    const post = vi.spyOn(apiClient, 'post')

    await wrapper.get('[data-teste="avaliacao-editar"]').trigger('click')
    expect(wrapper.get('textarea').element.value).toBe('Sem sal')
    expect(wrapper.get('[data-teste="estrela-2"]').attributes('aria-checked')).toBe('true')
    await escolherNota(wrapper, 5)
    await wrapper.get('textarea').setValue('Corrigiram o sal')
    await enviar(wrapper)

    expect(post).toHaveBeenCalledWith('/avaliacoes/', {
      refeicaoId: expect.any(Number),
      nota: 5,
      comentario: 'Corrigiram o sal',
    })
    expect(texto(wrapper)).toContain('Avaliação atualizada!')
    expect(texto(wrapper)).toContain('Sua nota: 5 estrelas')
    // Editar não duplica: só um comentário do próprio apelido.
    const meus = wrapper
      .findAll('[data-teste="avaliacao-comentario"]')
      .filter((c) => c.text().includes(CONTA_DEMO.apelido))
    expect(meus).toHaveLength(1)
  })

  it('Cancelar edição volta à confirmação sem enviar', async () => {
    await entrar()
    const wrapper = await montar()
    await escolherNota(wrapper, 3)
    await enviar(wrapper)
    const post = vi.spyOn(apiClient, 'post')

    await wrapper.get('[data-teste="avaliacao-editar"]').trigger('click')
    await wrapper.get('[data-teste="avaliacao-cancelar"]').trigger('click')

    expect(post).not.toHaveBeenCalled()
    expect(texto(wrapper)).toContain('Sua nota: 3 estrelas')
  })
})

describe('AvaliacaoWidget — motivos de indisponível (RF15.1, RF05)', () => {
  it('visitante: convite ao login citando os pontos, sem formulário', async () => {
    const wrapper = await montar()

    expect(texto(wrapper)).toContain('Entre para avaliar')
    expect(texto(wrapper)).toMatch(/pontos/)
    expect(formulario(wrapper).exists()).toBe(false)
  })

  it('refeição de outro dia: motivo, sem formulário', async () => {
    await entrar()
    const wrapper = await montar({ ...ALMOCO_HOJE, data: '2026-09-29' })

    expect(indisponivel(wrapper).text()).toContain('Esta refeição ainda não aconteceu.')
    expect(formulario(wrapper).exists()).toBe(false)
  })

  it('refeição de hoje que ainda não começou: diz quando abre', async () => {
    await entrar()
    const wrapper = await montar({ ...ALMOCO_HOJE, tipo: 'jantar' })

    expect(indisponivel(wrapper).text()).toContain('A avaliação do jantar abre às 17h')
    expect(formulario(wrapper).exists()).toBe(false)
  })

  it('refeição sem cardápio (fora do resumo do dia): motivo próprio', async () => {
    await entrar()
    // Domingo: o Gama não abre.
    const wrapper = await montar({ ...ALMOCO_HOJE, data: '2026-10-04' })

    expect(indisponivel(wrapper).text()).toContain('não tem cardápio publicado')
  })

  it('backend sem a BE-13 (501): avisa que as avaliações ainda não estão disponíveis', async () => {
    await entrar()
    simulacao.definirAvaliacoesDisponiveis(false)
    const wrapper = await montar()

    expect(indisponivel(wrapper).text()).toContain('As avaliações ainda não estão disponíveis.')
    expect(formulario(wrapper).exists()).toBe(false)
  })

  it('resumo do dia em 501: avisa que as avaliações ainda não estão disponíveis', async () => {
    await entrar()
    simulacao.definirResumoDoDiaDisponivel(false)
    const wrapper = await montar()

    expect(indisponivel(wrapper).text()).toContain('As avaliações ainda não estão disponíveis.')
  })

  it('servidor fecha a janela (422 janela_avaliacao_fechada): troca o formulário pelo motivo', async () => {
    await entrar()
    const { ApiError } = await import('@/services/apiClient')
    vi.spyOn(apiClient, 'post').mockRejectedValueOnce(
      new ApiError(422, { codigo: 'janela_avaliacao_fechada', mensagem: 'Fechada.' }),
    )
    const wrapper = await montar()

    await escolherNota(wrapper, 4)
    await enviar(wrapper)

    expect(indisponivel(wrapper).text()).toContain('A avaliação desta refeição está fechada.')
    expect(formulario(wrapper).exists()).toBe(false)
  })

  it('sessão perdida no envio (401): volta ao convite ao login, dizendo que expirou', async () => {
    await entrar()
    const wrapper = await montar()
    simulacao.expirarSessao()

    await escolherNota(wrapper, 4)
    await enviar(wrapper)

    expect(texto(wrapper)).toContain('Sua sessão expirou')
    expect(formulario(wrapper).exists()).toBe(false)
  })

  it('trocar de refeição descarta o rascunho e o motivo anterior', async () => {
    await entrar()
    const wrapper = await montar()
    await escolherNota(wrapper, 4)
    await wrapper.get('textarea').setValue('rascunho')

    await wrapper.setProps({ tipo: 'cafe' })
    await flushPromises()

    expect(wrapper.get('textarea').element.value).toBe('')
  })
})

/** Casos da revisão do PR #223. */
describe('AvaliacaoWidget — respostas inesperadas e falhas de carga', () => {
  it('2xx sem corpo: o botão volta de "Enviando…" e a mensagem aparece', async () => {
    await entrar()
    vi.spyOn(apiClient, 'post').mockResolvedValueOnce(null)
    vi.spyOn(console, 'error').mockImplementation(() => {})
    const wrapper = await montar()

    await escolherNota(wrapper, 4)
    await enviar(wrapper)

    const botao = wrapper.get('[data-teste="avaliacao-enviar"]')
    expect(botao.text()).toBe('Enviar avaliação')
    expect(botao.attributes('disabled')).toBeUndefined()
    expect(formulario(wrapper).text()).toContain('Não deu para confirmar se a avaliação foi salva.')
  })

  it('resumo do dia com 500: "Notas indisponíveis", erro com "Tentar de novo" que recupera', async () => {
    await entrar()
    const { ApiError } = await import('@/services/apiClient')
    vi.spyOn(apiClient, 'get').mockRejectedValueOnce(new ApiError(500, {}))
    vi.spyOn(console, 'error').mockImplementation(() => {})
    const wrapper = await montar()

    expect(wrapper.get('[data-teste="avaliacao-resumo"]').text()).toBe('Notas indisponíveis')
    expect(texto(wrapper)).not.toContain('Carregando')
    const erro = wrapper.get('[data-teste="avaliacao-erro"]')
    expect(erro.text()).toContain('Não foi possível carregar as avaliações.')

    await erro.get('[data-teste="avaliacao-tentar-de-novo"]').trigger('click')
    await flushPromises()

    expect(wrapper.find('[data-teste="avaliacao-erro"]').exists()).toBe(false)
    expect(formulario(wrapper).exists()).toBe(true)
    expect(wrapper.find('[data-teste="avaliacao-quantidade"]').exists()).toBe(true)
  })

  it('dia sem cardápio: o cartão de resumo diz "Sem avaliações ainda" (visitante e logada)', async () => {
    // Domingo: o Gama não abre.
    const visitante = await montar({ ...ALMOCO_HOJE, data: '2026-10-04' })
    expect(visitante.get('[data-teste="avaliacao-resumo"]').text()).toBe('Sem avaliações ainda')

    await entrar()
    const logada = await montar({ ...ALMOCO_HOJE, data: '2026-10-04' })
    expect(logada.get('[data-teste="avaliacao-resumo"]').text()).toBe('Sem avaliações ainda')
  })

  it('GET dos comentários falha: o formulário aparece mesmo assim, e os comentários têm "Tentar de novo"', async () => {
    await entrar()
    const avaliacoes = useAvaliacoesStore()
    await avaliacoes.carregarResumoDoDia(3, HOJE)
    const { ApiError } = await import('@/services/apiClient')
    vi.spyOn(apiClient, 'get').mockRejectedValueOnce(new ApiError(500, {}))
    vi.spyOn(console, 'error').mockImplementation(() => {})
    const wrapper = await montar()

    expect(formulario(wrapper).exists()).toBe(true)
    expect(wrapper.get('[data-teste="avaliacao-resumo"]').text()).toBe('Notas indisponíveis')
    const erro = wrapper.get('[data-teste="avaliacao-erro"]')

    await erro.get('[data-teste="avaliacao-tentar-de-novo"]').trigger('click')
    await flushPromises()

    expect(wrapper.findAll('[data-teste="avaliacao-comentario"]').length).toBeGreaterThan(0)
  })

  it('2xx com a recarga falhando: aviso neutro, sem erro vermelho', async () => {
    await entrar()
    const wrapper = await montar()
    const { ApiError } = await import('@/services/apiClient')
    vi.spyOn(apiClient, 'get').mockRejectedValue(new ApiError(0, { mensagem: 'Sem internet.' }))
    vi.spyOn(console, 'error').mockImplementation(() => {})

    await escolherNota(wrapper, 4)
    await enviar(wrapper)

    expect(texto(wrapper)).toContain('Avaliação enviada!')
    expect(wrapper.get('[data-teste="avaliacao-desatualizada"]').text()).toContain(
      'A média e os comentários ainda não foram atualizados.',
    )
    expect(wrapper.find('.mensagem--erro').exists()).toBe(false)
  })

  it.each([
    ['refeicao_nao_encontrada', 404, 'avaliacao-indisponivel', 'não está no cardápio'],
    ['nota_invalida', 422, 'avaliacao-formulario', 'Escolha uma nota de 1 a 5 estrelas.'],
    ['erro_interno', 500, 'avaliacao-formulario', 'Fora do ar.'],
  ])('%s (%i): mensagem no lugar certo', async (codigo, status, onde, trecho) => {
    await entrar()
    const { ApiError } = await import('@/services/apiClient')
    vi.spyOn(apiClient, 'post').mockRejectedValueOnce(
      new ApiError(status, { codigo, mensagem: 'Fora do ar.' }),
    )
    vi.spyOn(console, 'error').mockImplementation(() => {})
    const wrapper = await montar()

    await escolherNota(wrapper, 4)
    await enviar(wrapper)

    expect(wrapper.get(`[data-teste="${onde}"]`).text()).toContain(trecho)
  })

  it('envio duplo: dois toques seguidos mandam um POST só', async () => {
    await entrar()
    const post = vi.spyOn(apiClient, 'post')
    const wrapper = await montar()
    await escolherNota(wrapper, 4)

    wrapper.get('[data-teste="avaliacao-formulario"]').trigger('submit')
    wrapper.get('[data-teste="avaliacao-formulario"]').trigger('submit')
    await flushPromises()

    expect(post.mock.calls.filter(([caminho]) => caminho === '/avaliacoes/')).toHaveLength(1)
  })
})

describe('AvaliacaoWidget — troca de refeição no meio do envio', () => {
  it('resposta de um envio antigo não aparece na refeição nova', async () => {
    await entrar()
    let responder
    vi.spyOn(apiClient, 'post').mockImplementationOnce(
      () => new Promise((resolver) => (responder = resolver)),
    )
    const wrapper = await montar()
    await escolherNota(wrapper, 4)
    await wrapper.get('[data-teste="avaliacao-formulario"]').trigger('submit')

    await wrapper.setProps({ tipo: 'cafe' })
    await flushPromises()
    responder({
      avaliacao: {
        id: 1,
        refeicaoId: 1,
        nota: 4,
        comentario: '',
        criadaEm: SEGUNDA_MEIO_DIA.toISOString(),
        editadaEm: null,
      },
      pontos: { total: 5, contribuicao: 0, avaliacaoLiberada: 5 },
    })
    await flushPromises()

    expect(texto(wrapper)).not.toContain('Avaliação enviada!')
    expect(texto(wrapper)).not.toContain('+5 pontos')
    expect(wrapper.get('[data-teste="avaliacao-enviar"]').attributes('disabled')).toBeDefined()
    expect(wrapper.get('[data-teste="avaliacao-enviar"]').text()).toBe('Enviar avaliação')
  })
})

describe('AvaliacaoWidget — sessão expirada no envio', () => {
  it('avisa que a nota não foi enviada e guarda o rascunho para depois do login', async () => {
    await entrar()
    const wrapper = await montar()
    await escolherNota(wrapper, 4)
    await wrapper.get('textarea').setValue('Quase perdi isto')
    simulacao.expirarSessao()

    await enviar(wrapper)

    expect(texto(wrapper)).toContain('Sua sessão expirou')
    expect(texto(wrapper)).toContain('A avaliação não foi enviada')

    // Entra de novo (sem recarregar a página): o widget volta com o rascunho.
    await entrar()
    await flushPromises()
    expect(wrapper.get('textarea').element.value).toBe('Quase perdi isto')
    expect(wrapper.get('[data-teste="estrela-4"]').attributes('aria-checked')).toBe('true')
  })
})

describe('AvaliacaoWidget — acessibilidade', () => {
  it('o cartão do motivo é anunciado (role="status")', async () => {
    await entrar()
    const wrapper = await montar({ ...ALMOCO_HOJE, tipo: 'jantar' })

    expect(indisponivel(wrapper).attributes('role')).toBe('status')
  })

  it('depois do envio, o foco vai para a confirmação; o botão Editar fica fora do role="status"', async () => {
    await entrar()
    const wrapper = await montar()

    await escolherNota(wrapper, 4)
    await enviar(wrapper)

    const titulo = wrapper.get('[data-teste="avaliacao-enviada-titulo"]')
    expect(document.activeElement).toBe(titulo.element)
    const status = wrapper.get('[data-teste="avaliacao-enviada"] [role="status"]')
    expect(status.find('[data-teste="avaliacao-editar"]').exists()).toBe(false)
  })

  it('setas mudam a nota nas estrelas, com um só item tabulável', async () => {
    await entrar()
    const wrapper = await montar()
    const estrela = (n) => wrapper.get(`[data-teste="estrela-${n}"]`)

    await estrela(1).trigger('keydown', { key: 'ArrowRight' })
    expect(estrela(1).attributes('aria-checked')).toBe('true')
    await estrela(1).trigger('keydown', { key: 'ArrowRight' })
    expect(estrela(2).attributes('aria-checked')).toBe('true')
    expect(document.activeElement).toBe(estrela(2).element)
    await estrela(2).trigger('keydown', { key: 'ArrowLeft' })
    expect(estrela(1).attributes('aria-checked')).toBe('true')

    const tabulaveis = [1, 2, 3, 4, 5].filter((n) => estrela(n).attributes('tabindex') === '0')
    expect(tabulaveis).toEqual([1])
  })
})

describe('AvaliacaoWidget — relógio', () => {
  it('a janela abre sozinha quando dá a hora, com o widget aberto', async () => {
    vi.useFakeTimers({ toFake: ['Date', 'setInterval', 'clearInterval'] })
    vi.setSystemTime(new Date(2026, 8, 28, 10, 59, 40))
    await entrar()
    const wrapper = await montar()
    expect(indisponivel(wrapper).text()).toContain('abre às 11h')

    vi.advanceTimersByTime(30 * 1000)
    await flushPromises()

    expect(indisponivel(wrapper).exists()).toBe(false)
    expect(formulario(wrapper).exists()).toBe(true)
  })
})
