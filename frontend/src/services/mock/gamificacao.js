import { patenteDosPontos, proximaPatente } from '@/constants/patentes'
import { hojeISO } from '@/utils/datas'

const PONTOS_POR_CHECKIN = 10
const MINIMO_DE_DIAS = 3
const SEMESTRE = '2026.2'

const RANKING_SEMENTE = {
  1: [
    ['bandejeiro_raiz', 320, 'VETERANO'],
    ['fila_zero', 210, 'RATO_DE_RU'],
    ['ru_lover', 140, 'RATO_DE_RU'],
    ['cafe_das_sete', 90, 'CALOURO_DE_BANDEJA'],
  ],
  2: [['ceilandia_come', 180, 'RATO_DE_RU']],
  3: [
    ['gama_faminto', 260, 'VETERANO'],
    ['engenheira_do_ru', 120, 'CALOURO_DE_BANDEJA'],
  ],
  4: [['planaltina_rango', 60, 'CALOURO_DE_BANDEJA']],
  5: [],
}

const checkinsDe = (estado, usuarioId) =>
  (estado.checkins ?? []).filter((checkin) => checkin.usuarioId === usuarioId)

function segundaDaSemana(agora) {
  const segunda = new Date(agora)
  segunda.setDate(segunda.getDate() - ((segunda.getDay() + 6) % 7))
  return hojeISO(segunda)
}

export function progressoSimulado(estado, usuario, agora) {
  const checkins = checkinsDe(estado, usuario.id)
  const pontosTotais = checkins.length * PONTOS_POR_CHECKIN
  const patente = patenteDosPontos(pontosTotais)
  const proxima = proximaPatente(patente)
  const segunda = segundaDaSemana(agora)
  const diasNaSemana = new Set(checkins.filter((c) => c.data >= segunda).map((c) => c.data)).size
  return {
    patente,
    pontosTotais,
    faltaParaProxima: proxima ? proxima.minimo - pontosTotais : 0,
    sequencia: 0,
    diasNaSemana,
    minimoDias: MINIMO_DE_DIAS,
    participaRanking: Boolean(usuario.participaRanking),
  }
}

export function rankingSimulado(estado, campusId) {
  const linhas = (RANKING_SEMENTE[campusId] ?? []).map(([apelido, pontos, patente]) => ({
    apelido,
    pontos,
    patente,
  }))
  for (const usuario of estado.usuarios) {
    if (!usuario.participaRanking) continue
    const doCampus = checkinsDe(estado, usuario.id).filter((c) => c.campus === campusId)
    if (!doCampus.length) continue
    const total = checkinsDe(estado, usuario.id).length * PONTOS_POR_CHECKIN
    linhas.push({
      apelido: usuario.apelido,
      pontos: doCampus.length * PONTOS_POR_CHECKIN,
      patente: patenteDosPontos(total),
    })
  }
  return {
    campusId,
    semestre: SEMESTRE,
    linhas: linhas
      .sort((a, b) => b.pontos - a.pontos)
      .slice(0, 10)
      .map(({ apelido, patente }, i) => ({ posicao: i + 1, apelido, patente })),
  }
}
