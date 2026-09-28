<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import CabecalhoFormulario from '@/components/CabecalhoFormulario.vue'
import CampoTexto from '@/components/CampoTexto.vue'
import IconeSvg from '@/components/IconeSvg.vue'
import LinkSimulado from '@/components/LinkSimulado.vue'

/**
 * Confirmação de e-mail (RF02), com dois pontos de entrada:
 * - `?email=...` logo após o cadastro: "verifique seu e-mail" + reenvio;
 * - `?token=...` pelo link recebido: confirma a conta ao abrir a tela.
 */
const route = useRoute()
const auth = useAuthStore()

const token = computed(() => (typeof route.query.token === 'string' ? route.query.token : ''))
const email = ref(typeof route.query.email === 'string' ? route.query.email : '')

// estado: 'pendente' | 'confirmando' | 'confirmado' | 'invalido'
const estado = ref(token.value ? 'confirmando' : 'pendente')
const linkSimulado = ref(window.history.state?.linkSimulado ?? '')
const reenvio = ref('')
const erro = ref('')
const reenviando = ref(false)

// Observa o token (e não só a montagem): o link simulado reabre esta mesma tela.
watch(
  token,
  async (valor) => {
    if (!valor) return
    estado.value = 'confirmando'
    erro.value = ''
    try {
      await auth.confirmarEmail(valor)
      estado.value = 'confirmado'
    } catch (falha) {
      erro.value = falha.message
      estado.value = 'invalido'
    }
  },
  { immediate: true },
)

async function reenviar() {
  if (!email.value || reenviando.value) return
  reenviando.value = true
  erro.value = ''
  try {
    const resposta = await auth.reenviarConfirmacao(email.value)
    reenvio.value = resposta.detail
    linkSimulado.value = resposta.linkSimulado ?? ''
  } catch (falha) {
    erro.value = falha.message
  } finally {
    reenviando.value = false
  }
}
</script>

<template>
  <div class="tela">
    <CabecalhoFormulario
      titulo="Confirmar e-mail"
      subtitulo="Ative sua conta pelo link enviado"
      :voltar-para="{ name: 'login' }"
    />

    <div class="conteudo sem-barra pilha-4">
      <p v-if="estado === 'confirmando'" class="carregando" role="status">
        Confirmando seu e-mail…
      </p>

      <template v-else-if="estado === 'confirmado'">
        <div class="destaque destaque--sucesso">
          <div class="destaque-icone">
            <IconeSvg nome="check" :tamanho="22" cor="var(--sucesso-icone)" espessura="2.5" />
          </div>
          <div>
            <p class="destaque-titulo">Conta confirmada!</p>
            <p class="destaque-texto">Agora você já pode entrar e avaliar as refeições.</p>
          </div>
        </div>
        <RouterLink :to="{ name: 'login' }" class="botao botao--primario">Entrar</RouterLink>
      </template>

      <template v-else>
        <div v-if="estado === 'pendente'" class="cartao destaque">
          <div class="destaque-icone destaque-icone--neutro">
            <IconeSvg nome="email" :tamanho="22" cor="var(--verde-escuro)" />
          </div>
          <div>
            <p class="destaque-titulo destaque-titulo--escuro">Verifique seu e-mail</p>
            <p class="destaque-texto destaque-texto--suave">
              <template v-if="email"
                >Enviamos um link de confirmação para <strong>{{ email }}</strong
                >.</template
              >
              <template v-else
                >Enviamos um link de confirmação para o seu e-mail institucional.</template
              >
              O link vale por 24 horas; sem confirmação nesse prazo, o cadastro é excluído.
            </p>
          </div>
        </div>

        <p v-else class="mensagem mensagem--erro" role="alert">
          {{ erro || 'Link expirado ou inválido.' }} Informe seu e-mail para receber um novo link.
        </p>

        <LinkSimulado :link="linkSimulado" rotulo="Abrir link de confirmação recebido" />

        <form class="pilha-4" novalidate @submit.prevent="reenviar">
          <CampoTexto
            v-model="email"
            rotulo="E-mail institucional"
            type="email"
            inputmode="email"
            autocomplete="email"
            placeholder="matricula@aluno.unb.br"
          />
          <p v-if="reenvio" class="mensagem mensagem--sucesso" role="status">{{ reenvio }}</p>
          <p v-if="erro && estado === 'pendente'" class="mensagem mensagem--erro" role="alert">
            {{ erro }}
          </p>
          <button type="submit" class="botao botao--contorno" :disabled="!email || reenviando">
            {{ reenviando ? 'Enviando…' : 'Reenviar link de confirmação' }}
          </button>
        </form>

        <p class="rodape">
          Já confirmou?
          <RouterLink :to="{ name: 'login' }" class="link-forte">Entrar</RouterLink>
        </p>
      </template>
    </div>
  </div>
</template>

<style scoped>
.carregando {
  padding-top: 40px;
  text-align: center;
  color: var(--texto-suave);
}

.destaque {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 20px;
}
.destaque--sucesso {
  border-radius: var(--raio-lg);
  background: var(--sucesso-fundo);
}

.destaque-icone {
  width: 44px;
  height: 44px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--raio-md);
  background: var(--sucesso-icone-fundo);
}
.destaque-icone--neutro {
  background: var(--bege);
}

.destaque-titulo {
  font-family: var(--fonte-titulo);
  font-weight: 900;
  font-size: 16px;
  color: var(--sucesso-texto);
}
.destaque-titulo--escuro {
  color: var(--texto-escuro);
}

.destaque-texto {
  margin-top: 4px;
  font-size: 13px;
  line-height: 1.6;
  color: var(--sucesso-texto-suave);
  overflow-wrap: anywhere;
}
.destaque-texto--suave {
  color: var(--texto-suave);
}

.rodape {
  font-size: 14px;
  text-align: center;
  color: var(--texto-suave);
}
</style>
