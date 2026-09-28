/**
 * Cardápios de exemplo do backend simulado, no formato que a API devolverá
 * depois da leitura do PDF semanal (RF06). As datas são calculadas a partir
 * da semana atual, para o app sempre ter um cardápio "vigente".
 *
 * Casos cobertos para demonstração:
 * - Darcy Ribeiro serve almoço no sábado (dias vêm do PDF, RF06/RF07).
 * - Planaltina não serve jantar (o seletor mostra só as refeições do PDF, RF07).
 * - Ceilândia tem um jantar com "informação de alérgenos indisponível" (RF06/RF08).
 * - Fazenda Água Limpa ainda não publicou o cardápio da semana (RF07).
 */
import { inicioDaSemana, somarDias } from '@/utils/datas'

const p = (nome, ...marcadores) => ({ nome, marcadores })
const cat = (rotulo, dieta, pratos) => ({ rotulo, dieta, pratos })

const ALMOCOS = [
  [
    cat('Bebidas', 'todas', [p('Suco de caju'), p('Água')]),
    cat('Sopa', 'todas', [p('Caldo de feijão')]),
    cat('Prato Principal — Padrão', 'padrao', [
      p('Bife acebolado', 'suino'),
      p('Frango grelhado ao molho de ervas'),
    ]),
    cat('Prato Principal — Ovolactovegetariano', 'ovolacto', [
      p('Omelete de legumes', 'ovo', 'leite'),
    ]),
    cat('Prato Principal — Vegetariano Estrito', 'vegano', [p('Tofu grelhado ao shoyu', 'soja')]),
    cat('Guarnição', 'todas', [p('Purê de batata', 'leite')]),
    cat('Acompanhamentos', 'todas', [p('Arroz branco'), p('Arroz integral'), p('Feijão carioca')]),
    cat('Salada', 'todas', [p('Folhas verdes com tomate e cenoura')]),
    cat('Sobremesa', 'todas', [p('Gelatina de morango'), p('Banana')]),
  ],
  [
    cat('Bebidas', 'todas', [p('Suco de goiaba'), p('Água')]),
    cat('Sopa', 'todas', [p('Sopa de legumes')]),
    cat('Prato Principal — Padrão', 'padrao', [
      p('Carne de panela com batatas'),
      p('Linguiça acebolada', 'suino'),
    ]),
    cat('Prato Principal — Ovolactovegetariano', 'ovolacto', [
      p('Lasanha de berinjela', 'leite', 'trigo'),
    ]),
    cat('Prato Principal — Vegetariano Estrito', 'vegano', [
      p('Estrogonofe de grão-de-bico com cogumelos', 'cogumelo'),
    ]),
    cat('Guarnição', 'todas', [p('Macarrão alho e óleo', 'trigo')]),
    cat('Acompanhamentos', 'todas', [p('Arroz branco'), p('Arroz integral'), p('Feijão preto')]),
    cat('Salada', 'todas', [p('Repolho roxo com cenoura ralada')]),
    cat('Sobremesa', 'todas', [p('Doce de leite', 'leite'), p('Laranja')]),
  ],
  [
    cat('Bebidas', 'todas', [p('Suco de acerola'), p('Água')]),
    cat('Sopa', 'todas', [p('Sopa de abóbora com gengibre', 'pimenta')]),
    cat('Prato Principal — Padrão', 'padrao', [p('Frango xadrez', 'soja', 'amendoim')]),
    cat('Prato Principal — Ovolactovegetariano', 'ovolacto', [
      p('Torta de legumes', 'ovo', 'trigo', 'leite'),
    ]),
    cat('Prato Principal — Vegetariano Estrito', 'vegano', [p('Hambúrguer de lentilha', 'trigo')]),
    cat('Guarnição', 'todas', [p('Farofa de cenoura')]),
    cat('Acompanhamentos', 'todas', [p('Arroz branco'), p('Arroz integral'), p('Feijão carioca')]),
    cat('Salada', 'todas', [p('Alface americana com beterraba')]),
    cat('Sobremesa', 'todas', [p('Pudim de chocolate', 'leite', 'ovo'), p('Maçã')]),
  ],
  [
    cat('Bebidas', 'todas', [p('Suco de manga'), p('Água')]),
    cat('Sopa', 'todas', [p('Creme de milho', 'leite')]),
    cat('Prato Principal — Padrão', 'padrao', [
      p('Peixe empanado', 'trigo', 'ovo'),
      p('Costela suína ao barbecue', 'suino', 'pimenta'),
    ]),
    cat('Prato Principal — Ovolactovegetariano', 'ovolacto', [
      p('Panqueca de ricota com espinafre', 'leite', 'ovo', 'trigo'),
    ]),
    cat('Prato Principal — Vegetariano Estrito', 'vegano', [
      p('Moqueca de banana-da-terra com castanhas', 'oleaginosa', 'pimenta'),
    ]),
    cat('Guarnição', 'todas', [p('Couve refogada')]),
    cat('Acompanhamentos', 'todas', [p('Arroz branco'), p('Arroz integral'), p('Feijão preto')]),
    cat('Salada', 'todas', [p('Tomate com pepino e cebola')]),
    cat('Sobremesa', 'todas', [p('Mousse de maracujá', 'leite'), p('Mexerica')]),
  ],
  [
    cat('Bebidas', 'todas', [p('Suco de uva'), p('Água')]),
    cat('Sopa', 'todas', [p('Sopa de feijão com macarrão', 'trigo')]),
    cat('Prato Principal — Padrão', 'padrao', [p('Feijoada', 'suino')]),
    cat('Prato Principal — Ovolactovegetariano', 'ovolacto', [
      p('Feijoada vegetariana com queijo coalho', 'leite'),
    ]),
    cat('Prato Principal — Vegetariano Estrito', 'vegano', [
      p('Feijoada vegana com shitake', 'cogumelo', 'soja'),
    ]),
    cat('Guarnição', 'todas', [p('Couve refogada'), p('Farofa de mandioca')]),
    cat('Acompanhamentos', 'todas', [p('Arroz branco'), p('Arroz integral')]),
    cat('Salada', 'todas', [p('Vinagrete')]),
    cat('Sobremesa', 'todas', [p('Laranja'), p('Paçoca', 'amendoim')]),
  ],
]

