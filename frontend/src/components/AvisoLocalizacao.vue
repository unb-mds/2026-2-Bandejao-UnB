<script setup>
import { nextTick, onMounted, ref, watch } from 'vue'
import { usePreferenciasStore } from '@/stores/preferencias'
import { consultarPermissao, pedirPermissao } from '@/services/permissaoLocalizacao'
import { aberturasDoAvisoLocalizacao } from '@/composables/avisoLocalizacao'
import IconeSvg from './IconeSvg.vue'

/**
 * Aviso de localização em duas etapas (RF19, front 3a.1): primeiro o aviso
 * do Bandejão; se a pessoa escolhe "Permitir", o pedido do navegador.
 *
 * - Aparece sozinho só no primeiro acesso: sem permissão decidida no
 *   navegador e sem "Agora não" guardado na preferenciasStore.
 * - "Usar minha localização" (abrirAvisoLocalizacao) abre de novo a
 *   qualquer momento, ou vai direto ao passo a passo se o navegador já
 *   bloqueou.
 * - Emite `permitido` quando a permissão está concedida, para quem for
 *   detectar o campus.
 */
const emit = defineEmits(['permitido'])

const preferencias = usePreferenciasStore()

/** null (fechado) | 'aviso' | 'navegador' | 'bloqueado' */
const etapa = ref(null)
const titulo = ref(null)

async function mostrar(novaEtapa) {
  etapa.value = novaEtapa
  await nextTick()
  titulo.value?.focus()
}

function fechar() {
  etapa.value = null
}

function concluirPermitido() {
  fechar()
  emit('permitido')
}

async function abrir({ primeiroAcesso }) {
  const permissao = await consultarPermissao()
  if (permissao === 'concedida') return concluirPermitido()
  if (permissao === 'indisponivel') return
  if (primeiroAcesso) {
    if (permissao === 'pendente' && !preferencias.avisoLocalizacaoAdiado) mostrar('aviso')
    return
  }
  mostrar(permissao === 'negada' ? 'bloqueado' : 'aviso')
}

function agoraNao() {
  preferencias.adiarAvisoLocalizacao()
  fechar()
}

async function permitir() {
  etapa.value = 'navegador'
  const resultado = await pedirPermissao()
  if (resultado === 'concedida') concluirPermitido()
  else if (resultado === 'negada') mostrar('bloqueado')
  else fechar()
}

async function jaLiberei() {
  if ((await consultarPermissao()) === 'concedida') concluirPermitido()
}

onMounted(() => abrir({ primeiroAcesso: true }))
watch(aberturasDoAvisoLocalizacao, (vezes) => {
  if (vezes > 0) abrir({ primeiroAcesso: false })
})
</script>

<template>
  <div v-if="etapa" class="fundo" @keydown.esc="etapa !== 'navegador' && fechar()">
    <section
      class="painel"
      role="dialog"
      aria-modal="true"
      aria-labelledby="aviso-localizacao-titulo"
      aria-describedby="aviso-localizacao-texto"
    >
      <div class="icone-caixa" :class="{ 'icone-caixa--alerta': etapa === 'bloqueado' }">
        <IconeSvg
          :nome="etapa === 'bloqueado' ? 'proibido' : 'local'"
          :tamanho="24"
          :cor="etapa === 'bloqueado' ? 'var(--alerta-texto)' : 'var(--verde-escuro)'"
        />
      </div>

      <template v-if="etapa === 'aviso' || etapa === 'navegador'">
        <h2 id="aviso-localizacao-titulo" ref="titulo" tabindex="-1" class="titulo">
          Usar sua localização?
        </h2>
        <div id="aviso-localizacao-texto" class="texto pilha-3">
          <p>
            <strong>Para achar seu campus:</strong> o Bandejão abre direto no RU mais perto. As
            coordenadas não saem do aparelho.
          </p>
          <p>
            <strong>Para o check-in:</strong> confirma que você está no RU. As coordenadas são
            conferidas e descartadas na hora.
          </p>
          <p class="nota">
            Sem a localização, o cardápio, as avaliações e a fila continuam abertos.
          </p>
        </div>

        <p v-if="etapa === 'navegador'" class="mensagem mensagem--alerta" role="status">
          Agora é com o navegador: responda ao pedido que apareceu na tela.
        </p>

        <div class="acoes">
          <button
            type="button"
            class="botao botao--primario"
            :disabled="etapa === 'navegador'"
            @click="permitir"
          >
            Permitir
          </button>
          <button
            type="button"
            class="botao botao--contorno"
            :disabled="etapa === 'navegador'"
            @click="agoraNao"
          >
            Agora não
          </button>
        </div>
      </template>

      <template v-else>
        <h2 id="aviso-localizacao-titulo" ref="titulo" tabindex="-1" class="titulo">
          A localização está bloqueada
        </h2>
        <p id="aviso-localizacao-texto" class="texto">
          O navegador não deixa mais o Bandejão perguntar. Para liberar:
        </p>
        <ol class="passos">
          <li>
            Toque no ícone ao lado do endereço do site (cadeado ou <em>aA</em>) ou abra as
            configurações do app instalado.
          </li>
          <li>Abra <strong>Permissões</strong> ou <strong>Configurações do site</strong>.</li>
          <li>Em <strong>Localização</strong>, escolha <strong>Permitir</strong>.</li>
          <li>
            No iPhone, confira também
            <strong>Ajustes › Privacidade › Serviços de Localização</strong>.
          </li>
        </ol>

        <div class="acoes">
          <button type="button" class="botao botao--primario" @click="jaLiberei">Já liberei</button>
          <button type="button" class="botao botao--contorno" @click="fechar">Fechar</button>
        </div>
      </template>
    </section>
  </div>
</template>

<style scoped>
.fundo {
  position: absolute;
  inset: 0;
  z-index: 50;
  display: flex;
  align-items: flex-end;
  background: rgba(10, 26, 12, 0.55);
}

.painel {
  width: 100%;
  max-height: 100%;
  overflow-y: auto;
  padding: 28px 20px 24px;
  border-radius: var(--raio-lg) var(--raio-lg) 0 0;
  background: var(--cartao);
  font-family: var(--fonte-texto);
}

.icone-caixa {
  width: 48px;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--raio-md);
  background: var(--bege);
}

.icone-caixa--alerta {
  background: var(--alerta-fundo);
}

.titulo {
  margin-top: 16px;
  font-family: var(--fonte-titulo);
  font-weight: 900;
  font-size: 20px;
  color: var(--texto-escuro);
  outline: none;
}

.texto {
  margin-top: 12px;
  font-size: 14px;
  line-height: 1.5;
  color: var(--texto-suave);
}

.texto strong {
  color: var(--texto-escuro);
}

.nota {
  font-size: 12px;
  color: var(--texto-claro);
}

.passos {
  margin-top: 12px;
  padding-left: 20px;
  font-size: 14px;
  line-height: 1.5;
  color: var(--texto-suave);
}

.passos li + li {
  margin-top: 8px;
}

.passos strong {
  color: var(--texto-escuro);
}

.mensagem {
  margin-top: 16px;
}

.acoes {
  margin-top: 24px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
</style>
