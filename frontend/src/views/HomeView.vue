<script setup>
import { computed, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useAvaliacoesStore } from '@/stores/avaliacoes'
import { useCardapioStore } from '@/stores/cardapio'
import { usePreferenciasStore } from '@/stores/preferencias'
import { REFEICOES, horarioRefeicao } from '@/constants/refeicoes'
import { CANAL_CONTATO } from '@/constants/contato'
import { dataPorExtenso, diaCurto, hojeISO } from '@/utils/datas'
import { formatarNota, refeicaoPadrao, resumoRefeicao } from '@/utils/cardapio'
import AppLogo from '@/components/AppLogo.vue'
import EstrelasNota from '@/components/EstrelasNota.vue'
import IconeSvg from '@/components/IconeSvg.vue'

/** Tela inicial (protótipo): resumo do dia, fila, avaliações e satisfação da semana. */
const router = useRouter()
const auth = useAuthStore()
const avaliacoes = useAvaliacoesStore()
const cardapio = useCardapioStore()
const preferencias = usePreferenciasStore()

const agora = new Date()
const hoje = hojeISO(agora)
const menuAberto = ref(false)

const campusId = computed(() => preferencias.campusId)
const semana = computed(() => cardapio.semana(campusId.value))
const diaHoje = computed(() => semana.value?.dias.find((d) => d.data === hoje) ?? null)
const tipoHoje = computed(() =>
  diaHoje.value
    ? refeicaoPadrao(
        diaHoje.value.refeicoes.map((r) => r.tipo),
        agora,
      )
    : null,
)
const refeicaoHoje = computed(
  () => diaHoje.value?.refeicoes.find((r) => r.tipo === tipoHoje.value) ?? null,
)
const linhasResumo = computed(() =>
  refeicaoHoje.value ? resumoRefeicao(refeicaoHoje.value.categorias) : [],
)
const alvoHoje = computed(() => ({ campus: campusId.value, data: hoje, refeicao: tipoHoje.value }))
const avaliacaoHoje = computed(() =>
  tipoHoje.value ? avaliacoes.daRefeicao(alvoHoje.value) : null,
)

const resumo = computed(() => avaliacoes.resumoPorCampus[campusId.value] ?? null)
const barras = computed(() => {
  const dias = resumo.value?.dias ?? []
  const maior = Math.max(...dias.map((d) => d.media ?? 0))
  return dias.map((d) => ({
    dia: diaCurto(d.data),
    media: d.media,
    altura: d.media ? Math.round((d.media / 5) * 40) : 2,
    destaque: d.media !== null && d.media === maior,
  }))
})

watch(
  campusId,
  async (id) => {
    if (!id) return
    await Promise.all([cardapio.carregar(id), avaliacoes.carregarResumo(id)])
    if (tipoHoje.value) avaliacoes.carregar(alvoHoje.value)
  },
  { immediate: true },
)

function abrirCardapioDeHoje() {
  if (tipoHoje.value) preferencias.selecionar(hoje, tipoHoje.value)
  router.push({ name: 'cardapio' })
}

async function sair() {
  menuAberto.value = false
  await auth.sair()
  avaliacoes.limparCache()
  if (tipoHoje.value) avaliacoes.carregar(alvoHoje.value)
}
</script>

