import { createRouter, createWebHistory } from 'vue-router'

export const routes = [
  {
    path: '/',
    name: 'cardapio',
    component: () => import('@/views/CardapioView.vue'),
    meta: { title: 'Cardápio' },
  },
  {
    path: '/cardapio/:campusId',
    name: 'cardapio-campus',
    component: () => import('@/views/CardapioView.vue'),
    props: true,
    meta: { title: 'Cardápio' },
  },
  {
    path: '/avaliacoes',
    name: 'avaliacoes',
    component: () => import('@/views/AvaliacoesView.vue'),
    meta: { title: 'Avaliações' },
  },
  {
    path: '/fila',
    name: 'fila',
    component: () => import('@/views/FilaView.vue'),
    meta: { title: 'Previsão de pico' },
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

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
})

router.afterEach((to) => {
  document.title = to.meta.title ? `${to.meta.title} · Bandejão` : 'Bandejão'
})

export default router