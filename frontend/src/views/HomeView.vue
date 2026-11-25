<script setup>
import { computed, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useAvaliacoesStore } from '@/stores/avaliacoes'
import { useCardapioStore } from '@/stores/cardapio'
import { usePreferenciasStore } from '@/stores/preferencias'
import { REFEICOES, horarioRefeicao } from '@/constants/refeicoes'
import { CANAL_CONTATO } from '@/constants/contato'
import { dataCurta, dataPorExtenso, diaCurto, hojeISO, saudacao } from '@/utils/datas'
import { formatarNota, resumoRefeicao } from '@/utils/cardapio'
import { abrirAvisoLocalizacao } from '@/composables/avisoLocalizacao'
import { AVISO_SAIR_SEM_CONFIRMACAO, useSair } from '@/composables/sair'
import AppLogo from '@/components/AppLogo.vue'
import EstrelasNota from '@/components/EstrelasNota.vue'
import IconeSvg from '@/components/IconeSvg.vue'
import IlustracaoRefeicao from '@/components/IlustracaoRefeicao.vue'

/** Tela inicial (protótipo): resumo do dia, fila, avaliações e satisfação da semana. */
const router = useRouter()
const auth = useAuthStore()
const avaliacoes = useAvaliacoesStore()
const cardapio = useCardapioStore()
cardapio.carregarCampi()
const preferencias = usePreferenciasStore()

const agora = new Date()
const hoje = hojeISO(agora)
const menuAberto = ref(false)
const botaoPerfil = ref(null)
const { semConfirmacao: saidaSemConfirmacao, sair: sairDaConta } = useSair()

const campusId = computed(() => preferencias.campusId)
const nomeDoCampus = computed(() => cardapio.buscarCampus(campusId.value)?.nome)
const pedidoHoje = computed(() => ({ campus: campusId.value, dia: hoje }))
const cardapioHoje = computed(() => cardapio.daRefeicao(pedidoHoje.value))
const erroHoje = computed(() => cardapio.erroDaRefeicao(pedidoHoje.value))
const tipoHoje = computed(() => {
  const resposta = cardapioHoje.value
  const servidoHoje =
    resposta?.status === 'publicado' && !resposta.semServico && resposta.data === hoje
  return servidoHoje ? resposta.refeicao : null
})
const linhasResumo = computed(() =>
  tipoHoje.value ? resumoRefeicao(cardapioHoje.value.categorias) : [],
)
/**
 * Por que o cartão não tem o resumo. A data vem antes do `status`: se hoje não
 * tem serviço, o backend devolve o próximo dia com serviço, e a semana dele
 * pode ainda não ter PDF; isso continua sendo "sem refeições hoje".
 */
const mensagemSemResumo = computed(() => {
  const resposta = cardapioHoje.value
  if (!resposta) return ''
  if (resposta.semServico || resposta.data !== hoje) {
    return 'Não há refeições servidas hoje neste campus.'
  }
  if (resposta.status !== 'publicado') return 'Cardápio ainda não publicado.'
  // Servida hoje, mas sem nenhum prato nas categorias.
  return 'Os pratos desta refeição ainda não foram cadastrados.'
})
const notaHoje = computed(() => {
  if (!tipoHoje.value) return null
  const resumoDoDia = avaliacoes.daResumoDoDia(campusId.value, hoje) ?? []
  return resumoDoDia.find((r) => r.tipo === tipoHoje.value)?.media ?? null
})

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
  (id) => {
    if (!id) return
    cardapio.carregarRefeicao({ campus: id, dia: hoje })
    avaliacoes.carregarResumoDoDia(id, hoje)
    avaliacoes.carregarResumo(id)
  },
  { immediate: true },
)

function abrirCardapioDeHoje() {
  if (tipoHoje.value) preferencias.selecionar(hoje, tipoHoje.value)
  router.push({ name: 'cardapio' })
}

/**
 * Ponto fixo do RF19: abre o aviso de novo, o passo a passo se o navegador
 * bloqueou, a confirmação se já está liberada ou a explicação se não há como
 * usar a localização. O menu fecha ao abrir, então o foco volta ao botão do
 * perfil quando o aviso fecha. A CampusView tem o mesmo ponto fixo no
 * cabeçalho.
 */
