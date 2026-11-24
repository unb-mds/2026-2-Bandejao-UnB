<script setup>
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useFilaStore } from '@/stores/fila'
import { usePreferenciasStore } from '@/stores/preferencias'
import { mensagemDeErro } from '@/services/apiClient'
import { consultarPermissao } from '@/services/permissaoLocalizacao'
import { lerPosicao } from '@/services/leituraPosicao'
import { abrirAvisoLocalizacao } from '@/composables/avisoLocalizacao'
import AvisoPrivacidade from './AvisoPrivacidade.vue'
import ConviteLogin from './ConviteLogin.vue'
import IconeSvg from './IconeSvg.vue'

/**
 * Check-in "Estou no RU" com confirmação por GPS (RF11, RF12, fluxo 4a).
 *
 * 1. Visitante: ConviteLogin no lugar do botão (RF05).
 * 2. Com `avisoPrivacidadePendente`: AvisoPrivacidade antes do GPS; a
 *    ciência vai para POST /api/privacidade/aceite/ (RNF07.1).
 * 3. Sem permissão de localização: AvisoLocalizacao (ou o passo a passo, se o
 *    navegador bloqueou), pelo composable do FE-04 (RF19).
 * 4. Leitura com os critérios da RN03 (lerPosicao). Leitura ruim nunca chega
 *    ao backend e não conta como tentativa.
 * 5. filaStore.confirmarCheckin envia as coordenadas só no corpo do
 *    POST /api/checkins/. Elas não ficam neste componente: vivem só dentro
 *    de `localizarEEnviar` (RI09).
 *
 * Quem decide raio e horário é sempre o backend.
 */
// Sem mutação no argumento do defineProps (FE-17): o Stryker envolve os
// valores em chamadas stryMutAct_*/stryCov_*, declaradas no próprio script, e
// o defineProps é içado para fora do setup(), onde não pode usar variáveis
// locais.
// Stryker disable all
const props = defineProps({
  /** Id do campus no backend (`GET /api/campi/`). */
  campusId: { type: Number, required: true },
  /** 'cafe' | 'almoco' | 'jantar' */
  tipoRefeicao: { type: String, required: true },
})
// Stryker restore all

const auth = useAuthStore()
const fila = useFilaStore()
const preferencias = usePreferenciasStore()

/** 'inicial' | 'aviso-privacidade' | 'localizando' | 'enviando' | 'confirmado' */
const etapa = ref('inicial')
/** Motivo da última tentativa que não deu certo (recusa, leitura ruim, erro). */
const mensagem = ref('')
const erroCiencia = ref('')
const enviandoCiencia = ref(false)
// Muda a cada troca de campus ou refeição, a cada volta ao início e quando o
// botão sai da tela (ex.: a refeição encerrou): um fluxo que já estava
// rodando confere depois de cada `await` e, se ela mudou, descarta o
// resultado sem mexer na tela nem mandar o POST (mesmo padrão do `authStore`).
let geracao = 0

const ocupado = computed(() => etapa.value === 'localizando' || etapa.value === 'enviando')
const rotuloBotao = computed(() => {
  if (etapa.value === 'localizando') return 'Lendo sua localização…'
  if (etapa.value === 'enviando') return 'Confirmando check-in…'
  return 'Estou no RU'
})

/** Desfechos do AvisoLocalizacao (ou da leitura) que impedem o check-in. */
const MENSAGENS_SEM_LOCALIZACAO = {
  negada: 'Libere a localização do Bandejão nas configurações do navegador e tente de novo.',
  adiado: 'O check-in precisa da sua localização para confirmar que você está no RU.',
  dispensada: 'O check-in precisa da sua localização para confirmar que você está no RU.',
  'sem-resposta': 'O check-in precisa da sua localização para confirmar que você está no RU.',
  indisponivel: 'Este navegador não oferece localização, então o check-in não pode ser confirmado.',
  inseguro: 'A localização só funciona no endereço seguro (https://) do Bandejão.',
  'sem-sinal':
    'Não conseguimos ler a localização do aparelho. Verifique se ela está ligada e tente de novo.',
  'tempo-esgotado':
    'Não conseguimos ler sua localização a tempo. Verifique se ela está ligada e tente de novo.',
  'precisao-baixa':
    'A localização lida não tem precisão suficiente para confirmar o check-in. Tente de novo perto da entrada do RU.',
  'posicao-antiga': 'A localização do aparelho estava desatualizada. Tente de novo.',
}
const mensagemSemLocalizacao = (motivo) =>
  MENSAGENS_SEM_LOCALIZACAO[motivo] ?? MENSAGENS_SEM_LOCALIZACAO.adiado

function voltarAoInicio(texto = '') {
  geracao++
  etapa.value = 'inicial'
  mensagem.value = texto
}

onBeforeUnmount(() => {
  geracao++
})

// Outra refeição ou outro campus: outro check-in.
watch(
  () => [props.campusId, props.tipoRefeicao],
  () => {
    voltarAoInicio()
    erroCiencia.value = ''
  },
)

function iniciar() {
  mensagem.value = ''
  if (auth.avisoPrivacidadePendente) {
    erroCiencia.value = ''
    etapa.value = 'aviso-privacidade'
    return
  }
  localizarEEnviar()
}

