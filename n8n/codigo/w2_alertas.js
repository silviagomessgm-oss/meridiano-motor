// Cierres que requieren a dirección: cuenta clave perdida, cuenta marcada para dirección no recuperada, pérdida por reclamación.
const cierres = $('Solo cierres').all().map(i => i.json);
return $input.all().map((it, k) => {
  const r = ((it.json || {}).body || [])[0];
  if (!r) return null;
  const quien = (cierres[k] || {}).usuario || 'Un comercial';
  const motivos = [];
  if (r.cuenta_clave && r.estado_confirmado_comercial === 'Perdido') motivos.push('cuenta clave perdida');
  if (r.requiere_direccion && r.estado_confirmado_comercial !== 'Activo') motivos.push('cuenta marcada para dirección sin recuperar');
  if (r.motivo_confirmado === 'servicio_reclamacion' && r.estado_confirmado_comercial === 'Perdido') motivos.push('pérdida por reclamación');
  if (!motivos.length) return null;
  return { json: {
    asunto: `Meridiano · ${motivos.join(', ')}: ${r.razon_social}`,
    texto: `${quien} ha cerrado la propuesta de ${r.razon_social} (${r.id_cliente}), semana del ${String(r.fecha_corte).slice(0, 10)}.\n\n` +
      `Estado confirmado: ${r.estado_confirmado_comercial}\nMotivo confirmado: ${r.motivo_confirmado}\n` +
      `Diagnóstico del sistema correcto: ${r.diagnostico_correcto}\nFacturación en riesgo: ${r.facturacion_en_riesgo} €\n` +
      `Comentario: ${r.comentario_comercial || '—'}\n\nHistorial completo de la propuesta en el panel. Aviso generado por: ${motivos.join('; ')}.`,
  } };
}).filter(Boolean);
