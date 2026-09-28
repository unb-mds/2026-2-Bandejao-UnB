<script setup>
/**
 * Ícones de traço usados no protótipo (padrão 24×24, estilo Feather).
 * `cor` define o traço; `preenchimento` o fundo (padrão: sem preenchimento).
 * As cores vão em `style` (e não em atributos) para aceitar var(--token).
 */
defineProps({
  nome: { type: String, required: true },
  tamanho: { type: Number, default: 22 },
  cor: { type: String, default: 'currentColor' },
  preenchimento: { type: String, default: 'none' },
  espessura: { type: [Number, String], default: 2 },
})
</script>

<template>
  <svg
    :width="tamanho"
    :height="tamanho"
    viewBox="0 0 24 24"
    :style="{ fill: preenchimento, stroke: cor }"
    :stroke-width="espessura"
    stroke-linecap="round"
    stroke-linejoin="round"
    aria-hidden="true"
  >
    <template v-if="nome === 'voltar'">
      <path d="M19 12H5M12 5l-7 7 7 7" />
    </template>
    <template v-else-if="nome === 'avancar'">
      <path d="M5 12h14M12 5l7 7-7 7" />
    </template>
    <template v-else-if="nome === 'chevron'">
      <path d="M9 18l6-6-6-6" />
    </template>
    <template v-else-if="nome === 'estrela'">
      <polygon
        points="12,2 15.09,8.26 22,9.27 17,14.14 18.18,21.02 12,17.77 5.82,21.02 7,14.14 2,9.27 8.91,8.26"
      />
    </template>
    <template v-else-if="nome === 'casa'">
      <path d="M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z" />
      <polyline points="9,22 9,12 15,12 15,22" />
    </template>
    <template v-else-if="nome === 'talheres'">
      <path d="M3 2v7c0 1.1.9 2 2 2h4a2 2 0 002-2V2" />
      <path d="M7 2v20" />
      <path d="M21 15V2a5 5 0 00-5 5v6h3a2 2 0 012 2z" />
    </template>
    <template v-else-if="nome === 'relogio'">
      <circle cx="12" cy="12" r="10" />
      <polyline points="12,6 12,12 16,14" />
    </template>
    <template v-else-if="nome === 'usuario'">
      <path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2" />
      <circle cx="12" cy="7" r="4" />
    </template>
    <template v-else-if="nome === 'filtro'">
      <line x1="4" y1="6" x2="20" y2="6" />
      <line x1="8" y1="12" x2="16" y2="12" />
      <line x1="11" y1="18" x2="13" y2="18" />
    </template>
    <template v-else-if="nome === 'olho'">
      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
      <circle cx="12" cy="12" r="3" />
    </template>
    <template v-else-if="nome === 'olho-fechado'">
      <path
        d="M17.94 17.94A10.07 10.07 0 0112 20c-7 0-11-8-11-8a18.45 18.45 0 015.06-5.94M9.9 4.24A9.12 9.12 0 0112 4c7 0 11 8 11 8a18.5 18.5 0 01-2.16 3.19m-6.72-1.07a3 3 0 11-4.24-4.24"
      />
      <line x1="1" y1="1" x2="23" y2="23" />
    </template>
    <template v-else-if="nome === 'cadeado'">
      <rect x="3" y="11" width="18" height="11" rx="2" />
      <path d="M7 11V7a5 5 0 0110 0v4" />
    </template>
    <template v-else-if="nome === 'check'">
      <path d="M20 6L9 17l-5-5" />
    </template>
    <template v-else-if="nome === 'proibido'">
      <circle cx="12" cy="12" r="10" />
      <line x1="4.93" y1="4.93" x2="19.07" y2="19.07" />
    </template>
    <template v-else-if="nome === 'local'">
      <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0118 0z" />
      <circle cx="12" cy="10" r="3" />
    </template>
    <template v-else-if="nome === 'email'">
      <rect x="2" y="4" width="20" height="16" rx="2" />
      <path d="M22 6l-10 7L2 6" />
    </template>
    <template v-else-if="nome === 'alerta'">
      <path
        d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"
      />
      <line x1="12" y1="9" x2="12" y2="13" />
      <line x1="12" y1="17" x2="12.01" y2="17" />
    </template>
    <template v-else-if="nome === 'sair'">
      <path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4" />
      <polyline points="16,17 21,12 16,7" />
      <line x1="21" y1="12" x2="9" y2="12" />
    </template>
    <template v-else-if="nome === 'mapa'">
      <polygon points="1,6 1,22 8,18 16,22 23,18 23,2 16,6 8,2" />
      <line x1="8" y1="2" x2="8" y2="18" />
      <line x1="16" y1="6" x2="16" y2="22" />
    </template>
  </svg>
</template>
