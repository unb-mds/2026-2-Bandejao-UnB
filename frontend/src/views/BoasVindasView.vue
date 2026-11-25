<script setup>
import { useRouter } from 'vue-router'
import { useCardapioStore } from '@/stores/cardapio'
import { usePreferenciasStore } from '@/stores/preferencias'
import { ORDEM_REFEICOES, REFEICOES, horarioRefeicao } from '@/constants/refeicoes'
import IlustracaoRefeicao from '@/components/IlustracaoRefeicao.vue'
import AppLogo from '@/components/AppLogo.vue'

/**
 * Primeira visita: entrar na conta ou escolher o campus aqui mesmo. Quem
 * não permite a localização chega ao cardápio em 2 interações, "Agora não" e
 * o campus (RNF03 da Release 2, #285). A escolha fica lembrada no aparelho
 * (RN04), como no seletor.
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

    <!-- Desktop (FE-23): o lado verde do protótipo, com a chamada e as refeições. -->
    <section class="hero">
      <div class="hero-marca">
        <AppLogo :tamanho="52" />
        <span>
          <strong>bandejão</strong>
          <small>Restaurante Universitário · UnB</small>
        </span>
      </div>
      <div class="hero-texto">
        <p class="sobretitulo">O Restaurante Universitário na sua rotina</p>
        <h2 class="hero-titulo">Comer bem no campus ficou mais simples.</h2>
        <p class="hero-descricao">
          Descubra o cardápio do dia, escolha o melhor horário e compartilhe sua experiência com a
          comunidade.
        </p>
      </div>
      <ul class="hero-refeicoes" aria-label="Refeições do RU">
        <li
          v-for="refeicao in ORDEM_REFEICOES"
          :key="refeicao"
          class="hero-refeicao"
          :class="{ 'hero-refeicao--destaque': refeicao === 'almoco' }"
        >
          <IlustracaoRefeicao :refeicao="refeicao" />
          <span>{{ REFEICOES[refeicao].rotulo }}</span>
          <small>{{ horarioRefeicao(refeicao) }}</small>
        </li>
      </ul>
    </section>

    <div class="entrada">
      <div class="marca">
        <div class="logo">
          <AppLogo :tamanho="110" />
        </div>
        <h1 class="nome">bandejão</h1>
        <p class="slogan">Seu restaurante universitário na palma da mão</p>
        <p class="sobretitulo entrada-rotulo">Bem-vindo ao Bandejão</p>
        <h2 class="entrada-titulo">Como você quer continuar?</h2>
        <p class="entrada-descricao">
          Entre para avaliar refeições e participar do ranking, ou consulte as informações como
          visitante.
        </p>
      </div>

      <div class="acoes pilha-3">
        <RouterLink :to="{ name: 'login' }" class="botao botao--destaque"
          >Entrar na conta</RouterLink
        >

        <p id="boas-vindas-campus" class="chamada-campus">
          Ou escolha o campus para ver o cardápio sem login
        </p>
        <!-- Altura reservada: com os campi carregados, o "Entrar na conta" não sobe sob o dedo. -->
        <div class="area-campi">
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
          <p v-else-if="!cardapio.campi.length" class="nota">
            Nenhum campus disponível no momento.
          </p>
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
        </div>
        <p class="nota">Visitantes podem consultar o cardápio e as avaliações</p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.boas-vindas {
  position: relative;
  display: flex;
  flex-direction: column;
  height: 100%;
  /* Em paisagem (360 px de altura) a grade não cabe: a tela rola, em vez de cortar. */
  overflow-x: hidden;
  overflow-y: auto;
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
  flex: 1 0 auto;
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
  flex-shrink: 0;
  padding: 0 24px 48px;
}

/* 3 fileiras de campi (5 campi em 2 colunas) e as 2 lacunas de 8 px. */
.area-campi {
  min-height: 150px;
}

.chamada-campus {
  padding-top: 8px;
  font-size: 13px;
  text-align: center;
  color: var(--branco-70);
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
  color: var(--branco-70);
}

.tentar {
  margin-top: 8px;
  border: 1.5px solid var(--branco-70);
}

/* No celular, a entrada ocupa a tela como antes; o lado verde é só do desktop. */
.entrada {
  display: flex;
  flex: 1;
  flex-direction: column;
}

.hero,
.entrada-rotulo,
.entrada-titulo,
.entrada-descricao {
  display: none;
}

