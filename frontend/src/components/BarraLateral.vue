<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useCardapioStore } from '@/stores/cardapio'
import { usePreferenciasStore } from '@/stores/preferencias'
import { AVISO_SAIR_SEM_CONFIRMACAO, useSair } from '@/composables/sair'
import { CANAL_CONTATO, EMAIL_CONTATO } from '@/constants/contato'
import { ITENS_NAVEGACAO_LATERAL, itemAtivo } from '@/constants/navegacao'
import AppLogo from './AppLogo.vue'
import IconeSvg from './IconeSvg.vue'

/**
 * Navegação do desktop (FE-23, protótipo desktop): a partir de 1024 px, no
 * lugar da `NavegacaoTopo`. O menu principal não inclui Perfil: o atalho
 * de conta leva a Meu progresso para usuários autenticados e ao login para
 * visitantes. Mostra o campus atual (RN04) e o canal de contato (RNF08).
 */
// O Ranking (RF27) só tinha atalho no menu do perfil da Início, que some no
// desktop: aqui ele entra na navegação.
const ITENS = [...ITENS_NAVEGACAO_LATERAL, { rotulo: 'Ranking', rota: 'ranking', icone: 'trofeu' }]

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const cardapio = useCardapioStore()
const preferencias = usePreferenciasStore()
const { sair, saindo, semConfirmacao } = useSair()
cardapio.carregarCampi()

const ativo = (item) => itemAtivo(item, route.name, { marcarInicio: true })
const campus = computed(() =>
  preferencias.campusId ? cardapio.buscarCampus(preferencias.campusId) : null,
)
const inicial = computed(() => auth.apelido.charAt(0).toUpperCase())
// Com campus escolhido mas a lista dos campi fora do ar, não há nome para
// mostrar: o atalho continua levando à troca, sem dizer "Escolher".
const textoDoCampus = computed(() => {
  if (campus.value) return campus.value.nome
  return preferencias.campusId ? 'Trocar campus' : 'Escolher campus'
})

// Como o BotaoSair (RF03.3): volta à raiz quando o servidor confirma; senão,
// avisa que a sessão pode continuar ativa no servidor.
async function sairDaConta() {
  if (await sair()) await router.push({ name: 'raiz' })
}
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
        v-for="item in ITENS"
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
        <strong>{{ textoDoCampus }}</strong>
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

    <button
      v-if="auth.estaAutenticado"
      type="button"
      class="sair"
      :disabled="saindo"
      @click="sairDaConta"
    >
      <IconeSvg nome="sair" :tamanho="17" /> {{ saindo ? 'Saindo…' : 'Sair da conta' }}
    </button>
    <p v-if="semConfirmacao" class="aviso-sair" role="alert" data-teste="sair-aviso-lateral">
      {{ AVISO_SAIR_SEM_CONFIRMACAO }}
    </p>
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
    overflow-x: hidden;
    overflow-y: auto;
    padding: 28px 20px 18px;
    color: var(--branco);
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
  color: var(--branco);
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
  font-size: 11px;
  font-weight: 600;
  color: var(--branco-60);
}

nav {
  position: relative;
  z-index: 1;
}

.rotulo-lateral {
  margin: 0 12px 12px;
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--branco-60);
}

.item {
  display: flex;
  align-items: center;
  gap: 12px;
  margin: 4px 0;
  padding: 12px 13px;
  border-radius: var(--raio-11);
  font-size: 13px;
  font-weight: 700;
  color: var(--branco-75);
  text-decoration: none;
  transition: 0.2s ease;
}
.item:hover {
  color: var(--branco);
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
  font-size: 12px;
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
  color: var(--branco-60);
  text-decoration: none;
}
.atalho:hover {
  color: var(--branco);
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
  border-radius: var(--raio-9);
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
  font-size: 11px;
  color: var(--branco-60);
}

.atalho-texto strong {
  margin-top: 3px;
  font-size: 12px;
  color: var(--branco);
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
  font-size: 11px;
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
  font-size: 11px;
  color: var(--branco-60);
}
.sair:hover:not(:disabled) {
  color: var(--branco);
}

.aviso-sair {
  position: relative;
  z-index: 1;
  margin: 8px 6px 0;
  padding: 10px 12px;
  border-radius: var(--raio-10);
  font-size: 12px;
  line-height: 1.5;
  color: var(--erro-texto);
  background: var(--erro-fundo);
}
</style>
