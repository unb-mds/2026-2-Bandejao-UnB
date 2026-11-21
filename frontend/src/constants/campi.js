export const ID_CAMPUS_COM_EXECUTIVO = 1

export const CAMPI_ANTIGOS = {
  darcy: 1,
  ceilandia: 2,
  gama: 3,
  planaltina: 4,
  fal: 5,
}

export function idDeCampusValido(valor) {
  const id = typeof valor === 'string' && /^[1-9]\d*$/.test(valor) ? Number(valor) : valor
  return Number.isInteger(id) && id > 0 ? id : null
}

export function idDoCampusAntigo(valor) {
  return Object.hasOwn(CAMPI_ANTIGOS, valor) ? CAMPI_ANTIGOS[valor] : null
}

export function siglaCampus(nome) {
  return nome
    .split(' ')
    .map((palavra) => palavra[0])
    .join('')
    .slice(0, 3)
}
