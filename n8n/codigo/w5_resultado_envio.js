// Resultado de cada envío de Gmail → registrar_envio en Supabase (enviada con su id de mensaje, o error_envio con el motivo).
const enviados = $('Solo enviables').all().map(i => i.json);
const bloqueados = $('Preparar correo').all().map(i => i.json).filter(p => p.bloqueo);
const res = $input.all().map(i => i.json || {});
const out = enviados.map((p, k) => {
  const r = res[k] || {};
  const ok = !!(r.id || r.threadId) && !r.error;
  const error = ok ? null : String((r.error && (r.error.message || r.error.description)) || r.error || 'Gmail no ha confirmado el envío').slice(0, 400);
  return { json: { p_propuesta_id: p.id, p_accion: 'registrar_envio', p_usuario: 'n8n',
                   p_datos: ok ? { ok: true, id_mensaje: r.id } : { ok: false, error } } };
});
for (const p of bloqueados)
  out.push({ json: { p_propuesta_id: p.id, p_accion: 'registrar_envio', p_usuario: 'n8n', p_datos: { ok: false, error: p.bloqueo } } });
return out;
