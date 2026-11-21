<script setup>
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useAvaliacoesStore } from '@/stores/avaliacoes'
import { usePreferenciasStore } from '@/stores/preferencias'
import { USANDO_SIMULACAO, mensagemDeErro } from '@/services/apiClient'
import CabecalhoFormulario from '@/components/CabecalhoFormulario.vue'
import CampoTexto from '@/components/CampoTexto.vue'
import CampoSenha from '@/components/CampoSenha.vue'
import LinkSimulado from '@/components/LinkSimulado.vue'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const avaliacoes = useAvaliacoesStore()
const preferencias = usePreferenciasStore()

const emailInstitucional = ref('')
const senha = ref('')
const enviando = ref(false)
const erro = ref('')
const naoConfirmado = ref(false)
const reenvio = ref(null)
const reenviando = ref(false)
/** Conta de demonstração: só em desenvolvimento, sem levar o simulado ao build. */
const contaDemo = ref(null)
if (import.meta.env.DEV && USANDO_SIMULACAO) {
  import('@/services/mock/banco').then(({ CONTA_DEMO }) => (contaDemo.value = CONTA_DEMO))
}

const podeEnviar = computed(
  () => Boolean(emailInstitucional.value.trim()) && senha.value.length >= 1 && !enviando.value,
)
const podeReenviar = computed(() => Boolean(emailInstitucional.value.trim()) && !reenviando.value)

/**
 * Depois do login: volta à tela que pediu o login, ou segue direto para a tela
 * do campus lembrado (RF03.4), sem passo a mais; sem campus, para a escolha.
 */
function seguirAposLogin() {
  const voltar = route.query.voltar
  if (typeof voltar === 'string' && voltar.startsWith('/') && !voltar.startsWith('//')) {
    return router.replace(voltar)
  }
  if (!preferencias.campusId) return router.replace({ name: 'campus' })
  return router.replace({
    name: 'campus-tela',
    params: { campusId: String(preferencias.campusId) },
  })
}

async function entrar() {
  if (!podeEnviar.value) return
  enviando.value = true
  erro.value = ''
  naoConfirmado.value = false
  reenvio.value = null
  try {
    await auth.entrar(emailInstitucional.value, senha.value)
  } catch (falha) {
    erro.value = mensagemDeErro(falha)
    naoConfirmado.value = falha.codigo === 'conta_nao_confirmada'
    return
  } finally {
    enviando.value = false
  }
  avaliacoes.limparCache()
  await seguirAposLogin()
}

async function reenviarConfirmacao() {
  if (!podeReenviar.value) return
  reenviando.value = true
  try {
    reenvio.value = await auth.reenviarConfirmacao({
      emailInstitucional: emailInstitucional.value,
    })
  } catch (falha) {
    erro.value = mensagemDeErro(falha)
  } finally {
    reenviando.value = false
  }
}
</script>

<template>
  <div class="tela tela-formulario">
    <CabecalhoFormulario
      titulo="Entrar"
      subtitulo="Use seu e-mail institucional"
      :voltar-para="{ name: 'boas-vindas' }"
    />

    <form class="conteudo sem-barra pilha-4" novalidate @submit.prevent="entrar">
      <CampoTexto
        v-model="emailInstitucional"
        rotulo="E-mail institucional"
        type="email"
        maxlength="254"
        autocomplete="username"
        placeholder="matricula@aluno.unb.br ou nome@unb.br"
      />

      <CampoSenha v-model="senha" />

      <div class="esqueci">
        <RouterLink :to="{ name: 'recuperar-senha' }" class="link-destaque">
          Esqueci a senha
        </RouterLink>
      </div>

      <div v-if="erro" class="mensagem mensagem--erro" role="alert">
        {{ erro }}
        <button
          v-if="naoConfirmado && !reenvio"
          type="button"
          class="reenviar"
          :disabled="!podeReenviar"
          @click="reenviarConfirmacao"
        >
          Reenviar link de confirmação
        </button>
      </div>
      <p v-if="reenvio" class="mensagem mensagem--sucesso" role="status">{{ reenvio.mensagem }}</p>
      <LinkSimulado :link="reenvio?.linkSimulado" rotulo="Abrir link de confirmação recebido" />

      <button type="submit" class="botao botao--primario" :disabled="!podeEnviar">
        {{ enviando ? 'Entrando…' : 'Entrar' }}
      </button>

      <div class="divisor">ou</div>

      <p class="criar-conta">
        Não tem conta?
        <RouterLink :to="{ name: 'cadastro' }" class="link-forte">Criar conta</RouterLink>
      </p>

      <p v-if="contaDemo" class="demo">
        Demonstração: entre com o e-mail <strong>{{ contaDemo.email }}</strong> e a senha
        <strong>{{ contaDemo.senha }}</strong
        >, ou crie uma conta nova.
      </p>
    </form>
  </div>
</template>

<style scoped>
.esqueci {
  margin-top: 12px;
  text-align: right;
}

.reenviar {
  display: block;
  margin-top: 8px;
  font-size: 12px;
  font-weight: 700;
  color: var(--erro-texto);
  text-decoration: underline;
  text-underline-offset: 2px;
}

.reenviar:disabled {
  cursor: default;
  opacity: 0.6;
}

.criar-conta {
  font-size: 14px;
  text-align: center;
  color: var(--texto-suave);
}

.demo {
  font-size: 11px;
  line-height: 1.6;
  text-align: center;
  color: var(--texto-claro);
  overflow-wrap: anywhere;
}
</style>
