<script setup>
import { computed, ref, watch } from 'vue'
import { useAvaliacoesStore } from '@/stores/avaliacoes'
import { useCardapioStore } from '@/stores/cardapio'
import { usePreferenciasStore } from '@/stores/preferencias'
import { ORDEM_REFEICOES, REFEICOES, horarioRefeicao } from '@/constants/refeicoes'
import { rotuloDieta } from '@/constants/dietas'
import { rotuloMarcador } from '@/constants/marcadores'
import { diaCurto, diaMes } from '@/utils/datas'
import { filtrarCategorias, formatarNota } from '@/utils/cardapio'
import BotaoVoltar from '@/components/BotaoVoltar.vue'
import EstrelasNota from '@/components/EstrelasNota.vue'
import FiltroCardapio from '@/components/FiltroCardapio.vue'
import IconeSvg from '@/components/IconeSvg.vue'
import NavegacaoInferior from '@/components/NavegacaoInferior.vue'

/**
 * Cardápio da semana vigente (RF05–RF09): um dia e uma refeição por vez,
 * com filtros de dieta e de marcadores. Acessível sem login.
 */
const avaliacoes = useAvaliacoesStore()
const cardapio = useCardapioStore()
const preferencias = usePreferenciasStore()

const filtroAberto = ref(false)
const mostrarTodas = ref(false) // RF09: reverte temporariamente o filtro de dieta

const campusId = computed(() => preferencias.campusId)
const semana = computed(() => cardapio.semana(campusId.value))
const dias = computed(() => semana.value?.dias ?? [])
const diaAtual = computed(
  () => dias.value.find((d) => d.data === preferencias.dataSelecionada) ?? null,
)
const tiposDoDia = computed(() =>
  ORDEM_REFEICOES.filter((tipo) => diaAtual.value?.refeicoes.some((r) => r.tipo === tipo)),
)
const refeicao = computed(
  () => diaAtual.value?.refeicoes.find((r) => r.tipo === preferencias.refeicaoSelecionada) ?? null,
)
const semAlergenos = computed(() => Boolean(refeicao.value?.alergenosIndisponiveis))

const dietaEfetiva = computed(() => (mostrarTodas.value ? 'todos' : preferencias.dieta))
const marcadoresEfetivos = computed(() => (semAlergenos.value ? [] : preferencias.marcadores))
const categorias = computed(() =>
  refeicao.value
    ? filtrarCategorias(refeicao.value.categorias, {
        dieta: dietaEfetiva.value,
        marcadores: marcadoresEfetivos.value,
      })
    : [],
)
const nenhumPrato = computed(() => categorias.value.every((c) => c.pratos.length === 0))

const alvo = computed(() => ({
  campus: campusId.value,
  data: preferencias.dataSelecionada,
  refeicao: preferencias.refeicaoSelecionada,
}))
const notas = computed(() => (refeicao.value ? avaliacoes.daRefeicao(alvo.value) : null))

watch(
  campusId,
  async (id) => {
    const carregada = await cardapio.carregar(id)
    if (carregada) preferencias.ajustarSelecao(carregada.dias)
  },
  { immediate: true },
)

watch(
  alvo,
  (valor) => {
    if (refeicao.value && !avaliacoes.daRefeicao(valor)) avaliacoes.carregar(valor)
  },
  { immediate: true },
)

// Qualquer mudança nos filtros encerra o "mostrar todas".
watch(
  () => [preferencias.dieta, preferencias.marcadores],
  () => (mostrarTodas.value = false),
)

function escolherDia(dia) {
  const tipos = dia.refeicoes.map((r) => r.tipo)
  const tipo = tipos.includes(preferencias.refeicaoSelecionada)
    ? preferencias.refeicaoSelecionada
    : tipos[0]
  preferencias.selecionar(dia.data, tipo)
}

function tentarNovamente() {
  cardapio.carregar(campusId.value, { forcar: true }).then((carregada) => {
    if (carregada) preferencias.ajustarSelecao(carregada.dias)
  })
}
</script>

