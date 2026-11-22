// H6 · Escalado a dirección en el resumen de los lunes: seguimientos cuyo toque lleva 7 días vencido sin respuesta del
// cliente ni toque registrado (vista seguimientos_sin_atender; el grupo de control del piloto queda fuera) y el KPI de
// seguimientos al día por grupo del piloto. Se añade al resumen de dirección; si Supabase falla, se dice en el correo.
const base = $('Resumen para dirección').first().json || {};
const leer = nombre => {
  const n = $(nombre);
  const r = (n.isExecuted && n.first().json) || {};
  return r.statusCode >= 200 && r.statusCode < 300 && Array.isArray(r.body) ? r.body : null;
};
const sin = leer('Supabase: seguimientos sin atender');
const kpi = leer('Supabase: KPI de toques');
const dudosos = (() => { try { return leer('Supabase: envíos sin confirmar'); } catch (e) { return null; } })();
const fecha = s => { const [a, m, d] = String(s || '').slice(0, 10).split('-'); return `${d}/${m}`; };
const NOMBRE = { riesgo: 'riesgo', ampliacion: 'ampliación', lead_nuevo: 'lead nuevo', seguimiento: 'seguimiento' };

const lineas = ['', 'ESCALADO: SEGUIMIENTOS SIN ATENDER (toque vencido hace 7 días o más, sin actividad registrada)'];
if (!sin) lineas.push('No se ha podido consultar (Supabase no ha respondido). Revíselo en el panel.');
else if (!sin.length) lineas.push('Ninguno: todos los toques debidos están atendidos.');
else {
  const porCom = {};
  for (const s of sin) (porCom[s.comercial_nombre || s.comercial_asignado] ||= []).push(s);
  for (const [com, l] of Object.entries(porCom)) {
    lineas.push(`${com}: ${l.length}`);
    for (const s of l.slice(0, 10))
      lineas.push(s.fase === 'inicio'
        ? `  - ${s.razon_social} (${NOMBRE[s.etiqueta] || s.etiqueta}, llamada): aprobada el ${fecha(s.dia_envio)} y aún sin ` +
          `ninguna llamada registrada (${s.dias_vencido} días de retraso)`
        : `  - ${s.razon_social} (${NOMBRE[s.etiqueta] || s.etiqueta}, ${s.canal}): toque del día ${s.toque_debido} ` +
          `vencido hace ${s.dias_vencido} días; enviada el ${fecha(s.enviada_en)}` +
          (s.ultima_actividad ? `, última actividad el ${fecha(s.ultima_actividad)}` : ', sin actividad desde el envío'));
    if (l.length > 10) lineas.push(`  … y ${l.length - 10} más en el panel`);
  }
}
if (dudosos && dudosos.length) {
  lineas.push('', 'ENVÍOS SIN CONFIRMAR (Gmail no confirmó ni rechazó; comprobar Enviados y liberar con liberar_envio)');
  for (const d of dudosos) lineas.push(`  - Propuesta ${d.id} · ${d.razon_social} · reservada el ${fecha(d.envio_reservado_en)}`);
}
if (kpi && kpi.length) {
  lineas.push('', 'SEGUIMIENTOS AL DÍA POR GRUPO DEL PILOTO (propuestas con algún toque debido)');
  const grupos = {};
  for (const k of kpi) { const g = (grupos[k.grupo] ||= { d: 0, a: 0 }); g.d += Number(k.con_toque_debido) || 0; g.a += Number(k.al_dia) || 0; }
  for (const [g, v] of Object.entries(grupos))
    lineas.push(`  - ${g}: ${v.a} de ${v.d} al día (${v.d ? (100 * v.a / v.d).toFixed(1).replace('.', ',') : '0,0'} %)`);
  lineas.push('  El grupo de control no recibe avisos: su porcentaje es la referencia sin el sistema.');
}
const n = sin ? sin.length : null;
return [{ json: { ...base,
  asunto: base.asunto + (n ? ` · ${n} seguimiento${n === 1 ? '' : 's'} sin atender` : ''),
  texto: String(base.texto || '').includes('\n\nDetalle, alertas e indicadores')
    ? String(base.texto).replace('\n\nDetalle, alertas e indicadores', lineas.join('\n') + '\n\nDetalle, alertas e indicadores')
    : String(base.texto || '') + '\n' + lineas.join('\n'),
  seguimientos_sin_atender: n,
} }];
