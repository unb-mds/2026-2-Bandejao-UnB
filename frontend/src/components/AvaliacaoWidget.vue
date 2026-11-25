<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useAvaliacoesStore } from '@/stores/avaliacoes'
import { REFEICOES } from '@/constants/refeicoes'
import { formatarNota } from '@/utils/cardapio'
import { tempoRelativo } from '@/utils/datas'
import { motivoAvaliacaoIndisponivel } from '@/utils/avaliacao'
import ConviteLogin from './ConviteLogin.vue'
import EstrelasNota from './EstrelasNota.vue'
import IconeSvg from './IconeSvg.vue'

/**
 * Avaliação de uma refeição ligada à API (RF15, RF05).
 *
 * - Média, quantidade e comentários com apelido (ou "usuário removido"),
 *   para qualquer visitante (RF15.2), de
 *   `GET /api/refeicoes/{refeicaoId}/avaliacoes/`.
 * - O `refeicaoId` vem do resumo do dia (`GET /api/avaliacoes/resumo/`).
 * - Logado: nota de 1 a 5 e comentário opcional de até 500 caracteres pelo
 *   `POST /api/avaliacoes/`, que é sempre upsert, então "Editar" usa o mesmo
 *   envio (RF15.1). O formulário não depende do GET dos comentários.
 * - Quando não dá para avaliar, mostra o motivo no lugar do formulário: outro
 *   dia, refeição que ainda não começou, sem cardápio, janela fechada no
 *   servidor ou rotas de avaliação ainda respondendo 501.
 * - Falha ao carregar o resumo ou os comentários: "Notas indisponíveis" e um
 *   "Tentar de novo", em vez de "Carregando…" para sempre.
 * - Visitante: ConviteLogin citando os pontos (RF05). Se a sessão expira no
 *   envio, o convite diz que a nota não foi enviada, e o rascunho volta
 *   depois do login.
 */
const props = defineProps({
  /** Id do campus no backend. */
  campusId: { type: Number, required: true },
  /** Dia da refeição, 'AAAA-MM-DD'. */
  data: { type: String, required: true },
  /** 'cafe' | 'almoco' | 'jantar' */
  tipo: { type: String, required: true },
})

const ROTULOS_NOTA = ['', 'Péssimo', 'Ruim', 'Regular', 'Bom', 'Ótimo']
const LIMITE_COMENTARIO = 500
const USUARIO_REMOVIDO = 'usuário removido'
const MENSAGEM_INDISPONIVEL = 'As avaliações ainda não estão disponíveis. Tente de novo mais tarde.'
const INTERVALO_DO_RELOGIO = 30 * 1000

const auth = useAuthStore()
const avaliacoes = useAvaliacoesStore()

const nota = ref(0)
const notaSobMouse = ref(0)
const comentario = ref('')
const editando = ref(false)
const enviando = ref(false)
const erroEnvio = ref('')
/** Motivo devolvido pelo servidor no envio (janela fechada, 404, 501). */
const motivoDoServidor = ref('')
/** Último envio que deu certo: 'criada' | 'editada' | null. */
const ultimoEnvio = ref(null)
/** O envio deu certo, mas a média e os comentários não foram recarregados. */
const desatualizada = ref(false)
/** A sessão expirou no envio: o convite explica e o rascunho fica guardado. */
const sessaoExpirou = ref(false)
const tituloEnviada = ref(null)
// Botões das estrelas pela posição: o array de `ref` do v-for não garante a ordem.
const estrelas = []
// A janela de avaliação depende da hora: o motivo é recalculado a cada 30 s.
const agora = ref(new Date())
let relogio = null

const chaveAtual = () => `${props.campusId}|${props.data}|${props.tipo}`

