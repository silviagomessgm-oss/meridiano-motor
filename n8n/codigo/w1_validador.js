// Sensor computacional de Govern (equivalente a propuestas.validar_llm, con dos reglas más):
//  1. toda cifra del borrador debe aparecer en el contexto enviado a la IA;
//  2. ninguna condición económica (porcentajes, descuento, rebaja, gratis);
//  3. no menciona ni insinúa el riesgo de abandono (lista ampliada tras la auditoría, H3);   4. máximo 200 palabras;
//  5. texto completo (no cortado por max_tokens) y sin asunto ni formato Markdown (cuerpo listo para enviar).
// Si falla cualquier regla o la IA no responde, se conserva la plantilla del motor y se anota el motivo.
const propuestas = $('Separar propuestas').all();
// H3: el cliente no debe saber que el sistema le considera en riesgo. Se rechaza tanto la mención directa como
// las fórmulas que la insinúan («hemos notado que ha reducido…», «no queremos perderle»).
const RIESGO = [
  /\briesgo/i, /abandon/i, /\bchurn\b/i, /\bfuga\b/i, /\bperder(le|les|la|lo)?\b/i, /\bdejar de (anunciar|invertir|trabajar|contar)/i,
  /\bhemos (notado|detectado|observado|visto)\b/i, /\bnos preocupa/i, /\bpreocupaci[oó]n\b/i, /\binactiv/i,
  /\b(ca[ií]da|descenso|bajada|disminuci[oó]n) (de|en) (su )?(inversi[oó]n|actividad|campañas)/i, /\bprobabilidad\b/i,
  /\bimpago/i, /\bmoros/i, /\bfacturas? (pendientes?|vencidas?|impagadas?)/i,
];
const numeros = s => new Set(String(s || '').match(/\d+(?:[.,]\d+)?/g) || []);
return $input.all().map((it, i) => {
  const p = propuestas[i].json;
  const r = it.json || {};
  const texto = Array.isArray(r.content)
    ? r.content.filter(c => c.type === 'text').map(c => c.text).join('\n').trim() : '';
  const motivos = [];
  if (texto) {
    if (r.stop_reason === 'max_tokens') motivos.push('texto cortado por el límite de longitud');
    if (/^\s*(\*\*)?\s*asunto\s*:/im.test(texto) || /\*\*|^\s*#/m.test(texto)) motivos.push('incluye asunto o formato Markdown');
  }
  if (!texto) motivos.push('IA no disponible' + (r.error ? ` (${String(r.error.message || r.error).slice(0, 80)})` : ''));
  else {
    const ctx = numeros(p.contexto_ia);
    const inventadas = [...numeros(texto)].filter(n => !ctx.has(n)).sort();
    if (inventadas.length) motivos.push(`cifras no trazables [${inventadas.join(', ')}]`);
    if (/\d+\s*%|descuento|rebaja|gratis/i.test(texto)) motivos.push('condición económica');
    const insinua = RIESGO.filter(r => r.test(texto)).map(r => (texto.match(r) || [''])[0].toLowerCase());
    if (insinua.length) motivos.push(`menciona o insinúa el riesgo [${insinua.join(', ')}]`);
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
