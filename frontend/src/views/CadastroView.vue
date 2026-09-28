<script setup>
import { computed, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { CANAL_CONTATO } from '@/constants/contato'
import CabecalhoFormulario from '@/components/CabecalhoFormulario.vue'
import CampoTexto from '@/components/CampoTexto.vue'
import CampoSenha from '@/components/CampoSenha.vue'
import IconeSvg from '@/components/IconeSvg.vue'

/**
 * Cadastro em duas etapas (RF01): primeiro o tipo de usuário, depois os
 * campos daquele tipo. Professor e Servidor seguem o mesmo fluxo e viram o
 * mesmo tipo interno ("servidor"). As regras de formato são conferidas pela
 * API; aqui os campos só são formatados (sem espaços, só dígitos).
 */
const TIPOS = [
  { id: 'aluno', rotulo: 'Aluno' },
  { id: 'professor', rotulo: 'Professor' },
  { id: 'servidor', rotulo: 'Servidor' },
]

const router = useRouter()
const auth = useAuthStore()

const tipo = ref(null)
const apelido = ref('')
const siape = ref('')
const email = ref('')
const senha = ref('')
const aceitou = ref(false)
const avisoAberto = ref(false)
const pedirApelido = ref(false)
const enviando = ref(false)
const erro = ref('')

const ehAluno = computed(() => tipo.value === 'aluno')
const ehServidor = computed(() => tipo.value === 'professor' || tipo.value === 'servidor')
const mostrarApelido = computed(() => ehAluno.value || pedirApelido.value)

const podeEnviar = computed(
  () =>
    Boolean(tipo.value && email.value && senha.value && aceitou.value) &&
    (ehAluno.value ? Boolean(apelido.value) : Boolean(siape.value)) &&
    (!pedirApelido.value || Boolean(apelido.value)) &&
    !enviando.value,
)

watch(apelido, (valor) => {
  apelido.value = valor.replace(/\s/g, '')
})
watch(siape, (valor) => {
  siape.value = valor.replace(/\D/g, '')
})
watch(tipo, () => {
  erro.value = ''
  pedirApelido.value = false
})

async function criarConta() {
  if (!podeEnviar.value) return
  enviando.value = true
  erro.value = ''
  try {
    const resposta = await auth.cadastrar({
      tipo: ehAluno.value ? 'estudante' : 'servidor',
      email: email.value.trim(),
      senha: senha.value,
      apelido: mostrarApelido.value ? apelido.value : '',
      siape: ehServidor.value ? siape.value : '',
      aceitouPrivacidade: aceitou.value,
    })
    router.push({
      name: 'confirmar-email',
      query: { email: resposta.email },
      state: { linkSimulado: resposta.linkSimulado ?? null },
    })
  } catch (falha) {
    erro.value = falha.message
    // Apelido extraído do e-mail indisponível: o formulário ganha o campo de apelido (C4 4b).
    if (falha.codigo === 'apelido_manual') pedirApelido.value = true
  } finally {
    enviando.value = false
  }
}
</script>

<template>
  <div class="tela">
    <CabecalhoFormulario
      titulo="Criar conta"
      subtitulo="Comunidade da UnB"
      :voltar-para="{ name: 'login' }"
    />

    <form class="conteudo sem-barra pilha-5 formulario" novalidate @submit.prevent="criarConta">
      <div>
        <p class="rotulo rotulo-tipo">Você é</p>
        <div class="tipos" role="radiogroup" aria-label="Tipo de usuário">
          <button
            v-for="opcao in TIPOS"
            :key="opcao.id"
            type="button"
            role="radio"
            class="tipo"
            :class="{ 'tipo--ativo': tipo === opcao.id }"
            :aria-checked="tipo === opcao.id"
            @click="tipo = opcao.id"
          >
            {{ opcao.rotulo }}
          </button>
        </div>
      </div>

      <div v-if="tipo" class="pilha-4">
        <CampoTexto
          v-if="ehServidor"
          v-model="siape"
          :rotulo="tipo === 'professor' ? 'Matrícula Funcional' : 'SIAPE'"
          inputmode="numeric"
          maxlength="7"
          placeholder="7 dígitos"
          dica="Identificador institucional (dado privado)"
        />

        <CampoTexto
          v-if="mostrarApelido"
          v-model="apelido"
          rotulo="Apelido (nick)"
          maxlength="20"
          autocomplete="nickname"
          placeholder="3 a 20 caracteres, sem espaços"
          dica="Será exibido nas suas avaliações e não pode ser alterado depois"
        />

        <CampoTexto
          v-model="email"
          rotulo="E-mail institucional"
          type="email"
          inputmode="email"
          autocomplete="email"
          :placeholder="ehAluno ? 'matricula@aluno.unb.br' : 'nome.sobrenome@unb.br'"
          :dica="
            ehAluno
              ? 'Formato: matricula@aluno.unb.br'
              : 'Domínio: @unb.br — o apelido público é gerado a partir do texto antes do @'
          "
        />

        <CampoSenha v-model="senha" autocomplete="new-password" />

        <div class="cartao privacidade">
          <label class="aceite">
            <input v-model="aceitou" type="checkbox" class="visualmente-oculto" />
            <span class="caixa" :class="{ 'caixa--marcada': aceitou }" aria-hidden="true">
              <IconeSvg v-if="aceitou" nome="check" :tamanho="11" cor="#fff" espessura="3.5" />
            </span>
            <span class="texto-aceite">
              Li e aceito o
              <button type="button" class="link-aviso" @click.prevent="avisoAberto = !avisoAberto">
                aviso de privacidade</button
              >. Meus dados serão usados para login, recuperação de senha e identificação das
              avaliações.
            </span>
          </label>

          <div v-if="avisoAberto" class="aviso-completo">
            <p>
              <strong>Dados coletados:</strong> matrícula ou SIAPE, e-mail institucional e apelido.
            </p>
            <p>
              <strong>Para quê:</strong> entrar na conta, recuperar a senha e identificar o autor
              das avaliações. Só o apelido aparece publicamente; matrícula/SIAPE e e-mail nunca são
              exibidos a outras pessoas.
            </p>
            <p>
              <strong>Seus direitos (LGPD):</strong> a exclusão da conta pode ser solicitada à
              equipe; suas avaliações permanecem de forma anônima. Contato:
              <a :href="CANAL_CONTATO" target="_blank" rel="noopener">canal do projeto</a>.
            </p>
          </div>
        </div>

        <p v-if="erro" class="mensagem mensagem--erro" role="alert">{{ erro }}</p>

        <button type="submit" class="botao botao--primario" :disabled="!podeEnviar">
          {{ enviando ? 'Criando conta…' : 'Criar conta' }}
        </button>
      </div>
    </form>
  </div>
</template>

<style scoped>
.formulario {
  padding-bottom: 40px;
}

.rotulo-tipo {
  margin-bottom: 12px;
}

.tipos {
  display: flex;
  gap: 8px;
}

.tipo {
  flex: 1;
  padding: 14px 4px;
  border-radius: var(--raio-lg);
  font-size: 14px;
  font-weight: 700;
  text-align: center;
  background: var(--cartao);
  border: 2px solid var(--borda);
  color: var(--texto-escuro);
  transition: all 0.15s;
}
.tipo:active {
  transform: scale(0.95);
}
.tipo--ativo {
  background: var(--verde-escuro);
  border-color: var(--verde-escuro);
  color: #fff;
}

.privacidade {
  padding: 16px;
}

.aceite {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  cursor: pointer;
}

.caixa {
  width: 20px;
  height: 20px;
  flex-shrink: 0;
  margin-top: 2px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 6px;
  border: 2px solid var(--borda);
  transition: all 0.15s;
}
.caixa--marcada {
  background: var(--verde-escuro);
  border-color: var(--verde-escuro);
}
.aceite:has(input:focus-visible) .caixa {
  outline: 2px solid var(--dourado);
  outline-offset: 2px;
}

.texto-aceite {
  font-size: 12px;
  line-height: 1.6;
  color: var(--texto-suave);
}

.link-aviso {
  font-weight: 700;
  color: var(--verde-escuro);
  text-decoration: underline;
  text-underline-offset: 2px;
}

.aviso-completo {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--borda);
  font-size: 12px;
  line-height: 1.6;
  color: var(--texto-suave);
}
.aviso-completo p + p {
  margin-top: 6px;
}
.aviso-completo a {
  color: var(--verde-escuro);
  font-weight: 700;
}
</style>
