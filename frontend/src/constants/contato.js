/**
 * Canal público de contato para reclamações e pedidos de exclusão da conta
 * (RNF08, RNF07.4, Visão 9.1). É o endereço da equipe da ADR 0012, o mesmo
 * do aviso de privacidade. Precisa ficar igual ao `EMAIL_EQUIPE` do backend
 * (`backend/config/settings.py`), que recebe os alertas do leitor de cardápio.
 */
export const EMAIL_CONTATO = 'equipe@bandejaounb.com.br'
export const CANAL_CONTATO = `mailto:${EMAIL_CONTATO}`
