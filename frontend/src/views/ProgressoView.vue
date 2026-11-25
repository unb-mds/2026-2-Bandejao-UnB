<script setup>
import { computed, watch } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useGamificacaoStore } from '@/stores/gamificacao'
import { PATENTES, proximaPatente, rotuloPatente } from '@/constants/patentes'
import BotaoSair from '@/components/BotaoSair.vue'
import BotaoVoltar from '@/components/BotaoVoltar.vue'
import ConviteLogin from '@/components/ConviteLogin.vue'
import NavegacaoInferior from '@/components/NavegacaoInferior.vue'
import RankingAdesaoToggle from '@/components/RankingAdesaoToggle.vue'

const auth = useAuthStore()
const gamificacao = useGamificacaoStore()

const situacao = computed(() => gamificacao.progresso.situacao ?? 'carregando')
const dados = computed(() => gamificacao.progresso.dados)
const patente = computed(() => rotuloPatente(dados.value?.patente))
const proxima = computed(() => proximaPatente(dados.value?.patente))
const pontos = (valor) => `${valor} ${valor === 1 ? 'ponto' : 'pontos'}`

const percentual = computed(() => {
  if (!dados.value || !proxima.value) return 100
  const inicio = PATENTES.find((item) => item.id === dados.value.patente).minimo
  const faixa = proxima.value.minimo - inicio
  const feito = faixa - dados.value.faltaParaProxima
  return Math.min(100, Math.max(0, Math.round((feito / faixa) * 100)))
})

watch(
  () => auth.estaAutenticado,
  (logado) => {
    if (logado) gamificacao.carregarProgresso()
  },
  { immediate: true },
)

function tentarNovamente() {
  gamificacao.carregarProgresso({ forcar: true })
}

function alterarAdesao(participar) {
  gamificacao.alterarAdesao(participar)
}
</script>

<template>
  <div class="tela">
    <header class="cabecalho cabecalho-progresso fundo-escuro">
      <BotaoVoltar class="voltar" :para="{ name: 'raiz' }" />
      <h1 class="titulo-tela">Meu progresso</h1>
      <p v-if="auth.estaAutenticado" class="subtitulo">{{ auth.apelido }}</p>
    </header>

    <main class="conteudo sem-barra corpo pilha-4">
      <ConviteLogin
        v-if="!auth.estaAutenticado"
        titulo="Entre para ver seu progresso"
        texto="Com uma conta, seus check-ins e avaliações rendem pontos e patentes."
      />

      <template v-else>
        <!-- Desktop (FE-23): o cartão de identidade do protótipo. Repete o que a
             patente já diz, então fica fora da árvore de acessibilidade. -->
        <div v-if="situacao === 'carregado'" class="identidade fundo-escuro" aria-hidden="true">
          <span class="identidade-avatar">{{ auth.apelido.charAt(0).toUpperCase() }}</span>
          <div>
            <p class="sobretitulo">Perfil Bandejão</p>
            <p class="identidade-apelido">{{ auth.apelido }}</p>
          </div>
          <span class="identidade-pontos">
            <strong>{{ dados.pontosTotais }}</strong>
            <small>pontos</small>
          </span>
        </div>

        <div class="progresso-patente" aria-live="polite">
          <p v-if="situacao === 'carregando'" class="texto-pequeno estado">Carregando progresso…</p>

          <div
            v-else-if="situacao === 'indisponivel'"
            class="cartao estado"
            data-teste="progresso-indisponivel"
          >
            <p class="estado-titulo">Progresso ainda não disponível</p>
            <p class="texto-pequeno">
              Seus pontos já estão sendo contados e aparecem aqui assim que o progresso entrar no
              ar.
            </p>
          </div>

          <div v-else-if="situacao === 'erro'" class="cartao estado" data-teste="progresso-erro">
            <p class="estado-titulo">Não foi possível carregar seu progresso</p>
            <p class="texto-pequeno">{{ gamificacao.progresso.erro.mensagem }}</p>
            <button type="button" class="botao-pequeno tentar" @click="tentarNovamente">
              Tentar novamente
            </button>
          </div>

          <section
            v-else
            class="cartao patente pilha-3"
            aria-labelledby="titulo-patente"
            data-teste="progresso-patente"
          >
            <p class="rotulo">Sua patente</p>
            <p id="titulo-patente" class="nome-patente">{{ patente }}</p>
            <p class="pontos" data-teste="progresso-pontos">{{ pontos(dados.pontosTotais) }}</p>
            <template v-if="proxima">
              <div
                class="barra"
                role="progressbar"
                :aria-valuenow="percentual"
                aria-valuemin="0"
                aria-valuemax="100"
                :aria-label="`Progresso até ${proxima.rotulo}`"
              >
                <span class="barra-preenchida" :style="{ width: `${percentual}%` }" />
              </div>
              <p class="texto-pequeno falta" data-teste="progresso-falta">
                Faltam {{ pontos(dados.faltaParaProxima) }} para {{ proxima.rotulo }}
              </p>
            </template>
            <p v-else class="texto-pequeno falta" data-teste="progresso-falta">
              Você chegou à patente máxima.
            </p>
          </section>
        </div>

        <RankingAdesaoToggle
          v-if="situacao === 'carregado'"
          :participa="dados.participaRanking"
          :alterando="gamificacao.alterandoAdesao"
          :erro="gamificacao.erroDaAdesao"
          @alterar="alterarAdesao"
        />
      </template>

      <BotaoSair class="sair" />
    </main>

    <NavegacaoInferior />
  </div>
