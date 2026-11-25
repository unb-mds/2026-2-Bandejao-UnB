<script setup>
import { computed, onBeforeUnmount, onMounted, watch } from 'vue'
import { REFEICOES } from '@/constants/refeicoes'
import { useFilaStore } from '@/stores/fila'
import { diaCurto, diaMes, hojeISO } from '@/utils/datas'

// Sem mutação no argumento do defineProps (FE-17): o Stryker envolve os
// valores em chamadas stryMutAct_*/stryCov_*, declaradas no próprio script, e
// o defineProps é içado para fora do setup(), onde não pode usar variáveis
// locais.
// Stryker disable all
const props = defineProps({
  campusId: { type: Number, required: true },
  tipoRefeicao: { type: String, required: true },
  data: { type: String, required: true },
})
// Stryker restore all

const INTERVALO_DE_REVALIDACAO = 60 * 1000

const ROTULOS_DOS_NIVEIS = {
  vazia: 'Vazia',
  curta: 'Curta',
  moderada: 'Moderada',
  longa: 'Longa',
}

const fila = useFilaStore()

const pedido = computed(() => ({
  campus: props.campusId,
  refeicao: props.tipoRefeicao,
  data: props.data,
}))
const estado = computed(() => fila.estadoDaPrevisao(pedido.value))
const situacao = computed(() => estado.value?.situacao ?? 'carregando')
const previsao = computed(() => estado.value?.previsao ?? null)
const mostraPrevisao = computed(
  () => Boolean(previsao.value) && ['carregado', 'carregando'].includes(situacao.value),
)
const faixas = computed(() => (mostraPrevisao.value ? previsao.value.faixas : []))
const picos = computed(() => faixas.value.filter((faixa) => faixa.ehPico))
const podeTentarDeNovo = computed(() => ![400, 404].includes(estado.value?.erro?.status))

const dia = computed(() =>
  props.data === hojeISO() ? 'hoje' : `${diaCurto(props.data).toLowerCase()} ${diaMes(props.data)}`,
)
const titulo = computed(() => `Previsão · ${REFEICOES[props.tipoRefeicao].rotulo}, ${dia.value}`)

function hora(valor) {
  const [h, m] = valor.split(':')
  return m === '00' ? `${Number(h)}h` : `${Number(h)}h${m}`
}

const intervalo = (faixa) => `${hora(faixa.inicio)} às ${hora(faixa.fim)}`

function juntar(itens) {
  if (itens.length < 2) return itens.join('')
  return `${itens.slice(0, -1).join(', ')} e ${itens.at(-1)}`
}

const resumoDoPico = computed(() => {
  const textos = picos.value.map(intervalo)
  return textos.length > 1 ? `Picos previstos: ${juntar(textos)}` : `Pico previsto: ${textos[0]}`
})

watch(pedido, (valor) => fila.carregarPrevisao(valor), { immediate: true })

let revalidacao = null
onMounted(() => {
  revalidacao = setInterval(
    () => fila.carregarPrevisao(pedido.value, { emSegundoPlano: true }),
    INTERVALO_DE_REVALIDACAO,
  )
})
onBeforeUnmount(() => clearInterval(revalidacao))

function tentarNovamente() {
  fila.carregarPrevisao(pedido.value, { forcar: true })
}
</script>

<template>
  <section class="cartao previsao pilha-3" aria-labelledby="titulo-previsao">
    <p id="titulo-previsao" class="titulo-secao pequeno">{{ titulo }}</p>

    <div class="estados" aria-live="polite">
      <p v-if="situacao === 'carregando' && !previsao" class="texto-pequeno estado">
        Carregando previsão…
      </p>

      <div
        v-else-if="situacao === 'indisponivel'"
        class="estado"
        data-teste="previsao-indisponivel"
      >
        <p class="estado-titulo">Previsão fora do ar no momento</p>
        <p class="texto-pequeno">
          Não foi possível calcular a previsão agora. Tente de novo daqui a alguns minutos.
        </p>
      </div>

      <div v-else-if="situacao === 'erro'" class="estado" data-teste="previsao-erro">
        <p class="estado-titulo">Não foi possível carregar a previsão</p>
        <p class="texto-pequeno">{{ estado.erro.mensagem }}</p>
        <button
          v-if="podeTentarDeNovo"
          type="button"
          class="botao-pequeno tentar"
          @click="tentarNovamente"
        >
          Tentar novamente
        </button>
      </div>

      <div
        v-else-if="previsao.status === 'dados_insuficientes'"
        class="estado"
        data-teste="previsao-dados-insuficientes"
      >
        <p class="estado-titulo">Dados insuficientes</p>
        <p class="texto-pequeno">
          A previsão aparece quando houver check-ins em pelo menos 3 dias diferentes nas últimas 4
          semanas, neste dia da semana. Faça check-in quando estiver no RU para ajudar.
        </p>
      </div>

      <p v-else class="resumo-pico" data-teste="previsao-pico">{{ resumoDoPico }}</p>
    </div>

    <ol v-if="faixas.length" class="faixas" aria-label="Nível previsto da fila a cada 15 minutos">
      <li
        v-for="faixa in faixas"
        :key="faixa.inicio"
        class="faixa"
        :class="{ 'faixa--pico': faixa.ehPico }"
        data-teste="previsao-faixa"
      >
        <span class="faixa-hora">{{ intervalo(faixa) }}</span>
        <span class="faixa-inicio" aria-hidden="true">{{ hora(faixa.inicio) }}</span>
        <span class="faixa-barra" :class="`faixa-barra--${faixa.nivel}`" aria-hidden="true" />
        <span class="faixa-nivel">{{ ROTULOS_DOS_NIVEIS[faixa.nivel] }}</span>
        <span class="faixa-pico"><span v-if="faixa.ehPico" class="selo-pico">Pico</span></span>
      </li>
    </ol>
    <!-- No desktop (FE-23) as faixas viram colunas e o nível fica só na cor:
         a legenda diz o que cada cor é. Cada faixa já tem o nível em texto
         para leitores de tela, então a legenda fica fora da árvore. -->
    <ul v-if="faixas.length" class="legenda" aria-hidden="true" data-teste="previsao-legenda">
      <li v-for="(rotulo, nivel) in ROTULOS_DOS_NIVEIS" :key="nivel">
        <span class="legenda-cor" :class="`faixa-barra--${nivel}`" />{{ rotulo }}
      </li>
    </ul>
  </section>
