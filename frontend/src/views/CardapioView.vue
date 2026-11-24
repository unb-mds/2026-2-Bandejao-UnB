<script setup>
import { computed, ref, watch } from 'vue'
import { useAvaliacoesStore } from '@/stores/avaliacoes'
import { useCardapioStore } from '@/stores/cardapio'
import { usePreferenciasStore } from '@/stores/preferencias'
import { ORDEM_REFEICOES, horarioRefeicao } from '@/constants/refeicoes'
import { DIETA_PADRAO, rotuloDieta } from '@/constants/dietas'
import { rotuloMarcador } from '@/constants/marcadores'
import { diasDaSemanaVigente, formatarNota } from '@/utils/cardapio'
import AbasSemana from '@/components/AbasSemana.vue'
import EstrelasNota from '@/components/EstrelasNota.vue'
import FiltroCardapio from '@/components/FiltroCardapio.vue'
import IconeSvg from '@/components/IconeSvg.vue'
import SeletorRefeicao from '@/components/SeletorRefeicao.vue'

/**
 * Seção do cardápio da CampusView (RF05–RF09): um dia e uma refeição por vez,
 * já filtrados pela API (ADR 0005). Acessível sem login.
 */
const props = defineProps({
  campusId: { type: Number, required: true },
})

const avaliacoes = useAvaliacoesStore()
const cardapio = useCardapioStore()
const preferencias = usePreferenciasStore()

const filtroAberto = ref(false)
const mostrarTodas = ref(false)
const dias = diasDaSemanaVigente()

if (preferencias.dataSelecionada && !dias.includes(preferencias.dataSelecionada)) {
  preferencias.selecionar(null, null)
}

const pedido = computed(() => ({
  campus: props.campusId,
  dia: preferencias.dataSelecionada,
  refeicao: preferencias.refeicaoSelecionada,
  marcadores: preferencias.marcadores,
  dieta: mostrarTodas.value ? DIETA_PADRAO : preferencias.dieta,
}))
const atual = computed(() => cardapio.daRefeicao(pedido.value))
const erroAtual = computed(() => cardapio.erroDaRefeicao(pedido.value))
const semServico = computed(
  () =>
    atual.value?.semServico === true ||
    Boolean(pedido.value.dia && atual.value && atual.value.data !== pedido.value.dia),
)
const comDieta = computed(() => pedido.value.dieta !== DIETA_PADRAO)
const podeLimparFiltros = computed(
  () => erroAtual.value?.codigo === 'parametros_invalidos' && preferencias.filtrosAtivos > 0,
)
const podeTentarDeNovo = computed(() => erroAtual.value?.codigo !== 'parametros_invalidos')
const diaExibido = computed(() =>
  semServico.value ? pedido.value.dia : (atual.value?.data ?? preferencias.dataSelecionada),
)
const resumo = computed(() =>
  diaExibido.value ? avaliacoes.daResumoDoDia(props.campusId, diaExibido.value) : null,
)
const refeicoesDoDia = computed(() => {
  if (semServico.value || atual.value?.status !== 'publicado') return []
  if (resumo.value?.length) return resumo.value
  return ORDEM_REFEICOES.map((tipo) => ({ tipo, media: null }))
})
const notaAtual = computed(
  () => resumo.value?.find((r) => r.tipo === atual.value?.refeicao) ?? null,
)
const marcadoresAtivos = computed(() =>
  atual.value?.filtroMarcadorDesativado ? [] : preferencias.marcadores,
)

async function carregar(valor, opcoes) {
  const resposta = await cardapio.carregarRefeicao(valor, opcoes)
  const aindaAtual = valor.campus === props.campusId && valor.dia === preferencias.dataSelecionada
  const mesmoDia = !valor.dia || resposta?.data === valor.dia
  if (resposta && aindaAtual && mesmoDia && (!valor.dia || !valor.refeicao)) {
    preferencias.selecionar(resposta.data, resposta.refeicao)
  }
}

watch(pedido, (valor) => carregar(valor), { immediate: true, deep: true })

watch(
  () => [props.campusId, diaExibido.value],
  ([campus, dia]) => {
    if (dia && [null, 'erro'].includes(avaliacoes.situacaoDoResumoDoDia(campus, dia))) {
      avaliacoes.carregarResumoDoDia(campus, dia)
    }
  },
  { immediate: true },
)

watch(
  () => props.campusId,
  () => preferencias.selecionar(null, null),
  { flush: 'sync' },
)

watch(
  () => [preferencias.dieta, preferencias.marcadores],
  () => (mostrarTodas.value = false),
)

function escolherDia(dia) {
  preferencias.selecionar(dia, null)
}

function escolherRefeicao(tipo) {
  preferencias.selecionar(diaExibido.value, tipo)
}

function tentarNovamente() {
  carregar(pedido.value, { forcar: true })
}

