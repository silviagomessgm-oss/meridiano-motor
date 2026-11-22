// Junta el paquete y la rúbrica leídos de GitHub (con su versión: el sha del archivo) en la petición al auditor.
// Del archivo de rúbrica solo se usa la sección «## Mensaje de sistema».
const par = $('Parámetros de la auditoría').first().json;
// Decodifica base64 → UTF-8 sin depender de Buffer ni atob (no siempre existen en el entorno de los nodos Code de n8n)
function base64Utf8(b64) {
  const A = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/';
  const s = String(b64).replace(/[^A-Za-z0-9+/]/g, '');
  const bytes = [];
  for (let i = 0; i < s.length; i += 4) {
    const n = (A.indexOf(s[i]) << 18) | (A.indexOf(s[i + 1]) << 12) | ((A.indexOf(s[i + 2]) & 63) << 6) | (A.indexOf(s[i + 3]) & 63);
    bytes.push((n >> 16) & 255);
    if (i + 2 < s.length) bytes.push((n >> 8) & 255);
    if (i + 3 < s.length) bytes.push(n & 255);
  }
  let out = '', i = 0;
  while (i < bytes.length) {
    const c = bytes[i++];
    if (c < 128) out += String.fromCharCode(c);
    else if (c < 224) out += String.fromCharCode(((c & 31) << 6) | (bytes[i++] & 63));
    else if (c < 240) out += String.fromCharCode(((c & 15) << 12) | ((bytes[i++] & 63) << 6) | (bytes[i++] & 63));
    else {
      const cp = (((c & 7) << 18) | ((bytes[i++] & 63) << 12) | ((bytes[i++] & 63) << 6) | (bytes[i++] & 63)) - 0x10000;
      out += String.fromCharCode(0xD800 + (cp >> 10), 0xDC00 + (cp & 1023));
    }
  }
  return out;
}
function leer(nodo, ruta) {
  const r = $(nodo).first().json || {};
  if ((r.statusCode || 200) >= 300 || !r.body || !r.body.content) {
    const msg = (r.body && r.body.message) || JSON.stringify(r.body || r).slice(0, 200);
    throw new Error(`No se ha podido leer ${ruta} de GitHub (${r.statusCode || '?'}): ${msg}`);
  }
  return { texto: base64Utf8(r.body.content), sha: r.body.sha };
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