</template>

<style scoped>
.previsao {
  padding: 16px;
}

.pequeno {
  font-size: 14px;
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

.resumo-pico {
  font-size: 13px;
  font-weight: 700;
  color: var(--texto-escuro);
}

.faixas {
  display: grid;
  grid-template-columns: auto minmax(16px, 1fr) auto auto;
  row-gap: 4px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.faixa {
  display: grid;
  grid-column: 1 / -1;
  grid-template-columns: subgrid;
  align-items: center;
  gap: 8px;
  padding: 6px 8px;
  border-radius: var(--raio-sm);
  font-size: 13px;
  color: var(--texto-escuro);
}

.faixa--pico {
  background: var(--bege-selecionado);
  font-weight: 800;
}

.faixa-hora {
  white-space: nowrap;
}

.faixa-barra {
  height: 8px;
  border-radius: 999px;
}
.faixa-barra--vazia {
  background: var(--fila-vazia);
}
.faixa-barra--curta {
  background: var(--fila-curta);
}
.faixa-barra--moderada {
  background: var(--fila-moderada);
}
.faixa-barra--longa {
  background: var(--fila-longa);
}

.faixa-nivel {
  text-align: right;
}

.faixa-pico {
  display: flex;
  justify-content: flex-end;
}

.selo-pico {
  padding: 2px 8px;
  border-radius: 999px;
  background: var(--verde-escuro);
  color: var(--branco);
  font-size: 10px;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

@supports not (grid-template-columns: subgrid) {
  .faixa {
    grid-template-columns: auto minmax(16px, 1fr) auto auto;
  }
}

@media (max-width: 380px) {
  .previsao {
    padding: 12px;
  }

  .faixa {
    gap: 6px;
    padding: 6px;
    font-size: 12px;
  }
}

.faixa-inicio,
.legenda {
  display: none;
}

/* Desktop (FE-23, protótipo desktop): as faixas viram colunas, como o gráfico
   "Movimento" do protótipo. O nível continua escrito em cada faixa, para
   leitores de tela, mas fica fora da vista. */
@media (min-width: 1024px) {
  .previsao {
    padding: 30px;
    border-radius: var(--raio-xl);
  }
  .faixas {
    display: flex;
    align-items: stretch;
    gap: 8px;
    height: 240px;
    margin-top: 18px;
    padding-bottom: 6px;
    border-bottom: 1px solid var(--borda);
  }
  .faixa {
    position: relative;
    display: flex;
    flex: 1 1 0;
    flex-direction: column;
    justify-content: flex-end;
    gap: 6px;
    min-width: 0;
    padding: 0;
    background: transparent;
  }
  .faixa-barra {
    order: 1;
    width: 100%;
    border-radius: 6px 6px 3px 3px;
  }
  .faixa-barra--vazia {
    height: 22%;
  }
  .faixa-barra--curta {
    height: 45%;
  }
  .faixa-barra--moderada {
    height: 70%;
  }
  .faixa-barra--longa {
    height: 92%;
  }
  .faixa-inicio {
    display: block;
    order: 2;
    font-size: 11px;
    font-weight: 600;
    text-align: center;
    white-space: nowrap;
    color: var(--texto-suave);
  }
  .legenda {
    display: flex;
    flex-wrap: wrap;
    gap: 8px 18px;
    margin-top: 14px;
    list-style: none;
    font-size: 12px;
    font-weight: 600;
    color: var(--texto-suave);
  }
  .legenda li {
    display: flex;
    align-items: center;
    gap: 6px;
  }
  .legenda-cor {
    width: 12px;
    height: 12px;
    border-radius: 3px;
  }
  .faixa-hora,
  .faixa-nivel {
    position: absolute;
    width: 1px;
    height: 1px;
    overflow: hidden;
    clip-path: inset(50%);
  }
  .faixa-pico {
    position: absolute;
    top: 0;
    left: 50%;
    transform: translateX(-50%);
  }
}
</style>
