export const CAMPUS_COM_EXECUTIVO = 'Darcy Ribeiro'

export function idDeCampusValido(valor) {
  const id = typeof valor === 'string' && /^\d+$/.test(valor) ? Number(valor) : valor
  return Number.isInteger(id) && id > 0 ? id : null
}

export function siglaCampus(nome) {
  return nome
    .split(' ')
    .map((palavra) => palavra[0])
    .join('')
    .slice(0, 3)
}
