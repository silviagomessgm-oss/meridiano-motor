-- =====================================================================================================================
-- Panel de dirección centrado en el EQUIPO (28-nov-2026)
-- Dirección no ve clientes: ve cómo trabaja el equipo, cómo va la venta y qué conviene mejorar.
-- Se aplica DESPUÉS de modelo_churn.sql, resultado_riesgo.sql e importe_ganado.sql. Se puede ejecutar varias veces.
-- Sin bloques $$, sin variables locales y sin cadenas vacías: el editor de Supabase parte el texto por los «;».
--
--   equipo_semana          · por semana, comercial y tipo de propuesta: embudo (publicadas → aprobadas → enviadas →
--                            con respuesta → cerradas → ganadas), tiempos, uso de la IA, diagnóstico y facturación.
--   equipo_ahora           · por comercial, en este momento: carga abierta y retrasos (sin nombres de clientes).
--   recomendaciones_direccion · reglas fijas y explicables sobre las cuatro últimas semanas: qué mejorar y dónde.
-- Ninguna vista devuelve nombres de clientes ni identificadores de cuenta.
-- =====================================================================================================================

create or replace view equipo_semana with (security_invoker = true) as
  select p.fecha_corte, p.comercial_asignado, p.comercial_nombre, p.etiqueta,
         count(*)                                                                         as publicadas,
         count(*) filter (where p.aprobada_en is not null)                                as aprobadas,
         count(*) filter (where p.estado_envio = 'rechazada')                             as rechazadas,
         count(*) filter (where p.estado in ('pendiente_aprobacion', 'error_envio'))      as pendientes,
         count(*) filter (where p.enviada_en is not null or (p.canal = 'llamada' and p.aprobada_en is not null)) as en_marcha,
         count(*) filter (where p.ultima_respuesta_en is not null)                        as con_respuesta,
         count(*) filter (where p.estado = 'cerrada')                                     as cerradas,
         count(*) filter (where p.estado = 'cerrada' and p.desenlace = 'ganada')          as ganadas,
         round(100.0 * count(*) filter (where p.aprobada_en is not null) / nullif(count(*), 0), 1)            as pct_aprobadas,
         round(100.0 * count(*) filter (where p.estado = 'cerrada' and p.desenlace = 'ganada')
               / nullif(count(*) filter (where p.estado = 'cerrada'), 0), 1)                                  as pct_ganadas,
         round(avg(extract(epoch from (p.aprobada_en - p.creado_en)) / 86400.0)::numeric, 1)                  as dias_hasta_aprobar,
         round(avg(extract(epoch from (p.fecha_confirmacion - coalesce(p.enviada_en, p.aprobada_en))) / 86400.0)::numeric, 1) as dias_hasta_cerrar,
         count(*) filter (where p.fuente_material = 'llm')                                as textos_ia,
         count(*) filter (where p.aprobada_en is not null
                            and exists (select 1 from material_versiones v where v.propuesta_id = p.id and v.origen = 'comercial')) as aprobadas_editadas,
         count(*) filter (where p.diagnostico_correcto = 'Sí')                            as diagnostico_si,
         count(*) filter (where p.diagnostico_correcto is not null)                       as diagnostico_respondido,
         coalesce(sum(p.facturacion_en_riesgo), 0)                                        as facturacion_en_riesgo,
         coalesce(sum(p.facturacion_en_riesgo) filter (where p.estado = 'cerrada' and p.desenlace = 'ganada'), 0) as facturacion_recuperada,
         coalesce(sum(p.importe_propuesto_eur) filter (where p.estado = 'cerrada' and p.desenlace = 'ganada'), 0) as importe_ganado_propuesto,
         -- Facturación: lo aprobado (importe estimado de las propuestas aprobadas) y lo ganado (lo que declara el comercial)
         coalesce(round(sum(importe_estimado(p)) filter (where p.aprobada_en is not null)), 0)                    as importe_aprobado,
         coalesce(sum(p.importe_ganado_eur) filter (where p.estado = 'cerrada' and p.desenlace = 'ganada'), 0)   as importe_ganado,
         count(*) filter (where p.estado = 'cerrada' and p.desenlace = 'ganada' and p.importe_ganado_origen = 'comercial') as ganadas_importe_cambiado
  from propuestas p
  group by p.fecha_corte, p.comercial_asignado, p.comercial_nombre, p.etiqueta;
