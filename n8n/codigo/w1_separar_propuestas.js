// Una propuesta por item para que la IA redacte cada material por separado (solo si el motor terminó bien).
const r = $input.first().json || {};
if (!r.ok) return [];
const lista = r.detalle_propuestas || [];
return lista.map(p => ({ json: { ...p, fecha_corte: p.fecha_corte || r.fecha_corte, etiqueta_vigente: r.etiqueta_vigente } }));
