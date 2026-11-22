// W9 · Aviso de error (auditoría del backlog, H7): cualquier ejecución fallida de un flujo de Meridiano llega aquí
// (n8n «Error workflow») y se avisa a dirección y al responsable de datos con el flujo, el nodo, el error y el enlace.
const e = $('Error en un flujo').first().json || {};
const cfg = $('Configuración').first().json;
const ex = e.execution || {}, wf = e.workflow || {}, err = ex.error || e.trigger?.error || {};
const QUE_HACER = {
  'W0': 'La carga de datos no se ha completado: W1 y W4 no generarán propuestas hasta que termine bien. Revise la hoja y lance «Cargar ahora».',
  'W1': 'El ciclo del martes no ha publicado propuestas de riesgo. El panel conserva el plan anterior.',
  'W4': 'Los leads y ampliaciones del lunes no se han preparado.',
  'W5': 'Puede haber propuestas aprobadas sin enviar: revise «Error de envío» y «envíos sin confirmar» en el panel.',
  'W6': 'Los correos del lunes (comerciales y dirección) pueden no haber salido.',
  'W8': 'La página de baja ha fallado: si un contacto pide la baja por respuesta, regístrela desde el panel.',
};
const clave = (String(wf.name || '').match(/W\d/) || [''])[0];
return [{ json: {
  para: [cfg.correo_direccion, cfg.correo_datos].filter(Boolean).join(','),
  asunto: `Meridiano · ERROR en ${wf.name || 'un flujo'}`,
  texto: `Ha fallado una ejecución de n8n.\n\n` +
    `Flujo: ${wf.name || '(desconocido)'}\nNodo: ${ex.lastNodeExecuted || err.node?.name || '(desconocido)'}\n` +
    `Error: ${String(err.message || err.description || 'sin detalle').slice(0, 600)}\n` +
    (ex.url ? `Ejecución: ${ex.url}\n` : '') + `Modo: ${ex.mode || '-'}\n\n` +
    (QUE_HACER[clave] || 'Revise la ejecución en n8n.'),
} }];
