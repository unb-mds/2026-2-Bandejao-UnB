<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useCardapioStore } from '@/stores/cardapio'
import { usePreferenciasStore } from '@/stores/preferencias'
import { useSair } from '@/composables/sair'
import { CANAL_CONTATO, EMAIL_CONTATO } from '@/constants/contato'
import { ITENS_NAVEGACAO_TOPO, itemAtivo } from '@/constants/navegacao'
import AppLogo from './AppLogo.vue'
import IconeSvg from './IconeSvg.vue'

/**
 * Navegação do desktop (FE-23, protótipo desktop): a partir de 1024 px, no
 * lugar da `NavegacaoTopo`. Leva aos mesmos destinos, mostra o campus atual
 * (RN04) e a conta, e tem o canal de contato (RNF08).
 */
const route = useRoute()
const auth = useAuthStore()
const cardapio = useCardapioStore()
const preferencias = usePreferenciasStore()
const { sair, saindo } = useSair()
cardapio.carregarCampi()

const ativo = (item) => itemAtivo(item, route.name, { marcarInicio: true })
const campus = computed(() =>
  preferencias.campusId ? cardapio.buscarCampus(preferencias.campusId) : null,
)
const inicial = computed(() => auth.apelido.charAt(0).toUpperCase())
</script>

<template>
  <aside class="barra-lateral fundo-escuro">
    <RouterLink :to="{ name: 'raiz' }" class="marca">
      <AppLogo :tamanho="40" />
      <span>
        <strong>bandejão</strong>
        <small>Restaurante Universitário · UnB</small>
      </span>
    </RouterLink>

    <nav aria-label="Navegação principal">
      <p class="rotulo-lateral" aria-hidden="true">Navegação</p>
      <RouterLink
        v-for="item in ITENS_NAVEGACAO_TOPO"
        :key="item.rotulo"
        :to="{ name: item.rota }"
        class="item"
        :class="{ 'item--ativo': ativo(item) }"
        :aria-current="ativo(item) ? 'page' : undefined"
      >
        <IconeSvg
          :nome="item.icone"
          :tamanho="19"
          :preenchimento="item.icone === 'estrela' && ativo(item) ? 'currentColor' : 'none'"
        />
        <span>{{ item.rotuloLateral ?? item.rotulo }}</span>
      </RouterLink>
    </nav>

    <div class="preenche" />

    <a :href="CANAL_CONTATO" class="contato">
      <IconeSvg nome="email" :tamanho="15" />
      Contato
      <span class="visualmente-oculto">: {{ EMAIL_CONTATO }}</span>
    </a>

    <RouterLink :to="{ name: 'campus' }" class="atalho atalho--campus">
      <span class="atalho-icone"><IconeSvg nome="local" :tamanho="17" /></span>
      <span class="atalho-texto">
        <small>Campus atual</small>
        <strong>{{ campus?.nome ?? 'Escolher campus' }}</strong>
      </span>
      <IconeSvg nome="chevron" :tamanho="15" />
    </RouterLink>

    <RouterLink
      :to="{ name: auth.estaAutenticado ? 'progresso' : 'login' }"
      class="atalho atalho--conta"
    >
      <span class="avatar-lateral" aria-hidden="true">{{ inicial }}</span>
      <span class="atalho-texto">
        <strong>{{ auth.apelido }}</strong>
        <small>{{ auth.estaAutenticado ? 'Meu progresso' : 'Acessar conta' }}</small>
      </span>
      <IconeSvg nome="chevron" :tamanho="15" />
    </RouterLink>

    <button v-if="auth.estaAutenticado" type="button" class="sair" :disabled="saindo" @click="sair">
      <IconeSvg nome="sair" :tamanho="17" /> Sair da conta
    </button>
  </aside>
</template>

<style scoped>
.barra-lateral {
  display: none;
}

@media (min-width: 1024px) {
  .barra-lateral {
    position: relative;
    display: flex;
    flex-direction: column;
    height: 100%;
    overflow: hidden;
    padding: 28px 20px 18px;
    color: #fff;
    background: var(--verde-escuro);
  }
}

/* Os anéis decorativos do protótipo, atrás do conteúdo. */
.barra-lateral::before {
  content: '';
  position: absolute;
  width: 320px;
  height: 320px;
  left: -210px;
  bottom: 80px;
  border: 1px solid var(--branco-05);
  border-radius: 50%;
  box-shadow:
    0 0 0 48px var(--branco-02),
    0 0 0 96px var(--branco-02);
  pointer-events: none;
}

.marca {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  gap: 11px;
  margin: 0 8px 50px;
  color: #fff;
  text-decoration: none;
}

.marca strong,
.marca small {
  display: block;
}

.marca strong {
  font: 900 20px/1 var(--fonte-titulo);
  letter-spacing: -0.045em;
}

.marca small {
  margin-top: 5px;
  font-size: 7px;
  font-weight: 700;
  letter-spacing: 0.11em;
  text-transform: uppercase;
  color: var(--branco-40);
}

nav {
  position: relative;
  z-index: 1;
}

.rotulo-lateral {
  margin: 0 12px 12px;
  font-size: 8px;
  font-weight: 800;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--branco-30);
}

.item {
  display: flex;
  align-items: center;
  gap: 12px;
  margin: 4px 0;
  padding: 12px 13px;
  border-radius: 11px;
  font-size: 11px;
  font-weight: 700;
  color: var(--branco-55);
  text-decoration: none;
  transition: 0.2s ease;
}
.item:hover {
  color: #fff;
  background: var(--branco-07);
  transform: translateX(2px);
}
.item--ativo,
.item--ativo:hover {
  color: var(--verde-escuro);
  background: var(--dourado);
  box-shadow: 0 8px 18px var(--sombra-escura);
  transform: none;
}

.preenche {
  flex: 1;
}

.contato {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0 7px 12px;
  font-size: 9px;
  font-weight: 700;
  color: var(--dourado);
  text-decoration: none;
}
.contato:hover {
  color: var(--dourado-claro);
}

.atalho {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 7px;
  color: var(--branco-40);
  text-decoration: none;
}
.atalho:hover {
  color: #fff;
}

.atalho--campus {
  border-top: 1px solid var(--branco-10);
  border-bottom: 1px solid var(--branco-10);
}

.atalho--conta {
  margin-top: 7px;
}

.atalho-icone {
  display: grid;
  place-items: center;
  width: 31px;
  height: 31px;
  border-radius: 9px;
  color: var(--dourado);
  background: var(--branco-07);
}

.atalho-texto {
  flex: 1;
  min-width: 0;
}

.atalho-texto small,
.atalho-texto strong {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.atalho-texto small {
  font-size: 7px;
  color: var(--branco-35);
}

.atalho-texto strong {
  margin-top: 3px;
  font-size: 9px;
  color: #fff;
}

.atalho--conta .atalho-texto small {
  margin-top: 3px;
}

.avatar-lateral {
  display: grid;
  place-items: center;
  width: 34px;
  height: 34px;
  flex-shrink: 0;
  border-radius: 50%;
  font-size: 10px;
  font-weight: 900;
  color: var(--verde-escuro);
  background: var(--dourado-avatar);
}

.sair {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 4px 6px 0;
  padding: 7px 4px;
  font-size: 8px;
  color: var(--branco-35);
}
.sair:hover:not(:disabled) {
  color: #fff;
}
</style>