/* ─── Desktop (FE-23, protótipo desktop) ─────────────────────────────── */
@media (min-width: 1024px) {
  .boas-vindas {
    display: grid;
    grid-template-columns: minmax(0, 1.4fr) minmax(420px, 0.8fr);
    background: var(--creme);
  }
  .deco {
    display: none;
  }

  .hero {
    position: relative;
    display: flex;
    flex-direction: column;
    overflow: hidden;
    padding: clamp(32px, 4vw, 62px) clamp(38px, 5vw, 78px) 36px;
    color: #fff;
    background: var(--verde-escuro);
  }
  .hero::before,
  .hero::after {
    content: '';
    position: absolute;
    border-radius: 50%;
    pointer-events: none;
  }
  .hero::before {
    width: 650px;
    height: 650px;
    right: -300px;
    top: -300px;
    border: 1px solid var(--branco-07);
    box-shadow:
      0 0 0 75px var(--branco-02),
      0 0 0 150px var(--branco-02);
  }
  .hero::after {
    width: 430px;
    height: 430px;
    left: -280px;
    bottom: -160px;
    border: 1px solid var(--branco-10);
    box-shadow: 0 0 0 45px var(--branco-02);
  }
  .hero-marca {
    position: relative;
    z-index: 1;
    display: flex;
    align-items: center;
    gap: 14px;
  }
  .hero-marca strong,
  .hero-marca small {
    display: block;
  }
  .hero-marca strong {
    font: 900 25px / 1 var(--fonte-titulo);
    letter-spacing: -0.045em;
  }
  .hero-marca small {
    margin-top: 5px;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.11em;
    text-transform: uppercase;
    color: var(--branco-60);
  }
  .hero-texto {
    position: relative;
    z-index: 1;
    max-width: 760px;
    margin: auto 0 42px;
  }
  .hero-titulo {
    max-width: 740px;
    font: 900 clamp(46px, 5.2vw, 78px) / 0.98 var(--fonte-titulo);
    letter-spacing: -0.06em;
    text-wrap: balance;
  }
  .hero-descricao {
    max-width: 560px;
    margin-top: 25px;
    font-size: 14px;
    line-height: 1.75;
    color: var(--branco-60);
  }
  .hero-refeicoes {
    position: relative;
    z-index: 1;
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 11px;
    list-style: none;
  }
  .hero-refeicao {
    display: grid;
    grid-template-columns: 72px 1fr;
    grid-template-rows: 1fr 1fr;
    align-items: end;
    gap: 0 12px;
    min-height: 96px;
    padding: 11px 13px;
    border: 1px solid var(--branco-08);
    border-radius: 16px;
    color: var(--branco-60);
    background: var(--branco-05);
  }
  .hero-refeicao--destaque {
    color: #fff;
    border-color: var(--dourado);
    background: var(--branco-08);
  }
  .hero-refeicao > :first-child {
    grid-row: 1 / -1;
  }
  .hero-refeicao > span {
    font: 800 12px var(--fonte-titulo);
  }
  .hero-refeicao > small {
    align-self: start;
    margin-top: 3px;
    font-size: 11px;
    color: var(--branco-60);
  }

  .entrada {
    justify-content: center;
    width: 100%;
    max-width: 390px;
    margin: 0 auto;
    padding: 40px 0;
    color: var(--texto-escuro);
  }
  .entrada :focus-visible {
    outline-color: var(--verde-escuro);
  }
  .marca {
    flex: 0 0 auto;
    align-items: flex-start;
    padding: 0;
  }
  .logo {
    margin-bottom: 38px;
    filter: none;
  }
  .logo :deep(img) {
    width: 112px;
    height: 72px;
  }
  .slogan {
    display: none;
  }
  /* O h1 da página continua sendo o nome do app, fora da vista no desktop. */
  .nome {
    position: absolute;
    width: 1px;
    height: 1px;
    margin: 0;
    overflow: hidden;
    clip-path: inset(50%);
    white-space: nowrap;
  }
  .entrada-rotulo,
  .entrada-titulo,
  .entrada-descricao {
    display: block;
  }
  .entrada-rotulo {
    color: var(--texto-rotulo);
  }
  .entrada-titulo {
    max-width: 360px;
    font: 900 34px / 1.05 var(--fonte-titulo);
    letter-spacing: -0.04em;
    color: var(--verde-escuro);
  }
  .entrada-descricao {
    margin: 15px 0 30px;
    font-size: 12px;
    line-height: 1.7;
    color: var(--texto-suave);
  }
  .acoes {
    padding: 0;
  }
  .acoes .botao--destaque {
    color: #fff;
    background: var(--verde-escuro);
    box-shadow: 0 10px 20px var(--sombra-escura);
  }
  .visitante {
    border-color: var(--borda);
    color: var(--texto-suave);
  }
  .nota {
    color: var(--texto-suave);
  }
}

@media (min-width: 1024px) {
  .chamada-campus {
    color: var(--texto-suave);
  }

  .tentar {
    border-color: var(--borda);
  }
}
</style>
