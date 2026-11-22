// Página de baja con la identidad de Meridiano.
//  · GET  (el contacto pulsa el enlace del correo): pide confirmación con un botón. No da de baja todavía, porque los
//    filtros de seguridad del correo abren los enlaces automáticamente y darían de baja a quien no lo ha pedido.
//  · POST (pulsa «Confirmar la baja»): muestra el resultado de registrar_baja() en Supabase.
const abrir = $('Enlace de baja (abrir)');
const C = { ink: '#1B1712', paper: '#ECE5D3', paper2: '#E1D8BF', brass: '#C0902F', brassDark: '#8F6A22', teal: '#3E5C52',
            onInk: '#ECE5D3', onPaper: '#211D17', blanco: '#FBF8F1', alerta: '#A3412E' };
const esc = s => String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

function pagina(eyebrow, titulo, cuerpo) {
  return `<!DOCTYPE html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex"><title>Meridiano · ${esc(titulo)}</title>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:ital,wght@0,500;0,600;1,500&family=Libre+Franklin:wght@400;600&family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
 body{margin:0;background:${C.paper};color:${C.onPaper};font-family:'Libre Franklin',Arial,sans-serif;font-size:16px;line-height:1.6}
 header{background:${C.ink};padding:20px 28px}
 .logo{font-family:Fraunces,Georgia,serif;font-weight:600;font-size:24px;letter-spacing:.03em;color:${C.onInk}}
 .logo em{font-style:italic;font-weight:500;color:${C.brass}}
 main{max-width:560px;margin:48px auto;background:${C.blanco};border:1px solid ${C.paper2};padding:36px 32px}
 .eyebrow{font-family:'IBM Plex Mono',monospace;font-size:12px;letter-spacing:.08em;text-transform:uppercase;color:${C.teal}}
 .eyebrow:before{content:'';display:inline-block;width:20px;height:1px;background:${C.teal};vertical-align:middle;margin-right:10px}
 h1{font-family:Fraunces,Georgia,serif;font-weight:500;font-size:28px;line-height:1.1;margin:12px 0 18px}
 button{background:${C.brass};color:${C.ink};border:0;border-radius:2px;padding:12px 22px;font:600 15px 'Libre Franklin',Arial,sans-serif;cursor:pointer}
 button:hover{background:${C.brassDark};color:${C.blanco}}
 .nota{font-size:13px;color:#5A5246;margin-top:24px}
 .error{color:${C.alerta}}
</style></head><body>
<header><span class="logo">MERID<em>I</em>ANO</span></header>
<main><div class="eyebrow">${esc(eyebrow)}</div><h1>${esc(titulo)}</h1>${cuerpo}</main>
</body></html>`;
}

if (abrir.isExecuted) {
  const t = String((abrir.first().json.query || {}).t || '');
  if (!UUID.test(t))
    return [{ json: { html: pagina('Comunicaciones comerciales', 'Enlace no válido',
      `<p class="error">El enlace de baja está incompleto o no es válido.</p>
       <p>Si desea dejar de recibir comunicaciones comerciales, responda al correo indicando «Baja» y lo tramitaremos.</p>`) } }];
  return [{ json: { html: pagina('Comunicaciones comerciales', '¿Desea darse de baja?',
    `<p>Si confirma, Meridiano dejará de enviarle comunicaciones comerciales por correo electrónico a esta dirección.</p>
     <form method="post"><input type="hidden" name="t" value="${esc(t)}"><button type="submit">Confirmar la baja</button></form>
     <p class="nota">Puede volver a recibir información cuando lo desee: basta con pedírselo a su contacto en Meridiano.</p>`) } }];
}

// POST: resultado de Supabase (registrar_baja devuelve { ok, email } o { ok:false, motivo })
const r = $input.first().json || {};
const body = r.body && typeof r.body === 'object' ? r.body : r;
if (r.statusCode >= 300 || body.ok !== true)
  return [{ json: { html: pagina('Comunicaciones comerciales', 'No hemos podido tramitar la baja',
    `<p class="error">${body.motivo === 'enlace_no_valido' ? 'El enlace de baja no es válido o ha caducado.' : 'Se ha producido un error al registrar su solicitud.'}</p>
     <p>Responda al correo indicando «Baja» y la tramitaremos manualmente.</p>`) } }];
return [{ json: { html: pagina('Comunicaciones comerciales', 'Baja registrada',
  `<p>La dirección <strong>${esc(body.email)}</strong> ya no recibirá comunicaciones comerciales de Meridiano.</p>
   <p class="nota">Conservamos únicamente esta dirección en una lista de exclusión, para asegurarnos de no volver a escribirle.</p>`) } }];
