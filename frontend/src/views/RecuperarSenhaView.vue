<script setup>
import { ref } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import CabecalhoFormulario from '@/components/CabecalhoFormulario.vue'
import CampoTexto from '@/components/CampoTexto.vue'
import LinkSimulado from '@/components/LinkSimulado.vue'

/**
 * Recuperação de senha (RF04). A resposta é sempre a mesma, exista ou não
 * uma conta com o e-mail informado.
 */
const route = useRoute()
const auth = useAuthStore()

const email = ref(typeof route.query.email === 'string' ? route.query.email : '')
const enviando = ref(false)
const resposta = ref(null)
const erro = ref('')

async function solicitar() {
  if (!email.value || enviando.value) return
  enviando.value = true
  erro.value = ''
  resposta.value = null
  try {
    resposta.value = await auth.solicitarRecuperacao(email.value)
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
      titulo="Recuperar senha"
      subtitulo="Enviaremos um link para o seu e-mail"
      :voltar-para="{ name: 'login' }"
    />

    <form class="conteudo sem-barra pilha-4" novalidate @submit.prevent="solicitar">
      <p class="explicacao">
        Informe o e-mail institucional da sua conta. O link para criar uma nova senha vale por 1
        hora.
      </p>

      <CampoTexto
        v-model="email"
        rotulo="E-mail institucional"
        type="email"
        inputmode="email"
        autocomplete="username"
        placeholder="matricula@aluno.unb.br"
      />

      <p v-if="resposta" class="mensagem mensagem--sucesso" role="status">{{ resposta.detail }}</p>
      <p v-if="erro" class="mensagem mensagem--erro" role="alert">{{ erro }}</p>
      <LinkSimulado :link="resposta?.linkSimulado" rotulo="Abrir link de redefinição recebido" />

      <button type="submit" class="botao botao--primario" :disabled="!email || enviando">
        {{ enviando ? 'Enviando…' : 'Enviar link' }}
      </button>

      <p class="rodape">
        Lembrou a senha?
        <RouterLink :to="{ name: 'login' }" class="link-forte">Entrar</RouterLink>
      </p>
    </form>
  </div>
</template>

<style scoped>
.explicacao {
  font-size: 13px;
  line-height: 1.6;
  color: var(--texto-suave);
}

.rodape {
  font-size: 14px;
  text-align: center;
  color: var(--texto-suave);
}
</style>
