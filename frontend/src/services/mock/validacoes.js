/**
 * Regras de validação do cadastro (RF01). No sistema real elas pertencem ao
 * backend (C4 nível 4b): o frontend só formata os campos e exibe a mensagem
 * devolvida pela API. Ficam aqui para o backend simulado responder como o
 * backend real deverá responder.
 */

const DOMINIO_ESTUDANTE = /^([^@\s]+)@aluno\.unb\.br$/i
const DOMINIO_SERVIDOR = /^([^@\s]+)@unb\.br$/i

/** Código do semestre corrente (ex.: 262 = 2º semestre de 2026). Anexo A. */
export function codigoSemestreAtual(agora = new Date()) {
  const semestre = agora.getMonth() < 6 ? 1 : 2
  return (agora.getFullYear() % 100) * 10 + semestre
}

function ehSequencia(digitos, passo) {
  for (let i = 1; i < digitos.length; i++) {
    if (Number(digitos[i]) - Number(digitos[i - 1]) !== passo) return false
  }
  return true
}

/** Retorna a mensagem de erro, ou null se a matrícula de estudante é válida. */
export function validarMatriculaEstudante(matricula, agora = new Date()) {
  if (!/^\d{9}$/.test(matricula)) {
    return 'A matrícula de estudante deve ter exatamente 9 dígitos numéricos.'
  }
  const codigo = Number(matricula.slice(0, 3))
  const semestre = matricula[2]
  if (
    (semestre !== '1' && semestre !== '2') ||
    codigo < 101 ||
    codigo > codigoSemestreAtual(agora)
  ) {
    return 'Os 3 primeiros dígitos da matrícula não correspondem a um semestre de ingresso válido.'
  }
  const resto = matricula.slice(3)
  if (/^(\d)\1{5}$/.test(resto) || ehSequencia(resto, 1) || ehSequencia(resto, -1)) {
    return 'Matrícula inválida. Confira os dígitos informados.'
  }
  return null
}

export function validarSiape(siape) {
  return /^\d{7}$/.test(siape)
    ? null
    : 'A matrícula funcional/SIAPE deve ter exatamente 7 dígitos numéricos.'
}

/** Estudante: e-mail no formato matricula@aluno.unb.br. Devolve { erro, matricula }. */
export function analisarEmailEstudante(email, agora = new Date()) {
  const resultado = DOMINIO_ESTUDANTE.exec(email.trim())
  if (!resultado) {
    return { erro: 'Use o e-mail institucional no formato matricula@aluno.unb.br.' }
  }
  const matricula = resultado[1]
  const erro = validarMatriculaEstudante(matricula, agora)
  return erro ? { erro } : { erro: null, matricula }
}

/** Professor/Servidor: e-mail @unb.br. Devolve { erro, apelido } (apelido extraído). */
export function analisarEmailServidor(email) {
  const resultado = DOMINIO_SERVIDOR.exec(email.trim())
  if (!resultado) return { erro: 'Use seu e-mail institucional com domínio @unb.br.' }
  return { erro: null, apelido: resultado[1].replace(/[^a-zA-Z0-9]/g, '') }
}

export function validarApelido(apelido) {
  if (/\s/.test(apelido)) return 'O apelido não pode ter espaços.'
  if (apelido.length < 3 || apelido.length > 20) return 'O apelido deve ter de 3 a 20 caracteres.'
  return null
}

export function validarSenha(senha) {
  return senha.length >= 8 ? null : 'A senha deve ter no mínimo 8 caracteres.'
}
