<script setup>
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useCardapioStore } from '@/stores/cardapio'
import { usePreferenciasStore } from '@/stores/preferencias'
import { siglaCampus } from '@/constants/campi'
import AppLogo from '@/components/AppLogo.vue'
import IconeSvg from '@/components/IconeSvg.vue'

/**
 * Escolha do campus. Na rota `/campus` é a tela inteira: guarda o campus
 * lembrado e leva à tela do campus. Com `compacto`, fica dentro de outra
 * tela (o ranking, FE-13): mostra os campi como botões e só avisa a escolha
 * pelo evento `escolher`, sem navegar nem trocar o campus lembrado.
 */
const props = defineProps({
  compacto: { type: Boolean, default: false },
  /** Campus marcado na variante compacta. */
  selecionado: { type: Number, default: null },
})
const emit = defineEmits(['escolher'])

const router = useRouter()
const cardapio = useCardapioStore()
const preferencias = usePreferenciasStore()

onMounted(() => cardapio.carregarCampi())

function escolher(id) {
  if (props.compacto) {
    emit('escolher', id)
    return
  }
  preferencias.escolherCampus(id)
  router.push({ name: 'campus-tela', params: { campusId: id } })
}
</script>

<template>
  <div v-if="compacto" class="seletor-compacto" role="group" aria-label="Campus">
    <p
      v-if="cardapio.carregandoCampi || (!cardapio.campiCarregados && !cardapio.erroCampi)"
      class="estado-compacto"
      role="status"
    >
      Carregando campi…
    </p>
    <p
      v-else-if="cardapio.erroCampi && !cardapio.campi.length"
      class="estado-compacto"
      role="alert"
    >
      Não foi possível carregar os campi. {{ cardapio.erroCampi }}
      <button type="button" class="botao-pequeno" @click="cardapio.carregarCampi({ forcar: true })">
        Tentar novamente
      </button>
    </p>
    <p v-else-if="!cardapio.campi.length" class="estado-compacto">
      Nenhum campus disponível no momento.
    </p>
    <template v-else>
      <button
        v-for="campus in cardapio.campi"
        :key="campus.id"
        type="button"
        class="opcao"
        :class="{ 'opcao--atual': selecionado === campus.id }"
        :aria-pressed="selecionado === campus.id"
        data-teste="seletor-campus-opcao"
        @click="escolher(campus.id)"
      >
        {{ campus.nome }}
      </button>
    </template>
  </div>

  <div v-else class="tela tela-campus">
    <header class="cabecalho cabecalho-campus fundo-escuro">
      <div class="marca">
        <AppLogo :tamanho="36" />
        <span class="nome">bandejão</span>
      </div>
      <p class="sobretitulo so-desktop">Antes de começar</p>
      <h1 class="titulo-tela">Qual campus<br />você frequenta?</h1>
      <p class="subtitulo-tela subtitulo">Pode trocar depois a qualquer momento</p>
      <!-- Desktop (FE-23): os passos do protótipo, só como indicação visual. -->
      <ol class="passos so-desktop" aria-hidden="true">
        <li class="passo--feito"><span>1</span> Conta ou visitante</li>
        <li class="passo--atual"><span>2</span> Escolher campus</li>
        <li><span>3</span> Acessar o Bandejão</li>
      </ol>
    </header>

    <div class="conteudo sem-barra">
      <p class="sobretitulo so-desktop">Selecione uma unidade</p>
      <p class="titulo-lista so-desktop" aria-hidden="true">Qual campus você quer consultar?</p>
      <p
        v-if="cardapio.carregandoCampi || (!cardapio.campiCarregados && !cardapio.erroCampi)"
        class="estado"
        role="status"
      >
        Carregando campi…
      </p>

      <div v-else-if="cardapio.erroCampi && !cardapio.campi.length" class="estado" role="alert">
        <p>Não foi possível carregar os campi. {{ cardapio.erroCampi }}</p>
        <button
          type="button"
          class="botao-pequeno"
          @click="cardapio.carregarCampi({ forcar: true })"
        >
          Tentar novamente
        </button>
      </div>

      <p v-else-if="!cardapio.campi.length" class="estado">Nenhum campus disponível no momento.</p>

      <ul v-else class="pilha-3 lista">
        <li v-for="campus in cardapio.campi" :key="campus.id">
          <button
            type="button"
            class="cartao cartao-clicavel campus"
            :class="{ 'campus--atual': preferencias.campusId === campus.id }"
            @click="escolher(campus.id)"
          >
            <span class="sigla">{{ siglaCampus(campus.nome) }}</span>
            <span class="textos">
              <span class="nome-campus">{{ campus.nome }}</span>
            </span>
            <IconeSvg nome="chevron" :tamanho="16" cor="var(--borda)" espessura="2.5" />
          </button>
        </li>
      </ul>
    </div>
  </div>
