// Resultado de la carga: lo que se ha cargado por tabla, lo rechazado y cualquier error de Supabase.
const lotes = $('Solo cargables').all().map(i => i.json);
const resp = $input.all().map(i => i.json || {});
const resumen = lotes[0].resumen || [];
const errores = [];
lotes.forEach((l, k) => {
  const r = resp[k] || {};
  if (!(r.statusCode >= 200 && r.statusCode < 300))
    errores.push(`${l.tabla} (lote ${l.lote}): ${(r.body && r.body.message) || r.error?.message || 'sin respuesta de Supabase'}`);
});
const cargadas = {};
lotes.forEach((l, k) => { const r = resp[k] || {}; if (r.statusCode >= 200 && r.statusCode < 300) cargadas[l.tabla] = (cargadas[l.tabla] || 0) + l.filas.length; });
const tablas = resumen.map(r => ({ ...r, cargadas: cargadas[r.tabla] || 0 }));
const rechazadas = tablas.reduce((a, r) => a + r.rechazadas, 0);
const estado = errores.length ? 'carga_con_errores' : (rechazadas ? 'carga_con_avisos' : 'carga_ok');
const lineas = tablas.map(r => `${r.tabla}: ${r.cargadas} cargadas de ${r.leidas}` + (r.rechazadas ? ` · ${r.rechazadas} rechazadas` : '') +
  (r.ejemplos_rechazo.length ? '\n   ' + r.ejemplos_rechazo.slice(0, 5).map(e => `fila ${e.fila}: ${e.motivo}`).join('\n   ') : ''));
return [{ json: {
  avisar: estado !== 'carga_ok',
  registro: { origen: 'n8n', estado, detalle: { flujo: 'W0', tablas, errores } },
  asunto: estado === 'carga_con_errores' ? 'Meridiano · carga semanal de datos con ERRORES' : 'Meridiano · carga semanal de datos con filas rechazadas',
  texto: `Resultado de la carga de la hoja de datos a Supabase:\n\n${lineas.join('\n')}` +
    (errores.length ? `\n\nErrores de Supabase:\n- ${errores.join('\n- ')}` : '') +
    `\n\nLas filas rechazadas no se han cargado: corrígelas en la hoja (la próxima carga las recogerá).`,
} }];
