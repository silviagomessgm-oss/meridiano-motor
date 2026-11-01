// Recordatorio de los lunes, antes del ciclo del martes: tareas sin cerrar de cualquier semana, por comercial. Marca las que vencen en 7 días o ya vencieron.
const comerciales = $('Supabase: comerciales').all().map(i => i.json);
const tareas = $input.all().map(i => i.json).filter(t => t.id_cliente);
const hoy = new Date(); const en7 = new Date(hoy.getTime() + 7 * 864e5);
const panel = $('Configuración').first().json.panel_url;
return comerciales.map(c => {
  const suyas = tareas.filter(t => t.comercial_asignado === c.id_comercial);
  if (!suyas.length) return null;
  const urgentes = suyas.filter(t => new Date(t.fecha_limite) <= en7);
  const lineas = suyas.map(t => `- ${t.razon_social} · límite ${t.fecha_limite}${new Date(t.fecha_limite) < hoy ? ' (vencida)' : ''}`).join('\n');
  return { json: {
    correo: c.correo, pendientes: suyas.length, urgentes: urgentes.length,
    asunto: `Meridiano · ${suyas.length} propuestas sin cerrar (${urgentes.length} vencen esta semana)`,
    texto: `Hola, ${c.nombre.split(' ')[0]}:\n\nTienes ${suyas.length} propuestas sin cerrar. Mañana llegan las de la nueva semana:\n\n${lineas}\n\n${panel}`,
  } };
}).filter(Boolean);
