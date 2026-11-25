import { readonly, ref } from 'vue'

/**
 * Ponte entre as telas e o AvisoLocalizacao, que fica no App raiz (RF19).
 *
 * Um contador funciona como evento: cada abrirAvisoLocalizacao() soma um e o
 * componente, que observa o contador, abre o aviso. A Promise devolvida
 * resolve com o desfecho quando o aviso fecha, e estadoLocalizacao guarda o
 * último desfecho para qualquer tela consultar. Só o desfecho circula, nunca
 * coordenadas (RI09).
 *
 * Desfechos: 'concedida', 'sem-sinal' (permitida, mas a localização do
 * aparelho está desligada), 'negada', 'adiado' ("Agora não"),
 * 'indisponivel' e 'inseguro' (fora de HTTPS).
 */
const pedidos = ref(0)
const estado = ref(null)
let aguardando = []

export const pedidosDeAberturaDoAviso = readonly(pedidos)
export const estadoLocalizacao = readonly(estado)

export function abrirAvisoLocalizacao() {
  pedidos.value++
  return new Promise((resolver) => aguardando.push(resolver))
}

/** Chamado pelo AvisoLocalizacao quando sabe como a localização ficou. */
export function registrarDesfechoDoAviso(desfecho) {
  estado.value = desfecho
  const resolvedores = aguardando
  aguardando = []
  resolvedores.forEach((resolver) => resolver(desfecho))
}

/** Zera pedidos, estado e Promises pendentes entre um teste e outro. */
export function reiniciarAvisoLocalizacaoParaTestes() {
  pedidos.value = 0
  estado.value = null
  aguardando = []
}
