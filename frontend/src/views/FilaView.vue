<script setup>
import { REFEICOES } from '@/constants/refeicoes'
import CheckinBotao from '@/components/CheckinBotao.vue'
import FilaPrevisao from '@/components/FilaPrevisao.vue'
import RefeicaoEncerrada from '@/components/RefeicaoEncerrada.vue'

defineProps({
  campusId: { type: Number, required: true },
  tipoRefeicao: { type: String, required: true },
  encerrada: { type: Boolean, default: false },
  campusConfirmado: { type: Boolean, default: true },
  refeicaoPrevisao: { type: String, required: true },
  dataPrevisao: { type: String, required: true },
  mostrarPrevisao: { type: Boolean, required: true },
})
</script>

<template>
  <section id="fila" class="secao-fila pilha-4" aria-labelledby="titulo-fila">
    <h2 id="titulo-fila" class="titulo-fila">Fila do RU</h2>

    <FilaPrevisao
      v-if="mostrarPrevisao"
      :campus-id="campusId"
      :tipo-refeicao="refeicaoPrevisao"
      :data="dataPrevisao"
    />

    <RefeicaoEncerrada v-if="encerrada" :tipo-refeicao="tipoRefeicao" />

    <section v-else class="pilha-3" aria-labelledby="titulo-checkin">
      <p id="titulo-checkin" class="titulo-secao pequeno">
        Check-in · {{ REFEICOES[tipoRefeicao].rotulo }}
      </p>
      <CheckinBotao
        v-if="campusConfirmado"
        :campus-id="campusId"
        :tipo-refeicao="tipoRefeicao"
      />
      <p v-else class="texto-pequeno aguardando-campus" data-teste="checkin-aguardando-campus">
        O check-in fica disponível assim que a lista de campi carregar.
      </p>
    </section>

    <div class="cartao como-funciona">
      <p class="titulo-secao pequeno">Como funciona?</p>
      <p class="texto-pequeno explicacao">
        A previsão é calculada a partir dos check-ins de usuários cadastrados nas últimas 4 semanas,
        no mesmo dia da semana, em faixas de 15 minutos. O nível de cada faixa é relativo ao pico.
        Quanto mais check-ins, mais precisa a previsão; sem dados suficientes, aparece "dados
        insuficientes".
      </p>
    </div>
  </section>
</template>

<style scoped>
.secao-fila {
  padding: 16px;
}

.titulo-fila {
  font-family: var(--fonte-titulo);
  font-size: 18px;
  font-weight: 900;
  color: var(--texto-escuro);
}

.como-funciona {
  padding: 16px;
}

.pequeno {
  margin-bottom: 8px;
  font-size: 14px;
}

.aguardando-campus {
  color: var(--texto-suave);
}

.explicacao {
  line-height: 1.6;
  color: var(--texto-suave);
}
</style>