async function usarLocalizacao() {
  menuAberto.value = false
  await abrirAvisoLocalizacao()
  botaoPerfil.value?.focus()
}

async function sair() {
  menuAberto.value = false
  await sairDaConta()
}
</script>

<template>
  <div class="tela">
    <header class="cabecalho cabecalho-inicio fundo-escuro">
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
            <p class="campus-atual">{{ cardapio.buscarCampus(preferencias.campusId)?.nome }}</p>
          </div>
        </div>

        <div class="perfil">
          <button
            ref="botaoPerfil"
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
            <RouterLink :to="{ name: 'progresso' }" class="menu-item" role="menuitem">
              <IconeSvg nome="estrela" :tamanho="16" /> Meu progresso
            </RouterLink>
            <RouterLink :to="{ name: 'campus' }" class="menu-item" role="menuitem">
              <IconeSvg nome="mapa" :tamanho="16" /> Trocar campus
            </RouterLink>
            <RouterLink
              :to="{ name: 'ranking-campus', params: { campusId: String(campusId) } }"
              class="menu-item"
              role="menuitem"
            >
              <IconeSvg nome="estrela" :tamanho="16" /> Ranking do campus
            </RouterLink>
            <button type="button" class="menu-item" role="menuitem" @click="usarLocalizacao">
              <IconeSvg nome="local" :tamanho="16" /> Usar minha localização
            </button>
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

      <!-- Desktop (FE-23): no lugar da chamada, a barra do topo do protótipo. -->
      <div class="topo-desktop">
        <div>
          <p class="sobretitulo">
            Restaurante Universitário<template v-if="nomeDoCampus"> · {{ nomeDoCampus }}</template>
          </p>
          <!-- Barra do topo do desktop (FE-23): "Boa tarde, apelido!" e a data curta. -->
          <p class="saudacao">{{ saudacao(agora) }}, {{ auth.apelido }}!</p>
        </div>
        <p class="data-pilula">
          <IconeSvg nome="relogio" :tamanho="17" />
          {{ dataCurta(agora) }}
        </p>
      </div>
    </header>

    <main class="conteudo sem-barra pilha-3 cartoes">
      <p
        v-if="saidaSemConfirmacao"
        class="cartao aviso-sair texto-pequeno"
        role="alert"
        data-teste="sair-aviso"
      >
        {{ AVISO_SAIR_SEM_CONFIRMACAO }}
      </p>

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
          <div v-if="notaHoje" class="hoje-nota">
            <EstrelasNota :valor="notaHoje" :tamanho="12" />
            <span>{{ formatarNota(notaHoje) }}</span>
          </div>
        </div>

        <div v-if="linhasResumo.length" class="hoje-linhas">
          <div v-for="linha in linhasResumo" :key="linha.rotulo" class="hoje-linha">
            <span class="hoje-rotulo">{{ linha.rotulo }}</span>
            <span class="hoje-texto">{{ linha.texto }}</span>
          </div>
        </div>
        <p v-else-if="cardapioHoje" class="hoje-vazio">{{ mensagemSemResumo }}</p>
        <p v-else-if="erroHoje" class="hoje-vazio">{{ erroHoje.mensagem }}</p>
        <p v-else class="hoje-vazio">Carregando cardápio…</p>

        <div class="ver-mais">
          <span>{{
            linhasResumo.length ? 'Ver cardápio completo' : 'Ver cardápio da semana'
          }}</span>
          <IconeSvg nome="avancar" :tamanho="14" cor="var(--dourado)" espessura="2.5" />
        </div>

        <IlustracaoRefeicao v-if="tipoHoje" :refeicao="tipoHoje" grande class="hoje-arte" />
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
        <a :href="CANAL_CONTATO">Fale com a equipe</a>
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

