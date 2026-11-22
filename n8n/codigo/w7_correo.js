// Resumen por correo de la ejecución del auditor (la evidencia completa queda en la tabla auditorias de Supabase).
const f = $('Validar respuesta del auditor').first().json;
const NOMBRE = { prueba: 'PRUEBA del flujo', diseno: 'auditoría del diseño (paso 05)', backlog: 'auditoría del backlog (paso 08)' };
const cab = [`Tipo: ${NOMBRE[f.tipo] || f.tipo}`, `Modelo auditor: ${f.modelo}`,
  `Paquete: ${f.paquete_ruta} (versión ${String(f.paquete_sha || '').slice(0, 7)})`,
  `Rúbrica: ${f.rubrica_ruta} (versión ${String(f.rubrica_sha || '').slice(0, 7)})`];
let asunto, cuerpo;
if (f.estado !== 'ok') {
  asunto = `Meridiano · auditor: ${f.estado === 'error' ? 'el modelo no respondió' : 'respuesta con formato no válido'}`;
  cuerpo = [...cab, '', `Estado: ${f.estado}`, `Detalle: ${f.error}`, '',
    'La ejecución ha quedado registrada en la tabla auditorias con la respuesta tal cual.'].join('\n');
} else {
  asunto = `Meridiano · auditor: ${f.veredicto} (${f.n_altas} altas, ${f.n_medias} medias, ${f.n_bajas} bajas)`;
  const h = f.hallazgos.map(x => `- [${x.severidad.toUpperCase()}] ${x.id} · ${x.nodo} · ${x.criterio}: ${x.hallazgo}\n    Corrección: ${x.correccion_propuesta}`);
  cuerpo = [...cab, '', `VEREDICTO: ${f.veredicto.toUpperCase()}`, f.resumen, '', 'HALLAZGOS', ...(h.length ? h : ['(ninguno)']),
    ...(f.puntos_fuertes.length ? ['', 'PUNTOS FUERTES', ...f.puntos_fuertes.map(x => `- ${x}`)] : []),
    ...(f.avisos.length ? ['', 'AVISOS DE COHERENCIA', ...f.avisos.map(x => `- ${x}`)] : []),
    '', `Tokens: ${f.tokens_entrada} de entrada, ${f.tokens_salida} de salida. Detalle completo en la tabla auditorias.`].join('\n');
}
return [{ json: { asunto, texto: cuerpo } }];
