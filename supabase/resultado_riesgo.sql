-- =====================================================================================================================
-- Resultado de la acción al cerrar una propuesta de riesgo (28-nov-2026)
-- Se aplica DESPUÉS de modelo_churn.sql. Se puede ejecutar varias veces. Sin bloques $$, sin variables locales y sin
-- cadenas vacías: el editor de Supabase parte el texto por los «;».
--
--  Al cerrar una propuesta de riesgo el comercial decía cómo está la cuenta (Activo, Perdido…), pero no si la acción
--  la había ganado. Ahora el cierre de riesgo usa también el campo `desenlace` que ya tenían las demás etiquetas:
--    · ganada     → «Recuperada: ha firmado un pedido»
--    · perdida    → «No recuperada»
--    · descartada → «Sin decisión del cliente»
--  registrar_accion('cerrar') ya guarda `desenlace` y `motivo_desenlace` para cualquier etiqueta; aquí se exige en las de
--  riesgo y se comprueba que sea coherente con el estado confirmado (una cuenta «Perdido» no puede estar «Recuperada»).
--  Si la cuenta se cierra como «Perdido» o «Redujo mucho» sin resultado, se completa como «No recuperada».
--  Las propuestas de riesgo cerradas antes de este cambio no se tocan.
--
--  Para medirlo, la vista `recuperacion_riesgo` compara lo que declara el comercial con lo que dicen los datos: pedidos del
--  cliente en los 60 días siguientes al envío (o a la aprobación, si fue por llamada), por comercial y semana.
-- =====================================================================================================================

create or replace function exigir_resultado_riesgo() returns trigger language plpgsql security definer set search_path = public
as 'begin
  if new.estado_tarea = ''cerrada'' and old.estado_tarea is distinct from ''cerrada''
     and new.etiqueta = ''riesgo'' and new.estado_envio <> ''rechazada'' then
    -- Una cuenta perdida o que ha reducido mucho es, por definición, «No recuperada»: se completa sola
    if new.desenlace is null and new.estado_confirmado_comercial in (''Perdido'', ''Redujo mucho'') then
      new.desenlace := ''perdida'';
    end if;
    if new.desenlace is null then
      raise exception ''Indica el resultado de la acción: recuperada (ha firmado un pedido), no recuperada o sin decisión del cliente'';
    end if;
    if new.desenlace = ''ganada'' and new.estado_confirmado_comercial in (''Perdido'', ''Redujo mucho'') then
      raise exception ''Una cuenta «%» no puede cerrarse como recuperada'', new.estado_confirmado_comercial;
    end if;
  end if;
  return new;
end';
drop trigger if exists propuestas_exigir_resultado_riesgo on propuestas;
create trigger propuestas_exigir_resultado_riesgo before update of estado_tarea on propuestas
  for each row execute function exigir_resultado_riesgo();
revoke all on function exigir_resultado_riesgo() from public, anon, authenticated;

-- Medición: lo declarado por el comercial frente a los pedidos reales del cliente tras la acción
create or replace view recuperacion_riesgo with (security_invoker = true) as
  select p.fecha_corte, p.comercial_asignado, p.comercial_nombre,
         count(*)                                                                    as cerradas,
         count(*) filter (where p.desenlace = 'ganada')                              as recuperadas,
         count(*) filter (where p.desenlace = 'perdida')                             as no_recuperadas,
         count(*) filter (where p.desenlace = 'descartada')                          as sin_decision,
         count(*) filter (where p.desenlace is null)                                 as sin_resultado_anterior_al_cambio,
         round(100.0 * count(*) filter (where p.desenlace = 'ganada')
               / nullif(count(*) filter (where p.desenlace is not null), 0), 1)      as pct_recuperadas,
         count(*) filter (where pe.importe > 0)                                      as con_pedido_60_dias,
         count(*) filter (where p.desenlace = 'ganada' and coalesce(pe.importe, 0) = 0) as recuperadas_sin_pedido_aun,
         coalesce(sum(pe.importe), 0)                                                as importe_pedidos_60_dias,
         sum(p.facturacion_en_riesgo)                                                as facturacion_en_riesgo
  from propuestas p
  left join lateral (
    select sum(c.importe_eur) as importe from fact_campanas c
    where c.id_cliente = p.id_cliente
      and c.fecha_orden >  coalesce(p.enviada_en, p.aprobada_en)::date
      and c.fecha_orden <= coalesce(p.enviada_en, p.aprobada_en)::date + 60) pe on true
  where p.etiqueta = 'riesgo' and p.estado_tarea = 'cerrada' and p.estado_envio <> 'rechazada'
  group by p.fecha_corte, p.comercial_asignado, p.comercial_nombre;
comment on view recuperacion_riesgo is
  'Propuestas de riesgo cerradas por semana y comercial: resultado declarado (recuperada, no recuperada, sin decisión) y pedidos reales del cliente en los 60 días siguientes al envío.';
revoke all on recuperacion_riesgo from anon;
grant select on recuperacion_riesgo to authenticated, service_role;

-- ---------------------------------------------------------------- Comprobación (debe devolver: true, true)
select exists (select 1 from pg_trigger where tgname = 'propuestas_exigir_resultado_riesgo') as exige_resultado,
       to_regclass('public.recuperacion_riesgo') is not null as vista_recuperacion;
