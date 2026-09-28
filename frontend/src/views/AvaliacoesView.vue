<script setup>
import { computed, watch } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useAvaliacoesStore } from '@/stores/avaliacoes'
import { useCardapioStore } from '@/stores/cardapio'
import { usePreferenciasStore } from '@/stores/preferencias'
import { REFEICOES, horaInicio } from '@/constants/refeicoes'
import { diaCurto, diaMes, hojeISO, minutosAgora, minutosDoDia, tempoRelativo } from '@/utils/datas'
import { formatarNota } from '@/utils/cardapio'
import AvaliacaoWidget from '@/components/AvaliacaoWidget.vue'
import BotaoVoltar from '@/components/BotaoVoltar.vue'
import ConviteLogin from '@/components/ConviteLogin.vue'
import EstrelasNota from '@/components/EstrelasNota.vue'
import IconeSvg from '@/components/IconeSvg.vue'
import NavegacaoInferior from '@/components/NavegacaoInferior.vue'

/**
 * Avaliações da refeição selecionada no cardápio (RF15): nota média,
 * quantidade, comentários com apelido e o formulário para quem está logado.
 */
const auth = useAuthStore()
const avaliacoes = useAvaliacoesStore()
const cardapio = useCardapioStore()
const preferencias = usePreferenciasStore()

const campusId = computed(() => preferencias.campusId)
const tipo = computed(() => preferencias.refeicaoSelecionada)
const data = computed(() => preferencias.dataSelecionada)
const alvo = computed(() => ({ campus: campusId.value, data: data.value, refeicao: tipo.value }))
const dados = computed(() => (tipo.value && data.value ? avaliacoes.daRefeicao(alvo.value) : null))

const subtitulo = computed(() => {
  const partes = [preferencias.campus?.nome]
  if (tipo.value && data.value) {
    partes.push(REFEICOES[tipo.value].rotulo, `${diaCurto(data.value)}, ${diaMes(data.value)}`)
  }
  return partes.join(' · ')
})

/** Motivo para não exibir o formulário a um usuário logado (RF15), ou null. */
const motivoIndisponivel = computed(() => {
  if (!tipo.value || !data.value) return null
  const agora = new Date()
  if (data.value !== hojeISO(agora)) return 'Só é possível avaliar refeições do dia de hoje.'
  if (minutosAgora(agora) < minutosDoDia(REFEICOES[tipo.value].inicio)) {
    return `A avaliação do ${REFEICOES[tipo.value].rotuloCurto} abre às ${horaInicio(tipo.value)}, quando a refeição começa.`
  }
  return null
})

watch(
  campusId,
  async (id) => {
    const semana = await cardapio.carregar(id)
    if (semana) preferencias.ajustarSelecao(semana.dias)
  },
  { immediate: true },
)

watch(
  [alvo, () => auth.estaAutenticado],
  () => {
    if (tipo.value && data.value) avaliacoes.carregar(alvo.value)
  },
  { immediate: true },
)
</script>

<template>
  <div class="tela">
    <header class="cabecalho cabecalho-avaliacoes">
      <BotaoVoltar class="voltar" :para="{ name: 'inicio' }" />
      <h1 class="titulo-tela">Avaliações</h1>
      <p class="subtitulo">{{ subtitulo }}</p>
      <div class="resumo">
        <template v-if="dados?.quantidade">
          <EstrelasNota :valor="dados.media" :tamanho="15" />
          <span class="resumo-nota">{{ formatarNota(dados.media) }}</span>
          <span class="resumo-total">{{ dados.quantidade }} avaliações</span>
        </template>
        <span v-else class="resumo-total">{{
          dados ? 'Sem avaliações ainda' : 'Carregando…'
        }}</span>
      </div>
    </header>

    <main class="conteudo sem-barra pilha-4 corpo">
      <template v-if="tipo && data">
        <ConviteLogin
          v-if="!auth.estaAutenticado"
          titulo="Avaliação bloqueada"
          texto="Faça login para avaliar refeições"
        />

        <div v-else-if="motivoIndisponivel" class="cartao indisponivel">
          <div class="indisponivel-icone">
            <IconeSvg nome="relogio" :tamanho="20" cor="var(--texto-suave)" />
          </div>
          <div>
            <p class="indisponivel-titulo">Avaliação indisponível</p>
            <p class="indisponivel-texto">{{ motivoIndisponivel }}</p>
          </div>
        </div>

        <AvaliacaoWidget v-else :alvo="alvo" :minha="dados?.minha ?? null" />
      </template>

      <p
        v-else-if="cardapio.semana(campusId)?.publicado === false"
        class="mensagem mensagem--alerta"
      >
        O cardápio desta semana ainda não foi publicado, então ainda não há refeições para avaliar.
      </p>

      <p v-if="avaliacoes.erro" class="mensagem mensagem--erro" role="alert">
        {{ avaliacoes.erro }}
      </p>

      <h2 class="titulo-secao">Avaliações recentes</h2>

      <p v-if="dados && dados.avaliacoes.length === 0" class="vazio">
        {{
          dados.quantidade
            ? 'Nenhum comentário escrito para esta refeição.'
            : 'Sem avaliações ainda.'
        }}
      </p>

      <article
        v-for="avaliacao in dados?.avaliacoes ?? []"
        :key="avaliacao.id"
        class="cartao comentario"
      >
        <div class="comentario-topo">
          <span class="inicial">{{ avaliacao.apelido.slice(0, 1).toUpperCase() }}</span>
          <span class="apelido">{{ avaliacao.apelido }}</span>
          <EstrelasNota :valor="avaliacao.nota" :tamanho="11" />
          <time class="quando" :datetime="avaliacao.criadaEm">{{
            tempoRelativo(avaliacao.criadaEm)
          }}</time>
        </div>
        <p class="texto">{{ avaliacao.comentario }}</p>
      </article>
    </main>

    <NavegacaoInferior />
  </div>
</template>

<style scoped>
.cabecalho-avaliacoes {
  padding-bottom: 20px;
}

.voltar {
  margin-bottom: 16px;
}

.subtitulo {
  margin-top: 4px;
  font-size: 12px;
  color: var(--branco-40);
}

.resumo {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 16px;
  padding: 12px 16px;
  border-radius: var(--raio-lg);
  background: var(--branco-07);
}

.resumo-nota {
  font-size: 14px;
  font-weight: 700;
  color: #fff;
}

.resumo-total {
  font-size: 12px;
  color: var(--branco-45);
}

.corpo {
  padding: 16px;
}

.indisponivel {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px;
}

.indisponivel-icone {
  width: 44px;
  height: 44px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--raio-md);
  background: var(--bege);
}

.indisponivel-titulo {
  font-size: 14px;
  font-weight: 600;
  color: var(--texto-escuro);
}

.indisponivel-texto {
  margin-top: 2px;
  font-size: 12px;
  color: var(--texto-claro);
}

.vazio {
  font-size: 13px;
  color: var(--texto-claro);
}

.comentario {
  padding: 16px;
}

.comentario-topo {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.inicial {
  width: 28px;
  height: 28px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  font-size: 12px;
  font-weight: 900;
  background: var(--verde-escuro);
  color: #fff;
}

.apelido {
  font-size: 12px;
  font-weight: 700;
  color: var(--texto-escuro);
}

.quando {
  margin-left: auto;
  font-size: 11px;
  color: var(--texto-claro);
}

.texto {
  font-size: 14px;
  line-height: 1.6;
  color: var(--texto-suave);
  overflow-wrap: anywhere;
}
</style>
