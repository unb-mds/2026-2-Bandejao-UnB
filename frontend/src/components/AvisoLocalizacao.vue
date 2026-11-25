<script setup>
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { usePreferenciasStore } from '@/stores/preferencias'
import { consultarPermissao, pedirPermissao } from '@/services/permissaoLocalizacao'
import { pedidosDeAberturaDoAviso, registrarDesfechoDoAviso } from '@/composables/avisoLocalizacao'
import IconeSvg from './IconeSvg.vue'

/**
 * Aviso de localização em duas etapas (RF19, front 3a.1 e 4d): primeiro o
 * aviso do Bandejão; se a pessoa escolhe "Permitir localização", o pedido do
 * navegador.
 *
 * - Abre sozinho a cada abertura do app enquanto o navegador ainda pode
 *   perguntar e não há "Agora não" guardado. Sem Permissions API, abre até a
 *   pessoa permitir uma vez (marca guardada na preferenciasStore).
 * - abrirAvisoLocalizacao() (composable) abre de qualquer tela e sempre dá um
 *   retorno: o aviso, o passo a passo se o navegador bloqueou, a confirmação
 *   se já está liberada ou a explicação se não há como usar a localização.
 * - O desfecho vai para o composable (registrarDesfechoDoAviso), que o
 *   entrega a quem abriu o aviso. Só o desfecho, sem coordenadas (RI09).
 */
const preferencias = usePreferenciasStore()

/**
 * null (fechado) | 'aviso' | 'navegador' (esperando o pedido do navegador) |
 * 'bloqueado' (passo a passo) | 'concedida' | 'sem-sinal' | 'indisponivel' |
 * 'inseguro' (as quatro últimas só quando aberto de propósito ou após pedir)
 */
const etapa = ref(null)
const mensagem = ref('')
const dialogo = ref(null)
const titulo = ref(null)
let focoAnterior = null
let consultando = false
// Abertura pelo menu que chegou enquanto a abertura do app ainda consultava.
let pedidoDuranteConsulta = false
// Cada pedido ao navegador ganha um número; respostas de pedidos antigos são ignoradas.
let pedidoAtual = 0

const INFORMACOES = {
  concedida: {
    icone: 'check',
    titulo: 'A localização já está liberada',
    texto: 'O Bandejão já pode usar a localização para achar seu campus e para o check-in.',
    botao: 'Entendi',
  },
  'sem-sinal': {
    icone: 'alerta',
    titulo: 'A localização do aparelho está desligada',
    texto:
      'O navegador deixou, mas não conseguiu ler a posição. Ative a localização nas configurações do aparelho e tente de novo.',
    botao: 'Fechar',
  },
  indisponivel: {
    icone: 'alerta',
    titulo: 'Este navegador não oferece localização',
    texto: 'O cardápio, as avaliações e a fila continuam abertos.',
    botao: 'Fechar',
  },
  inseguro: {
    icone: 'cadeado',
    titulo: 'A localização precisa de uma conexão segura',
    texto:
      'O navegador só libera a localização em endereços com https://. Abra o Bandejão pelo endereço oficial.',
    botao: 'Fechar',
  },
}
const informacao = computed(() => INFORMACOES[etapa.value] ?? null)

/** Abre como modal; sem showModal (navegador antigo), só marca como aberto. */
function abrirDialogo() {
  const el = dialogo.value
  if (!el || el.open) return
  if (typeof el.showModal === 'function') el.showModal()
  else el.setAttribute('open', '')
}

function fecharDialogo() {
  const el = dialogo.value
  if (!el) return
  if (typeof el.close === 'function') el.close()
  else el.removeAttribute('open')
}

async function mostrar(novaEtapa, novaMensagem = '') {
  if (!etapa.value) focoAnterior = document.activeElement
  etapa.value = novaEtapa
  mensagem.value = novaMensagem
  await nextTick()
  abrirDialogo()
  titulo.value?.focus()
}

function fechar(desfecho) {
  pedidoAtual++
  etapa.value = null
  mensagem.value = ''
  fecharDialogo()
  if (focoAnterior?.isConnected) focoAnterior.focus()
  focoAnterior = null
  registrarDesfechoDoAviso(desfecho)
}

async function abrir({ primeiroAcesso }) {
  // Já aberto (inclusive esperando o navegador): quem pediu recebe o desfecho deste aviso.
  if (etapa.value) return
  if (consultando) {
    if (!primeiroAcesso) pedidoDuranteConsulta = true
    return
  }
  consultando = true
  try {
    const permissao = await consultarPermissao()
    if (primeiroAcesso) return abrirSozinho(permissao)
    if (permissao === 'negada') return mostrar('bloqueado')
    if (permissao === 'pendente' || permissao === 'desconhecida') return mostrar('aviso')
    mostrar(permissao)
  } finally {
    consultando = false
    // A abertura do app pode ter decidido não mostrar nada; o pedido do menu ainda merece resposta.
    const reabrir = pedidoDuranteConsulta && !etapa.value
    pedidoDuranteConsulta = false
    if (reabrir) abrir({ primeiroAcesso: false })
  }
}