comment on view equipo_semana is 'Embudo y rendimiento por semana, comercial y tipo de propuesta (sin clientes).';

create or replace view equipo_ahora with (security_invoker = true) as
  select c.id_comercial as comercial_asignado, c.nombre as comercial_nombre,
         (select count(*) from propuestas p where p.comercial_asignado = c.id_comercial and p.estado = 'pendiente_aprobacion') as pendientes_aprobar,
         (select count(*) from propuestas p where p.comercial_asignado = c.id_comercial and p.estado = 'pendiente_aprobacion'
            and p.creado_en < now() - interval '3 days')                                                             as pendientes_mas_3_dias,
         (select count(*) from propuestas p where p.comercial_asignado = c.id_comercial and p.estado = 'en_seguimiento') as en_seguimiento,
         (select count(*) from seguimientos_estado s where s.comercial_asignado = c.id_comercial
            and s.toque_pendiente is not null and s.dias_vencido >= 0
            and s.grupo_piloto is distinct from 'control')                                                           as toques_pendientes,
         (select count(*) from seguimientos_sin_atender s where s.comercial_asignado = c.id_comercial)               as sin_atender_7_dias,
         (select count(*) from propuestas p where p.comercial_asignado = c.id_comercial and p.estado = 'error_envio') as errores_envio
  from dim_comercial c;
comment on view equipo_ahora is 'Carga abierta y retrasos de cada comercial en este momento (sin clientes).';

-- Reglas de mejora sobre las cuatro últimas semanas de propuestas (umbrales fijos, a revisar por dirección)
create or replace view recomendaciones_direccion with (security_invoker = true) as
with ult as (select max(fecha_corte) as f from propuestas where etiqueta = 'riesgo'),
     ventana as (select * from equipo_semana where fecha_corte > (select f from ult) - 28),
     por_com as (select comercial_asignado, comercial_nombre,
                        sum(publicadas) as publicadas, sum(aprobadas) as aprobadas, sum(cerradas) as cerradas, sum(ganadas) as ganadas,
                        sum(textos_ia) as textos_ia, sum(aprobadas_editadas) as editadas,
                        sum(diagnostico_si) as diag_si, sum(diagnostico_respondido) as diag_n
                 from ventana group by comercial_asignado, comercial_nombre),
     equipo as (select sum(cerradas) as cerradas, sum(ganadas) as ganadas, sum(aprobadas) as aprobadas,
                       sum(editadas) as editadas, sum(diag_si) as diag_si, sum(diag_n) as diag_n from por_com),
     kpi as (select indicador, valor from kpis_ciclo where fecha_corte = (select max(fecha_corte) from kpis_ciclo))
