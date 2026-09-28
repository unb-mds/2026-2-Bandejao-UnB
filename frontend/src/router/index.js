import { createRouter, createWebHistory } from 'vue-router'
import { campusValido } from '@/constants/campi'
import { usePreferenciasStore } from '@/stores/preferencias'

/**
 * Rotas nomeadas e com lazy-loading (C4 — Estratégia de roteamento).
 *
 * Fluxo do protótipo: Boas-vindas → (Entrar | Continuar sem login) → Campus
 * → Início → Cardápio / Fila / Avaliações. Na raiz, quem já escolheu o
 * campus cai direto no cardápio (RF05, RNF03); na primeira visita, nas
 * boas-vindas. Nenhuma rota exige login: ações restritas mostram um convite
 * ao login dentro da própria tela (RF05, RI06).
 */
export const routes = [
  {
    path: '/',
    name: 'raiz',
    redirect: () => ({ name: usePreferenciasStore().campusId ? 'cardapio' : 'boas-vindas' }),
  },
  {
    path: '/boas-vindas',
    name: 'boas-vindas',
    component: () => import('@/views/BoasVindasView.vue'),
    meta: { title: 'Boas-vindas' },
  },
  {
    path: '/campus',
    name: 'campus',
    component: () => import('@/views/CampusView.vue'),
    meta: { title: 'Escolha o campus' },
  },
  {
    path: '/inicio',
    name: 'inicio',
    component: () => import('@/views/HomeView.vue'),
    meta: { title: 'Início', requerCampus: true },
  },
  {
    path: '/cardapio',
    name: 'cardapio',
    component: () => import('@/views/CardapioView.vue'),
    meta: { title: 'Cardápio', requerCampus: true },
  },
  {
    // Link compartilhável do cardápio de um campus: também passa a ser o campus lembrado.
    path: '/cardapio/:campusId',
    name: 'cardapio-campus',
    component: () => import('@/views/CardapioView.vue'),
    meta: { title: 'Cardápio' },
    beforeEnter: (to) => {
      if (!campusValido(to.params.campusId)) {
        return { name: 'nao-encontrada', params: { pathMatch: to.path.slice(1).split('/') } }
      }
      usePreferenciasStore().escolherCampus(to.params.campusId)
    },
  },
  {
    path: '/avaliacoes',
    name: 'avaliacoes',
    component: () => import('@/views/AvaliacoesView.vue'),
    meta: { title: 'Avaliações', requerCampus: true },
  },
  {
    path: '/fila',
    name: 'fila',
    component: () => import('@/views/FilaView.vue'),
    meta: { title: 'Fila do RU', requerCampus: true },
  },
  {
    path: '/login',
    name: 'login',
    component: () => import('@/views/LoginView.vue'),
    meta: { title: 'Entrar' },
  },
  {
    path: '/cadastro',
    name: 'cadastro',
    component: () => import('@/views/CadastroView.vue'),
    meta: { title: 'Criar conta' },
  },
  {
    path: '/confirmar-email',
    name: 'confirmar-email',
    component: () => import('@/views/ConfirmarEmailView.vue'),
    meta: { title: 'Confirmar e-mail' },
  },
  {
    path: '/recuperar-senha',
    name: 'recuperar-senha',
    component: () => import('@/views/RecuperarSenhaView.vue'),
    meta: { title: 'Recuperar senha' },
  },
  {
    path: '/redefinir-senha',
    name: 'redefinir-senha',
    component: () => import('@/views/RedefinirSenhaView.vue'),
    meta: { title: 'Redefinir senha' },
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'nao-encontrada',
    component: () => import('@/views/NotFoundView.vue'),
    meta: { title: 'Página não encontrada' },
  },
]

/** Telas que dependem do campus mandam para a escolha de campus na primeira visita. */
export function exigirCampus(to) {
  if (to.meta.requerCampus && !usePreferenciasStore().campusId) return { name: 'campus' }
}

export function atualizarTitulo(to) {
  document.title = to.meta.title ? `${to.meta.title} · Bandejão` : 'Bandejão'
}

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
})

router.beforeEach(exigirCampus)
router.afterEach(atualizarTitulo)

export default router
