// @vitest-environment node
// Ambiente node: o `URL` do Node aceita `import.meta.url`, e o caminho do
// arquivo não depende da pasta onde o comando é rodado.
import { readFileSync, existsSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'

/**
 * O que o navegador confere para oferecer "Instalar app" (FE-14, RNF05,
 * Visão 9.2): manifest, ícones e as metas do iPhone no index.html. A
 * instalação de verdade é conferida no Chrome (Page.getInstallabilityErrors)
 * e nos aparelhos; aqui fica o que pode quebrar sem ninguém ver.
 */
const arquivo = (caminho) => fileURLToPath(new URL(`../${caminho}`, import.meta.url))
const publico = (caminho) => arquivo(`public${caminho}`)
const manifest = JSON.parse(readFileSync(publico('/manifest.webmanifest'), 'utf8'))
const indexHtml = readFileSync(arquivo('index.html'), 'utf8')

/** Tipo de cor do PNG (byte 25 do IHDR): 2 é RGB, sem canal alfa. */
const tipoDeCorPng = (caminho) => readFileSync(publico(caminho))[25]

/** Largura e altura de um PNG, lidas do cabeçalho IHDR. */
function tamanhoPng(caminho) {
  const bytes = readFileSync(publico(caminho))
  expect(bytes.subarray(1, 4).toString()).toBe('PNG')
  return `${bytes.readUInt32BE(16)}x${bytes.readUInt32BE(20)}`
}

describe('manifest.webmanifest', () => {
  it('tem nome, id, início, escopo e exibição de app', () => {
    expect(manifest).toMatchObject({
      name: expect.any(String),
      short_name: 'Bandejão',
      id: '/',
      start_url: '/',
      scope: '/',
      display: 'standalone',
      lang: 'pt-BR',
    })
    expect(manifest.short_name.length).toBeLessThanOrEqual(12)
  })

  it('cores iguais à theme-color do index.html', () => {
    const tema = indexHtml.match(/name="theme-color" content="([^"]+)"/)[1]

    expect(manifest.theme_color).toBe(tema)
    expect(manifest.background_color).toBe(tema)
  })

  it('ícones PNG de 192 e 512 para "any", com os arquivos no tamanho declarado', () => {
    const png = (tamanho) =>
      manifest.icons.find(
        (i) => i.sizes === tamanho && i.type === 'image/png' && i.purpose === 'any',
      )

    expect(['192x192', '512x512'].map((t) => png(t) && tamanhoPng(png(t).src))).toEqual([
      '192x192',
      '512x512',
    ])
  })

  it('um ícone "maskable" separado (o Chrome desaconselha "any maskable" no mesmo ícone)', () => {
    const mascaraveis = manifest.icons.filter((i) => i.purpose === 'maskable')

    expect(mascaraveis.length).toBeGreaterThan(0)
    for (const icone of mascaraveis) expect(tamanhoPng(icone.src)).toBe(icone.sizes)
    expect(manifest.icons.some((i) => i.purpose?.includes(' '))).toBe(false)
  })

  it('todo ícone declarado existe em public/', () => {
    const faltando = manifest.icons.map((i) => i.src).filter((src) => !existsSync(publico(src)))

    expect(faltando).toEqual([])
  })

  it('capturas para a janela de instalação com prévia: uma "wide" e uma "narrow"', () => {
    const formatos = manifest.screenshots.map((s) => s.form_factor).sort()

    expect(formatos).toEqual(['narrow', 'wide'])
    for (const captura of manifest.screenshots) {
      expect(captura.type).toBe('image/png')
      expect(captura.label).toEqual(expect.any(String))
      expect(tamanhoPng(captura.src)).toBe(captura.sizes)
      const [largura, altura] = captura.sizes.split('x').map(Number)
      // Regras do Chrome: entre 320 e 3840 px, e o lado maior até 2,3 vezes o menor.
      for (const lado of [largura, altura]) {
        expect(lado).toBeGreaterThanOrEqual(320)
        expect(lado).toBeLessThanOrEqual(3840)
      }
      expect(Math.max(largura, altura) / Math.min(largura, altura)).toBeLessThanOrEqual(2.3)
      // "wide" é deitada; "narrow", em pé.
      expect(largura > altura).toBe(captura.form_factor === 'wide')
    }
  })
})

describe('index.html', () => {
  it('liga o manifest', () => {
    expect(indexHtml).toContain('<link rel="manifest" href="/manifest.webmanifest" />')
  })

  it('iPhone: ícone da tela inicial que existe, nome curto e modo app', () => {
    const icone = indexHtml.match(/rel="apple-touch-icon" href="([^"]+)"/)[1]

    // O iPhone usa 180x180 na tela inicial e não aceita transparência.
    expect(tamanhoPng(icone)).toBe('180x180')
    expect(tipoDeCorPng(icone)).toBe(2)
    expect(indexHtml).toContain('<meta name="apple-mobile-web-app-title" content="Bandejão" />')
    expect(indexHtml).toContain('<meta name="mobile-web-app-capable" content="yes" />')
    expect(indexHtml).toContain('<meta name="apple-mobile-web-app-capable" content="yes" />')
  })
})
