<script setup>
import AppLogo from './AppLogo.vue'
import IlustracaoRefeicao from './IlustracaoRefeicao.vue'

/**
 * Lado verde das telas de conta no desktop (FE-23, protótipo desktop): a
 * marca, a ilustração do almoço e a chamada. Decorativo: as telas de conta
 * têm o próprio título e não dependem dele.
 */
defineProps({
  /** Passo marcado na barrinha de baixo: 1 (entrar) ou 2 (criar conta). */
  passo: { type: Number, default: 1 },
})
</script>

<template>
  <aside class="aside-conta fundo-escuro" aria-hidden="true">
    <div class="marca">
      <AppLogo :tamanho="52" />
      <span>
        <strong>bandejão</strong>
        <small>Restaurante Universitário · UnB</small>
      </span>
    </div>
    <div class="arte">
      <IlustracaoRefeicao refeicao="almoco" grande />
    </div>
    <div class="texto">
      <p class="sobretitulo">Feito para a comunidade UnB</p>
      <p class="chamada">Seu RU, do seu jeito.</p>
      <p class="descricao">Cardápio, previsão de fila e avaliações em um só lugar.</p>
    </div>
    <div class="passos">
      <span class="passo--ativo" />
      <span :class="{ 'passo--ativo': passo >= 2 }" />
      <span />
    </div>
  </aside>
</template>

<style scoped>
.aside-conta {
  display: none;
}

@media (min-width: 1024px) {
  .aside-conta {
    position: relative;
    display: flex;
    flex-direction: column;
    height: 100%;
    overflow: hidden;
    padding: clamp(32px, 4vw, 58px);
    color: var(--branco);
    background: var(--verde-escuro);
  }
}

.aside-conta::before {
  content: '';
  position: absolute;
  width: 500px;
  height: 500px;
  right: -280px;
  top: -180px;
  border: 1px solid var(--branco-07);
  border-radius: 50%;
  box-shadow: 0 0 0 60px var(--branco-02);
  pointer-events: none;
}

.marca {
  position: relative;
  display: flex;
  align-items: center;
  gap: 14px;
}

.marca strong,
.marca small {
  display: block;
}

.marca strong {
  font: 900 25px / 1 var(--fonte-titulo);
  letter-spacing: -0.045em;
}

.marca small {
  margin-top: 5px;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.11em;
  text-transform: uppercase;
  color: var(--branco-60);
}

.arte {
  display: grid;
  flex: 1;
  place-items: center;
  min-height: 240px;
}

.texto {
  position: relative;
}

.chamada {
  max-width: 430px;
  font: 900 clamp(32px, 3.4vw, 50px) / 1 var(--fonte-titulo);
  letter-spacing: -0.05em;
}

.descricao {
  margin-top: 13px;
  font-size: 13px;
  color: var(--branco-60);
}

.passos {
  display: flex;
  gap: 7px;
  margin-top: 32px;
}

.passos span {
  width: 28px;
  height: 3px;
  border-radius: var(--raio-5);
  background: var(--branco-10);
}

.passos .passo--ativo {
  background: var(--dourado);
}
</style>