</template>

<style scoped>
.cabecalho-progresso {
  padding-bottom: 20px;
}

.voltar {
  margin-bottom: 16px;
}

.subtitulo {
  margin-top: 4px;
  font-size: 12px;
  color: var(--branco-75);
}

.estado {
  padding: 16px;
}

.estado-titulo {
  font-weight: 800;
  color: var(--texto-escuro);
}

.estado .texto-pequeno {
  margin-top: 4px;
  line-height: 1.6;
  color: var(--texto-suave);
}

.tentar {
  margin-top: 8px;
}

.patente {
  padding: 20px;
}

.rotulo {
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--texto-suave);
}

.nome-patente {
  font-family: var(--fonte-titulo);
  font-size: 24px;
  font-weight: 900;
  color: var(--texto-escuro);
}

.pontos {
  font-size: 15px;
  font-weight: 700;
  color: var(--verde-escuro);
}

.barra {
  height: 10px;
  overflow: hidden;
  border-radius: 999px;
  background: var(--bege-selecionado);
}

.barra-preenchida {
  display: block;
  height: 100%;
  border-radius: 999px;
  background: var(--dourado);
}

.falta {
  color: var(--texto-suave);
}

.sair {
  align-self: flex-start;
}

/* ─── Desktop (FE-23, protótipo desktop) ─────────────────────────────── */
.identidade {
  display: none;
}

@media (min-width: 1024px) {
  .corpo {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 16px;
    align-content: start;
  }
  .corpo > * {
    grid-column: 1 / -1;
    margin-top: 0;
  }
  .corpo > .progresso-patente {
    grid-column: 1;
  }
  .corpo > .progresso-patente + * {
    grid-column: 2;
  }
  .corpo > .sair {
    justify-self: start;
  }

  .identidade {
    display: grid;
    grid-template-columns: auto minmax(0, 1fr) auto;
    align-items: center;
    gap: 22px;
    min-height: 170px;
    padding: 32px;
    border-radius: var(--raio-28);
    color: var(--branco);
    background: var(--verde-escuro);
    box-shadow: 0 18px 40px var(--sombra-escura);
  }
  .identidade-avatar {
    display: grid;
    place-items: center;
    width: 76px;
    height: 76px;
    border-radius: var(--raio-20);
    font: 900 28px var(--fonte-titulo);
    color: var(--branco);
    background: var(--dourado);
    box-shadow: 0 10px 24px var(--sombra-logo-cor);
  }
  .identidade-apelido {
    font: 900 28px / 1.1 var(--fonte-titulo);
    letter-spacing: -0.03em;
  }
  .identidade-pontos {
    display: grid;
    place-content: center;
    width: 96px;
    height: 96px;
    border: 6px solid var(--dourado);
    border-radius: 50%;
    text-align: center;
  }
  .identidade-pontos strong {
    font: 900 24px / 1 var(--fonte-titulo);
  }
  .identidade-pontos small {
    margin-top: 2px;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--branco-60);
  }

  .patente,
  .corpo :deep(.cartao) {
    padding: 28px;
    border-radius: var(--raio-xl);
    box-shadow: 0 8px 22px var(--sombra-cartao-cor);
  }
  .nome-patente {
    font-size: 30px;
    letter-spacing: -0.03em;
  }
}
</style>
