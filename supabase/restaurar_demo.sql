-- =====================================================================================================================
-- Meridiano · RESTAURAR LA DEMO (esquema del 22-nov-2026)
-- Deja las propuestas de la última semana como recién publicadas, para repetir la demo desde el principio.
-- Ejecutar en el SQL Editor de Supabase, entero y de una vez. Se puede ejecutar varias veces.
--
-- QUÉ BORRA (solo datos de la demo, no se puede deshacer):
--   · Eventos de acciones (aprobar, enviar, toques, respuestas, cierres, avisos…) de las propuestas de la última semana.
--     Se conservan los eventos de publicación y de material de la IA.
--   · Versiones del texto escritas por el comercial en esas propuestas.
--   · Bajas de la lista de exclusión de contactos ficticios (@….example).
-- QUÉ NO TOCA: las propuestas de semanas anteriores, las auditorías, las ejecuciones, los leads de semanas anteriores,
-- los contactos ni las tablas cargadas desde la hoja.
-- «Última semana» = fecha de corte en los 7 días anteriores a la fecha de corte más reciente (lunes y martes de esa semana).
-- =====================================================================================================================

-- 1. Eventos de acciones de esas propuestas (se conservan publicación y material de la IA)
delete from eventos_propuesta
where propuesta_id in (select id from propuestas where fecha_corte >= (select max(fecha_corte) - 7 from propuestas))
  and accion not in ('publicada', 'material_ia', 'material_plantilla');

-- 2. Versiones del texto escritas por el comercial
delete from material_versiones
where origen = 'comercial'
  and propuesta_id in (select id from propuestas where fecha_corte >= (select max(fecha_corte) - 7 from propuestas));

-- 3. Propuestas: de vuelta a «Pendiente de aprobación», sin envío, reserva, toques, respuestas ni cierre
update propuestas set
  estado_envio = 'pendiente_aprobacion', estado_tarea = 'pendiente',
  texto_aprobado = null, version_aprobada = null, aprobada_por = null, aprobada_en = null, motivo_rechazo = null,
  enviada_en = null, id_mensaje = null, error_envio = null, envio_reservado_en = null, envio_reserva = null,
  ultima_respuesta_en = null, ultimo_toque_en = null, desenlace = null, motivo_desenlace = null,
  estado_confirmado_comercial = null, motivo_confirmado = null, diagnostico_correcto = null, comentario_comercial = null,
  material_editado = null, fecha_confirmacion = null
where fecha_corte >= (select max(fecha_corte) - 7 from propuestas);

-- 4. Leads de esas propuestas que pasaron a «en curso» al enviarse: vuelven a «nuevo»
update leads set estado = 'nuevo'
where estado in ('en_curso', 'convertido')
  and id_lead in (select id_lead from propuestas
                  where id_lead is not null and fecha_corte >= (select max(fecha_corte) - 7 from propuestas));

-- 5. Bajas de prueba de contactos ficticios
delete from exclusiones where email like '%.example';

-- ---------------------------------------------------------------- Comprobación
-- Debe devolver: todas pendientes · 0 aprobadas · 0 reservas · 0 toques · 0 bajas de prueba
select (select count(*) from propuestas where fecha_corte >= (select max(fecha_corte) - 7 from propuestas)) as propuestas_restauradas,
       (select count(*) from propuestas where fecha_corte >= (select max(fecha_corte) - 7 from propuestas)
          and estado <> 'pendiente_aprobacion') as no_pendientes,
       (select count(*) from propuestas where envio_reservado_en is not null) as reservas,
       (select count(*) from propuestas where fecha_corte >= (select max(fecha_corte) - 7 from propuestas)
          and ultimo_toque_en is not null) as toques,
       (select count(*) from exclusiones where email like '%.example') as bajas_de_prueba;