<template>
  <div class="tela">
    <header class="cabecalho cabecalho-inicio">
      <svg
        class="deco"
        width="100%"
        height="100%"
        viewBox="0 0 400 180"
        preserveAspectRatio="xMaxYMin slice"
        aria-hidden="true"
      >
        <path
          d="M350 0 C280 60 180 100 120 180"
          stroke="white"
          stroke-width="1.5"
          stroke-opacity="0.04"
          fill="none"
        />
        <path
          d="M380 20 C310 70 210 110 140 180"
          stroke="white"
          stroke-width="1"
          stroke-opacity="0.03"
          fill="none"
        />
      </svg>

      <div class="topo">
        <div class="marca">
          <AppLogo :tamanho="34" />
          <div>
            <span class="nome">bandejão</span>
            <p class="campus-atual">{{ preferencias.campus?.nome }}</p>
          </div>
        </div>

        <div class="perfil">
          <button
            type="button"
            class="avatar"
            :aria-label="`Perfil de ${auth.apelido}`"
            :aria-expanded="menuAberto"
            @click="menuAberto = !menuAberto"
          >
            {{ auth.apelido.slice(0, 1).toUpperCase() }}
          </button>

          <div v-if="menuAberto" class="menu-fundo" @click="menuAberto = false" />
          <div v-if="menuAberto" class="menu" role="menu">
            <p class="menu-apelido">{{ auth.apelido }}</p>
            <p class="menu-tipo">
              {{
                auth.estaAutenticado
                  ? auth.usuario.tipo === 'estudante'
                    ? 'Estudante'
                    : 'Professor/Servidor'
                  : 'Sem login'
              }}
            </p>
            <RouterLink :to="{ name: 'campus' }" class="menu-item" role="menuitem">
              <IconeSvg nome="mapa" :tamanho="16" /> Trocar campus
            </RouterLink>
            <button
              v-if="auth.estaAutenticado"
              type="button"
              class="menu-item"
              role="menuitem"
              @click="sair"
            >
              <IconeSvg nome="sair" :tamanho="16" /> Sair da conta
            </button>
            <RouterLink v-else :to="{ name: 'login' }" class="menu-item" role="menuitem">
              <IconeSvg nome="usuario" :tamanho="16" /> Entrar na conta
            </RouterLink>
          </div>
        </div>
      </div>

      <p class="data-hoje">{{ dataPorExtenso(agora) }}</p>
      <h1 class="chamada">Comida boa,<br />sem perder tempo.</h1>
    </header>

    <main class="conteudo sem-barra pilha-3 cartoes">
      <!-- Cardápio de hoje -->
      <button type="button" class="cartao cartao-clicavel cartao-hoje" @click="abrirCardapioDeHoje">
        <div class="hoje-topo">
          <div>
            <div class="hoje-etiquetas">
              <span class="etiqueta">Hoje</span>
              <span v-if="tipoHoje" class="horario">
                {{ REFEICOES[tipoHoje].rotulo }} · {{ horarioRefeicao(tipoHoje, '–') }}
              </span>
            </div>
            <p class="hoje-titulo">Cardápio de hoje</p>
          </div>
          <div v-if="avaliacaoHoje?.media" class="hoje-nota">
            <EstrelasNota :valor="avaliacaoHoje.media" :tamanho="12" />
            <span>{{ formatarNota(avaliacaoHoje.media) }}</span>
          </div>
        </div>

        <div v-if="linhasResumo.length" class="hoje-linhas">
          <div v-for="linha in linhasResumo" :key="linha.rotulo" class="hoje-linha">
            <span class="hoje-rotulo">{{ linha.rotulo }}</span>
            <span class="hoje-texto">{{ linha.texto }}</span>
          </div>
        </div>
        <p v-else-if="semana" class="hoje-vazio">
          {{
            semana.publicado
              ? 'Não há refeições servidas hoje neste campus.'
              : 'Cardápio ainda não publicado.'
          }}
        </p>
        <p v-else-if="cardapio.erro" class="hoje-vazio">{{ cardapio.erro }}</p>
        <p v-else class="hoje-vazio">Carregando cardápio…</p>

        <div class="ver-mais">
          <span>{{
            linhasResumo.length ? 'Ver cardápio completo' : 'Ver cardápio da semana'
          }}</span>
          <IconeSvg nome="avancar" :tamanho="14" cor="var(--dourado)" espessura="2.5" />
        </div>
      </button>

      <div class="linha-cartoes">
        <!-- Fila (Release 2) -->
        <RouterLink :to="{ name: 'fila' }" class="cartao cartao-clicavel cartao-pequeno">
          <div class="pequeno-topo">
            <span class="ponto" />
            <span class="rotulo">Fila</span>
          </div>
          <p class="pequeno-valor">Em breve</p>
          <p class="pequeno-legenda">previsão de pico</p>
          <p class="pequeno-rodape pequeno-rodape--suave">Na próxima versão</p>
        </RouterLink>

        <!-- Avaliações -->
        <RouterLink :to="{ name: 'avaliacoes' }" class="cartao cartao-clicavel cartao-pequeno">
          <div class="pequeno-topo">
            <IconeSvg
              nome="estrela"
              :tamanho="10"
              cor="var(--dourado)"
              preenchimento="var(--dourado)"
            />
            <span class="rotulo">Avaliações</span>
          </div>
          <p class="pequeno-valor">{{ formatarNota(resumo?.media) }}</p>
          <p class="pequeno-legenda">
            {{ resumo?.media ? '/ 5 · esta semana' : 'sem avaliações ainda' }}
          </p>
          <div class="pequeno-rodape">
            <EstrelasNota :valor="resumo?.media ?? 0" :tamanho="11" />
          </div>
        </RouterLink>
      </div>

      <!-- Satisfação da semana -->
      <RouterLink :to="{ name: 'avaliacoes' }" class="cartao cartao-clicavel cartao-semana">
        <div class="semana-topo">
          <p class="titulo-secao">Satisfação da semana</p>
          <span class="contagem">{{ resumo?.quantidade ?? 0 }} avaliações</span>
        </div>

        <div class="grafico" role="img" aria-label="Nota média por dia da semana">
          <div v-for="barra in barras" :key="barra.dia" class="barra-coluna">
            <span class="barra-valor">{{ barra.media ? formatarNota(barra.media) : '–' }}</span>
            <div
              class="barra"
              :class="{ 'barra--destaque': barra.destaque }"
              :style="{ height: `${barra.altura}px` }"
            />
            <span class="barra-dia">{{ barra.dia }}</span>
          </div>
        </div>

        <div class="semana-media">
          <EstrelasNota :valor="resumo?.media ?? 0" :tamanho="13" />
          <span class="semana-nota">{{ formatarNota(resumo?.media) }} / 5</span>
          <span class="semana-legenda">média geral</span>
        </div>
      </RouterLink>

      <p class="contato">
        Dúvidas ou reclamações?
        <a :href="CANAL_CONTATO" target="_blank" rel="noopener">Fale com a equipe</a>
      </p>
    </main>
  </div>
