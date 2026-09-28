<script setup>
import { computed, ref } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import CabecalhoFormulario from '@/components/CabecalhoFormulario.vue'
import CampoSenha from '@/components/CampoSenha.vue'

/**
 * Definição da nova senha pelo link recebido por e-mail (RF04). O link é
 * de uso único e vale 1 hora; depois da troca, as sessões ativas caem.
 */
const route = useRoute()
const auth = useAuthStore()

const token = computed(() => (typeof route.query.token === 'string' ? route.query.token : ''))
const senha = ref('')
const confirmacao = ref('')
const enviando = ref(false)
const concluido = ref(false)
const erro = ref('')

const senhasDiferentes = computed(
  () => Boolean(confirmacao.value) && senha.value !== confirmacao.value,
)
const podeEnviar = computed(
  () =>
    Boolean(token.value && senha.value && confirmacao.value) &&
    !senhasDiferentes.value &&
    !enviando.value,
)

async function redefinir() {
  if (!podeEnviar.value) return
  enviando.value = true
  erro.value = ''
  try {
    await auth.redefinirSenha(token.value, senha.value)
    concluido.value = true
  } catch (falha) {
    erro.value = falha.message
  } finally {
    enviando.value = false
  }
}
</script>

<template>
  <div class="tela">
    <CabecalhoFormulario
      titulo="Redefinir senha"
      subtitulo="Escolha uma nova senha"
      :voltar-para="{ name: 'login' }"
    />

    <div class="conteudo sem-barra pilha-4">
      <template v-if="concluido">
        <p class="mensagem mensagem--sucesso" role="status">
          Senha alterada! Use a nova senha para entrar.
        </p>
        <RouterLink :to="{ name: 'login' }" class="botao botao--primario">Entrar</RouterLink>
      </template>

      <template v-else-if="!token">
        <p class="mensagem mensagem--erro" role="alert">
          Link de redefinição inválido. Abra o link recebido por e-mail ou peça um novo.
        </p>
        <RouterLink :to="{ name: 'recuperar-senha' }" class="botao botao--contorno">
          Pedir novo link
        </RouterLink>
      </template>

      <form v-else class="pilha-4" novalidate @submit.prevent="redefinir">
        <CampoSenha v-model="senha" rotulo="Nova senha" autocomplete="new-password" />
        <CampoSenha
          v-model="confirmacao"
          rotulo="Confirme a nova senha"
          placeholder="Repita a nova senha"
          autocomplete="new-password"
          :dica="senhasDiferentes ? 'As senhas não conferem.' : ''"
        />

        <div v-if="erro" class="mensagem mensagem--erro" role="alert">
          {{ erro }}
          <RouterLink :to="{ name: 'recuperar-senha' }" class="novo-link"
            >Pedir novo link</RouterLink
          >
        </div>

        <button type="submit" class="botao botao--primario" :disabled="!podeEnviar">
          {{ enviando ? 'Salvando…' : 'Salvar nova senha' }}
        </button>
      </form>
    </div>
  </div>
</template>

<style scoped>
.novo-link {
  display: block;
  margin-top: 8px;
  font-size: 12px;
  font-weight: 700;
  color: var(--erro-texto);
}
</style>
