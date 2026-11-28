// Envíos con respuesta ambigua de Gmail (timeout, red, 5xx o sin respuesta): no se registran ni se reintentan solos.
// Aviso inmediato a dirección para que compruebe en Enviados si el correo salió: si salió, lo registra con
// confirmar_envio_manual(id, id_mensaje, fecha); si no, lo libera con liberar_envio(id).
const enviados = $('Solo reservados').all().map(i => i.json);
const res = $('Enviar al contacto').all().map(i => i.json || {});
const AMBIGUO = /timeout|timed out|ETIMEDOUT|ECONNRESET|ECONNABORTED|ECONNREFUSED|EAI_AGAIN|socket hang up|network|aborted/i;
const ambiguo = r => {
  if ((r.id || r.threadId) && !r.error) return false;
  const e = r.error || {};
  const msg = String(e.message || e.description || (typeof e === 'string' ? e : '') || '');
  const code = Number(e.httpCode || e.status || e.statusCode || (msg.match(/\b([45]\d\d)\b/) || [])[1] || 0);
  return !(code >= 400 && code < 500 && !AMBIGUO.test(msg));
};
const dudosos = enviados.map((p, k) => ({ p, r: res[k] || {} })).filter(x => ambiguo(x.r));
if (!dudosos.length) return [];
const cfg = $('Configuración').first().json;
return [{ json: {
  para: cfg.correo_direccion,
  asunto: `Meridiano · ${dudosos.length} envío${dudosos.length === 1 ? '' : 's'} sin confirmar: revisar antes de reintentar`,
  texto: 'Gmail no ha confirmado ni rechazado estos envíos, así que el correo pudo salir o no. No se reintentan solos para ' +
    'no enviarlos dos veces.\n\n' +
    dudosos.map(({ p, r }) => `- Propuesta ${p.id} · ${p.razon_social} · para ${p.para}\n  Respuesta: ` +
      String((r.error && (r.error.message || r.error)) || 'sin respuesta').slice(0, 200)).join('\n') +
    '\n\nCompruebe la carpeta Enviados. Si el correo SÍ salió, regístrelo en Supabase con: ' +
    "select confirmar_envio_manual(<id>, '<id del mensaje de Gmail>', '<fecha y hora del envío>'); " +
    'así pasa a «En seguimiento» y los toques cuentan desde esa fecha. Si NO salió, libérelo con: ' +
    'select liberar_envio(<id>); y vuelva a lanzar «Reintentar envíos pendientes» en W5.',
} }];
