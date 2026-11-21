<script setup>
import { computed } from 'vue'
import { REFEICOES } from '@/constants/refeicoes'
import IconeSvg from './IconeSvg.vue'

const props = defineProps({
  tipoRefeicao: { type: String, required: true },
})

const rotulo = computed(() => REFEICOES[props.tipoRefeicao]?.rotuloCurto ?? 'refeição')
</script>

<template>
  <div class="cartao encerrada" role="status" data-teste="refeicao-encerrada">
    <IconeSvg nome="relogio" :tamanho="20" cor="var(--texto-claro)" espessura="2.2" />
    <div>
      <p class="titulo">Refeição encerrada</p>
      <p class="texto">
        O {{ rotulo }} de hoje já terminou. A previsão e o check-in voltam na próxima refeição, e
        você ainda pode avaliar até 23h59.
      </p>
    </div>
  </div>
</template>

<style scoped>
.encerrada {
  display: flex;
  gap: 12px;
  align-items: flex-start;
  padding: 16px;
}

.titulo {
  font-family: var(--fonte-titulo);
  font-size: 14px;
  font-weight: 700;
  color: var(--texto-escuro);
}

.texto {
  margin-top: 4px;
  font-size: 13px;
  line-height: 1.5;
  color: var(--texto-suave);
}
</style>