select * from (
  -- Capacidad: cuentas en riesgo que se quedan sin plaza
  select 1 as prioridad, 'Capacidad' as ambito, null::text as comercial,
         'Esta semana ' || k.valor || ' cuentas en riesgo se quedaron sin plaza (tope de 4 por comercial). Valorar subir el tope, priorizar solo las cuentas clave o reforzar el equipo.' as recomendacion,
         k.valor as dato
  from kpi k where k.indicador = 'Aplazadas por capacidad' and k.valor ~ '^[0-9]+$' and k.valor::int > 12
  union all
  -- Medición: sin grupo de control no se puede medir el efecto
  select 1, 'Medición', null,
         'Esta semana no hay grupo de control: el efecto de las acciones no se puede medir. Revisar el sorteo (hoy solo en riesgo medio) o reservar una parte de las cuentas de riesgo alto.',
         k.valor
  from kpi k where k.indicador = 'Grupo de control' and k.valor in ('0', '0.0')
  union all
  -- Ritmo: propuestas sin aprobar desde hace más de 3 días
  select 2, 'Ritmo', a.comercial_nombre,
         a.comercial_nombre || ' tiene ' || a.pendientes_mas_3_dias || ' propuestas sin decidir desde hace más de 3 días. Revisar su carga o repartir parte de su cartera.',
         a.pendientes_mas_3_dias::text
  from equipo_ahora a where a.pendientes_mas_3_dias > 0
  union all
  -- Seguimiento: toques vencidos más de 7 días
  select 2, 'Seguimiento', a.comercial_nombre,
         a.comercial_nombre || ' tiene ' || a.sin_atender_7_dias || ' seguimientos con el toque vencido hace más de 7 días. Sin seguimiento la propuesta se pierde: acordar un hueco fijo semanal para los toques.',
         a.sin_atender_7_dias::text
  from equipo_ahora a where a.sin_atender_7_dias > 0
  union all
  -- Aprobación baja: el comercial no se cree las cuentas que le propone el sistema
  select 3, 'Aprobación', c.comercial_nombre,
         c.comercial_nombre || ' aprueba el ' || round(100.0 * c.aprobadas / c.publicadas) || ' % de lo que se le propone (equipo: '
           || round(100.0 * (select aprobadas from equipo) / nullif((select sum(publicadas) from por_com), 0)) || ' %). Revisar con él los motivos de rechazo y si las cuentas encajan con su cartera.',
         round(100.0 * c.aprobadas / c.publicadas)::text
  from por_com c where c.publicadas >= 5 and 100.0 * c.aprobadas / c.publicadas < 50
  union all
  -- Conversión: un comercial gana claramente menos que el equipo
  select 3, 'Conversión', c.comercial_nombre,
         c.comercial_nombre || ' gana el ' || round(100.0 * c.ganadas / c.cerradas) || ' % de lo que cierra frente al '
           || round(100.0 * (select ganadas from equipo) / nullif((select cerradas from equipo), 0)) || ' % del equipo. Sesión de buenas prácticas con quien más gana y revisar sus motivos de pérdida.',
         round(100.0 * c.ganadas / c.cerradas)::text
  from por_com c
  where c.cerradas >= 5 and (select cerradas from equipo) >= 10
    and 100.0 * c.ganadas / c.cerradas < 100.0 * (select ganadas from equipo) / (select cerradas from equipo) - 15
  union all
  -- Modelo: el equipo no comparte el diagnóstico
  select 4, 'Modelo', null,
         'El equipo considera correcto el diagnóstico del modelo solo en el ' || round(100.0 * e.diag_si / e.diag_n) || ' % de los cierres. Revisar con los comerciales los motivos que da el modelo.',
         round(100.0 * e.diag_si / e.diag_n)::text
  from equipo e where e.diag_n >= 10 and 100.0 * e.diag_si / e.diag_n < 60
  union all
  -- IA: los comerciales reescriben la mayoría de los textos
  select 4, 'Textos de la IA', null,
         'Los comerciales corrigen el ' || round(100.0 * e.editadas / e.aprobadas) || ' % de los textos antes de aprobarlos. Revisar el prompt o las plantillas con los cambios más repetidos.',
         round(100.0 * e.editadas / e.aprobadas)::text
  from equipo e where e.aprobadas >= 10 and 100.0 * e.editadas / e.aprobadas > 60
  union all
  -- Verificación: recuperadas declaradas sin pedido en los datos
  select 5, 'Verificación', r.comercial_nombre,
         r.comercial_nombre || ' ha cerrado ' || sum(r.recuperadas_sin_pedido_aun) || ' cuentas como recuperadas que aún no tienen pedido en los datos. Confirmar en la próxima reunión.',
         sum(r.recuperadas_sin_pedido_aun)::text
  from recuperacion_riesgo r where r.fecha_corte > (select f from ult) - 28
  group by r.comercial_nombre having sum(r.recuperadas_sin_pedido_aun) > 0
) t
order by prioridad, ambito, comercial;
comment on view recomendaciones_direccion is
  'Qué mejorar: reglas fijas sobre las cuatro últimas semanas (capacidad, medición, ritmo, seguimiento, aprobación, conversión, modelo, IA y verificación). Sin clientes.';

revoke all on equipo_semana, equipo_ahora, recomendaciones_direccion from anon;
grant select on equipo_semana, equipo_ahora, recomendaciones_direccion to authenticated, service_role;

-- ---------------------------------------------------------------- Comprobación (debe devolver: true, true, true)
select to_regclass('public.equipo_semana') is not null as equipo_semana,
       to_regclass('public.equipo_ahora') is not null as equipo_ahora,
       to_regclass('public.recomendaciones_direccion') is not null as recomendaciones;
