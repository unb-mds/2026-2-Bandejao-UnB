<script setup>
import { REFEICOES } from '@/constants/refeicoes'
import CheckinBotao from '@/components/CheckinBotao.vue'
import IconeSvg from '@/components/IconeSvg.vue'
import RefeicaoEncerrada from '@/components/RefeicaoEncerrada.vue'

defineProps({
  campusId: { type: Number, required: true },
  tipoRefeicao: { type: String, required: true },
  encerrada: { type: Boolean, default: false },
})

const NIVEIS = [
  { id: 'vazia', rotulo: 'Vazia' },
  { id: 'curta', rotulo: 'Curta' },
  { id: 'moderada', rotulo: 'Moderada' },
  { id: 'longa', rotulo: 'Longa' },
]
</script>

<template>
  <section id="fila" class="secao-fila pilha-4" aria-labelledby="titulo-fila">
    <h2 id="titulo-fila" class="titulo-fila">Fila do RU</h2>

    <RefeicaoEncerrada v-if="encerrada" :tipo-refeicao="tipoRefeicao" />

    <section v-else class="pilha-3" aria-labelledby="titulo-checkin">
      <p id="titulo-checkin" class="titulo-secao pequeno">
        Check-in · {{ REFEICOES[tipoRefeicao].rotulo }}
      </p>
      <CheckinBotao :campus-id="campusId" :tipo-refeicao="tipoRefeicao" />
    </section>

    <div class="cartao em-breve">
      <span class="selo">Em breve</span>
      <div class="relogio">
        <IconeSvg nome="relogio" :tamanho="48" cor="var(--dourado)" espessura="1.6" />
      </div>
      <p class="titulo-secao">A previsão de fila chega na próxima versão</p>
      <p class="texto">
        Você vai poder ver, antes de sair de casa, em que horários a fila do RU costuma estar vazia
        ou longa — e ajudar a previsão fazendo check-in quando estiver no restaurante.
      </p>
    </div>

    <div class="escala" aria-hidden="true">
      <div v-for="nivel in NIVEIS" :key="nivel.id" class="nivel">
        <div class="nivel-barra" :class="`nivel-barra--${nivel.id}`" />
        <span class="nivel-rotulo">{{ nivel.rotulo }}</span>
      </div>
    </div>

    <div class="cartao como-funciona">
      <p class="titulo-secao pequeno">Como vai funcionar?</p>
      <p class="texto-pequeno explicacao">
        A previsão será calculada a partir dos check-ins de usuários cadastrados nas últimas 4
        semanas, em faixas de 15 minutos. Quanto mais check-ins, mais precisa a previsão. Sem dados
        suficientes, o sistema exibirá "dados insuficientes".
      </p>
    </div>
  </section>
</template>

<style scoped>
.secao-fila {
  padding: 16px;
}

.titulo-fila {
  font-family: var(--fonte-titulo);
  font-size: 18px;
  font-weight: 900;
  color: var(--texto-escuro);
}

.em-breve {
  padding: 24px 20px;
  border-radius: var(--raio-xl);
  text-align: center;
}

.selo {
  display: inline-block;
  margin-bottom: 16px;
  padding: 4px 12px;
  border-radius: 999px;
  font-size: 10px;
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  background: var(--verde-escuro);
  color: #fff;
}

.relogio {
  width: 128px;
  height: 128px;
  margin: 0 auto 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  border: 4px dashed var(--borda);
  background: var(--bege);
}

.texto {
  margin-top: 8px;
  font-size: 14px;
  line-height: 1.6;
  color: var(--texto-suave);
}

.escala {
  display: flex;
  gap: 6px;
  padding: 0 4px;
}

.nivel {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}

.nivel-barra {
  width: 100%;
  height: 8px;
  border-radius: 999px;
  opacity: 0.35;
}
.nivel-barra--vazia {
  background: var(--fila-vazia);
}
.nivel-barra--curta {
  background: var(--fila-curta);
}
.nivel-barra--moderada {
  background: var(--fila-moderada);
}
.nivel-barra--longa {
  background: var(--fila-longa);
}

.nivel-rotulo {
  font-size: 9px;
  font-weight: 600;
  color: var(--texto-claro);
}

.como-funciona {
  padding: 16px;
}

.pequeno {
  margin-bottom: 8px;
  font-size: 14px;
}

.explicacao {
  line-height: 1.6;
  color: var(--texto-suave);
}
</style>