const situacaoDoResumo = computed(() =>
  avaliacoes.situacaoDoResumoDoDia(props.campusId, props.data),
)
const resumoDoDia = computed(() => avaliacoes.daResumoDoDia(props.campusId, props.data))
const refeicaoId = computed(
  () => resumoDoDia.value?.find((r) => r.tipo === props.tipo)?.refeicaoId ?? null,
)
const situacaoDaRefeicao = computed(() =>
  refeicaoId.value ? avaliacoes.situacaoDaRefeicao(refeicaoId.value) : null,
)
const dados = computed(() =>
  refeicaoId.value ? avaliacoes.avaliacoesDaRefeicao(refeicaoId.value) : null,
)
const resumo = computed(() => dados.value?.resumoAvaliacoes ?? null)
const comentariosEscritos = computed(
  () => dados.value?.comentarios.filter((c) => c.comentario.trim()) ?? [],
)
const minha = computed(() =>
  refeicaoId.value && auth.estaAutenticado
    ? avaliacoes.minhaAvaliacao(refeicaoId.value, auth.apelido)
    : null,
)

/** O backend ainda responde 501 no resumo ou nos comentários. */
const indisponivelNoServidor = computed(
  () => situacaoDoResumo.value === 'indisponivel' || situacaoDaRefeicao.value === 'indisponivel',
)
/** O resumo do dia veio, e a refeição não está nele (sem cardápio). */
const semRefeicao = computed(() => Boolean(resumoDoDia.value) && !refeicaoId.value)
const falhaNoResumo = computed(() => situacaoDoResumo.value === 'erro' && !resumoDoDia.value)
const falhaNaRefeicao = computed(() => situacaoDaRefeicao.value === 'erro' && !dados.value)
const falhaAoCarregar = computed(() => falhaNoResumo.value || falhaNaRefeicao.value)

const textoDoResumo = computed(() => {
  if (resumo.value || semRefeicao.value) return 'Sem avaliações ainda'
  if (indisponivelNoServidor.value || falhaAoCarregar.value) return 'Notas indisponíveis'
  return 'Carregando…'
})

const motivo = computed(() => {
  if (indisponivelNoServidor.value) return MENSAGEM_INDISPONIVEL
  return (
    motivoAvaliacaoIndisponivel({
      data: props.data,
      tipo: props.tipo,
      agora: agora.value,
      semRefeicao: semRefeicao.value,
    }) ||
    motivoDoServidor.value ||
    null
  )
})

/** O formulário só precisa do `refeicaoId`; os comentários podem ter falhado. */
const carregandoAcao = computed(
  () => !refeicaoId.value || (!dados.value && situacaoDaRefeicao.value !== 'erro'),
)

const notaVisivel = computed(() => notaSobMouse.value || nota.value)
const estrelaTabulavel = computed(() => nota.value || 1)
const pergunta = computed(() => `Como foi o ${REFEICOES[props.tipo].rotuloCurto}?`)
const textoTituloEnviada = computed(() => {
  if (ultimoEnvio.value === 'editada') return 'Avaliação atualizada!'
  if (ultimoEnvio.value === 'criada') return 'Avaliação enviada!'
  return 'Você já avaliou'
})

const plural = (n, um, varios) => `${n} ${n === 1 ? um : varios}`

function descartarRascunho() {
  nota.value = 0
  notaSobMouse.value = 0
  comentario.value = ''
  editando.value = false
  enviando.value = false
  erroEnvio.value = ''
  motivoDoServidor.value = ''
  ultimoEnvio.value = null
  desatualizada.value = false
}

// Outra refeição: rascunho e motivo novos; carrega o que faltar.
watch(
  () => [props.campusId, props.data, props.tipo],
  ([campus, data]) => {
    descartarRascunho()
    if ([null, 'erro'].includes(avaliacoes.situacaoDoResumoDoDia(campus, data))) {
      avaliacoes.carregarResumoDoDia(campus, data)
    }
  },
  { immediate: true },
)

watch(
  refeicaoId,
  (id) => {
    if (id && [null, 'erro'].includes(avaliacoes.situacaoDaRefeicao(id))) {
      avaliacoes.carregarAvaliacoesDaRefeicao(id)
    }
  },
  { immediate: true },
)

