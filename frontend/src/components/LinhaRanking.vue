<script setup>
import { rotuloPatente } from '@/constants/patentes'

/**
 * Uma linha do ranking (RF27.2): posição, apelido e patente. Nunca os pontos
 * (RI12), que nem chegam ao PWA.
 * TODO: o DistintivoIndicador (Bandeja de Ouro, RF33.2) entra ao lado do
 * apelido quando o campo `distintivo` estiver no contrato.
 */
defineProps({
  /** `{ posicao, apelido, patente }` (schema LinhaRankingPublica). */
  linha: { type: Object, required: true },
})
</script>

<template>
  <li
    class="cartao linha"
    :class="{ 'linha--podio': linha.posicao <= 3 }"
    data-teste="linha-ranking"
  >
    <span class="posicao" data-teste="linha-posicao">{{ linha.posicao }}º</span>
    <span class="textos">
      <span class="apelido" data-teste="linha-apelido">{{ linha.apelido }}</span>
      <span class="patente" data-teste="linha-patente">{{ rotuloPatente(linha.patente) }}</span>
    </span>
  </li>
</template>

<style scoped>
.linha {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 12px 16px;
}

.posicao {
  display: flex;
  flex-shrink: 0;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border-radius: 50%;
  font-family: var(--fonte-titulo);
  font-size: 14px;
  font-weight: 900;
  color: var(--texto-escuro);
  background: var(--bege);
}

.linha--podio .posicao {
  color: #fff;
  background: var(--dourado);
}

.textos {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.apelido {
  font-size: 15px;
  font-weight: 700;
  color: var(--texto-escuro);
  overflow-wrap: anywhere;
}

.patente {
  margin-top: 2px;
  font-size: 12px;
  color: var(--texto-suave);
}
</style>
