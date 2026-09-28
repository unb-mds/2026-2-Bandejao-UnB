<script setup>
import { useRouter } from 'vue-router'
import { usePreferenciasStore } from '@/stores/preferencias'
import { CAMPI, siglaCampus } from '@/constants/campi'
import AppLogo from '@/components/AppLogo.vue'
import IconeSvg from '@/components/IconeSvg.vue'

/** Escolha do campus no início da jornada (RF07). Fica lembrado no aparelho. */
const router = useRouter()
const preferencias = usePreferenciasStore()

function escolher(id) {
  preferencias.escolherCampus(id)
  router.push({ name: 'inicio' })
}
</script>

<template>
  <div class="tela">
    <header class="cabecalho cabecalho-campus">
      <div class="marca">
        <AppLogo :tamanho="36" />
        <span class="nome">bandejão</span>
      </div>
      <h1 class="titulo-tela">Qual campus<br />você frequenta?</h1>
      <p class="subtitulo-tela subtitulo">Pode trocar depois a qualquer momento</p>
    </header>

    <ul class="conteudo sem-barra pilha-3 lista">
      <li v-for="campus in CAMPI" :key="campus.id">
        <button
          type="button"
          class="cartao cartao-clicavel campus"
          :class="{ 'campus--atual': preferencias.campusId === campus.id }"
          @click="escolher(campus.id)"
        >
          <span class="sigla">{{ siglaCampus(campus.nome) }}</span>
          <span class="textos">
            <span class="nome-campus">{{ campus.nome }}</span>
            <span class="descricao">{{ campus.descricao }}</span>
          </span>
          <IconeSvg nome="chevron" :tamanho="16" cor="var(--borda)" espessura="2.5" />
        </button>
      </li>
    </ul>
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

.descricao {
  margin-top: 2px;
  font-size: 12px;
  color: var(--texto-claro);
}
</style>
