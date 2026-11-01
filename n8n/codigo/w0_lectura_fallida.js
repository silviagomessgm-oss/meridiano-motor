// Una pestaña no se ha podido leer (nombre cambiado, permiso, identificador de la hoja…): la carga se detiene sin escribir nada.
const it = $input.first().json || {};
const err = it.error || {};
const detalle = typeof err === 'string' ? err : (err.message || err.description || JSON.stringify(err).slice(0, 500));
return [{ json: {
  registro: { origen: 'n8n', estado: 'carga_detenida', detalle: { flujo: 'W0', fatales: [`lectura de la hoja: ${detalle}`] } },
  asunto: 'Meridiano · carga semanal de datos DETENIDA (no se ha podido leer la hoja)',
  texto: `No se ha podido leer la hoja de datos, así que no se ha cargado nada.\n\n` +
    `Error: ${detalle}\n\nComprueba el identificador de la hoja en el nodo Configuración, que las 8 pestañas existen con su nombre exacto ` +
    `y que la credencial de Google tiene acceso. Después vuelve a lanzar «W0 · Carga semanal».`,
} }];
