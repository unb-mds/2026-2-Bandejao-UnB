<script setup>
import { onMounted, ref } from 'vue'
import IconeSvg from './IconeSvg.vue'

/**
 * Aviso de privacidade atualizado (RF11, RNF07.1), mostrado pelo
 * CheckinBotao antes de pedir a localização no primeiro check-in de quem tem
 * `avisoPrivacidadePendente` na sessão. Cita fila, localização, gamificação,
 * ranking e Bandeja de Ouro (front 3a.2). O texto completo está em
 * docs/requisitos/aviso-de-privacidade.md.
 *
 * Só mostra e avisa: quem registra a ciência (POST /api/privacidade/aceite/)
 * é o authStore, chamado pelo CheckinBotao no evento `ciente`.
 */
defineProps({
  enviando: { type: Boolean, default: false },
  erro: { type: String, default: '' },
})
const emit = defineEmits(['ciente', 'agora-nao'])

const titulo = ref(null)
// Quem usa leitor de tela ouve o aviso assim que ele aparece.
onMounted(() => titulo.value?.focus())
</script>

<template>
  <section
    class="cartao aviso"
    data-teste="aviso-privacidade"
    aria-labelledby="aviso-privacidade-titulo"
  >
    <div class="cabeca">
      <IconeSvg nome="cadeado" :tamanho="20" cor="var(--verde-medio)" />
      <h2 id="aviso-privacidade-titulo" ref="titulo" class="titulo" tabindex="-1">
        Atualizamos o aviso de privacidade
      </h2>
    </div>

    <p class="texto">
      Antes do seu primeiro check-in, veja o que mudou com a fila e a gamificação:
    </p>
    <ul class="itens">
      <li>
        <strong>Check-in e fila:</strong> guardamos o campus, a refeição, a data e a hora do
        check-in, para prever o movimento da fila e estimar a espera.
      </li>
      <li>
        <strong>Localização:</strong> a localização do aparelho é lida só no momento do check-in,
        para confirmar que você está no RU. As coordenadas não são guardadas.
      </li>
      <li>
        <strong>Pontos e patente:</strong> cada check-in e avaliação rende pontos, ligados à sua
        conta.
      </li>
      <li>
        <strong>Ranking e Bandeja de Ouro:</strong> você só aparece no ranking do campus se escolher
        participar; os 30 primeiros do semestre ganham a Bandeja de Ouro.
      </li>
    </ul>

    <p v-if="erro" class="mensagem mensagem--erro" role="alert">{{ erro }}</p>

    <div class="acoes">
      <button
        type="button"
        class="botao botao--primario"
        data-teste="aviso-privacidade-ciente"
        :disabled="enviando"
        :aria-busy="enviando"
        @click="emit('ciente')"
      >
        {{ enviando ? 'Registrando…' : 'Li e estou ciente' }}
      </button>
      <button
        type="button"
        class="botao botao--contorno"
        data-teste="aviso-privacidade-agora-nao"
        :disabled="enviando"
        @click="emit('agora-nao')"
      >
        Agora não
      </button>
    </div>
  </section>
</template>

<style scoped>
.aviso {
  padding: 20px;
}

.cabeca {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
}

.titulo {
  font-family: var(--fonte-titulo);
  font-size: 16px;
  font-weight: 800;
  color: var(--texto-escuro);
  outline: none;
}

.texto,
.itens {
  font-size: 13px;
  line-height: 1.5;
  color: var(--texto-suave);
}

.itens {
  margin: 8px 0 14px;
  padding-left: 18px;
}

.itens li + li {
  margin-top: 6px;
}

.itens strong {
  color: var(--texto-escuro);
}

.mensagem {
  margin-bottom: 12px;
}

.acoes {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
</style>
