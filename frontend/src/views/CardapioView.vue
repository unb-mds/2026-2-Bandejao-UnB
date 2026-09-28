<script setup>
defineProps({
  campusId: { type: String, default: null },
})
</script>

<template>
  <section>
    <h1>Cardápio</h1>
    <p>Campus: {{ campusId ?? 'padrão' }}</p>
    <p>TODO: implementar (RF05–RF07)</p>
  </section>
</template>