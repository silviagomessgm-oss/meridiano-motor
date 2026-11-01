// Registro de la ejecución de n8n en la tabla ejecuciones (trazabilidad para Govern).
const filas = $input.all().map(i => i.json);
const llm = filas.filter(f => f.valido).length;
return [{ json: { origen: 'n8n', estado: 'ok', detalle: {
  flujo: 'W1', fecha_corte: filas[0]?.fecha_corte, propuestas: filas.length,
  material_ia: llm, material_plantilla: filas.length - llm,
  descartes: filas.filter(f => !f.valido).map(f => ({ id_cliente: f.id_cliente, motivo: f.fuente_material })),
} } }];