function abrirSozinho(permissao) {
  const podePerguntar =
    permissao === 'pendente' || (permissao === 'desconhecida' && !preferencias.localizacaoPermitida)
  if (!podePerguntar) {
    if (permissao !== 'desconhecida') registrarDesfechoDoAviso(permissao)
    return
  }
  if (!preferencias.avisoLocalizacaoAdiado) mostrar('aviso')
}

function agoraNao() {
  preferencias.adiarAvisoLocalizacao()
  fechar('adiado')
}

async function permitir() {
  const pedido = ++pedidoAtual
  etapa.value = 'navegador'
  mensagem.value = ''
  const resultado = await pedirPermissao()
  if (pedido !== pedidoAtual) return

  if (resultado === 'concedida' || resultado === 'sem-sinal') {
    preferencias.registrarLocalizacaoPermitida()
  }
  if (resultado === 'concedida') return fechar('concedida')
  if (resultado === 'negada') return mostrar('bloqueado')
  if (resultado === 'dispensada' || resultado === 'sem-resposta') {
    return mostrar(
      'aviso',
      'O navegador não respondeu. Toque em "Permitir localização" para tentar de novo.',
    )
  }
  mostrar(resultado)
}

async function jaLiberei() {
  const estado = await consultarPermissao()
  if (estado === 'concedida') return fechar('concedida')
  if (estado === 'pendente' || estado === 'desconhecida') return permitir()
  mensagem.value = 'Ainda está bloqueado. Confira os passos acima.'
}

/**
 * Esc, gesto de voltar ou o navegador fechando o <dialog> sozinho: no aviso
 * vale como "Agora não"; nas outras etapas, fecha. O close disparado pelo
 * próprio fechar() não faz nada, porque a etapa já foi zerada.
 */
function pedirFechamento() {
  if (!etapa.value) return
  if (etapa.value === 'aviso' || etapa.value === 'navegador') return agoraNao()
  fechar(etapa.value === 'bloqueado' ? 'negada' : etapa.value)
}

onMounted(() => abrir({ primeiroAcesso: true }))
// O reinício do contador (testes) não é pedido de abertura.
watch(pedidosDeAberturaDoAviso, (vezes) => {
  if (vezes > 0) abrir({ primeiroAcesso: false })
})
</script>

<template>
  <dialog
    ref="dialogo"
    class="aviso-localizacao"
    aria-labelledby="aviso-localizacao-titulo"
    aria-describedby="aviso-localizacao-texto"
    @cancel.prevent="pedirFechamento"
    @keydown.esc.prevent="pedirFechamento"
    @close="etapa && pedirFechamento()"
  >
    <section v-if="etapa" class="cartao painel">
      <template v-if="etapa === 'aviso' || etapa === 'navegador'">
        <div class="icone-caixa">
          <IconeSvg nome="local" :tamanho="24" cor="var(--branco)" />
        </div>
        <p class="rotulo rotulo-desktop">Localização</p>
        <h2 id="aviso-localizacao-titulo" ref="titulo" tabindex="-1" class="titulo">
          Usar sua localização?
        </h2>
        <p id="aviso-localizacao-texto" class="texto">
          Ela identifica o campus mais próximo e confirma o check-in no RU. Na identificação do
          campus, as coordenadas não saem do aparelho; no check-in, são descartadas depois da
          conferência.
        </p>

        <p v-if="etapa === 'navegador'" class="mensagem mensagem--alerta" role="status">
          Agora é com o navegador: responda ao pedido que apareceu na tela.
        </p>
        <p v-else-if="mensagem" class="mensagem mensagem--alerta" role="status">{{ mensagem }}</p>

        <div class="acoes">
          <button
            type="button"
            class="botao botao--primario"
            :disabled="etapa === 'navegador'"
            @click="permitir"
          >
            Permitir localização
            <IconeSvg nome="local" :tamanho="18" class="icone-desktop" />
          </button>
          <button type="button" class="botao-texto botao-secundario" @click="agoraNao">
            Agora não
          </button>
        </div>
      </template>

      <template v-else-if="etapa === 'bloqueado'">
        <div class="alerta">
          <IconeSvg nome="alerta" :tamanho="20" cor="var(--dourado)" />
          <div>
            <h2 id="aviso-localizacao-titulo" ref="titulo" tabindex="-1" class="alerta-titulo">
              O acesso à localização foi bloqueado
            </h2>
            <p id="aviso-localizacao-texto" class="alerta-texto">
              Libere a localização nas configurações do navegador:
            </p>
          </div>
        </div>
        <ol class="passos">
          <li>
            Toque no ícone ao lado do endereço do site (cadeado ou <em>aA</em>) ou abra as
            configurações do app instalado.
          </li>
          <li>Abra <strong>Permissões</strong> ou <strong>Configurações do site</strong>.</li>
          <li>Em <strong>Localização</strong>, escolha <strong>Permitir</strong>.</li>
          <li>
            No iPhone, confira também
            <strong>Ajustes › Privacidade › Serviços de Localização</strong>.
          </li>
        </ol>
        <p class="nota">Sem a localização, o cardápio, as avaliações e a fila continuam abertos.</p>
        <p v-if="mensagem" class="mensagem mensagem--alerta" role="status">{{ mensagem }}</p>

        <div class="acoes">
          <button type="button" class="botao botao--primario" @click="jaLiberei">Já liberei</button>
          <button type="button" class="botao-texto botao-secundario" @click="fechar('negada')">
            Fechar
          </button>
        </div>
      </template>

      <template v-else-if="informacao">
        <div class="icone-caixa" :class="{ 'icone-caixa--suave': etapa !== 'concedida' }">
          <IconeSvg
            :nome="informacao.icone"
            :tamanho="24"
            :cor="etapa === 'concedida' ? 'var(--branco)' : 'var(--alerta-texto)'"
          />
        </div>
        <h2 id="aviso-localizacao-titulo" ref="titulo" tabindex="-1" class="titulo">
          {{ informacao.titulo }}
        </h2>
        <p id="aviso-localizacao-texto" class="texto">{{ informacao.texto }}</p>

        <div class="acoes">
          <button
            v-if="etapa === 'sem-sinal'"
            type="button"
            class="botao botao--primario"
            @click="permitir"
          >
            Tentar de novo
          </button>
          <button
            type="button"
            :class="
              etapa === 'sem-sinal' ? 'botao-texto botao-secundario' : 'botao botao--primario'
            "
            @click="fechar(etapa)"
          >
            {{ informacao.botao }}
          </button>
        </div>
      </template>
    </section>
  </dialog>
