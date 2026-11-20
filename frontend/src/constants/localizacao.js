/**
 * Limites da leitura de localização aceita (RN03, Anexo A do Documento de
 * Requisitos). Quem confere esses limites é o PWA, antes de mandar o
 * check-in (decisão 4 do backlog): o backend confere horário, duplicidade e
 * distância ao RU.
 *
 * O tempo limite (5 s) está fixado no Anexo A. A precisão mínima e a idade
 * máxima ainda estão "a definir pela equipe" (Anexo A; no backend,
 * `ParametrosLocalizacaoConfig` também guarda `None`). Os valores abaixo são
 * PROVISÓRIOS: trocar aqui quando a equipe fixar o Anexo A (e validar o
 * raio em campo, L05).
 */
export const TEMPO_LIMITE_LEITURA_MS = 5_000

/** Raio de incerteza máximo aceito, em metros (`coords.accuracy`). Provisório. */
export const PRECISAO_MINIMA_METROS = 100

/** Idade máxima da posição (`maximumAge` e `timestamp`), em ms. Provisório. */
export const IDADE_MAXIMA_POSICAO_MS = 60_000