const ALMOCO_SABADO = [
  cat('Bebidas', 'todas', [p('Suco de laranja'), p('Água')]),
  cat('Prato Principal — Padrão', 'padrao', [p('Frango assado com ervas')]),
  cat('Prato Principal — Ovolactovegetariano', 'ovolacto', [
    p('Quiche de alho-poró', 'ovo', 'leite', 'trigo'),
  ]),
  cat('Prato Principal — Vegetariano Estrito', 'vegano', [p('Risoto de cogumelos', 'cogumelo')]),
  cat('Acompanhamentos', 'todas', [p('Arroz branco'), p('Feijão carioca')]),
  cat('Salada', 'todas', [p('Mix de folhas')]),
  cat('Sobremesa', 'todas', [p('Banana')]),
]

const CAFES = [
  [
    cat('Bebidas', 'todas', [p('Café com leite', 'leite'), p('Suco de laranja')]),
    cat('Complemento — Ovolactovegetariano', 'ovolacto', [
      p('Pão francês com manteiga', 'trigo', 'leite'),
      p('Queijo minas', 'leite'),
    ]),
    cat('Complemento — Vegetariano Estrito', 'vegano', [
      p('Pão integral', 'trigo'),
      p('Geleia de morango'),
    ]),
    cat('Fruta', 'todas', [p('Mamão')]),
  ],
  [
    cat('Bebidas', 'todas', [p('Café preto'), p('Chá de camomila com mel', 'mel')]),
    cat('Complemento — Ovolactovegetariano', 'ovolacto', [
      p('Pão de queijo', 'leite', 'ovo'),
      p('Ovos mexidos', 'ovo'),
    ]),
    cat('Complemento — Vegetariano Estrito', 'vegano', [
      p('Tapioca com coco'),
      p('Pasta de amendoim', 'amendoim'),
    ]),
    cat('Fruta', 'todas', [p('Melancia')]),
  ],
  [
    cat('Bebidas', 'todas', [p('Achocolatado', 'leite'), p('Suco de abacaxi')]),
    cat('Complemento — Ovolactovegetariano', 'ovolacto', [
      p('Bolo de fubá', 'ovo', 'leite', 'trigo'),
      p('Requeijão', 'leite'),
    ]),
    cat('Complemento — Vegetariano Estrito', 'vegano', [
      p('Cuscuz de milho'),
      p('Castanhas mistas', 'oleaginosa'),
    ]),
    cat('Fruta', 'todas', [p('Banana')]),
  ],
]

