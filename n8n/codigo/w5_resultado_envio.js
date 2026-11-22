// Resultado de cada envío de Gmail → registrar_envio en Supabase.
//  · Gmail confirma (id de mensaje)                → «enviada» con su id.
//  · Gmail rechaza de forma explícita (error 4xx) → «error_envio» con el motivo: el correo no salió y se puede reintentar.
//  · Respuesta ambigua (timeout, red, 5xx, vacía)  → NO se registra: la reserva queda en envios_sin_confirmar y dirección
//    la libera tras mirar Enviados en Gmail (el correo pudo salir; reintentarlo podría duplicarlo). Lo avisa
//    «Envíos sin confirmar» (w5_sin_confirmar.js), que usa la misma clasificación.
// Gmail devuelve un elemento por cada correo, en el mismo orden que «Solo reservados».
const enviados = $('Solo reservados').all().map(i => i.json);
const res = $input.all().map(i => i.json || {});
const AMBIGUO = /timeout|timed out|ETIMEDOUT|ECONNRESET|ECONNABORTED|ECONNREFUSED|EAI_AGAIN|socket hang up|network|aborted/i;
function clasificar(r) {
  if ((r.id || r.threadId) && !r.error) return { tipo: 'ok' };
  const e = r.error || {};
  const msg = String(e.message || e.description || (typeof e === 'string' ? e : '') || '');
  const code = Number(e.httpCode || e.status || e.statusCode || (msg.match(/\b([45]\d\d)\b/) || [])[1] || 0);
  if (code >= 400 && code < 500 && !AMBIGUO.test(msg)) return { tipo: 'error', error: msg.slice(0, 400) || `Gmail: error ${code}` };
  return { tipo: 'ambiguo', error: (msg || 'Gmail no ha respondido').slice(0, 400) };
}
return enviados.map((p, k) => ({ p, c: clasificar(res[k] || {}), r: res[k] || {} }))
  .filter(x => x.c.tipo !== 'ambiguo')
  .map(({ p, c, r }) => ({ json: { p_propuesta_id: p.id, p_accion: 'registrar_envio', p_usuario: 'n8n',
    p_datos: c.tipo === 'ok' ? { ok: true, id_mensaje: r.id } : { ok: false, error: c.error } } }));
