<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useAvaliacoesStore } from '@/stores/avaliacoes'
import { usePreferenciasStore } from '@/stores/preferencias'
import { USANDO_SIMULACAO } from '@/services/apiClient'
import CabecalhoFormulario from '@/components/CabecalhoFormulario.vue'
import CampoTexto from '@/components/CampoTexto.vue'
import CampoSenha from '@/components/CampoSenha.vue'
import LinkSimulado from '@/components/LinkSimulado.vue'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const avaliacoes = useAvaliacoesStore()
const preferencias = usePreferenciasStore()

const matriculaSiape = ref('')
const senha = ref('')
const enviando = ref(false)
const erro = ref('')
const naoConfirmado = ref(false)
const reenvio = ref(null)
/** Conta de demonstração: só em desenvolvimento, sem levar o simulado ao build. */
const contaDemo = ref(null)
if (import.meta.env.DEV && USANDO_SIMULACAO) {
  import('@/services/mock/banco').then(({ CONTA_DEMO }) => (contaDemo.value = CONTA_DEMO))
}

// Matrícula (9 dígitos) ou SIAPE (7): só números.
watch(matriculaSiape, (valor) => {
  matriculaSiape.value = valor.replace(/\D/g, '')
})

const podeEnviar = computed(
  () => Boolean(matriculaSiape.value) && senha.value.length >= 1 && !enviando.value,
)

/** Depois do login: volta à tela que pediu o login, ou segue para a Início (RF03). */
function seguirAposLogin() {
  const voltar = route.query.voltar
  if (typeof voltar === 'string' && voltar.startsWith('/') && !voltar.startsWith('//')) {
    router.replace(voltar)
  } else {
    router.replace({ name: preferencias.campusId ? 'inicio' : 'campus' })
  }
}

async function entrar() {
  if (!podeEnviar.value) return
  enviando.value = true
  erro.value = ''
  naoConfirmado.value = false
  reenvio.value = null
  try {
    await auth.entrar(matriculaSiape.value, senha.value)
    avaliacoes.limparCache()
    seguirAposLogin()
  } catch (falha) {
    erro.value = falha.message
    naoConfirmado.value = falha.codigo === 'conta_nao_confirmada'
  } finally {
    enviando.value = false
  }
}

async function reenviarConfirmacao() {
  try {
    reenvio.value = await auth.reenviarConfirmacao({ matriculaSiape: matriculaSiape.value })
  } catch (falha) {
    erro.value = falha.message
  }
}
</script>

<template>
  <div class="tela">
    <CabecalhoFormulario
      titulo="Entrar"
      subtitulo="Use sua matrícula ou SIAPE"
      :voltar-para="{ name: 'boas-vindas' }"
    />

    <form class="conteudo sem-barra pilha-4" novalidate @submit.prevent="entrar">
      <CampoTexto
        v-model="matriculaSiape"
        rotulo="Matrícula ou SIAPE"
        inputmode="numeric"
        maxlength="9"
        autocomplete="username"
        placeholder="9 dígitos (aluno) ou 7 (SIAPE)"
      />

      <CampoSenha v-model="senha" />

      <div class="esqueci">
        <RouterLink
          :to="{ name: 'recuperar-senha' }"
          class="link-destaque"
        >
          Esqueci a senha
        </RouterLink>
      </div>

      <div v-if="erro" class="mensagem mensagem--erro" role="alert">
        {{ erro }}
        <button
          v-if="naoConfirmado && !reenvio"
          type="button"
          class="reenviar"
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
        Demonstração: entre com a matrícula <strong>{{ contaDemo.matricula }}</strong> e a senha
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
