// Alerta inmediata a dirección (2.ª auditoría): las propuestas marcadas «escalar a dirección» (cuenta clave con cambio de
// interlocutor, reclamación o cobro) se avisan el mismo martes en que se publican, no en el resumen del lunes siguiente.
const r = $('Resultado del motor').first().json || {};
const lista = (r.detalle_propuestas || []).filter(p => p.requiere_direccion === true || p.requiere_direccion === 1);
if (!r.ok || !lista.length) return [];
const cfg = $('Configuración').first().json;
const MOTIVO = { relacion_interlocutor: 'cambio de interlocutor', servicio_reclamacion: 'reclamación sin resolver',
                 cobro_financiero: 'incidencia de cobro', perdida_contacto: 'sin contacto comercial',
                 presupuesto_inversion: 'baja la inversión', rendimiento_campanas: 'bajo rendimiento de campañas',
                 sin_pedido_firmado: 'sin pedidos firmados', temporada: 'su temporada sin reservar',
                 patron_compra: 'compra menos y en menos productos', propuestas_perdidas: 'propuestas perdidas',
                 inactividad: 'inactividad' };
const eur = n => String(Math.round(Number(n) || 0)).replace(/\B(?=(\d{3})+(?!\d))/g, '.') + ' €';
return [{ json: {
  para: cfg.correo_direccion,
  asunto: `Meridiano · ${lista.length} cuenta${lista.length === 1 ? '' : 's'} clave para dirección esta semana`,
  texto: `El ciclo de retención del ${r.fecha_corte} ha publicado propuestas que requieren a dirección antes de actuar:\n\n` +
    lista.map(p => `- ${p.razon_social} · ${MOTIVO[p.motivo_principal] || p.motivo_principal} · comercial: ${p.comercial_nombre}` +
      (p.facturacion_en_riesgo != null ? ` · facturación en riesgo: ${eur(p.facturacion_en_riesgo)}` : '')).join('\n') +
    `\n\nEstán en el panel, pendientes de aprobar:\n${cfg.panel_url || ''}`,
} }];
