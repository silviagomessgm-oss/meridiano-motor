// Un correo por comercial cada martes: sus propuestas nuevas de la semana. El detalle está en el panel.
const filas = $('Validador (sensor Govern)').all().map(i => i.json);
const panel = $('Configuración').first().json.panel_url;
const grupos = {};
for (const f of filas) (grupos[f.comercial_asignado] ??= []).push(f);
return Object.values(grupos).map(g => {
  const c = g[0];
  const lineas = g.map((f, i) => `${i + 1}. ${f.razon_social}`).join('\n');
  return { json: {
    correo: c.correo_comercial, comercial: c.comercial_nombre, propuestas: g.length,
    asunto: `Meridiano · ${g.length} cuentas nuevas en tu plan de retención (semana del ${c.fecha_corte})`,
    texto: `Hola, ${String(c.comercial_nombre || '').split(' ')[0]}:\n\n` +
      `Esta semana se añaden ${g.length} cuentas a tu plan, por orden de prioridad:\n\n${lineas}\n\n` +
      `En el panel tienes la ficha de cada cuenta, el motivo detectado y un material de apoyo que puedes editar antes de usarlo. ` +
      `Al terminar cada acción, ciérrala con el estado del cliente, el motivo y si el diagnóstico era correcto.\n\n${panel}\n\n` +
      `Este correo es interno. No se ha enviado nada a ningún anunciante.`,
  } };
});
