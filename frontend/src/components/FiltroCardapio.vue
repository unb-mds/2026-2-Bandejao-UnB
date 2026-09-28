<script setup>
import { ref, watch } from 'vue'
import { usePreferenciasStore } from '@/stores/preferencias'
import { DIETAS } from '@/constants/dietas'
import { MARCADORES } from '@/constants/marcadores'
import IconeSvg from './IconeSvg.vue'

/**
 * Gaveta "Filtros alimentares" (RF08 marcadores, RF09 dieta). As escolhas
 * só valem ao tocar em "Aplicar" e ficam lembradas no aparelho.
 */
const props = defineProps({
  /** Refeição sem informação de alérgenos (RF06): filtro de marcadores desativado. */
  marcadoresIndisponiveis: { type: Boolean, default: false },
})

const aberto = defineModel('aberto', { type: Boolean, default: false })
const preferencias = usePreferenciasStore()

const dietaPendente = ref(preferencias.dieta)
const marcadoresPendentes = ref([...preferencias.marcadores])

watch(aberto, (abrindo) => {
  if (!abrindo) return
  dietaPendente.value = preferencias.dieta
  marcadoresPendentes.value = [...preferencias.marcadores]
})

function alternarMarcador(id) {
  if (props.marcadoresIndisponiveis) return
  const lista = marcadoresPendentes.value
  marcadoresPendentes.value = lista.includes(id) ? lista.filter((m) => m !== id) : [...lista, id]
}

function limpar() {
  dietaPendente.value = 'todos'
  marcadoresPendentes.value = []
}

function aplicar() {
  preferencias.aplicarFiltros(dietaPendente.value, marcadoresPendentes.value)
  aberto.value = false
}
</script>

<template>
  <Transition name="gaveta">
    <div v-if="aberto" class="sobreposicao" @keydown.esc="aberto = false">
      <div class="fundo" @click="aberto = false" />
      <section
        class="gaveta sem-barra"
        role="dialog"
        aria-modal="true"
        aria-labelledby="titulo-filtros"
      >
        <div class="alca" />
        <h2 id="titulo-filtros" class="titulo">Filtros alimentares</h2>

        <p class="rotulo rotulo-grupo">Dieta</p>
        <div class="dietas">
          <button
            v-for="dieta in DIETAS"
            :key="dieta.id"
            type="button"
            class="opcao-dieta"
            :class="{ 'opcao-dieta--ativa': dietaPendente === dieta.id }"
            :aria-pressed="dietaPendente === dieta.id"
            @click="dietaPendente = dieta.id"
          >
            {{ dieta.rotulo }}
          </button>
        </div>

        <p class="rotulo rotulo-grupo">Evitar marcadores</p>
        <p v-if="marcadoresIndisponiveis" class="mensagem mensagem--alerta indisponivel">
          Informação de alérgenos indisponível para esta refeição: não foi possível ler os
          marcadores do cardápio oficial, por isso este filtro está desativado.
        </p>
        <div class="marcadores" :class="{ 'marcadores--desativados': marcadoresIndisponiveis }">
          <button
            v-for="marcador in MARCADORES"
            :key="marcador.id"
            type="button"
            class="opcao-marcador"
            :class="{ 'opcao-marcador--ativa': marcadoresPendentes.includes(marcador.id) }"
            :aria-pressed="marcadoresPendentes.includes(marcador.id)"
            :disabled="marcadoresIndisponiveis"
            @click="alternarMarcador(marcador.id)"
          >
            <span class="bolinha">
              <IconeSvg
                v-if="marcadoresPendentes.includes(marcador.id)"
                nome="check"
                :tamanho="8"
                cor="#fff"
                espessura="4"
              />
            </span>
            <span class="nome-marcador">{{ marcador.rotulo }}</span>
          </button>
        </div>

        <p class="aviso-fixo">
          Os filtros se baseiam no cardápio oficial do RU, que está sujeito a alteração. A ausência
          de marcador não garante que o prato esteja livre do ingrediente, e o cardápio oficial não
          marca peixe nem frutos do mar.
        </p>

        <div class="acoes">
          <button type="button" class="botao botao--contorno limpar" @click="limpar">Limpar</button>
          <button type="button" class="botao botao--primario aplicar" @click="aplicar">
            Aplicar
          </button>
        </div>
      </section>
    </div>
  </Transition>
</template>

<style scoped>
.sobreposicao {
  position: absolute;
  inset: 0;
  z-index: 50;
}

.fundo {
  position: absolute;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
}

.gaveta {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  max-height: 82%;
  overflow-y: auto;
  padding: 20px 20px 40px;
  border-radius: var(--raio-xl) var(--raio-xl) 0 0;
  background: var(--bege);
}

.alca {
  width: 40px;
  height: 4px;
  margin: 0 auto 20px;
  border-radius: 999px;
  background: var(--borda);
}

.titulo {
  margin-bottom: 20px;
  font-family: var(--fonte-titulo);
  font-weight: 900;
  font-size: 20px;
  color: var(--texto-escuro);
}

.rotulo-grupo {
  margin-bottom: 12px;
}

.dietas {
  display: flex;
  gap: 8px;
  margin-bottom: 24px;
}

.opcao-dieta {
  flex: 1;
  padding: 10px 4px;
  border-radius: var(--raio-md);
  font-size: 12px;
  font-weight: 700;
  text-align: center;
  background: var(--cartao);
  border: 1.5px solid var(--borda);
  color: var(--texto-escuro);
  transition: all 0.15s;
}
.opcao-dieta--ativa {
  background: var(--verde-escuro);
  border-color: var(--verde-escuro);
  color: #fff;
}

.indisponivel {
  margin-bottom: 12px;
}

.marcadores {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
  margin-bottom: 20px;
}
.marcadores--desativados {
  opacity: 0.45;
}

.opcao-marcador {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: var(--raio-md);
  background: var(--cartao);
  border: 1.5px solid var(--borda);
  transition: all 0.15s;
}
.opcao-marcador--ativa {
  background: var(--bege-selecionado);
  border-color: var(--dourado);
}

.bolinha {
  width: 14px;
  height: 14px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  border: 2px solid var(--borda);
  transition: all 0.15s;
}
.opcao-marcador--ativa .bolinha {
  background: var(--dourado);
  border-color: var(--dourado);
}

.nome-marcador {
  font-size: 12px;
  font-weight: 600;
  color: var(--texto-escuro);
}
.opcao-marcador--ativa .nome-marcador {
  color: var(--dourado);
}

.aviso-fixo {
  margin-bottom: 24px;
  font-size: 11px;
  line-height: 1.6;
  color: var(--texto-suave);
}

.acoes {
  display: flex;
  gap: 12px;
}
.limpar {
  flex: 1;
  padding: 14px;
}
.aplicar {
  flex: 2;
  padding: 14px;
}

/* Animação: fundo esmaece e a gaveta sobe */
.gaveta-enter-active,
.gaveta-leave-active {
  transition: opacity 0.2s;
}
.gaveta-enter-active .gaveta,
.gaveta-leave-active .gaveta {
  transition: transform 0.25s ease-out;
}
.gaveta-enter-from,
.gaveta-leave-to {
  opacity: 0;
}
.gaveta-enter-from .gaveta,
.gaveta-leave-to .gaveta {
  transform: translateY(100%);
}
</style>