const JANTARES = [
  [
    cat('Bebidas', 'todas', [p('Suco de maracujá'), p('Água')]),
    cat('Prato Principal — Padrão', 'padrao', [p('Filé de peixe ao limão')]),
    cat('Prato Principal — Ovolactovegetariano', 'ovolacto', [
      p('Quiche de espinafre', 'ovo', 'leite', 'trigo'),
    ]),
    cat('Prato Principal — Vegetariano Estrito', 'vegano', [p('Lentilha ensopada com legumes')]),
    cat('Guarnição', 'todas', [p('Mandioca cozida')]),
    cat('Acompanhamentos', 'todas', [
      p('Arroz integral'),
      p('Feijão preto'),
      p('Farofa temperada'),
    ]),
    cat('Salada', 'todas', [p('Alface com tomate e pepino')]),
    cat('Sobremesa', 'todas', [p('Pudim de leite', 'leite', 'ovo')]),
  ],
  [
    cat('Bebidas', 'todas', [p('Suco de limão'), p('Água')]),
    cat('Sopa', 'todas', [p('Canja de legumes')]),
    cat('Prato Principal — Padrão', 'padrao', [p('Almôndegas ao sugo', 'trigo', 'ovo')]),
    cat('Prato Principal — Ovolactovegetariano', 'ovolacto', [
      p('Nhoque ao molho branco', 'trigo', 'leite'),
    ]),
    cat('Prato Principal — Vegetariano Estrito', 'vegano', [
      p('Escondidinho de mandioca com proteína de soja', 'soja'),
    ]),
    cat('Acompanhamentos', 'todas', [p('Arroz branco'), p('Feijão carioca')]),
    cat('Salada', 'todas', [p('Cenoura e chuchu cozidos')]),
    cat('Sobremesa', 'todas', [p('Goiabada')]),
  ],
  [
    cat('Bebidas', 'todas', [p('Suco de tangerina'), p('Água')]),
    cat('Prato Principal — Padrão', 'padrao', [p('Lombo suíno assado', 'suino')]),
    cat('Prato Principal — Ovolactovegetariano', 'ovolacto', [
      p('Omelete de queijo', 'ovo', 'leite'),
    ]),
    cat('Prato Principal — Vegetariano Estrito', 'vegano', [p('Curry de grão-de-bico', 'pimenta')]),
    cat('Guarnição', 'todas', [p('Batata sauté')]),
    cat('Acompanhamentos', 'todas', [p('Arroz integral'), p('Feijão preto')]),
    cat('Salada', 'todas', [p('Acelga com tomate')]),
    cat('Sobremesa', 'todas', [p('Salada de frutas')]),
  ],
]

/** Configuração de cada campus no "PDF" da semana. */
const CAMPI_SIMULADOS = {
  darcy: { publicado: true, deslocamento: 0, sabado: true, jantar: true },
  ceilandia: { publicado: true, deslocamento: 2, jantar: true, jantarSemAlergenos: 2 },
  gama: { publicado: true, deslocamento: 1, jantar: true },
  planaltina: { publicado: true, deslocamento: 3, jantar: false },
  fal: { publicado: false },
}

/** Segunda-feira da semana vigente; no domingo, já considera a semana seguinte. */
export function inicioSemanaVigente(agora = new Date()) {
  const segunda = inicioDaSemana(agora)
  return agora.getDay() === 0 ? somarDias(segunda, 7) : segunda
}

const escolher = (lista, indice) => lista[indice % lista.length]

export function montarCardapioSemana(campusId, agora = new Date()) {
  const config = CAMPI_SIMULADOS[campusId]
  const segunda = inicioSemanaVigente(agora)
  const semana = { inicio: segunda, fim: somarDias(segunda, 6) }
  if (!config?.publicado) return { campus: campusId, semana, publicado: false, dias: [] }

  const dias = []
  for (let i = 0; i < 5; i++) {
    const indice = i + config.deslocamento
    const refeicoes = [
      { tipo: 'cafe', categorias: escolher(CAFES, indice) },
      { tipo: 'almoco', categorias: escolher(ALMOCOS, indice) },
    ]
    if (config.jantar) {
      refeicoes.push({
        tipo: 'jantar',
        categorias: escolher(JANTARES, indice),
        alergenosIndisponiveis: config.jantarSemAlergenos === i,
      })
    }
    dias.push({ data: somarDias(segunda, i), refeicoes })
  }
  if (config.sabado) {
    dias.push({
      data: somarDias(segunda, 5),
      refeicoes: [{ tipo: 'almoco', categorias: ALMOCO_SABADO }],
    })
  }

  for (const dia of dias) {
    for (const refeicao of dia.refeicoes) refeicao.alergenosIndisponiveis ??= false
  }
  return { campus: campusId, semana, publicado: true, dias: structuredClone(dias) }
}

export function refeicaoExiste(campusId, data, tipo, agora = new Date()) {
  const { dias } = montarCardapioSemana(campusId, agora)
  return dias.some((d) => d.data === data && d.refeicoes.some((r) => r.tipo === tipo))
}
