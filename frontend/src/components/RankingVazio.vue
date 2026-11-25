<script setup>
import IconeSvg from './IconeSvg.vue'

/** Ranking sem ninguém no campus (RF27.2): "ninguém no ranking ainda". */
</script>

<template>
  <div class="cartao vazio" data-teste="ranking-vazio">
    <IconeSvg nome="estrela" :tamanho="32" cor="var(--dourado)" />
    <p class="titulo">Ninguém no ranking ainda</p>
    <p class="texto">
      O ranking mostra quem escolheu participar. Os pontos vêm de check-ins e avaliações neste
      campus durante o semestre.
    </p>
  </div>
</template>

<style scoped>
.vazio {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 32px 20px;
  text-align: center;
}

.titulo {
  font-family: var(--fonte-titulo);
  font-size: 16px;
  font-weight: 800;
  color: var(--texto-escuro);
}

.texto {
  font-size: 13px;
  line-height: 1.5;
  color: var(--texto-suave);
}
</style>
