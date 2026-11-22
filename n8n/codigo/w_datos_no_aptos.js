// H7 · Si la carga de datos no es válida: aviso a dirección y al responsable de datos, y registro en ejecuciones.
const r = $input.first().json || {};
const c = (r.body && typeof r.body === 'object') ? r.body : {};
if (r.statusCode >= 200 && r.statusCode < 300 && c.apta === true) return [];
const cfg = $('Configuración').first().json;
const flujo = (typeof $workflow !== 'undefined' && $workflow.name) || 'Meridiano';
const motivo = c.motivo || `no se ha podido consultar el estado de la carga (Supabase: ${r.statusCode || 'sin respuesta'})`;
return [{ json: {
  para: [cfg.correo_direccion, cfg.correo_datos].filter(Boolean).join(','),
  asunto: 'Meridiano · ciclo detenido: los datos no están al día',
  texto: `${flujo} no ha generado propuestas porque ${motivo}.\n\n` +
    (c.fecha ? `Última carga registrada: ${String(c.fecha).slice(0, 16).replace('T', ' ')} (${c.estado}).\n\n` : '') +
    'Revise la hoja de datos y lance W0 («Cargar ahora»); después vuelva a ejecutar este flujo a mano. ' +
    'El panel conserva el plan de la semana anterior.',
  registro: { origen: 'n8n', estado: 'detenido_por_datos', detalle: { flujo: flujo, motivo, ultima_carga: c } },
} }];