async function darCiencia() {
  const minhaGeracao = geracao
  enviandoCiencia.value = true
  erroCiencia.value = ''
  try {
    await auth.registrarCienciaPrivacidade()
  } catch (falha) {
    if (minhaGeracao === geracao) erroCiencia.value = mensagemDeErro(falha)
    return
  } finally {
    enviandoCiencia.value = false
  }
  // Trocou de campus ou refeição (ou fechou o aviso) enquanto a ciência ia.
  if (minhaGeracao !== geracao) return
  localizarEEnviar()
}

/**
 * Precisa abrir o AvisoLocalizacao antes de ler? Sim, se o navegador ainda
 * vai perguntar ou já bloqueou. Sem Permissions API ('desconhecida'), só se a
 * pessoa nunca permitiu neste aparelho.
 */
async function localizacaoLiberada() {
  const permissao = await consultarPermissao()
  if (permissao === 'concedida') return { liberada: true }
  if (permissao === 'desconhecida' && preferencias.localizacaoPermitida) return { liberada: true }
  const desfecho = await abrirAvisoLocalizacao()
  return { liberada: desfecho === 'concedida', motivo: desfecho }
}

async function localizarEEnviar() {
  // O POST usa o campus e a refeição de quando o fluxo começou, junto com a
  // posição lida para eles.
  const { campusId, tipoRefeicao } = props
  const minhaGeracao = ++geracao
  const descartado = () => minhaGeracao !== geracao
  etapa.value = 'localizando'

  try {
    const { liberada, motivo } = await localizacaoLiberada()
    if (descartado()) return
    if (!liberada) return voltarAoInicio(mensagemSemLocalizacao(motivo))

    const leitura = await lerPosicao()
    if (descartado()) return
    if (!leitura.ok) {
      // Negada na própria leitura: o AvisoLocalizacao mostra como liberar.
      if (leitura.motivo === 'negada') await abrirAvisoLocalizacao()
      if (descartado()) return
      return voltarAoInicio(mensagemSemLocalizacao(leitura.motivo))
    }

    etapa.value = 'enviando'
    const resultado = await fila.confirmarCheckin({
      campusId,
      tipoRefeicao,
      coordenadas: leitura.coordenadas,
    })
    if (descartado()) return
    mostrarResultado(resultado)
  } catch (falha) {
    // Uma exceção inesperada não pode deixar o botão em "Lendo sua localização…".
    if (!descartado()) voltarAoInicio(mensagemDeErro(falha))
  }
}

function mostrarResultado(resultado) {
  switch (resultado.desfecho) {
    case 'confirmado':
      etapa.value = 'confirmado'
      mensagem.value = ''
      return
    case 'aviso_privacidade_pendente':
      auth.marcarAvisoPrivacidadePendente()
      erroCiencia.value = ''
      etapa.value = 'aviso-privacidade'
      return
    case 'nao_autenticado':
      // O authStore já foi limpo: o ConviteLogin aparece sozinho.
      return voltarAoInicio()
    default:
      return voltarAoInicio(resultado.mensagem)
  }
}
</script>

<template>
  <ConviteLogin
    v-if="!auth.estaAutenticado"
    titulo="Entre para fazer check-in"
    texto="Com uma conta, você confirma que está no RU, ajuda a prever a fila e ganha pontos."
  />

  <AvisoPrivacidade
    v-else-if="etapa === 'aviso-privacidade'"
    :enviando="enviandoCiencia"
    :erro="erroCiencia"
    @ciente="darCiencia"
    @agora-nao="voltarAoInicio()"
  />

  <div
    v-else-if="etapa === 'confirmado'"
    class="cartao confirmado"
    role="status"
    data-teste="checkin-confirmado"
  >
    <div class="icone-caixa">
      <IconeSvg nome="check" :tamanho="20" cor="var(--sucesso-icone)" espessura="3" />
    </div>
    <div>
      <p class="titulo">Check-in confirmado</p>
      <p class="texto">Obrigado! Seu check-in ajuda a prever a fila do RU.</p>
    </div>
  </div>

  <div v-else class="pilha-3">
    <button
      type="button"
      class="botao botao--primario"
      data-teste="checkin-botao"
      :disabled="ocupado"
      :aria-busy="ocupado"
      @click="iniciar"
    >
      <IconeSvg nome="local" :tamanho="18" espessura="2.5" />
      {{ rotuloBotao }}
    </button>
    <p class="texto-pequeno legenda">
      Confirma pelo GPS que você entrou no RU. A localização é lida só agora e não é guardada.
    </p>
    <p v-if="mensagem" class="mensagem mensagem--alerta" role="alert" data-teste="checkin-mensagem">
      {{ mensagem }}
    </p>
  </div>
</template>

<style scoped>
.confirmado {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px;
  background: var(--sucesso-fundo);
  border-color: var(--sucesso-borda);
}

.icone-caixa {
  display: grid;
  flex-shrink: 0;
  place-items: center;
  width: 44px;
  height: 44px;
  border-radius: 50%;
  background: var(--sucesso-icone-fundo);
}

.titulo {
  font-family: var(--fonte-titulo);
  font-size: 15px;
  font-weight: 800;
  color: var(--sucesso-texto);
}

.texto {
  margin-top: 2px;
  font-size: 13px;
  color: var(--sucesso-texto-suave);
}

.legenda {
  text-align: center;
}
</style>