</template>

<style scoped>
.seletor-compacto {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.opcao {
  padding: 8px 14px;
  border-radius: 999px;
  font-size: 13px;
  font-weight: 700;
  color: var(--texto-suave);
  background: var(--cartao);
  border: 1.5px solid var(--borda);
}

.opcao--atual {
  color: #fff;
  background: var(--verde-escuro);
  border-color: var(--verde-escuro);
}

.estado-compacto {
  font-size: 13px;
  color: var(--texto-suave);
}

.cabecalho-campus {
  padding-bottom: 32px;
}

.marca {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 24px;
}

.nome {
  font-family: var(--fonte-titulo);
  font-weight: 900;
  font-size: 20px;
  letter-spacing: -0.5px;
  color: #fff;
}

.subtitulo {
  margin-top: 8px;
}

.lista {
  list-style: none;
  padding: 20px 16px 32px;
}

.campus {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 16px;
}
.campus--atual {
  border-color: var(--verde-escuro);
}

.sigla {
  width: 44px;
  height: 44px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--raio-md);
  background: var(--verde-escuro);
  font-size: 12px;
  font-weight: 900;
  letter-spacing: -0.3px;
  color: #fff;
}

.textos {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.nome-campus {
  font-family: var(--fonte-titulo);
  font-size: 14px;
  font-weight: 700;
  color: var(--texto-escuro);
}

.estado {
  padding: 32px 16px;
  text-align: center;
  color: var(--texto-suave);
}

.estado .botao-pequeno {
  margin-top: 12px;
}

/* ─── Desktop (FE-23, protótipo desktop) ─────────────────────────────── */
.so-desktop {
  display: none;
}

@media (min-width: 1024px) {
  .tela-campus {
    display: grid;
    grid-template-columns: minmax(360px, 464px) minmax(0, 1fr);
    height: 100%;
  }
  .cabecalho-campus {
    justify-content: flex-start;
    padding: clamp(32px, 4vw, 58px) clamp(32px, 5vw, 68px);
  }
  .cabecalho-campus .marca {
    margin-bottom: auto;
  }
  .so-desktop {
    display: block;
  }
  .cabecalho-campus .sobretitulo {
    margin-top: 48px;
  }
  .cabecalho-campus .titulo-tela {
    font-size: clamp(44px, 4.4vw, 64px);
    line-height: 0.98;
    letter-spacing: -0.06em;
  }
  .cabecalho-campus .subtitulo {
    margin-top: 22px;
    font-size: 12px;
  }
  .passos {
    display: flex;
    gap: 0;
    margin-top: auto;
    padding-top: 40px;
    list-style: none;
    font-size: 8px;
    font-weight: 700;
    color: var(--branco-35);
  }
  .passos li {
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 10px;
  }
  .passos span {
    display: grid;
    place-items: center;
    width: 23px;
    height: 23px;
    border: 1px solid var(--branco-20);
    border-radius: 50%;
  }
  .passos .passo--feito,
  .passos .passo--atual {
    color: #fff;
  }
  .passo--feito span {
    border-color: var(--dourado);
    color: var(--verde-escuro);
    background: var(--dourado);
  }
  .passo--atual span {
    border-color: var(--dourado);
    color: var(--dourado);
  }

  .tela-campus .conteudo {
    display: flex;
    flex-direction: column;
    justify-content: center;
    padding: 40px clamp(40px, 7vw, 96px);
  }
  .titulo-lista {
    margin-bottom: 26px;
    font: 900 clamp(26px, 2.4vw, 34px) / 1.1 var(--fonte-titulo);
    letter-spacing: -0.04em;
    color: var(--verde-escuro);
  }
  .lista {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 12px;
    max-width: 720px;
    padding: 0;
  }
  .lista > * + * {
    margin-top: 0;
  }
  .campus {
    min-height: 78px;
    border-radius: 16px;
  }
}
</style>
