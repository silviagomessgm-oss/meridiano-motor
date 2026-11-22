// Sensor de Govern sobre la respuesta del auditor: debe ser el JSON pedido por la rúbrica. Se guarda SIEMPRE una fila
// (también si falla), con la respuesta tal cual, para que la evidencia no dependa de que el formato sea correcto.
const p = $('Preparar la petición').first().json;
const r = $input.first().json || {};
const VEREDICTOS = ['aprobado', 'aprobado con cambios', 'rechazado'];
const SEV = ['alta', 'media', 'baja'];
const CAMPOS = ['id', 'nodo', 'criterio', 'hallazgo', 'evidencia', 'severidad', 'correccion_propuesta'];
const fila = {
  tipo: p.tipo, modelo: p.modelo, paquete_ruta: p.paquete_ruta, paquete_sha: p.paquete_sha,
  rubrica_ruta: p.rubrica_ruta, rubrica_sha: p.rubrica_sha,
  estado: 'error', veredicto: null, resumen: null, hallazgos: [], puntos_fuertes: [],
  n_altas: 0, n_medias: 0, n_bajas: 0, avisos: [], error: null, respuesta_bruta: null,
  tokens_entrada: null, tokens_salida: null,
};
const b = r.body || {};
if ((r.statusCode || 0) >= 300 || !Array.isArray(b.content)) {
  const e = b.error || {};
  fila.error = `El modelo auditor no respondió (${r.statusCode || 'sin respuesta'}): ${e.message || JSON.stringify(b).slice(0, 300)}`;
  return [{ json: fila }];
}
fila.tokens_entrada = (b.usage || {}).input_tokens ?? null;
fila.tokens_salida = (b.usage || {}).output_tokens ?? null;
const texto = b.content.filter(c => c.type === 'text').map(c => c.text).join('\n').trim();
fila.respuesta_bruta = texto.slice(0, 100000);
const errores = [];
let j = null;
try {
  const ini = texto.indexOf('{'), fin = texto.lastIndexOf('}');
  j = JSON.parse(texto.slice(ini, fin + 1));
} catch (e) { errores.push('la respuesta no es un JSON válido'); }
if (j) {
  if (!VEREDICTOS.includes(j.veredicto)) errores.push(`veredicto «${j.veredicto}» no válido`);
  if (typeof j.resumen !== 'string' || !j.resumen.trim()) errores.push('falta el resumen');
  if (!Array.isArray(j.hallazgos)) errores.push('hallazgos no es una lista');
  else {
    if (j.hallazgos.length > 12) errores.push(`${j.hallazgos.length} hallazgos (máximo 12)`);
    j.hallazgos.forEach((h, i) => {
      const faltan = CAMPOS.filter(c => typeof (h || {})[c] !== 'string' || !h[c].trim());
      if (faltan.length) errores.push(`hallazgo ${i + 1}: faltan ${faltan.join(', ')}`);
      else if (!SEV.includes(h.severidad)) errores.push(`hallazgo ${i + 1}: severidad «${h.severidad}» no válida`);
    });
  }
  if (j.puntos_fuertes !== undefined && !Array.isArray(j.puntos_fuertes)) errores.push('puntos_fuertes no es una lista');
}
if (errores.length) {
  fila.estado = 'formato_invalido';
  fila.error = errores.slice(0, 10).join('; ');
  return [{ json: fila }];
}
const cuenta = s => j.hallazgos.filter(h => h.severidad === s).length;
Object.assign(fila, {
  estado: 'ok', veredicto: j.veredicto, resumen: j.resumen.trim(), hallazgos: j.hallazgos,
  puntos_fuertes: (j.puntos_fuertes || []).slice(0, 3), n_altas: cuenta('alta'), n_medias: cuenta('media'), n_bajas: cuenta('baja'),
});
// Coherencia con la rúbrica (aviso, no invalida: queda registrado para revisarlo)
if (fila.veredicto === 'aprobado' && (fila.n_altas || fila.n_medias)) fila.avisos.push('veredicto «aprobado» con hallazgos altos o medios');
if (fila.veredicto === 'rechazado' && !fila.n_altas) fila.avisos.push('veredicto «rechazado» sin hallazgos altos');
return [{ json: fila }];
