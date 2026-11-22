-- =====================================================================================================================
-- Correcciones rápidas de la SEGUNDA auditoría del diseño (diseno-v2). Se aplica DESPUÉS de seguimiento.sql.
-- Se puede ejecutar varias veces. Sin bloques $$ y sin variables locales.
--
--  · Llamada nunca iniciada (N7): una propuesta por llamada aprobada y sin ninguna llamada registrada cuenta desde la
--    aprobación; si a los 4 días no hay actividad vence el toque «inicio», y a los 7 días de retraso se escala a dirección.
--  · Validador sobre el texto del comercial (N5): cada versión corregida en el panel y cada texto aprobado se revisan con
--    las mismas reglas que el validador de la IA. No bloquea (decide la persona): guarda los avisos en la versión y registra
--    el evento «aprobada_con_aviso».
-- =====================================================================================================================

-- ---------------------------------------------------------------- 1. Seguimientos: llamada nunca iniciada
drop view if exists kpi_toques_por_grupo, seguimientos_sin_atender, seguimientos_estado;
create view seguimientos_estado with (security_invoker = true) as
with base as (
  select p.id, p.comercial_asignado, p.comercial_nombre, p.razon_social, p.etiqueta, p.canal, p.grupo_piloto, p.enviada_en,
         case when p.enviada_en is null then 'inicio' else 'seguimiento' end as fase,     -- inicio: llamada aún no hecha
         greatest(p.ultima_respuesta_en, p.ultimo_toque_en) as ultima_actividad,
         (coalesce(p.enviada_en, p.aprobada_en) at time zone 'Europe/Madrid')::date as dia_envio,
         (greatest(p.ultima_respuesta_en, p.ultimo_toque_en) at time zone 'Europe/Madrid')::date as dia_actividad,
         current_date - (coalesce(p.enviada_en, p.aprobada_en) at time zone 'Europe/Madrid')::date as dias_desde_envio
  from propuestas p
  where p.estado = 'en_seguimiento'
    and (p.enviada_en is not null or (p.canal = 'llamada' and p.aprobada_en is not null))),
toque as (
  select b.*,
         case when dias_desde_envio >= 25 then 25 when dias_desde_envio >= 12 then 12 when dias_desde_envio >= 4 then 4 end as toque_debido,
         case when dias_desde_envio >= 4  and (dia_actividad is null or dia_actividad < dia_envio + 4)  then 4
              when dias_desde_envio >= 12 and (dia_actividad is null or dia_actividad < dia_envio + 12) then 12
              when dias_desde_envio >= 25 and (dia_actividad is null or dia_actividad < dia_envio + 25) then 25 end as toque_pendiente
  from base b)
select t.id, t.comercial_asignado, t.comercial_nombre, t.razon_social, t.etiqueta, t.canal, t.grupo_piloto, t.enviada_en,
       t.ultima_actividad, t.dias_desde_envio, t.toque_debido, t.toque_pendiente,
       t.dia_envio + t.toque_pendiente as fecha_toque,
       current_date - (t.dia_envio + t.toque_pendiente) as dias_vencido,
       coalesce(current_date - (t.dia_envio + t.toque_pendiente) >= 7, false) as sin_atender,
       t.fase, t.dia_envio
from toque t;

create view seguimientos_sin_atender with (security_invoker = true) as
  select id, comercial_asignado, comercial_nombre, razon_social, etiqueta, canal, grupo_piloto,
         enviada_en, dias_desde_envio, toque_pendiente as toque_debido, fecha_toque, dias_vencido, ultima_actividad,
         fase, dia_envio
  from seguimientos_estado
  where sin_atender and grupo_piloto is distinct from 'control';

create view kpi_toques_por_grupo with (security_invoker = true) as
  select coalesce(grupo_piloto, 'fuera del piloto') as grupo, comercial_asignado, comercial_nombre,
         count(*) as con_toque_debido,
         count(*) filter (where not sin_atender) as al_dia,
         round(100.0 * count(*) filter (where not sin_atender) / nullif(count(*), 0), 1) as pct_al_dia
  from seguimientos_estado
  where toque_debido is not null
  group by 1, 2, 3;
grant select on seguimientos_estado, seguimientos_sin_atender, kpi_toques_por_grupo to authenticated, service_role;

-- ---------------------------------------------------------------- 2. Validador sobre el texto del comercial (avisos)
-- Mismas reglas que el validador de la IA (n8n/codigo/w1_validador.js), salvo la de cifras trazables: el comercial puede
-- añadir cifras que conoce. Devuelve la lista de avisos (vacía si no hay ninguno).
create or replace function avisos_texto(t text) returns text[] language sql immutable
as 'select array_remove(array[
      case when t ~* ''(\mriesgo|abandon|\mchurn\M|\mfuga\M)'' then ''menciona el riesgo'' end,
      case when t ~* ''(hemos (notado|detectado|observado|visto)|nos preocupa|preocupaci[oó]n|inactiv|\mperder(le|les|la|lo)?\M|dejar de (anunciar|invertir|trabajar|contar))''
           then ''insinúa el riesgo'' end,
      case when t ~* ''(\d+\s*%|descuento|rebaja|gratis)'' then ''condición económica'' end,
      case when t ~* ''(impago|\mmoros|facturas? (pendientes?|vencidas?|impagadas?))'' then ''menciona cobros o impagos'' end
    ]::text[], null)';
grant execute on function avisos_texto(text) to authenticated, service_role;

alter table material_versiones add column if not exists avisos text[];

create or replace function avisar_version() returns trigger language plpgsql security definer set search_path = public
as 'begin
  if new.origen = ''comercial'' then new.avisos := avisos_texto(new.texto); end if;
  return new;
end';
drop trigger if exists material_versiones_avisos on material_versiones;
create trigger material_versiones_avisos before insert on material_versiones for each row execute function avisar_version();

create or replace function avisar_aprobacion() returns trigger language plpgsql security definer set search_path = public
as 'begin
  if new.estado_envio = ''aprobada'' and old.estado_envio is distinct from ''aprobada''
     and cardinality(avisos_texto(new.texto_aprobado)) > 0 then
    insert into eventos_propuesta (propuesta_id, accion, usuario, estado_antes, estado_despues, datos)
    values (new.id, ''aprobada_con_aviso'', coalesce(new.aprobada_por, ''panel''), old.estado, new.estado,
            jsonb_build_object(''avisos'', to_jsonb(avisos_texto(new.texto_aprobado))));
  end if;
  return null;
end';
drop trigger if exists propuestas_avisar_aprobacion on propuestas;
create trigger propuestas_avisar_aprobacion after update of estado_envio on propuestas
  for each row execute function avisar_aprobacion();

-- ---------------------------------------------------------------- Comprobación
-- Debe devolver: true · {"menciona el riesgo","condición económica"} · {} · número de llamadas sin iniciar
select exists (select 1 from information_schema.columns where table_name = 'material_versiones' and column_name = 'avisos') as columna_avisos,
       avisos_texto('Su cuenta está en riesgo; le ofrecemos un 10 % de descuento') as ejemplo_con_avisos,
       avisos_texto('Le resumo sus 3 campañas del último año') as ejemplo_sin_avisos,
       (select count(*) from seguimientos_estado where fase = 'inicio') as llamadas_sin_iniciar;
