/**
 * "Banco de dados" do backend simulado. Guarda contas, avaliações e links
 * enviados por e-mail no localStorage do navegador, só para que a
 * demonstração sobreviva a um recarregamento de página. Não é usado quando
 * VITE_USE_MOCK=false.
 */

const CHAVE = 'bandejao:backend-simulado'

/**
 * Resumo não reversível da senha. Apenas para a simulação: o backend real
 * usa o hasher de senhas do Django (RNF04/RI04).
 */
export function resumoSenha(senha) {
  let hash = 0x811c9dc5
  for (const caractere of `bandejao:${senha}`) {
    hash ^= caractere.codePointAt(0)
    hash = Math.imul(hash, 0x01000193) >>> 0
  }
  return hash.toString(16)
}

/** Conta de demonstração, já confirmada, para testar o login. */
export const CONTA_DEMO = {
  email: '231034567@aluno.unb.br',
  senha: 'bandejao123',
  apelido: 'estudante_demo',
}

function estadoInicial() {
  return {
    usuarios: [
      {
        id: 1,
        tipo: 'estudante',
        email: CONTA_DEMO.email,
        identificador: '231034567',
        apelido: CONTA_DEMO.apelido,
        senha: resumoSenha(CONTA_DEMO.senha),
        confirmado: true,
        criadoEm: new Date(0).toISOString(),
      },
    ],
    avaliacoes: [],
    links: [],
    proximoId: 2,
  }
}

function lerArmazenado() {
  try {
    const bruto = globalThis.localStorage?.getItem(CHAVE)
    return bruto ? JSON.parse(bruto) : null
  } catch {
    return null
  }
}

let estado = lerArmazenado() ?? estadoInicial()

export const banco = {
  get estado() {
    return estado
  },
  salvar() {
    try {
      globalThis.localStorage?.setItem(CHAVE, JSON.stringify(estado))
    } catch {
      // armazenamento indisponível (aba anônima, cota): segue só em memória
    }
  },
  reiniciar() {
    estado = estadoInicial()
    this.salvar()
  },
  novoId() {
    return estado.proximoId++
  },
}
