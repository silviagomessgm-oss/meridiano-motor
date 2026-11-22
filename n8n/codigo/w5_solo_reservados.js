// Solo se envían las propuestas que ESTA ejecución ha conseguido reservar en Supabase (reservar_envios).
// Si el aviso del panel y un reintento manual coinciden, la otra ejecución no recibe la reserva y no envía (H1).
const r = $input.first().json || {};
const reservadas = new Set((r.reservadas || []).map(Number));
return $('Preparar correo').all().filter(i => !i.json.bloqueo && reservadas.has(Number(i.json.id)));
