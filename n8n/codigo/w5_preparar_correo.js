// Un correo por propuesta aceptada, con el TEXTO APROBADO (el que quedó congelado al pulsar «Aceptar»).
// Seguridad: un contacto ficticio nunca recibe correo fuera del modo demo.
const cfg = $('Configuración').first().json;
const filas = $input.all().map(i => i.json).filter(p => p && p.id);
return filas.map(p => {
  const bloqueo = (!cfg.modo_demo && p.contacto_ficticio) ? 'Contacto ficticio: no se envía fuera del modo demo' : null;
  const aviso = cfg.modo_demo ? `[Correo de demostración. En real iría a ${p.contacto_nombre} <${p.contacto_email}>]\n\n` : '';
  return { json: {
    id: p.id, razon_social: p.razon_social, bloqueo,
    para: p.contacto_email,
    asunto: p.asunto_email || p.material_titulo || `Meridiano · ${p.razon_social}`,
    texto: aviso + p.texto_aprobado + `\n\n${p.comercial_nombre}\nMeridiano · Departamento comercial`,
  } };
});