// Entrou de novo depois da sessão expirar: o rascunho volta ao formulário.
// `immediate` e o `refeicaoId` juntos: no app, o "Entrar" leva a /login e
// desmonta este widget; o rascunho volta no widget novo, montado já logado.
watch(
  [() => auth.estaAutenticado, refeicaoId],
  ([autenticado, id]) => {
    if (!autenticado || !id) return
    sessaoExpirou.value = false
    const rascunho = avaliacoes.retomarRascunho(id)
    if (!rascunho) return
    nota.value = rascunho.nota
    comentario.value = rascunho.comentario
    // Pelo rascunho, e não por `minha`: na montagem os comentários ainda não
    // chegaram, e sem isso a edição sumiria atrás de "Você já avaliou".
    editando.value = rascunho.editando
  },
  { immediate: true },
)

onMounted(() => {
  relogio = setInterval(() => {
    agora.value = new Date()
  }, INTERVALO_DO_RELOGIO)
})
onBeforeUnmount(() => clearInterval(relogio))

function tentarDeNovo() {
  if (falhaNoResumo.value) avaliacoes.carregarResumoDoDia(props.campusId, props.data)
  else if (refeicaoId.value) avaliacoes.carregarAvaliacoesDaRefeicao(refeicaoId.value)
}

function editar() {
  nota.value = minha.value.nota
  comentario.value = minha.value.comentario ?? ''
  erroEnvio.value = ''
  desatualizada.value = false
  editando.value = true
}

function cancelarEdicao() {
  editando.value = false
  erroEnvio.value = ''
}

/** Setas, Home e End mudam a nota (padrão de radiogroup). */
function navegarEstrelas(evento) {
  const passos = { ArrowRight: 1, ArrowUp: 1, ArrowLeft: -1, ArrowDown: -1 }
  let nova
  if (evento.key in passos) nova = Math.min(5, Math.max(1, (nota.value || 0) + passos[evento.key]))
  else if (evento.key === 'Home') nova = 1
  else if (evento.key === 'End') nova = 5
  else return
  evento.preventDefault()
  nota.value = nova
  estrelas[nova - 1]?.focus()
}

async function enviar() {
  if (nota.value === 0 || enviando.value || !refeicaoId.value) return
  // Se a refeição mudar durante o envio, a resposta não vale para a nova.
  const chave = chaveAtual()
  const rascunho = { nota: nota.value, comentario: comentario.value }
  const id = refeicaoId.value
  enviando.value = true
  erroEnvio.value = ''
  let resultado
  try {
    resultado = await avaliacoes.avaliar({
      refeicaoId: id,
      campus: props.campusId,
      data: props.data,
      ...rascunho,
    })
  } finally {
    if (chave === chaveAtual()) enviando.value = false
  }
  if (chave !== chaveAtual()) return

  switch (resultado.desfecho) {
    case 'criada':
    case 'editada':
      ultimoEnvio.value = resultado.desfecho
      desatualizada.value = !resultado.atualizada
      editando.value = false
      await nextTick()
      tituloEnviada.value?.focus()
      return
    case 'indisponivel':
      motivoDoServidor.value = resultado.mensagem
      editando.value = false
      return
    case 'nao_autenticado':
      // O authStore já foi limpo: o convite aparece no lugar do formulário.
      avaliacoes.guardarRascunho(id, { ...rascunho, editando: editando.value })
      sessaoExpirou.value = true
      return
    default:
      erroEnvio.value = resultado.mensagem
  }
}
</script>

