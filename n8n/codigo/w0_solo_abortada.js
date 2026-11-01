// Carga detenida antes de escribir nada: aviso y registro.
return $input.all().filter(i => i.json.abortar).map(i => ({ json: {
  registro: { origen: 'n8n', estado: 'carga_detenida', detalle: { flujo: 'W0', fatales: i.json.fatales, tablas: i.json.resumen } },
  asunto: 'Meridiano · carga semanal de datos DETENIDA (no se ha cargado nada)',
  texto: `La carga de la hoja de datos a Supabase se ha detenido sin escribir nada:\n\n- ${i.json.fatales.join('\n- ')}\n\n` +
    `Corrige la hoja y vuelve a lanzar "W0 · Carga semanal" a mano antes del martes a las 7:00; si no, el cálculo del martes usará los datos de la semana anterior.\n\n` +
    (i.json.resumen || []).map(r => `${r.tabla}: ${r.leidas} leídas, ${r.rechazadas} con errores` +
      (r.ejemplos_rechazo.length ? '\n   ' + r.ejemplos_rechazo.slice(0, 5).map(e => `fila ${e.fila}: ${e.motivo}`).join('\n   ') : '')).join('\n'),
} }));
