<script setup>
import { computed, ref, watch } from 'vue'
import { useAvaliacoesStore } from '@/stores/avaliacoes'
import { REFEICOES } from '@/constants/refeicoes'
import IconeSvg from './IconeSvg.vue'

/**
 * Formulário de avaliação de uma refeição (RF15): nota de 1 a 5 estrelas
 * obrigatória e comentário opcional de até 500 caracteres. Se o usuário já
 * avaliou, mostra a confirmação e permite editar (até 23h59 do dia).
 */
const props = defineProps({
  alvo: { type: Object, required: true }, // { campus, data, refeicao }
  minha: { type: Object, default: null }, // { nota, comentario } já enviada
})

const ROTULOS_NOTA = ['', 'Péssimo', 'Ruim', 'Regular', 'Bom', 'Ótimo']
const LIMITE_COMENTARIO = 500

const avaliacoes = useAvaliacoesStore()
const nota = ref(0)
const notaSobMouse = ref(0)
const comentario = ref('')
const editando = ref(false)
const enviando = ref(false)
const erro = ref('')

const notaVisivel = computed(() => notaSobMouse.value || nota.value)
const enviada = computed(() => Boolean(props.minha) && !editando.value)
const pergunta = computed(() => `Como foi o ${REFEICOES[props.alvo.refeicao].rotuloCurto} de hoje?`)

// Troca de refeição: descarta o rascunho.
watch(
  () => [props.alvo.campus, props.alvo.data, props.alvo.refeicao],
  () => {
    nota.value = 0
    comentario.value = ''
    editando.value = false
    erro.value = ''
  },
)

function editar() {
  nota.value = props.minha.nota
  comentario.value = props.minha.comentario ?? ''
  editando.value = true
}

async function enviar() {
  if (nota.value === 0 || enviando.value) return
  enviando.value = true
  erro.value = ''
  try {
    await avaliacoes.enviar(props.alvo, nota.value, comentario.value)
    editando.value = false
  } catch (falha) {
    erro.value = falha.message
  } finally {
    enviando.value = false
  }
}
</script>

<template>
  <div v-if="enviada" class="enviada">
    <div class="enviada-linha">
      <div class="enviada-icone">
        <IconeSvg nome="check" :tamanho="20" cor="var(--sucesso-icone)" espessura="2.5" />
      </div>
      <div class="enviada-textos">
        <p class="enviada-titulo">Avaliação enviada!</p>
        <p class="enviada-texto">
          Obrigado pelo seu feedback. Sua nota: {{ minha.nota }}
          {{ minha.nota === 1 ? 'estrela' : 'estrelas' }}.
        </p>
      </div>
      <button type="button" class="enviada-editar" @click="editar">Editar</button>
    </div>
  </div>

  <form v-else class="cartao formulario" @submit.prevent="enviar">
    <p class="titulo-secao pergunta">{{ pergunta }}</p>

    <div class="estrelas" role="radiogroup" aria-label="Nota da refeição">
      <button
        v-for="i in 5"
        :key="i"
        type="button"
        class="estrela"
        role="radio"
        :aria-checked="nota === i"
        :aria-label="`${i} ${i === 1 ? 'estrela' : 'estrelas'} — ${ROTULOS_NOTA[i]}`"
        @mouseenter="notaSobMouse = i"
        @mouseleave="notaSobMouse = 0"
        @click="nota = i"
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

    <p v-if="erro" class="mensagem mensagem--erro erro" role="alert">{{ erro }}</p>

    <button type="submit" class="botao botao--primario" :disabled="nota === 0 || enviando">
      {{ enviando ? 'Enviando…' : editando ? 'Salvar alteração' : 'Enviar avaliação' }}
    </button>
    <button v-if="editando" type="button" class="cancelar" @click="editando = false">
      Cancelar edição
    </button>
  </form>
</template>

<style scoped>
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
</style>