.aviso-sair {
  padding: 12px 16px;
  line-height: 1.6;
  color: var(--erro-texto);
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

/* ─── Desktop (FE-23, protótipo desktop) ─────────────────────────────── */
.topo-desktop,
.hoje-arte {
  display: none;
}

@media (min-width: 1024px) {
  .cabecalho-inicio {
    min-height: 112px;
    padding: 24px clamp(28px, 4vw, 62px);
    color: var(--texto-escuro);
    background: var(--cartao);
    border-bottom: 1px solid var(--borda);
  }

  .cabecalho-inicio .deco,
  .topo,
  .data-hoje {
    display: none;
  }
  /* O h1 da página continua sendo a chamada, fora da vista no desktop. */
  .chamada {
    position: absolute;
    width: 1px;
    height: 1px;
    overflow: hidden;
    clip-path: inset(50%);
    white-space: nowrap;
  }

  .topo-desktop {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 24px;
  }

  /* No desktop o cabeçalho é claro: o rótulo e o foco voltam às cores do bege. */
  .topo-desktop .sobretitulo {
    color: var(--texto-rotulo);
  }
  .cabecalho-inicio :focus-visible {
    outline-color: var(--verde-escuro);
  }

  .saudacao {
    font: 900 clamp(28px, 2.5vw, 37px) / 1 var(--fonte-titulo);
    letter-spacing: -0.045em;
    color: var(--verde-escuro);
  }

  .data-pilula {
    display: flex;
    align-items: center;
    gap: 8px;
    min-height: 40px;
    padding: 0 13px;
    border: 1px solid var(--borda);
    border-radius: 11px;
    font-size: 12px;
    font-weight: 700;
    color: var(--texto-suave);
    background: var(--cartao);
    box-shadow: 0 4px 14px var(--sombra-cartao);
  }

  .cartoes {
    display: grid;
    grid-template-columns: minmax(0, 1.65fr) minmax(0, 1fr) minmax(0, 1fr);
    gap: 16px;
    align-content: start;
    padding: 27px clamp(28px, 4vw, 62px) 50px;
  }
  .cartoes > * + * {
    margin-top: 0;
  }
  .aviso-sair,
  .contato {
    grid-column: 1 / -1;
  }

  .cartao {
    border-radius: var(--raio-xl);
    box-shadow: 0 8px 22px var(--sombra-cartao);
  }

  /* Cardápio de hoje: o cartão verde grande, com a ilustração da refeição. */
  .cartao-hoje {
    position: relative;
    grid-row: span 2;
    display: grid;
    grid-template-columns: minmax(0, 1fr) minmax(0, 0.9fr);
    grid-template-rows: auto auto 1fr auto;
    column-gap: 12px;
    min-height: 408px;
    overflow: hidden;
    padding: 32px;
    border: 0;
    text-align: left;
    color: #fff;
    background: var(--verde-escuro);
  }
  .cartao-hoje::before {
    content: '';
    position: absolute;
    width: 420px;
    height: 420px;
    right: -170px;
    top: -170px;
    border-radius: 50%;
    border: 1px solid var(--branco-05);
    box-shadow: 0 0 0 70px var(--branco-02);
    pointer-events: none;
  }
  .hoje-topo,
  .hoje-linhas,
  .hoje-vazio,
  .ver-mais {
    position: relative;
    grid-column: 1;
  }
  .hoje-topo {
    flex-direction: column;
    gap: 22px;
  }
  .cartao-hoje .etiqueta {
    color: var(--verde-escuro);
    background: var(--dourado-claro);
  }
  .cartao-hoje .horario,
  .cartao-hoje .hoje-rotulo,
  .cartao-hoje .hoje-vazio {
    color: var(--branco-60);
  }
  .cartao-hoje .hoje-titulo {
    font-size: clamp(28px, 2.6vw, 38px);
    line-height: 1.02;
    letter-spacing: -0.045em;
    color: #fff;
  }
  .cartao-hoje .hoje-nota span {
    color: #fff;
  }
  .cartao-hoje .hoje-linhas {
    border-top: 0;
    margin-top: 18px;
    padding-top: 0;
  }
  .cartao-hoje .hoje-texto {
    color: var(--branco-75);
  }
  .cartao-hoje .ver-mais {
    align-self: end;
    justify-content: flex-start;
    color: var(--dourado-claro);
  }
  .hoje-arte {
    grid-column: 2;
    grid-row: 1 / -1;
    align-self: center;
  }
  /* Abaixo de 1280 px, a ilustração ficaria por cima do nome dos pratos. */
  @media (min-width: 1280px) {
    .hoje-arte {
      display: grid;
    }
  }

  .linha-cartoes {
    display: contents;
  }
  .cartao-pequeno {
    padding: 24px;
  }
  .cartao-semana {
    grid-column: 2 / 4;
  }
}
</style>
