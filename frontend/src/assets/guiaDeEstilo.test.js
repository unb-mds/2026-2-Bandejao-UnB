// @vitest-environment node
import { readFileSync, readdirSync } from 'node:fs'
import { join, sep } from 'node:path'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'

/**
 * Guia de estilo (RF17, #286): cores e raios vêm dos tokens do `base.css`.
 * Confere o código-fonte de todas as telas, componentes e do `main.css`. Ficam
 * de fora apenas o próprio `base.css`, que define os tokens.
 * Sombras completas devem ocupar todo o valor da propriedade CSS.
 * A guarda cobre hex, rgb/rgba, hsl/hsla, branco literal em SVG e raios CSS.
 * Não é um parser CSS/JS: outras funções, palavras-chave e borderRadius em JS
 * não são cobertos integralmente.
 */
const SRC = fileURLToPath(new URL('..', import.meta.url))
const FORA = ['assets/base.css']

// Lidos do disco: no Vitest, o `?raw` de um .css chega vazio.
const ARQUIVOS = Object.fromEntries(
  readdirSync(SRC, { recursive: true })
    .map((caminho) => caminho.split(sep).join('/'))
    .filter((caminho) => /\.(vue|css)$/.test(caminho) && !FORA.includes(caminho))
    .map((caminho) => [caminho, readFileSync(join(SRC, caminho), 'utf-8')]),
)

const BASE = readFileSync(join(SRC, 'assets/base.css'), 'utf-8')

// Preserva as linhas para que os diagnósticos apontem para o código original.
function semComentarios(codigo) {
  return codigo.replace(/<!--[^]*?-->|\/\*[^]*?\*\/|^\s*\/\/[^\n]*/gm, (trecho) =>
    trecho.replace(/[^\n]/g, ' '),
  )
}

/** Cada ocorrência de `padrao` como "arquivo:linha: trecho". */
function ocorrencias(padrao) {
  return Object.entries(ARQUIVOS).flatMap(([arquivo, codigo]) =>
    semComentarios(codigo)
      .split('\n')
      .map((linha, indice) => ({ linha, numero: indice + 1 }))
      .filter(({ linha }) => padrao.test(linha))
      .map(({ linha, numero }) => `${arquivo}:${numero}: ${linha.trim()}`),
  )
}

describe('guia de estilo: cores e raios só pelos tokens do base.css (RF17, #286)', () => {
  it('confere os arquivos de verdade (a leitura não veio vazia)', () => {
    expect(ARQUIVOS['assets/main.css']).toContain('.botao')
    expect(ARQUIVOS['views/HomeView.vue']).toContain('<template>')
    expect(Object.keys(ARQUIVOS)).toContain('components/AppLogo.vue')
    expect(BASE).toContain('--verde-escuro')
  })

  it('nenhuma cor hexadecimal solta, nem o branco (#fff)', () => {
    expect(ocorrencias(/#[0-9a-f]{3,8}\b/i)).toEqual([])
  })

  it('nenhuma cor rgb() ou rgba() solta (sombras, fundos de diálogo e textos)', () => {
    expect(ocorrencias(/\brgba?\(/i)).toEqual([])
  })

  it('nenhuma cor hsl/hsla ou branco literal em SVG', () => {
    expect(ocorrencias(/\bhsla?\(|\b(?:stroke|fill)=["']white["']/i)).toEqual([])
  })

  it('ignora números de issues em comentários', () => {
    expect(semComentarios('/* #286 */\n<!-- #192 -->\n// #290\ncolor: #fff;')).not.toMatch(
      /#(?:286|192|290)/,
    )
    expect(semComentarios('/* #286 */\ncolor: #fff;')).toContain('color: #fff;')
  })

  it('todos os tokens referenciados estão definidos', () => {
    const definidos = new Set(
      [...semComentarios(BASE).matchAll(/(--[\w-]+)\s*:/g)].map((m) => m[1]),
    )
    const ausentes = Object.entries(ARQUIVOS).flatMap(([arquivo, codigo]) =>
      [...semComentarios(codigo).matchAll(/var\(\s*(--[\w-]+)/g)]
        .filter((m) => !definidos.has(m[1]))
        .map((m) => `${arquivo}: ${m[1]}`),
    )
    expect(ausentes).toEqual([])
  })

  it('raio só por token, ou o círculo (50%) e a pílula (999px)', () => {
    const raios = ocorrencias(/border(-[a-z]+)*-radius\s*:/).filter((trecho) => {
      const valor = trecho
        .split(/radius\s*:/)[1]
        .replace(/;.*$/, '')
        .trim()
      return !/^(50%|999px|(var\(--raio-[a-z0-9]+\)|0)( (var\(--raio-[a-z0-9]+\)|0))*)$/.test(valor)
    })
    expect(raios).toEqual([])
  })

  it.each(['--branco', '--fundo-dialogo', '--raio-xs', '--raio-2xs'])(
    'o base.css define o token %s',
    (token) => {
      expect(BASE).toMatch(new RegExp(`${token}\\s*:`))
    },
  )

  it('o base.css nao possui tokens duplicados', () => {
    const tokens = [...semComentarios(BASE).matchAll(/(--[\w-]+)\s*:/g)].map((m) => m[1])
    const duplicados = tokens.filter((token, indice) => tokens.indexOf(token) !== indice)

    expect(duplicados).toEqual([])
  })

  it('sombras completas não podem ser combinadas com outros valores', () => {
    const completas = [...semComentarios(BASE).matchAll(/(--sombra-[\w-]+)\s*:\s*([^;]+);/g)]
      .filter((m) => /^-?\d/.test(m[2].trim()))
      .map((m) => m[1])

    expect(completas.length).toBeGreaterThan(0)

    const invalidas = Object.entries(ARQUIVOS).flatMap(([arquivo, codigo]) =>
      semComentarios(codigo)
        .split('\n')
        .flatMap((linha, indice) =>
          completas
            .filter((token) => linha.includes(`var(${token})`))
            .filter((token) => {
              const valor = `var(${token})`
              return !(
                linha.trim() === `box-shadow: ${valor};` ||
                linha.trim() === `filter: drop-shadow(${valor});`
              )
            })
            .map(() => `${arquivo}:${indice + 1}: ${linha.trim()}`),
        ),
    )

    expect(invalidas).toEqual([])
  })
})
