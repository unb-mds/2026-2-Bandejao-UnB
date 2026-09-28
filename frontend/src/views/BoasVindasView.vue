<script setup>
import AppLogo from '@/components/AppLogo.vue'
</script>

<template>
  <div class="boas-vindas">
    <!-- Linhas decorativas -->
    <svg
      class="deco deco--topo"
      width="160"
      height="200"
      viewBox="0 0 160 200"
      fill="none"
      aria-hidden="true"
    >
      <path
        d="M140 10 C100 60 40 100 10 200"
        stroke="white"
        stroke-width="1.5"
        stroke-opacity="0.05"
      />
      <path
        d="M160 40 C120 80 60 120 20 200"
        stroke="white"
        stroke-width="1"
        stroke-opacity="0.04"
      />
    </svg>
    <svg
      class="deco deco--base"
      width="120"
      height="160"
      viewBox="0 0 120 160"
      fill="none"
      aria-hidden="true"
    >
      <path
        d="M10 0 C40 50 80 100 120 160"
        stroke="white"
        stroke-width="1.5"
        stroke-opacity="0.05"
      />
    </svg>

    <div class="marca">
      <div class="logo">
        <AppLogo :tamanho="110" />
      </div>
      <h1 class="nome">bandejão</h1>
      <p class="slogan">Seu restaurante universitário na palma da mão</p>
    </div>

    <div class="acoes pilha-3">
      <RouterLink :to="{ name: 'login' }" class="botao botao--destaque">Entrar na conta</RouterLink>
      <RouterLink :to="{ name: 'campus' }" class="botao visitante">Continuar sem login</RouterLink>
      <p class="nota">Visitantes podem consultar o cardápio e as avaliações</p>
    </div>
  </div>
</template>

<style scoped>
.boas-vindas {
  position: relative;
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
  background: var(--verde-escuro);
}

.deco {
  position: absolute;
  pointer-events: none;
}
.deco--topo {
  top: 0;
  right: 0;
}
.deco--base {
  bottom: 0;
  left: 0;
}

.marca {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 0 32px;
}

.logo {
  filter: drop-shadow(0 20px 40px rgba(0, 0, 0, 0.5));
}

.nome {
  margin-top: 24px;
  font-family: var(--fonte-titulo);
  font-size: 52px;
  font-weight: 900;
  line-height: 1;
  letter-spacing: -1.5px;
  color: #fff;
}

.slogan {
  max-width: 260px;
  margin-top: 12px;
  font-size: 14px;
  line-height: 1.6;
  text-align: center;
  color: var(--branco-45);
}

.acoes {
  padding: 0 24px 48px;
}

.visitante {
  font-weight: 600;
  border: 1.5px solid var(--branco-20);
  color: var(--branco-70);
}

.nota {
  font-size: 12px;
  text-align: center;
  color: var(--branco-25);
}
</style>
