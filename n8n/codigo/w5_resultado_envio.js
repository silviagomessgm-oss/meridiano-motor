// Resultado de cada envío de Gmail → registrar_envio en Supabase (enviada con su id de mensaje, o error_envio con el motivo).
// Gmail devuelve un elemento por cada correo, en el mismo orden que «Solo reservados».
const enviados = $('Solo reservados').all().map(i => i.json);
const res = $input.all().map(i => i.json || {});
return enviados.map((p, k) => {
  const r = res[k] || {};
  const ok = !!(r.id || r.threadId) && !r.error;
  const error = ok ? null : String((r.error && (r.error.message || r.error.description)) || r.error || 'Gmail no ha confirmado el envío').slice(0, 400);
  return { json: { p_propuesta_id: p.id, p_accion: 'registrar_envio', p_usuario: 'n8n',
                   p_datos: ok ? { ok: true, id_mensaje: r.id } : { ok: false, error } } };
});
