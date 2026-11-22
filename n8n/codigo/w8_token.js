// Token de la baja enviado por el formulario (POST). Si no es un identificador válido se sustituye por uno nulo,
// y registrar_baja() responde «enlace no válido» sin dar de baja a nadie.
const w = $('Enlace de baja (confirmar)').first().json;
const t = String((w.body || {}).t || (w.query || {}).t || '');
const valido = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(t);
return [{ json: { p_token: valido ? t : '00000000-0000-0000-0000-000000000000' } }];
