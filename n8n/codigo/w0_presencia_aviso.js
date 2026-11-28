// Resultado de marcar_presencia_carga(): aviso al responsable de datos si hay ausentes nuevos, propuestas cerradas, si la
// salvaguarda del 20 % detuvo el marcado o si Supabase no respondió. Si no ha cambiado nada, no hay aviso.
const r = $input.first().json || {};
const b = r.body || {};
const ok = r.statusCode >= 200 && r.statusCode < 300;
const asunto = 'Meridiano · carga semanal: clientes o contactos que ya no están en la hoja';
if (!ok) return [{ json: { avisar: true, asunto: 'Meridiano · carga semanal: no se han podido marcar las filas borradas',
  texto: `Supabase no ha respondido al marcar los clientes y contactos borrados de la hoja (${(b && b.message) || r.error?.message || 'sin respuesta'}). ` +
    'Los datos se han cargado, pero lo borrado en la hoja puede seguir recibiendo propuestas hasta la próxima carga.' } }];
if (b.ok === false) return [{ json: { avisar: true, asunto: 'Meridiano · carga semanal: filas borradas SIN marcar (revisar la hoja)',
  texto: `${b.motivo}.\n\nEn la hoja faltan ${b.clientes_ausentes} clientes y ${b.contactos_ausentes} contactos que sí están en Supabase. ` +
    'Si se han borrado a propósito, vuelva a lanzar la carga; si no, recupere la hoja antes de la próxima.' } }];
const nuevos = (b.clientes_nuevos_ausentes || 0) + (b.contactos_nuevos_ausentes || 0);
if (!nuevos && !b.propuestas_cerradas && !b.clientes_que_vuelven && !b.contactos_que_vuelven) return [];
return [{ json: { avisar: true, asunto, texto:
  `Resultado de comparar la hoja con Supabase:\n\n` +
  `- Clientes que ya no están en la hoja: ${b.clientes_ausentes} (${b.clientes_nuevos_ausentes} nuevos esta semana)\n` +
  `- Contactos que ya no están en la hoja: ${b.contactos_ausentes} (${b.contactos_nuevos_ausentes} nuevos esta semana)\n` +
  `- Vuelven a estar en la hoja: ${b.clientes_que_vuelven} clientes y ${b.contactos_que_vuelven} contactos\n` +
  `- Propuestas cerradas por este motivo: ${b.propuestas_cerradas}\n\n` +
  'A un cliente o contacto ausente no se le puede aprobar ni enviar nada, ni se le preparan propuestas nuevas. ' +
  'Si se borró por error, vuelva a añadirlo en la hoja: la próxima carga lo reactiva. Si fue una petición de supresión ' +
  'de la persona, dé además de baja su correo en el panel para que nunca vuelva a recibir comunicaciones.' } }];
