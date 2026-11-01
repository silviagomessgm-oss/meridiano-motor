// Sensor computacional de Govern (equivalente a propuestas.validar_llm, con dos reglas más):
//  1. toda cifra del borrador debe aparecer en el contexto enviado a la IA;
//  2. ninguna condición económica (porcentajes, descuento, rebaja, gratis);
//  3. no menciona el riesgo de abandono;   4. máximo 200 palabras.
// Si falla cualquier regla o la IA no responde, se conserva la plantilla del motor y se anota el motivo.
const propuestas = $('Separar propuestas').all();
const numeros = s => new Set(String(s || '').match(/\d+(?:[.,]\d+)?/g) || []);
return $input.all().map((it, i) => {
  const p = propuestas[i].json;
  const r = it.json || {};
  const texto = Array.isArray(r.content)
    ? r.content.filter(c => c.type === 'text').map(c => c.text).join('\n').trim() : '';
  const motivos = [];
  if (!texto) motivos.push('IA no disponible' + (r.error ? ` (${String(r.error.message || r.error).slice(0, 80)})` : ''));
  else {
    const ctx = numeros(p.contexto_ia);
    const inventadas = [...numeros(texto)].filter(n => !ctx.has(n)).sort();
    if (inventadas.length) motivos.push(`cifras no trazables [${inventadas.join(', ')}]`);
    if (/\d+\s*%|descuento|rebaja|gratis/i.test(texto)) motivos.push('condición económica');
    if (/riesgo|abandon/i.test(texto)) motivos.push('menciona el riesgo');
    const palabras = texto.split(/\s+/).filter(Boolean).length;
    if (palabras > 200) motivos.push(`${palabras} palabras`);
  }
  const ok = motivos.length === 0;
  return { json: {
    fecha_corte: p.fecha_corte, id_cliente: p.id_cliente, razon_social: p.razon_social,
    comercial_asignado: p.comercial_asignado, comercial_nombre: p.comercial_nombre, correo_comercial: p.correo_comercial,
    material_cuerpo: ok ? texto : p.material_cuerpo,
    fuente_material: ok ? 'llm' : `plantilla (IA descartada: ${motivos.join('; ')})`,
    valido: ok,
  } };
});
