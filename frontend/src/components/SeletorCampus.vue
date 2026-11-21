<script setup>
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useCardapioStore } from '@/stores/cardapio'
import { usePreferenciasStore } from '@/stores/preferencias'
import { siglaCampus } from '@/constants/campi'
import AppLogo from '@/components/AppLogo.vue'
import IconeSvg from '@/components/IconeSvg.vue'

const router = useRouter()
const cardapio = useCardapioStore()
const preferencias = usePreferenciasStore()

onMounted(() => cardapio.carregarCampi())

function escolher(id) {
  preferencias.escolherCampus(id)
  router.push({ name: 'campus-tela', params: { campusId: id } })
}
</script>

<template>
  <div class="tela">
    <header class="cabecalho cabecalho-campus fundo-escuro">
      <div class="marca">
        <AppLogo :tamanho="36" />
        <span class="nome">bandejão</span>
      </div>
      <h1 class="titulo-tela">Qual campus<br />você frequenta?</h1>
      <p class="subtitulo-tela subtitulo">Pode trocar depois a qualquer momento</p>
    </header>

    <div class="conteudo sem-barra">
      <p
        v-if="cardapio.carregandoCampi || (!cardapio.campiCarregados && !cardapio.erroCampi)"
        class="estado"
        role="status"
      >
        Carregando campi…
      </p>

      <div v-else-if="cardapio.erroCampi && !cardapio.campi.length" class="estado" role="alert">
        <p>Não foi possível carregar os campi. {{ cardapio.erroCampi }}</p>
        <button
          type="button"
          class="botao-pequeno"
          @click="cardapio.carregarCampi({ forcar: true })"
        >
          Tentar novamente
        </button>
      </div>

      <p v-else-if="!cardapio.campi.length" class="estado">Nenhum campus disponível no momento.</p>

      <ul v-else class="pilha-3 lista">
        <li v-for="campus in cardapio.campi" :key="campus.id">
          <button
            type="button"
            class="cartao cartao-clicavel campus"
            :class="{ 'campus--atual': preferencias.campusId === campus.id }"
            @click="escolher(campus.id)"
          >
            <span class="sigla">{{ siglaCampus(campus.nome) }}</span>
            <span class="textos">
              <span class="nome-campus">{{ campus.nome }}</span>
            </span>
            <IconeSvg nome="chevron" :tamanho="16" cor="var(--borda)" espessura="2.5" />
          </button>
        </li>
      </ul>
    </div>
  </div>
</template>

<style scoped>
.cabecalho-campus {
  padding-bottom: 32px;
}

.marca {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 24px;
}

.nome {
  font-family: var(--fonte-titulo);
  font-weight: 900;
  font-size: 20px;
  letter-spacing: -0.5px;
  color: #fff;
}

.subtitulo {
  margin-top: 8px;
}

.lista {
  list-style: none;
  padding: 20px 16px 32px;
}

.campus {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 16px;
}
.campus--atual {
  border-color: var(--verde-escuro);
}

.sigla {
  width: 44px;
  height: 44px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--raio-md);
  background: var(--verde-escuro);
  font-size: 12px;
  font-weight: 900;
  letter-spacing: -0.3px;
  color: #fff;
}

.textos {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.nome-campus {
  font-family: var(--fonte-titulo);
  font-size: 14px;
  font-weight: 700;
  color: var(--texto-escuro);
}

.estado {
  padding: 32px 16px;
  text-align: center;
  color: var(--texto-suave);
}

.estado .botao-pequeno {
  margin-top: 12px;
}
</style>