</template>

<style scoped>
.cabecalho-inicio {
  position: relative;
  overflow: visible;
  padding: 52px 20px 28px;
}

.deco {
  position: absolute;
  inset: 0;
  pointer-events: none;
}

.topo {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
}

.marca {
  display: flex;
  align-items: center;
  gap: 12px;
}

.nome {
  font-family: var(--fonte-titulo);
  font-weight: 900;
  font-size: 16px;
  letter-spacing: -0.3px;
  color: #fff;
}

.campus-atual {
  font-size: 11px;
  color: var(--branco-40);
}

.perfil {
  position: relative;
}

.avatar {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  font-size: 14px;
  font-weight: 900;
  background: var(--branco-10);
  color: #fff;
}

.menu-fundo {
  position: fixed;
  inset: 0;
  z-index: 10;
}

.menu {
  position: absolute;
  top: 44px;
  right: 0;
  z-index: 11;
  min-width: 200px;
  padding: 12px;
  border-radius: var(--raio-lg);
  background: var(--cartao);
  box-shadow: 0 12px 32px rgba(0, 0, 0, 0.25);
}

.menu-apelido {
  font-family: var(--fonte-titulo);
  font-weight: 900;
  font-size: 15px;
  color: var(--texto-escuro);
}

.menu-tipo {
  margin-bottom: 8px;
  font-size: 11px;
  color: var(--texto-claro);
}

