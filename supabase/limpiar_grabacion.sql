-- =====================================================================================================================
-- Meridiano · LIMPIEZA PARA GRABAR LA DEMO EN DIRECTO (28-nov-2026)
-- Deja Supabase como antes de lanzar el ciclo de la semana del 23-nov-2026, para que en la grabación W1 publique las
-- propuestas del modelo nuevo desde cero. Ejecutar en el SQL Editor de Supabase, entero y de una vez. Se puede repetir.
--
-- QUÉ BORRA (no se puede deshacer):
--   · Las propuestas de RIESGO con fecha de corte 23-nov-2026 (las de las pruebas de hoy con el modelo nuevo), con sus
--     eventos y versiones de texto, y lo que el motor subió para esa semana: asignaciones (plan y grupo de control),
--     estado de la etiqueta y KPIs del cuadro de mando.
--   · Las bajas de prueba de contactos ficticios (@….example).
-- QUÉ DEJA COMO ESTÁ:
--   · Las propuestas del modelo anterior (semanas anteriores): se ven en el panel como «Modelo anterior».
--   · Las propuestas de ampliación y de leads (W4), que vuelven a «Pendiente de aprobación» sin acciones.
--   · Las tablas cargadas desde la hoja, los leads, los contactos, las auditorías, las ejecuciones y resultado_acciones
--     (el simulacro se carga y se borra con sus propios scripts de demo/salida/).
-- Antes de ejecutarlo, si quieres ver qué se va a borrar: ejecuta solo la consulta de «0. Vista previa».
-- =====================================================================================================================

-- 0. Vista previa (no cambia nada)
select (select count(*) from propuestas where fecha_corte = '2026-11-23' and etiqueta = 'riesgo')               as propuestas_riesgo_a_borrar,
       (select count(*) from eventos_propuesta where propuesta_id in
          (select id from propuestas where fecha_corte = '2026-11-23' and etiqueta = 'riesgo'))                 as eventos_a_borrar,
       (select count(*) from asignaciones_ciclo where fecha_corte = '2026-11-23')                               as asignaciones_a_borrar,
       (select count(*) from propuestas where etiqueta <> 'riesgo'
          and fecha_corte >= (select max(fecha_corte) - 7 from propuestas where etiqueta <> 'riesgo'))          as ampliacion_y_leads_a_reiniciar,
       (select count(*) from exclusiones where email like '%.example')                                          as bajas_de_prueba;

-- 1. Propuestas de riesgo de la semana del 23-nov-2026, con sus eventos y versiones
delete from eventos_propuesta
where propuesta_id in (select id from propuestas where fecha_corte = '2026-11-23' and etiqueta = 'riesgo');
delete from material_versiones
where propuesta_id in (select id from propuestas where fecha_corte = '2026-11-23' and etiqueta = 'riesgo');
delete from propuestas where fecha_corte = '2026-11-23' and etiqueta = 'riesgo';

-- 2. Lo que subió el motor para esa semana (el ciclo en directo lo vuelve a crear igual)
delete from asignaciones_ciclo where fecha_corte = '2026-11-23';
delete from estado_etiqueta where fecha_corte = '2026-11-23';
delete from kpis_ciclo where fecha_corte = '2026-11-23';

-- 3. Ampliación y leads de la última semana de W4: de vuelta a «Pendiente de aprobación», sin acciones
delete from eventos_propuesta
where propuesta_id in (select id from propuestas where etiqueta <> 'riesgo'
                         and fecha_corte >= (select max(fecha_corte) - 7 from propuestas where etiqueta <> 'riesgo'))
  and accion not in ('publicada', 'material_ia', 'material_plantilla');
delete from material_versiones
where origen = 'comercial'
  and propuesta_id in (select id from propuestas where etiqueta <> 'riesgo'
                         and fecha_corte >= (select max(fecha_corte) - 7 from propuestas where etiqueta <> 'riesgo'));
update propuestas set
  estado_envio = 'pendiente_aprobacion', estado_tarea = 'pendiente',
  texto_aprobado = null, version_aprobada = null, aprobada_por = null, aprobada_en = null, motivo_rechazo = null,
  enviada_en = null, id_mensaje = null, error_envio = null, envio_reservado_en = null, envio_reserva = null,
  ultima_respuesta_en = null, ultimo_toque_en = null, desenlace = null, motivo_desenlace = null,
  estado_confirmado_comercial = null, motivo_confirmado = null, diagnostico_correcto = null, comentario_comercial = null,
  material_editado = null, fecha_confirmacion = null
where etiqueta <> 'riesgo'
  and fecha_corte >= (select max(fecha_corte) - 7 from propuestas where etiqueta <> 'riesgo');
update leads set estado = 'nuevo'
where estado in ('en_curso', 'convertido')
  and id_lead in (select id_lead from propuestas where id_lead is not null
                    and fecha_corte >= (select max(fecha_corte) - 7 from propuestas where etiqueta <> 'riesgo'));

-- 4. Bajas de prueba de contactos ficticios (la protección de la lista de exclusión permite borrar solo estas)
delete from exclusiones where email like '%.example';

-- ---------------------------------------------------------------- Comprobación
-- Debe devolver: 0 · 0 · 0 · todas pendientes (0 no pendientes) · 0 reservas · 0 bajas de prueba
select (select count(*) from propuestas where fecha_corte = '2026-11-23' and etiqueta = 'riesgo')               as riesgo_23nov,
       (select count(*) from asignaciones_ciclo where fecha_corte = '2026-11-23')                               as asignaciones_23nov,
       (select count(*) from kpis_ciclo where fecha_corte = '2026-11-23')                                       as kpis_23nov,
       (select count(*) from propuestas where etiqueta <> 'riesgo' and estado <> 'pendiente_aprobacion'
          and fecha_corte >= (select max(fecha_corte) - 7 from propuestas where etiqueta <> 'riesgo'))          as ampliacion_no_pendientes,
       (select count(*) from propuestas where envio_reservado_en is not null)                                   as reservas,
       (select count(*) from exclusiones where email like '%.example')                                          as bajas_de_prueba;
