<script setup>
import { useRouter } from 'vue-router'
import { useCardapioStore } from '@/stores/cardapio'
import { usePreferenciasStore } from '@/stores/preferencias'
import AppLogo from '@/components/AppLogo.vue'

/**
 * Primeira visita: entrar na conta ou escolher o campus aqui mesmo. Sem o
 * passo "Continuar sem login", quem não permite a localização chega ao
 * cardápio em 2 interações, "Agora não" e o campus (RNF03 da Release 2,
 * #285). A escolha fica lembrada no aparelho (RN04), como no seletor.
 */
const router = useRouter()
const cardapio = useCardapioStore()
const preferencias = usePreferenciasStore()
cardapio.carregarCampi()

function escolher(id) {
  preferencias.escolherCampus(id)
  router.push({ name: 'campus-tela', params: { campusId: String(id) } })
}
</script>

<template>
  <div class="boas-vindas fundo-escuro">
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

      <p id="boas-vindas-campus" class="chamada-campus">
        Ou escolha o campus para ver o cardápio sem login
      </p>
      <p
        v-if="cardapio.carregandoCampi || (!cardapio.campiCarregados && !cardapio.erroCampi)"
        class="nota"
        role="status"
      >
        Carregando campi…
      </p>
      <div v-else-if="cardapio.erroCampi && !cardapio.campi.length" class="nota" role="alert">
        <p>Não foi possível carregar os campi. {{ cardapio.erroCampi }}</p>
        <button
          type="button"
          class="botao-pequeno tentar"
          @click="cardapio.carregarCampi({ forcar: true })"
        >
          Tentar novamente
        </button>
      </div>
      <p v-else-if="!cardapio.campi.length" class="nota">Nenhum campus disponível no momento.</p>
      <div v-else class="campi" role="group" aria-labelledby="boas-vindas-campus">
        <button
          v-for="campus in cardapio.campi"
          :key="campus.id"
          type="button"
          class="botao visitante"
          @click="escolher(campus.id)"
        >
          {{ campus.nome }}
        </button>
      </div>
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

.chamada-campus {
  padding-top: 8px;
  font-size: 13px;
  text-align: center;
  color: var(--branco-45);
}

.campi {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}

.visitante {
  padding: 12px;
  font-size: 13px;
  font-weight: 600;
  text-align: center;
  border: 1.5px solid var(--branco-20);
  color: var(--branco-70);
}

.nota {
  font-size: 12px;
  text-align: center;
  color: var(--branco-25);
}

.tentar {
  margin-top: 8px;
}
</style>
