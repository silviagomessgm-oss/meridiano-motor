// Junta el paquete y la rúbrica leídos de GitHub (con su versión: el sha del archivo) en la petición al auditor.
// Del archivo de rúbrica solo se usa la sección «## Mensaje de sistema».
const par = $('Parámetros de la auditoría').first().json;
function leer(nodo, ruta) {
  const r = $(nodo).first().json || {};
  if ((r.statusCode || 200) >= 300 || !r.body || !r.body.content) {
    const msg = (r.body && r.body.message) || JSON.stringify(r.body || r).slice(0, 200);
    throw new Error(`No se ha podido leer ${ruta} de GitHub (${r.statusCode || '?'}): ${msg}`);
  }
  return { texto: Buffer.from(r.body.content, 'base64').toString('utf8'), sha: r.body.sha };
}
const paquete = leer('GitHub: leer paquete', par.paquete);
const rubrica = leer('GitHub: leer rúbrica', par.rubrica);
const m = rubrica.texto.match(/## Mensaje de sistema\s*\n([\s\S]*?)(?=\n## |\s*$)/);
if (!m || m[1].trim().length < 200) throw new Error(`La rúbrica ${par.rubrica} no tiene la sección «## Mensaje de sistema»`);
return [{ json: {
  tipo: par.tipo, modelo: par.modelo,
  paquete_ruta: par.paquete, paquete_sha: paquete.sha, rubrica_ruta: par.rubrica, rubrica_sha: rubrica.sha,
  sistema: m[1].trim(), paquete: paquete.texto,
} }];
