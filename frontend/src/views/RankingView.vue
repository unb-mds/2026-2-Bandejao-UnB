<script setup>
import { computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useCardapioStore } from '@/stores/cardapio'
import { useGamificacaoStore } from '@/stores/gamificacao'
import { idDeCampusValido } from '@/constants/campi'
import BotaoVoltar from '@/components/BotaoVoltar.vue'
import LinhaRanking from '@/components/LinhaRanking.vue'
import NavegacaoInferior from '@/components/NavegacaoInferior.vue'
import RankingVazio from '@/components/RankingVazio.vue'
import SeletorCampus from '@/components/SeletorCampus.vue'

/**
 * Ranking do semestre por campus (RF27.2), público: até 10 linhas com
 * posição, apelido e patente, nunca os pontos (RI12). O campus vem da rota
 * `/ranking/:campusId` e troca pelo SeletorCampus, sem mudar o campus
 * lembrado do cardápio. Um id mal formado nem chega à API.
 */
const props = defineProps({
  campusId: { type: String, default: null },
})

const router = useRouter()
const cardapio = useCardapioStore()
const gamificacao = useGamificacaoStore()

const id = computed(() => (props.campusId ? idDeCampusValido(props.campusId) : null))
const situacao = computed(() => (id.value ? gamificacao.situacaoDoRanking(id.value) : null))
const ranking = computed(() => (id.value ? gamificacao.rankingDoCampus(id.value) : null))
const naoEncontrado = computed(
  () => Boolean(props.campusId) && (!id.value || situacao.value === 'nao_encontrado'),
)

const subtitulo = computed(() =>
  [
    id.value ? cardapio.buscarCampus(id.value)?.nome : null,
    ranking.value ? `semestre ${ranking.value.semestre}` : null,
  ]
    .filter(Boolean)
    .join(' · '),
)

// Busca quando o campus muda e também quando o ranking some ou fica
// desatualizado com a tela aberta: o `limpar()` do logout ou de um 401 apaga
// os rankings, e o `invalidarRanking` os marca para buscar de novo.
watch(
  [id, situacao],
  ([valor, atual]) => {
    if (valor && (atual === null || atual === 'desatualizado')) {
      gamificacao.carregarRanking(valor)
    }
  },
  { immediate: true },
)

function escolherCampus(campus) {
  router.push({ name: 'ranking-campus', params: { campusId: String(campus) } })
}

function tentarDeNovo() {
  gamificacao.carregarRanking(id.value, { forcar: true })
}
</script>

<template>
  <div class="tela">
    <header class="cabecalho cabecalho-ranking fundo-escuro">
      <BotaoVoltar class="voltar" :para="{ name: 'inicio' }" />
      <h1 class="titulo-tela">Ranking do semestre</h1>
      <p class="subtitulo">{{ subtitulo || 'Quem mais contribui em cada campus' }}</p>
    </header>

    <main class="conteudo sem-barra pilha-4 corpo">
      <SeletorCampus compacto :selecionado="id" @escolher="escolherCampus" />

      <p v-if="!campusId" class="estado" role="status">Escolha um campus para ver o ranking.</p>

      <div
        v-else-if="naoEncontrado"
        class="cartao estado"
        role="status"
        data-teste="ranking-estado"
      >
        <p class="estado-titulo">Campus não encontrado</p>
        <p>Escolha um dos campi acima.</p>
      </div>

      <template v-else-if="ranking">
        <!-- Uma falha ao atualizar não tira da tela o ranking que já estava lá. -->
        <div
          v-if="situacao === 'erro' || situacao === 'indisponivel'"
          class="mensagem mensagem--alerta aviso"
          role="status"
          data-teste="ranking-aviso"
        >
          <p>Não foi possível atualizar o ranking. {{ gamificacao.erroDoRanking(id) }}</p>
          <button
            type="button"
            class="botao-pequeno"
            data-teste="ranking-tentar-de-novo"
            @click="tentarDeNovo"
          >
            Tentar de novo
          </button>
        </div>

        <RankingVazio v-if="ranking.linhas.length === 0" />

        <template v-else>
          <ol class="pilha-3 lista" data-teste="ranking-lista">
            <LinhaRanking v-for="linha in ranking.linhas" :key="linha.posicao" :linha="linha" />
          </ol>
          <p class="legenda">
            Só aparece quem escolheu participar. Os pontos de cada pessoa não são mostrados.
          </p>
        </template>
      </template>

      <div
        v-else-if="situacao === 'indisponivel'"
        class="cartao estado"
        role="status"
        data-teste="ranking-estado"
      >
        <p>O ranking ainda não está disponível. Tente de novo mais tarde.</p>
      </div>

      <div
        v-else-if="situacao === 'erro'"
        class="cartao estado"
        role="alert"
        data-teste="ranking-estado"
      >
        <p>Não foi possível carregar o ranking. {{ gamificacao.erroDoRanking(id) }}</p>
        <button
          type="button"
          class="botao-pequeno"
          data-teste="ranking-tentar-de-novo"
          @click="tentarDeNovo"
        >
          Tentar de novo
        </button>
      </div>

      <p v-else class="estado" role="status">Carregando ranking…</p>
    </main>

    <NavegacaoInferior />
  </div>
</template>

<style scoped>
.cabecalho-ranking {
  padding-bottom: 20px;
}

.voltar {
  margin-bottom: 16px;
}

.subtitulo {
  margin-top: 4px;
  font-size: 12px;
  color: var(--branco-60);
}

.corpo {
  padding: 16px;
}

.lista {
  padding: 0;
  list-style: none;
}

.estado {
  padding: 20px;
  font-size: 13px;
  line-height: 1.5;
  color: var(--texto-suave);
}

.estado .botao-pequeno {
  margin-top: 10px;
}

.estado-titulo {
  font-family: var(--fonte-titulo);
  font-size: 15px;
  font-weight: 800;
  color: var(--texto-escuro);
}

.aviso .botao-pequeno {
  margin-top: 8px;
}

.legenda {
  font-size: 12px;
  line-height: 1.5;
  text-align: center;
  color: var(--texto-suave);
}

/* Desktop (FE-23): o ranking num cartão, como no protótipo, com as margens da página. */
@media (min-width: 1024px) {
  .corpo {
    padding: 27px clamp(28px, 4vw, 62px) 50px;
  }
  .lista {
    padding: 24px;
    border: 1px solid var(--borda);
    border-radius: var(--raio-xl);
    background: var(--cartao);
    box-shadow: 0 8px 22px var(--sombra-cartao-cor);
  }
}
</style>
