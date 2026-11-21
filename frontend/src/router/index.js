import { createRouter, createWebHistory } from 'vue-router'
import { idDeCampusValido } from '@/constants/campi'
import { usePreferenciasStore } from '@/stores/preferencias'
import { useAuthStore } from '@/stores/auth'

/**
 * Rotas nomeadas e com lazy-loading (C4 — Estratégia de roteamento).
 *
 * Fluxo do protótipo: Boas-vindas → (Entrar | Continuar sem login) → Campus
 * → tela do campus (cardápio e fila). Na raiz, quem já escolheu o campus cai
 * direto na tela dele (RN04, RF05, RNF03); na primeira visita, nas
 * boas-vindas. Nenhuma rota exige login: ações restritas mostram um convite
 * ao login dentro da própria tela (RF05, RI06).
 */
function telaDoCampusLembrado(destinoSemCampus, hash = '') {
  const campusId = usePreferenciasStore().campusId
  if (!campusId) return { name: destinoSemCampus }
  return { name: 'campus-tela', params: { campusId: String(campusId) }, hash }
}

export const routes = [
  {
    path: '/',
    name: 'raiz',
    redirect: () => telaDoCampusLembrado('boas-vindas'),
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
    component: () => import('@/components/SeletorCampus.vue'),
    meta: { title: 'Escolha o campus' },
  },
  {
    path: '/campus/:campusId',
    name: 'campus-tela',
    component: () => import('@/views/CampusView.vue'),
    props: true,
    meta: { title: 'Cardápio e fila' },
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
    redirect: () => telaDoCampusLembrado('campus'),
  },
  {
    path: '/cardapio/:campusId',
    name: 'cardapio-campus',
    redirect: (to) =>
      idDeCampusValido(to.params.campusId)
        ? { name: 'campus-tela', params: { campusId: to.params.campusId } }
        : telaDoCampusLembrado('campus'),
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
    redirect: () => telaDoCampusLembrado('campus', '#fila'),
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

/**
 * Na primeira navegação, pergunta ao servidor se há sessão (GET /api/sessao/):
 * depois de um F5 quem estava logado continua logado (ADR 0007, FE-03).
 * Não recusa nenhuma rota (sem sessão, o app abre como visitante, RF05), mas
 * a primeira tela espera a resposta por no máximo 3 s (`carregarSessao`).
 */
export async function carregarSessaoAoAbrir() {
  const auth = useAuthStore()
  if (!auth.sessaoCarregada) await auth.carregarSessao()
}

/** Telas que dependem do campus mandam para a escolha de campus na primeira visita. */
export function exigirCampus(to) {
  if (to.meta.requerCampus && !usePreferenciasStore().campusId) return { name: 'campus' }
}

export function atualizarTitulo(to) {
  document.title = to.meta.title ? `${to.meta.title} · Bandejão` : 'Bandejão'
}

/** Os guardas do app num lugar só: o `router` abaixo e os testes usam a mesma função. */
export function instalarGuardas(roteador) {
  roteador.beforeEach(carregarSessaoAoAbrir)
  roteador.beforeEach(exigirCampus)
  roteador.afterEach(atualizarTitulo)
}

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
})
instalarGuardas(router)

export default router
