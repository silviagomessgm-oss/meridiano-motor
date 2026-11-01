// Webhook de base de datos de Supabase: { type, table, record } por cada fila nueva de eventos_propuesta.
// La traza ya está guardada en Supabase; aquí solo interesan los cierres, para avisar a dirección si procede.
return $('Evento registrado en Supabase').all()
  .map(i => i.json.body || i.json)
  .filter(b => b.table === 'eventos_propuesta' && b.type === 'INSERT' && b.record && b.record.accion === 'cerrar')
  .map(b => ({ json: { propuesta_id: b.record.propuesta_id, usuario: b.record.usuario, fecha: b.record.creado_en } }));
