<script setup>
import { USANDO_SIMULACAO } from '@/services/apiClient'

/**
 * Só aparece com o backend simulado: mostra o link que o sistema real
 * enviaria por e-mail (confirmação de cadastro ou redefinição de senha),
 * para a demonstração poder seguir o fluxo completo.
 */
defineProps({
  link: { type: String, default: '' },
  rotulo: { type: String, required: true },
})
</script>

<template>
  <div v-if="USANDO_SIMULACAO && link" class="simulacao">
    <p class="aviso">Modo demonstração — nenhum e-mail é enviado de verdade.</p>
    <RouterLink :to="link" class="link">{{ rotulo }}</RouterLink>
  </div>
</template>

<style scoped>
.simulacao {
  padding: 12px 16px;
  border-radius: var(--raio-md);
  border: 1.5px dashed var(--dourado);
  background: var(--bege-selecionado);
}

.aviso {
  font-size: 11px;
  color: var(--texto-suave);
}

.link {
  display: inline-block;
  margin-top: 4px;
  font-size: 13px;
  font-weight: 700;
  color: var(--dourado);
}
</style>
