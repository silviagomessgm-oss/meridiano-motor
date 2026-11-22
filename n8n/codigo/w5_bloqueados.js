// Propuestas que no se pueden enviar (contacto dado de baja, ficticio fuera del modo demo, sin enlace de baja):
// se registran como error_envio con el motivo, en una rama propia para que se registren aunque no haya nada que enviar.
return $input.all().map(i => i.json).filter(p => p.bloqueo).map(p => ({ json: {
  p_propuesta_id: p.id, p_accion: 'registrar_envio', p_usuario: 'n8n', p_datos: { ok: false, error: p.bloqueo } } }));