<template>
  <section class="widget-avaliacao pilha-4" aria-label="Avaliações da refeição">
    <div class="cartao resumo" data-teste="avaliacao-resumo">
      <template v-if="resumo?.quantidade">
        <p class="sobretitulo resumo-rotulo" aria-hidden="true">Média geral</p>
        <EstrelasNota :valor="resumo.media" :tamanho="15" />
        <span class="resumo-nota" data-teste="avaliacao-media">{{
          formatarNota(resumo.media)
        }}</span>
        <span class="resumo-total" data-teste="avaliacao-quantidade">{{
          plural(resumo.quantidade, 'avaliação', 'avaliações')
        }}</span>
      </template>
      <span v-else class="resumo-total">{{ textoDoResumo }}</span>
    </div>

    <ConviteLogin
      v-if="!auth.estaAutenticado && sessaoExpirou"
      titulo="Sua sessão expirou"
      texto="A avaliação não foi enviada. Entre de novo e ela volta preenchida."
    />
    <ConviteLogin
      v-else-if="!auth.estaAutenticado"
      titulo="Entre para avaliar"
      texto="Com uma conta, você avalia as refeições e ganha pontos quando avalia uma refeição em que fez check-in."
    />

    <div
      v-else-if="motivo"
      class="cartao indisponivel"
      role="status"
      data-teste="avaliacao-indisponivel"
    >
      <div class="indisponivel-icone">
        <IconeSvg nome="relogio" :tamanho="20" cor="var(--texto-suave)" />
      </div>
      <div>
        <p class="indisponivel-titulo">Avaliação indisponível</p>
        <p class="indisponivel-texto">{{ motivo }}</p>
      </div>
    </div>

    <template v-else-if="falhaNoResumo" />

    <p v-else-if="carregandoAcao" class="vazio" role="status">Carregando avaliação…</p>

    <div v-else-if="minha && !editando" class="enviada" data-teste="avaliacao-enviada">
      <div class="enviada-linha">
        <div class="enviada-icone">
          <IconeSvg nome="check" :tamanho="20" cor="var(--sucesso-icone)" espessura="2.5" />
        </div>
        <div class="enviada-textos" role="status">
          <p
            ref="tituloEnviada"
            class="enviada-titulo"
            tabindex="-1"
            data-teste="avaliacao-enviada-titulo"
          >
            {{ textoTituloEnviada }}
          </p>
          <p class="enviada-texto">
            Sua nota: {{ plural(minha.nota, 'estrela', 'estrelas') }}. Dá para editar até 23h59.
          </p>
        </div>
        <button type="button" class="enviada-editar" data-teste="avaliacao-editar" @click="editar">
          Editar
        </button>
      </div>
      <p v-if="desatualizada" class="desatualizada" data-teste="avaliacao-desatualizada">
        Sua avaliação foi salva. A média e os comentários ainda não foram atualizados.
      </p>
    </div>

    <form
      v-else
      class="cartao formulario"
      data-teste="avaliacao-formulario"
      @submit.prevent="enviar"
    >
      <p class="titulo-secao pergunta">{{ pergunta }}</p>

      <div class="estrelas" role="radiogroup" aria-label="Nota da refeição">
        <button
          v-for="i in 5"
          :key="i"
          :ref="(el) => (estrelas[i - 1] = el)"
          type="button"
          class="estrela"
          role="radio"
          :data-teste="`estrela-${i}`"
          :tabindex="i === estrelaTabulavel ? 0 : -1"
          :aria-checked="nota === i"
          :aria-label="`${plural(i, 'estrela', 'estrelas')} — ${ROTULOS_NOTA[i]}`"
          @mouseenter="notaSobMouse = i"
          @mouseleave="notaSobMouse = 0"
          @click="nota = i"
          @keydown="navegarEstrelas"
        >
          <IconeSvg
            nome="estrela"
            :tamanho="44"
            :cor="notaVisivel >= i ? 'var(--dourado)' : 'var(--borda)'"
            :preenchimento="notaVisivel >= i ? 'var(--dourado)' : 'none'"
          />
        </button>
      </div>
      <p v-if="nota > 0" class="rotulo-nota">{{ ROTULOS_NOTA[nota] }}</p>

      <label class="visualmente-oculto" for="comentario-avaliacao">Comentário opcional</label>
      <textarea
        id="comentario-avaliacao"
        v-model="comentario"
        :maxlength="LIMITE_COMENTARIO"
        rows="3"
        class="comentario"
        placeholder="Comentário opcional — o que achou dos pratos?"
      />
      <p class="contador">{{ comentario.length }}/{{ LIMITE_COMENTARIO }}</p>

      <p v-if="erroEnvio" class="mensagem mensagem--erro erro" role="alert">{{ erroEnvio }}</p>

      <button
        type="submit"
        class="botao botao--primario"
        data-teste="avaliacao-enviar"
        :disabled="nota === 0 || enviando"
      >
        {{ enviando ? 'Enviando…' : editando ? 'Salvar alteração' : 'Enviar avaliação' }}
      </button>
      <button
        v-if="editando"
        type="button"
        class="cancelar"
        data-teste="avaliacao-cancelar"
        @click="cancelarEdicao"
      >
        Cancelar edição
      </button>
    </form>

    <h2 class="titulo-secao">Comentários</h2>

    <div v-if="falhaAoCarregar" class="cartao falha" role="alert" data-teste="avaliacao-erro">
      <p>
        Não foi possível carregar as avaliações.
        {{ falhaNaRefeicao ? avaliacoes.erroDaRefeicao(refeicaoId) : '' }}
      </p>
      <button
        type="button"
        class="botao-pequeno"
        data-teste="avaliacao-tentar-de-novo"
        @click="tentarDeNovo"
      >
        Tentar de novo
      </button>
    </div>
    <p v-else-if="dados && comentariosEscritos.length === 0" class="vazio">
      {{
        resumo?.quantidade
          ? 'Nenhum comentário escrito para esta refeição.'
          : 'Sem avaliações ainda.'
      }}
    </p>

    <article
      v-for="item in comentariosEscritos"
      :key="`${item.apelido}|${item.criadaEm}`"
      class="cartao comentario-item"
      data-teste="avaliacao-comentario"
    >
      <div class="comentario-topo">
        <span class="inicial" aria-hidden="true">{{
          item.apelido === USUARIO_REMOVIDO ? '?' : item.apelido.slice(0, 1).toUpperCase()
        }}</span>
        <span
          class="apelido"
          :class="{ 'apelido--removido': item.apelido === USUARIO_REMOVIDO }"
          :data-removido="item.apelido === USUARIO_REMOVIDO"
          data-teste="comentario-apelido"
        >
          {{ item.apelido }}
        </span>
        <EstrelasNota :valor="item.nota" :tamanho="11" />
        <time class="quando" :datetime="item.criadaEm">{{ tempoRelativo(item.criadaEm) }}</time>
      </div>
      <p class="texto">{{ item.comentario }}</p>
    </article>
  </section>
