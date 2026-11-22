// Un correo por propuesta aceptada, con el TEXTO APROBADO (el que quedó congelado al pulsar «Aceptar»),
// maquetado con la identidad de Meridiano (misma paleta y tipografías que la web y el panel) y con pie de baja (H2).
// Bloqueos: contacto ficticio fuera del modo demo · contacto en la lista de exclusión · falta el enlace de baja.
const cfg = $('Configuración').first().json;
const filas = $input.all().map(i => i.json).filter(p => p && p.id);

const C = { ink: '#1B1712', paper: '#ECE5D3', paper2: '#E1D8BF', brass: '#C0902F', brassDark: '#8F6A22',
            teal: '#3E5C52', onInk: '#ECE5D3', onPaper: '#211D17', blanco: '#FBF8F1' };
const SERIF = "Fraunces, Georgia, 'Times New Roman', serif";
const SANS = "'Libre Franklin', 'Helvetica Neue', Arial, sans-serif";
const MONO = "'IBM Plex Mono', 'Courier New', monospace";
const esc = s => String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
const EYEBROW = { riesgo: 'Su cuenta en Meridiano', ampliacion: 'Propuesta para su marca', lead_nuevo: 'Primer contacto',
                  seguimiento: 'Seguimiento' };

// Párrafos del texto aprobado; las líneas que empiezan por «- » o «• » se maquetan como lista
function cuerpo(texto) {
  return String(texto || '').trim().split(/\n\s*\n/).map(bloque => {
    const lineas = bloque.split('\n');
    if (lineas.every(l => /^\s*[-•]\s+/.test(l)))
      return `<ul style="margin:0 0 16px;padding-left:20px;">${lineas.map(l =>
        `<li style="margin:0 0 6px;">${esc(l.replace(/^\s*[-•]\s+/, ''))}</li>`).join('')}</ul>`;
    return `<p style="margin:0 0 16px;">${lineas.map(esc).join('<br>')}</p>`;
  }).join('\n');
}

function html(p, enlaceBaja, asunto) {
  const demo = cfg.modo_demo ? `
  <tr><td style="background:${C.paper2};border-bottom:1px solid ${C.brassDark};padding:10px 32px;font-family:${MONO};font-size:11px;letter-spacing:.06em;text-transform:uppercase;color:${C.brassDark};">
    Correo de demostración · En real iría a ${esc(p.contacto_nombre)} &lt;${esc(p.contacto_email)}&gt;
  </td></tr>` : '';
  return `<!DOCTYPE html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="light only"><title>${esc(asunto)}</title>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:ital,wght@0,500;0,600;1,500&family=Libre+Franklin:wght@400;600&family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet">
</head>
<body style="margin:0;padding:0;background:${C.paper};">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:${C.paper};">
<tr><td align="center" style="padding:24px 12px;">
<table role="presentation" width="600" cellpadding="0" cellspacing="0" style="width:100%;max-width:600px;background:${C.blanco};border:1px solid ${C.paper2};">
  <tr><td style="background:${C.ink};padding:22px 32px;">
    <span style="font-family:${SERIF};font-size:26px;font-weight:600;letter-spacing:.03em;color:${C.onInk};">MERID<em style="font-style:italic;font-weight:500;color:${C.brass};">I</em>ANO</span>
    <span style="font-family:${MONO};font-size:11px;letter-spacing:.08em;text-transform:uppercase;color:${C.brass};padding-left:12px;">Departamento comercial</span>
  </td></tr>${demo}
  <tr><td style="padding:32px 32px 8px;">
    <div style="font-family:${MONO};font-size:11px;letter-spacing:.08em;text-transform:uppercase;color:${C.teal};margin-bottom:10px;">&mdash;&nbsp; ${esc(EYEBROW[p.etiqueta] || 'Meridiano')}</div>
    <h1 style="margin:0 0 20px;font-family:${SERIF};font-weight:500;font-size:24px;line-height:1.15;color:${C.onPaper};">${esc(asunto)}</h1>
  </td></tr>
  <tr><td style="padding:0 32px 8px;font-family:${SANS};font-size:15px;line-height:1.6;color:${C.onPaper};">
${cuerpo(p.texto_aprobado)}
  </td></tr>
  <tr><td style="padding:8px 32px 28px;">
    <div style="border-top:1px solid ${C.brass};width:40px;margin:0 0 12px;"></div>
    <div style="font-family:${SERIF};font-size:17px;font-weight:500;color:${C.onPaper};">${esc(p.comercial_nombre)}</div>
    <div style="font-family:${SANS};font-size:13px;color:${C.teal};">Meridiano · Departamento comercial${p.comercial_correo ? ` · <a href="mailto:${esc(p.comercial_correo)}" style="color:${C.teal};">${esc(p.comercial_correo)}</a>` : ''}</div>
  </td></tr>
  <tr><td style="background:${C.paper2};padding:18px 32px;font-family:${SANS};font-size:11.5px;line-height:1.55;color:#5A5246;">
    Recibe este mensaje porque ${p.etiqueta === 'lead_nuevo' ? 'aceptó recibir información comercial de Meridiano' : 'su empresa mantiene una relación comercial con Meridiano'}.
    Meridiano trata sus datos de contacto para gestionar esa relación; puede ejercer sus derechos de acceso, rectificación, oposición y supresión escribiendo a ${esc(cfg.correo_privacidad || 'privacidad@meridiano.example')}.<br><br>
    Si no desea recibir más comunicaciones comerciales de Meridiano, puede
    <a href="${esc(enlaceBaja)}" style="color:${C.brassDark};font-weight:600;">darse de baja aquí</a>.
  </td></tr>
</table>
<div style="font-family:${MONO};font-size:10px;letter-spacing:.08em;text-transform:uppercase;color:${C.brassDark};padding-top:14px;">Meridiano · Medio para el público senior · Caso de estudio ficticio</div>
</td></tr></table>
</body></html>`;
}

return filas.map(p => {
  const enlaceBaja = cfg.baja_url && p.token_baja ? `${cfg.baja_url}?t=${encodeURIComponent(p.token_baja)}` : null;
  const bloqueo = p.contacto_excluido ? 'El contacto se ha dado de baja de las comunicaciones comerciales'
    : (!cfg.modo_demo && p.contacto_ficticio) ? 'Contacto ficticio: no se envía fuera del modo demo'
    : !enlaceBaja ? 'Falta el enlace de baja (baja_url en Configuración o token del contacto): no se envía sin él'
    : null;
  const asunto = p.asunto_email || p.material_titulo || `Meridiano · ${p.razon_social}`;
  const aviso = cfg.modo_demo ? `[Correo de demostración. En real iría a ${p.contacto_nombre} <${p.contacto_email}>]\n\n` : '';
  return { json: {
    id: p.id, razon_social: p.razon_social, bloqueo,
    para: p.contacto_email,
    asunto,
    html: enlaceBaja ? html(p, enlaceBaja, asunto) : null,
    // Versión en texto (registro y lectores sin HTML)
    texto: aviso + p.texto_aprobado + `\n\n${p.comercial_nombre}\nMeridiano · Departamento comercial`
           + (enlaceBaja ? `\n\nSi no desea recibir más comunicaciones comerciales de Meridiano: ${enlaceBaja}` : ''),
  } };
});