function limparFiltros() {
  preferencias.aplicarFiltros(DIETA_PADRAO, [])
}
</script>

<template>
  <section class="secao-cardapio" aria-labelledby="titulo-cardapio">
    <div class="cabecalho-cardapio fundo-escuro">
      <div class="barra-topo">
        <h2 id="titulo-cardapio" class="titulo">Cardápio</h2>
        <button
          type="button"
          class="botao-filtro"
          aria-label="Filtros alimentares"
          @click="filtroAberto = true"
        >
          <IconeSvg nome="filtro" cor="var(--branco-65)" espessura="2.2" />
          <span v-if="preferencias.filtrosAtivos > 0" class="contador-filtros">
            {{ preferencias.filtrosAtivos }}
          </span>
        </button>
      </div>

      <AbasSemana :dias="dias" :selecionado="diaExibido" @escolher="escolherDia" />

      <SeletorRefeicao
        v-if="refeicoesDoDia.length"
        :refeicoes="refeicoesDoDia"
        :selecionada="atual?.refeicao ?? preferencias.refeicaoSelecionada"
        @escolher="escolherRefeicao"
      />
    </div>

    <RouterLink
      v-if="atual?.status === 'publicado' && !semServico"
      :to="{ name: 'avaliacoes' }"
      class="barra-avaliacao"
    >
      <template v-if="notaAtual?.quantidade">
        <EstrelasNota :valor="notaAtual.media" :tamanho="12" />
        <span class="nota">{{ formatarNota(notaAtual.media) }}</span>
        <span class="suave">({{ notaAtual.quantidade }} avaliações)</span>
      </template>
      <span v-else class="suave">Sem avaliações ainda</span>
      <span class="suave horario">{{ horarioRefeicao(atual.refeicao) }}</span>
    </RouterLink>

    <div class="corpo">
      <p v-if="!atual && cardapio.estaCarregandoRefeicao(pedido)" class="estado" role="status">
        Carregando cardápio…
      </p>

      <div v-else-if="!atual && erroAtual" class="estado">
        <p class="estado-titulo">Não foi possível carregar o cardápio</p>
        <p class="estado-texto">{{ erroAtual.mensagem }}</p>
        <button
          v-if="podeLimparFiltros"
          type="button"
          class="botao-pequeno tentar"
          data-teste="limpar-filtros"
          @click="limparFiltros"
        >
          Limpar filtros
        </button>
        <button
          v-else-if="podeTentarDeNovo"
          type="button"
          class="botao-pequeno tentar"
          @click="tentarNovamente"
        >
          Tentar novamente
        </button>
      </div>

      <div v-else-if="semServico" class="estado">
        <IconeSvg
          class="estado-icone"
          nome="talheres"
          :tamanho="40"
          cor="var(--borda)"
          espessura="1.5"
        />
        <p class="estado-titulo">Sem refeições neste dia</p>
        <p class="estado-texto">O RU deste campus não abre neste dia.</p>
      </div>

      <div v-else-if="atual?.status === 'nao_publicado'" class="estado">
        <IconeSvg
          class="estado-icone"
          nome="talheres"
          :tamanho="40"
          cor="var(--borda)"
          espessura="1.5"
        />
        <p class="estado-titulo">Cardápio ainda não publicado</p>
        <p class="estado-texto">O RU deste campus ainda não publicou o cardápio deste dia.</p>
      </div>

      <template v-else-if="atual">
        <div
          v-if="preferencias.dieta !== DIETA_PADRAO || marcadoresAtivos.length"
          class="filtros-ativos"
        >
          <p v-if="preferencias.dieta !== DIETA_PADRAO">
            <template v-if="mostrarTodas">Exibindo todas as linhas de prato.</template>
            <template v-else>
              Dieta: <strong>{{ rotuloDieta(preferencias.dieta) }}</strong
              >.
            </template>
            <button type="button" class="alternar-dieta" @click="mostrarTodas = !mostrarTodas">
              {{ mostrarTodas ? 'Voltar ao filtro' : 'Mostrar todas' }}
            </button>
          </p>
          <p v-if="marcadoresAtivos.length">
            Evitando: {{ marcadoresAtivos.map(rotuloMarcador).join(', ') }}.
          </p>
        </div>

        <p
          v-if="atual.filtroMarcadorDesativado"
          class="mensagem mensagem--alerta alergenos"
          data-teste="filtro-desativado"
        >
          <strong>Informação de alérgenos indisponível</strong> para esta refeição. O filtro de
          marcadores está desativado.
        </p>

        <div v-if="!atual.categorias.length" class="estado">
          <IconeSvg
            class="estado-icone"
            nome="proibido"
            :tamanho="40"
            cor="var(--borda)"
            espessura="1.5"
          />
          <template v-if="comDieta">
            <p class="estado-titulo">Nenhuma opção encontrada</p>
            <p class="estado-texto">Tente ajustar os filtros</p>
          </template>
          <template v-else>
            <p class="estado-titulo">Refeição não servida</p>
            <p class="estado-texto">Esta refeição não é servida neste dia.</p>
          </template>
        </div>

        <div v-else class="pilha-5">
          <section v-for="categoria in atual.categorias" :key="categoria.nome" class="categoria">
            <h3 class="categoria-titulo">
              <span>{{ categoria.nome }}</span>
            </h3>

            <p v-if="categoria.semOpcaoCompativel" class="sem-opcao">
              Sem opção compatível com o filtro ativo
            </p>
            <ul class="pratos pilha-3">
              <li
                v-for="prato in categoria.pratos"
                :key="prato.descricao"
                class="prato"
                :class="{ 'prato--alerta': prato.contemMarcadorSelecionado }"
              >
                <span class="marcador-lista" aria-hidden="true" />
                <div>
                  <p class="prato-nome">{{ prato.descricao }}</p>
                  <div
                    v-if="prato.marcadores.length && !atual.filtroMarcadorDesativado"
                    class="contem"
                  >
                    <span class="contem-rotulo">Contém:</span>
                    <span v-for="marcador in prato.marcadores" :key="marcador" class="chip">
                      {{ rotuloMarcador(marcador) }}
                    </span>
                  </div>
                </div>
              </li>
            </ul>
          </section>

          <p class="aviso-alteracao">{{ atual.avisoSujeitoAAlteracao }}</p>
        </div>
      </template>
    </div>

    <FiltroCardapio
      v-model:aberto="filtroAberto"
      :marcadores-indisponiveis="Boolean(atual?.filtroMarcadorDesativado)"
    />
  </section>