</template>

<style scoped>
.resumo {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
}

.resumo-nota {
  font-size: 14px;
  font-weight: 700;
  color: var(--texto-escuro);
}

.resumo-total {
  font-size: 12px;
  color: var(--texto-suave);
}

.indisponivel {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px;
}

.indisponivel-icone {
  width: 44px;
  height: 44px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--raio-md);
  background: var(--bege);
}

.indisponivel-titulo {
  font-size: 14px;
  font-weight: 600;
  color: var(--texto-escuro);
}

.indisponivel-texto {
  margin-top: 2px;
  font-size: 12px;
  color: var(--texto-suave);
}

.vazio {
  font-size: 13px;
  color: var(--texto-claro);
}

.formulario {
  padding: 20px;
}

.pergunta {
  margin-bottom: 16px;
}

.estrelas {
  display: flex;
  justify-content: center;
  gap: 8px;
  margin-bottom: 12px;
}

.estrela {
  transition: transform 0.1s;
}
.estrela:active {
  transform: scale(1.1);
}
.estrela :deep(svg) {
  transition: all 0.1s;
}

.rotulo-nota {
  margin-bottom: 16px;
  text-align: center;
  font-size: 14px;
  font-weight: 900;
  color: var(--dourado);
}

.comentario {
  display: block;
  width: 100%;
  padding: 12px;
  resize: none;
  border-radius: var(--raio-md);
  font-size: 14px;
  background: var(--bege);
  border: 1.5px solid var(--borda);
  color: var(--texto-escuro);
}
.comentario::placeholder {
  color: var(--texto-claro);
}
.comentario:focus {
  outline: none;
  border-color: var(--verde-escuro);
}