</template>

<style scoped>
/* Visual do protótipo (cartão "Usar sua localização?" da tela de campus). */
.aviso-localizacao {
  /* showModal põe o <dialog> na camada do topo; o fixed cobre o navegador sem showModal. */
  position: fixed;
  inset: 0;
  z-index: 50;
  width: calc(100% - 32px);
  max-width: 420px;
  height: fit-content;
  max-height: calc(100% - 32px);
  margin: auto;
  padding: 0;
  border: 0;
  background: transparent;
  overflow: visible;
}

.aviso-localizacao::backdrop {
  background: var(--fundo-dialogo);
}

.painel {
  max-height: calc(100dvh - 32px);
  overflow-y: auto;
  padding: 24px;
  font-family: var(--fonte-texto);
}

.icone-caixa {
  width: 56px;
  height: 56px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--raio-md);
  background: var(--verde-escuro);
}

.icone-caixa--suave {
  background: var(--alerta-fundo);
}

.titulo {
  margin-top: 16px;
  font-family: var(--fonte-titulo);
  font-weight: 900;
  font-size: 20px;
  color: var(--texto-escuro);
  outline: none;
}

.texto {
  margin-top: 12px;
  font-size: 14px;
  line-height: 1.6;
  color: var(--texto-suave);
}

.alerta {
  display: flex;
  gap: 12px;
  padding: 16px;
  border: 1.5px solid var(--alerta-borda);
  border-radius: var(--raio-md);
  background: var(--alerta-fundo);
}

.alerta :deep(svg) {
  flex-shrink: 0;
}

.alerta-titulo {
  font-size: 14px;
  font-weight: 900;
  color: var(--texto-escuro);
  outline: none;
}

.alerta-texto {
  margin-top: 4px;
  font-size: 13px;
  line-height: 1.5;
  color: var(--texto-suave);
}

.passos {
  margin-top: 16px;
  padding-left: 20px;
  font-size: 14px;
  line-height: 1.5;
  color: var(--texto-suave);
}

.passos li + li {
  margin-top: 8px;
}

.passos strong {
  color: var(--texto-escuro);
}

.nota {
  margin-top: 16px;
  font-size: 12px;
  color: var(--texto-claro);
}

.mensagem {
  margin-top: 16px;
}

.acoes {
  margin-top: 24px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.botao-texto {
  padding: 14px;
  text-align: center;
  font-size: 14px;
  font-weight: 700;
  color: var(--texto-suave);
}

.botao-texto:disabled {
  color: var(--texto-claro);
}

.rotulo-desktop,
.icone-desktop {
  display: none;
}

/* Desktop: proporções do painel de localização do protótipo desktop. */
@media (min-width: 768px) {
  .aviso-localizacao {
    max-width: 560px;
  }

  .painel {
    padding: 40px;
  }

  .icone-caixa {
    margin-bottom: 24px;
    border-radius: var(--raio-lg);
    box-shadow: var(--sombra-destaque);
  }

  .rotulo-desktop {
    display: block;
    margin-bottom: 8px;
  }

  .icone-desktop {
    display: block;
  }

  .titulo {
    margin-top: 0;
    font-size: 32px;
    line-height: 1.05;
    letter-spacing: -0.02em;
  }

  .texto {
    margin-top: 10px;
  }

  .acoes {
    gap: 10px;
  }

  .botao--primario {
    box-shadow: var(--sombra-destaque);
  }

  .botao-secundario {
    border: 1.5px solid var(--borda);
    border-radius: var(--raio-lg);
  }

  .botao-secundario:hover:not(:disabled) {
    color: var(--verde-escuro);
  }
}
</style>