</template>

<style scoped>
.cabecalho-cardapio {
  flex-shrink: 0;
  background: var(--verde-escuro);
}

.barra-topo {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px 12px;
}

.titulo {
  font-family: var(--fonte-titulo);
  font-weight: 900;
  font-size: 16px;
  color: var(--branco);
}

.botao-filtro {
  position: relative;
  transition: opacity 0.15s;
}
.botao-filtro:active {
  opacity: 0.6;
}

.contador-filtros {
  position: absolute;
  top: -4px;
  right: -4px;
  width: 16px;
  height: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  font-size: 9px;
  font-weight: 900;
  background: var(--dourado);
  color: var(--branco);
}

.barra-avaliacao {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 20px;
  font-size: 12px;
  text-decoration: none;
  background: var(--bege);
  border-bottom: 1px solid var(--borda);
}

.nota {
  font-weight: 700;
  color: var(--texto-escuro);
}

.suave {
  color: var(--texto-claro);
}

.horario {
  margin-left: auto;
}

.corpo {
  padding: 20px;
}

.estado {
  padding-top: 56px;
  text-align: center;
}

.estado-icone {
  margin: 0 auto 12px;
}

.estado-titulo {
  font-family: var(--fonte-titulo);
  font-weight: 700;
  font-size: 16px;
  color: var(--texto-escuro);
}

.estado-texto {
  margin-top: 4px;
  font-size: 14px;
  color: var(--texto-claro);
}

.tentar {
  margin-top: 16px;
}

.filtros-ativos {
  margin-bottom: 16px;
  padding: 10px 14px;
  border-radius: var(--raio-md);
  font-size: 12px;
  line-height: 1.6;
  background: var(--bege-selecionado);
  border: 1px solid var(--borda);
  color: var(--texto-suave);
}

.alternar-dieta {
  margin-left: 4px;
  font-weight: 700;
  color: var(--dourado);
  text-decoration: underline;
  text-underline-offset: 2px;
}

.alergenos {
  margin-bottom: 16px;
}

.categoria-titulo {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;
  font-size: 10px;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--dourado);
}
.categoria-titulo::after {
  content: '';
  flex: 1;
  height: 1px;
  background: var(--borda);
}

.sem-opcao {
  padding-left: 4px;
  font-size: 12px;
  font-style: italic;
  color: var(--texto-claro);
}

.pratos {
  list-style: none;
}

.prato {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding-left: 4px;
}

.marcador-lista {
  width: 6px;
  height: 6px;
  flex-shrink: 0;
  margin-top: 7px;
  border-radius: 50%;
  background: var(--verde-medio);
}

.prato--alerta .prato-nome {
  font-weight: 700;
}

.prato-nome {
  font-size: 14px;
  color: var(--texto-escuro);
}

.contem {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 4px;
  margin-top: 6px;
}

.contem-rotulo {
  font-size: 10px;
  font-weight: 700;
  color: var(--texto-suave);
}

.chip {
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 10px;
  font-weight: 600;
  background: var(--bege-claro);
  border: 1px solid var(--borda);
  color: var(--texto-suave);
}

.aviso-alteracao {
  padding: 8px 0 4px;
  font-size: 11px;
  line-height: 1.6;
  text-align: center;
  color: var(--texto-claro);
}
</style>