.contador {
  margin: 4px 0 16px;
  text-align: right;
  font-size: 11px;
  color: var(--texto-claro);
}

.erro {
  margin-bottom: 12px;
}

.cancelar {
  display: block;
  margin: 12px auto 0;
  font-size: 12px;
  font-weight: 600;
  color: var(--texto-suave);
}

.enviada {
  padding: 20px;
  border-radius: var(--raio-lg);
  background: var(--sucesso-fundo);
}

.enviada-linha {
  display: flex;
  align-items: center;
  gap: 12px;
}

.enviada-icone {
  width: 44px;
  height: 44px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--raio-md);
  background: var(--sucesso-icone-fundo);
}

.enviada-textos {
  flex: 1;
}

.enviada-titulo {
  font-size: 14px;
  font-weight: 700;
  color: var(--sucesso-texto);
}

.enviada-texto {
  margin-top: 2px;
  font-size: 12px;
  color: var(--sucesso-texto-suave);
}

.enviada-editar {
  flex-shrink: 0;
  font-size: 12px;
  font-weight: 700;
  color: var(--sucesso-texto);
  text-decoration: underline;
  text-underline-offset: 2px;
}

.comentario-item {
  padding: 16px;
}

.comentario-topo {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.inicial {
  width: 28px;
  height: 28px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  font-size: 12px;
  font-weight: 900;
  background: var(--verde-escuro);
  color: var(--branco);
}

.apelido {
  font-size: 12px;
  font-weight: 700;
  color: var(--texto-escuro);
}

.apelido--removido {
  font-style: italic;
  font-weight: 600;
  color: var(--texto-claro);
}

.quando {
  margin-left: auto;
  font-size: 11px;
  color: var(--texto-claro);
}

.texto {
  font-size: 14px;
  line-height: 1.6;
  color: var(--texto-suave);
  overflow-wrap: anywhere;
}

.falha {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 10px;
  padding: 16px;
  font-size: 13px;
  color: var(--erro-texto);
  background: var(--erro-fundo);
  border-color: var(--erro-borda);
}

.desatualizada {
  margin-top: 10px;
  font-size: 12px;
  color: var(--alerta-texto);
}

.enviada-titulo:focus {
  outline: none;
}

.resumo-rotulo {
  display: none;
}

/* Desktop (FE-23, protótipo desktop): o resumo e a avaliação lado a lado,
   os comentários embaixo, na largura toda. */
@media (min-width: 1024px) {
  .widget-avaliacao {
    display: grid;
    grid-template-columns: minmax(0, 0.8fr) minmax(0, 1fr);
    gap: 16px;
    align-items: start;
  }
  .widget-avaliacao > * {
    grid-column: 1 / -1;
    margin-top: 0;
  }
  .widget-avaliacao > .resumo {
    grid-column: 1;
    align-self: stretch;
  }
  .widget-avaliacao > .resumo + * {
    grid-column: 2;
    align-self: stretch;
  }
  .widget-avaliacao > .cartao,
  .widget-avaliacao > .resumo + * {
    padding: 28px;
    border-radius: var(--raio-xl);
    box-shadow: 0 8px 22px var(--sombra-cartao-cor);
  }
  /* Resumo: a média grande, como no protótipo. */
  .widget-avaliacao > .resumo {
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    justify-content: center;
    gap: 6px;
  }
  .resumo-rotulo {
    display: block;
    margin: 0;
  }
  .resumo-nota {
    order: -1;
    font: 900 64px / 0.95 var(--fonte-titulo);
    letter-spacing: -0.06em;
    color: var(--verde-escuro);
  }
  .resumo-rotulo {
    order: -2;
  }
  .widget-avaliacao > .titulo-secao {
    margin-top: 16px;
    font-size: 22px;
    letter-spacing: -0.03em;
  }
  .widget-avaliacao > .comentario-item {
    padding: 18px 24px;
    border-radius: var(--raio-18);
  }
}
</style>