.menu-item {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: 10px 8px;
  border-radius: var(--raio-sm);
  border-top: 1px solid var(--borda);
  font-size: 13px;
  font-weight: 600;
  text-decoration: none;
  color: var(--texto-escuro);
}
.menu-item:active {
  background: var(--bege);
}

.data-hoje {
  position: relative;
  margin-bottom: 4px;
  font-size: 12px;
  color: var(--branco-35);
}

.chamada {
  position: relative;
  font-family: var(--fonte-titulo);
  font-weight: 900;
  font-size: 28px;
  line-height: 1.25;
  letter-spacing: -0.5px;
  color: #fff;
}

.cartoes {
  padding: 20px 16px 24px;
}

.cartao-clicavel {
  display: block;
  text-decoration: none;
  color: inherit;
}

/* Cardápio de hoje */
.cartao-hoje {
  padding: 20px;
}

.hoje-topo {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 8px;
}

.hoje-etiquetas {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.etiqueta {
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 10px;
  font-weight: 900;
  background: var(--verde-escuro);
  color: #fff;
}

.horario {
  font-size: 10px;
  font-weight: 600;
  color: var(--texto-claro);
}

.hoje-titulo {
  font-family: var(--fonte-titulo);
  font-weight: 900;
  font-size: 18px;
  line-height: 1.25;
  color: var(--texto-escuro);
}

.hoje-nota {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  font-weight: 700;
  color: var(--texto-escuro);
}

.hoje-linhas {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--borda);
}
.hoje-linha + .hoje-linha {
  margin-top: 6px;
}

.hoje-linha {
  display: flex;
  gap: 8px;
  font-size: 12px;
}

.hoje-rotulo {
  width: 96px;
  flex-shrink: 0;
  font-weight: 700;
  color: var(--texto-suave);
}

.hoje-texto {
  color: var(--texto-escuro);
}

.hoje-vazio {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--borda);
  font-size: 12px;
  color: var(--texto-suave);
}

.ver-mais {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 6px;
  margin-top: 12px;
  font-size: 12px;
  font-weight: 600;
  color: var(--dourado);
}

/* Fila + Avaliações */
.linha-cartoes {
  display: flex;
  gap: 12px;
}

.cartao-pequeno {
  flex: 1;
  padding: 16px;
}
.cartao-pequeno:active {
  transform: scale(0.97);
}

.pequeno-topo {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}
.pequeno-topo .rotulo {
  letter-spacing: 0.05em;
}

.ponto {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: var(--borda-estrela);
}

.pequeno-valor {
  font-family: var(--fonte-titulo);
  font-weight: 900;
  font-size: 24px;
  line-height: 1;
  color: var(--texto-escuro);
}

.pequeno-legenda {
  margin-top: 4px;
  font-size: 12px;
  color: var(--texto-claro);
}

.pequeno-rodape {
  margin-top: 12px;
  font-size: 12px;
  font-weight: 600;
}
.pequeno-rodape--suave {
  color: var(--dourado);
}

/* Satisfação da semana */
.cartao-semana {
  padding: 20px;
}

.semana-topo {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.contagem {
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
  background: var(--bege);
  color: var(--texto-suave);
}

.grafico {
  display: flex;
  align-items: flex-end;
  gap: 8px;
}

.barra-coluna {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
}

.barra-valor {
  font-size: 9px;
  font-weight: 700;
  color: var(--dourado);
}

.barra {
  width: 100%;
  border-radius: 2px 2px 0 0;
  background: var(--borda);
}
.barra--destaque {
  background: var(--dourado);
}

.barra-dia {
  font-size: 9px;
  color: var(--texto-claro);
}

.semana-media {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 16px;
}

.semana-nota {
  font-size: 14px;
  font-weight: 900;
  color: var(--texto-escuro);
}

.semana-legenda {
  font-size: 12px;
  color: var(--texto-claro);
}

.contato {
  padding-top: 4px;
  font-size: 11px;
  text-align: center;
  color: var(--texto-claro);
}
.contato a {
  font-weight: 700;
  color: var(--texto-suave);
}
</style>
