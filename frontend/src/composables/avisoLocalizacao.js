import { readonly, ref } from 'vue'

/**
 * Abre o AvisoLocalizacao (que fica no App raiz) a partir de qualquer tela:
 * o ponto fixo "Usar minha localização" e, depois, o CheckinBotao (RF19).
 */
const pedidoDeAbertura = ref(0)

export const aberturasDoAvisoLocalizacao = readonly(pedidoDeAbertura)

export function abrirAvisoLocalizacao() {
  pedidoDeAbertura.value++
}

/** Zera os pedidos de abertura (usado nos testes). */
export function fecharAvisoLocalizacao() {
  pedidoDeAbertura.value = 0
}
