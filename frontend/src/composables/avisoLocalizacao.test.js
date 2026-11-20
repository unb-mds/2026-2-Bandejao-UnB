import { beforeEach, describe, expect, it } from 'vitest'
import {
  abrirAvisoLocalizacao,
  estadoLocalizacao,
  pedidosDeAberturaDoAviso,
  registrarDesfechoDoAviso,
  reiniciarAvisoLocalizacaoParaTestes,
} from './avisoLocalizacao'

beforeEach(() => {
  reiniciarAvisoLocalizacaoParaTestes()
})

describe('composable avisoLocalizacao', () => {
  it('cada abertura é um novo pedido para o AvisoLocalizacao', () => {
    abrirAvisoLocalizacao()
    abrirAvisoLocalizacao()

    expect(pedidosDeAberturaDoAviso.value).toBe(2)
  })

  it('abrirAvisoLocalizacao devolve como o aviso terminou', async () => {
    const desfecho = abrirAvisoLocalizacao()

    registrarDesfechoDoAviso('adiado')

    expect(await desfecho).toBe('adiado')
  })

  it('todas as aberturas pendentes recebem o mesmo desfecho', async () => {
    const primeira = abrirAvisoLocalizacao()
    const segunda = abrirAvisoLocalizacao()

    registrarDesfechoDoAviso('concedida')

    expect(await Promise.all([primeira, segunda])).toEqual(['concedida', 'concedida'])
  })

  it('o último desfecho fica disponível para qualquer tela, sem coordenadas (RI09)', () => {
    registrarDesfechoDoAviso('negada')

    expect(estadoLocalizacao.value).toBe('negada')
  })

  it('o reinício para testes zera pedidos e estado', () => {
    abrirAvisoLocalizacao()
    registrarDesfechoDoAviso('concedida')

    reiniciarAvisoLocalizacaoParaTestes()

    expect(pedidosDeAberturaDoAviso.value).toBe(0)
    expect(estadoLocalizacao.value).toBeNull()
  })
})
