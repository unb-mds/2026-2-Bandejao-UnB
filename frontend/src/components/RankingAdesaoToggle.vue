<script setup>
defineProps({
  participa: { type: Boolean, required: true },
  alterando: { type: Boolean, default: false },
  erro: { type: String, default: null },
})

const emit = defineEmits(['alterar'])
</script>

<template>
  <section class="cartao adesao pilha-3" aria-labelledby="titulo-adesao">
    <div class="linha">
      <p id="titulo-adesao" class="titulo-secao pequeno">Participar do ranking</p>
      <button
        type="button"
        role="switch"
        class="interruptor"
        :class="{ 'interruptor--ligado': participa }"
        :aria-checked="participa"
        aria-labelledby="titulo-adesao"
        aria-describedby="aviso-adesao"
        :disabled="alterando"
        data-teste="adesao-interruptor"
        @click="emit('alterar', !participa)"
      >
        <span class="bolinha" aria-hidden="true" />
      </button>
    </div>
    <p id="aviso-adesao" class="texto-pequeno aviso" data-teste="adesao-aviso">
      Ao participar, seu apelido e sua patente ficam visíveis para todos no ranking do semestre.
      Você pode sair quando quiser; seus pontos continuam contando.
    </p>
    <p v-if="alterando" class="texto-pequeno estado" role="status">Salvando…</p>
    <p v-else-if="erro" class="texto-pequeno erro" role="alert" data-teste="adesao-erro">
      {{ erro }}
    </p>
  </section>
</template>

<style scoped>
.adesao {
  padding: 16px;
}

.linha {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.pequeno {
  font-size: 14px;
}

.interruptor {
  position: relative;
  flex-shrink: 0;
  width: 48px;
  height: 28px;
  border: 0;
  border-radius: 999px;
  background: var(--texto-suave);
  cursor: pointer;
  transition: background 0.15s;
}

.interruptor--ligado {
  background: var(--verde-escuro);
}

.interruptor:disabled {
  opacity: 0.6;
  cursor: progress;
}

.interruptor:focus-visible {
  outline: 2px solid var(--dourado);
  outline-offset: 2px;
}

.bolinha {
  position: absolute;
  top: 3px;
  left: 3px;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: var(--branco);
  transition: transform 0.15s;
}

.interruptor--ligado .bolinha {
  transform: translateX(20px);
}

.aviso {
  line-height: 1.6;
  color: var(--texto-suave);
}

.erro {
  color: var(--erro-texto);
}

@media (prefers-reduced-motion: reduce) {
  .interruptor,
  .bolinha {
    transition: none;
  }
}
</style>