<template>
  <div class="tela">
    <header class="cabecalho-cardapio">
      <div class="barra-topo">
        <BotaoVoltar :para="{ name: 'inicio' }" />
        <div class="titulo-centro">
          <h1 class="titulo">Cardápio</h1>
          <p class="campus">{{ preferencias.campus?.nome }}</p>
        </div>
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

      <div v-if="dias.length" class="dias sem-barra" role="tablist" aria-label="Dia da semana">
        <button
          v-for="dia in dias"
          :key="dia.data"
          type="button"
          role="tab"
          class="dia"
          :class="{ 'dia--ativo': dia.data === preferencias.dataSelecionada }"
          :aria-selected="dia.data === preferencias.dataSelecionada"
          @click="escolherDia(dia)"
        >
          <span class="dia-semana">{{ diaCurto(dia.data) }}</span>
          <span class="dia-data">{{ diaMes(dia.data) }}</span>
        </button>
      </div>

      <div v-if="tiposDoDia.length" class="refeicoes" role="tablist" aria-label="Refeição">
        <button
          v-for="tipo in tiposDoDia"
          :key="tipo"
          type="button"
          role="tab"
          class="refeicao"
          :class="{ 'refeicao--ativa': tipo === preferencias.refeicaoSelecionada }"
          :aria-selected="tipo === preferencias.refeicaoSelecionada"
          @click="preferencias.selecionar(preferencias.dataSelecionada, tipo)"
        >
          {{ REFEICOES[tipo].rotulo }}
        </button>
      </div>
    </header>

    <RouterLink v-if="refeicao" :to="{ name: 'avaliacoes' }" class="barra-avaliacao">
      <template v-if="notas?.quantidade">
        <EstrelasNota :valor="notas.media" :tamanho="12" />
        <span class="nota">{{ formatarNota(notas.media) }}</span>
        <span class="suave">({{ notas.quantidade }} avaliações)</span>
      </template>
      <span v-else class="suave">Sem avaliações ainda</span>
      <span class="suave horario">{{ horarioRefeicao(preferencias.refeicaoSelecionada) }}</span>
    </RouterLink>

    <main class="conteudo sem-barra corpo">
      <p v-if="cardapio.carregando && !semana" class="estado" role="status">Carregando cardápio…</p>

      <div v-else-if="cardapio.erro && !semana" class="estado">
        <p class="estado-titulo">Não foi possível carregar o cardápio</p>
        <p class="estado-texto">{{ cardapio.erro }}</p>
        <button type="button" class="botao-pequeno tentar" @click="tentarNovamente">
          Tentar novamente
        </button>
      </div>

      <div v-else-if="semana && !semana.publicado" class="estado">
        <IconeSvg
          class="estado-icone"
          nome="talheres"
          :tamanho="40"
          cor="var(--borda)"
          espessura="1.5"
        />
        <p class="estado-titulo">Cardápio ainda não publicado</p>
        <p class="estado-texto">
          O RU de {{ preferencias.campus?.nome }} ainda não publicou o cardápio desta semana.
        </p>
      </div>

      <template v-else-if="refeicao">
        <div
          v-if="preferencias.dieta !== 'todos' || marcadoresEfetivos.length"
          class="filtros-ativos"
        >
          <p v-if="preferencias.dieta !== 'todos'">
            <template v-if="mostrarTodas">Exibindo todas as linhas de prato.</template>
            <template v-else>
              Dieta: <strong>{{ rotuloDieta(preferencias.dieta) }}</strong
              >.
            </template>
            <button type="button" class="alternar-dieta" @click="mostrarTodas = !mostrarTodas">
              {{ mostrarTodas ? `Voltar ao filtro` : 'Mostrar todas' }}
            </button>
          </p>
          <p v-if="marcadoresEfetivos.length">
            Ocultando pratos com: {{ marcadoresEfetivos.map(rotuloMarcador).join(', ') }}.
          </p>
        </div>

        <p v-if="semAlergenos" class="mensagem mensagem--alerta alergenos">
          <strong>Informação de alérgenos indisponível</strong> para esta refeição. O filtro de
          marcadores está desativado.
        </p>

        <div v-if="nenhumPrato" class="estado">
          <IconeSvg
            class="estado-icone"
            nome="proibido"
            :tamanho="40"
            cor="var(--borda)"
            espessura="1.5"
          />
          <p class="estado-titulo">Nenhuma opção encontrada</p>
          <p class="estado-texto">Tente ajustar os filtros</p>
        </div>

        <div v-else class="pilha-5">
          <section v-for="categoria in categorias" :key="categoria.rotulo" class="categoria">
            <h2 class="categoria-titulo">
              <span>{{ categoria.rotulo }}</span>
            </h2>

            <p v-if="categoria.pratos.length === 0" class="sem-opcao">
              Sem opção compatível com o filtro ativo
            </p>
            <ul v-else class="pratos pilha-3">
              <li v-for="prato in categoria.pratos" :key="prato.nome" class="prato">
                <span class="marcador-lista" aria-hidden="true" />
                <div>
                  <p class="prato-nome">{{ prato.nome }}</p>
                  <div v-if="prato.marcadores.length && !semAlergenos" class="contem">
                    <span class="contem-rotulo">Contém:</span>
                    <span v-for="marcador in prato.marcadores" :key="marcador" class="chip">
                      {{ rotuloMarcador(marcador) }}
                    </span>
                  </div>
                </div>
              </li>
            </ul>
          </section>

          <p class="aviso-alteracao">
            Cardápio sujeito a alteração. A ausência de marcador não garante que o prato esteja
            livre do ingrediente.
          </p>
        </div>
      </template>
    </main>

    <NavegacaoInferior />

    <FiltroCardapio v-model:aberto="filtroAberto" :marcadores-indisponiveis="semAlergenos" />
  </div>
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
  padding: 56px 20px 12px;
}

.titulo-centro {
  text-align: center;
}

.titulo {
  font-family: var(--fonte-titulo);
  font-weight: 900;
  font-size: 16px;
  color: #fff;
}

.campus {
  font-size: 11px;
  color: var(--branco-40);
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
  color: #fff;
}

.dias {
  display: flex;
  gap: 8px;
  overflow-x: auto;
  padding: 0 16px 12px;
}

.dia {
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 6px 14px;
  border-radius: var(--raio-md);
  background: var(--branco-08);
  transition: all 0.15s;
}
.dia--ativo {
  background: #fff;
}

.dia-semana {
  font-size: 10px;
  font-weight: 600;
  color: var(--branco-45);
}
.dia--ativo .dia-semana {
  color: var(--texto-suave);
}

.dia-data {
  font-size: 12px;
  font-weight: 900;
  color: var(--branco-75);
}
.dia--ativo .dia-data {
  color: var(--verde-escuro);
}

.refeicoes {
  display: flex;
  border-top: 1px solid var(--branco-08);
}

.refeicao {
  flex: 1;
  padding: 12px 0;
  text-align: center;
  font-size: 12px;
  font-weight: 700;
  border-bottom: 2px solid transparent;
  color: var(--branco-40);
  transition: all 0.15s;
}
.refeicao--ativa {
  border-color: #fff;
  color: #fff;
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
