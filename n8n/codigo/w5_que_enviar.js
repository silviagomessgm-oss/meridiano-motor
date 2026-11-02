// ¿Qué hay que enviar?
//  · Webhook de Supabase (evento nuevo): solo la propuesta de ese evento, y solo si el evento es una aceptación.
//    Así dos aceptaciones seguidas no se envían dos veces.
//  · Lanzamiento a mano («Reintentar envíos pendientes»): todas las aceptadas que sigan sin enviar.
const wh = $('Propuesta aceptada en el panel');
if (wh.isExecuted) {
  return wh.all()
    .map(i => i.json.body || i.json)
    .filter(b => b.table === 'eventos_propuesta' && b.type === 'INSERT' && b.record && b.record.accion === 'aprobar')
    .map(b => ({ json: { filtro: `&id=eq.${Number(b.record.propuesta_id)}` } }));
}
return [{ json: { filtro: '' } }];
