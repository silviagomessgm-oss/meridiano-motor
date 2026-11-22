-- =====================================================================================================================
-- H5 y H6 (auditoría del diseño). Se aplica DESPUÉS de schema.sql, bajas.sql, envios.sql y controles.sql (y del piloto).
-- Se puede ejecutar varias veces. Sin bloques $$ y sin variables locales.
--
--  H5 · registrar_toque(): el comercial registra en el panel cada toque de seguimiento (llamada, correo propio o reunión)
--       con su resultado. En una propuesta por llamada, la primera llamada es su «envío»: desde ahí cuentan los toques.
--  H6 · seguimientos_estado: para cada propuesta en seguimiento, qué toque toca (días 4 · 12 · 25 desde el envío) y si está
--       sin atender (7 días vencido sin respuesta del cliente ni toque registrado).
--       seguimientos_sin_atender: lo que se escala a dirección en el correo de los lunes (W6). El grupo «control» del
--       piloto queda fuera: no recibe avisos, así que tampoco se le escala (no se contamina el experimento).
--       kpi_toques_por_grupo: % de seguimientos al día por grupo del piloto y comercial (incluido el control).
-- =====================================================================================================================

alter table propuestas add column if not exists ultimo_toque_en timestamptz;
alter table propuestas add column if not exists grupo_piloto text;          -- ya existe si se aplicó piloto.sql

create or replace function registrar_toque(p_propuesta_id bigint, p_tipo text, p_resultado text, p_nota text default null)
returns jsonb language plpgsql security definer set search_path = public
as 'begin
  if not exists (select 1 from perfiles where correo = auth.jwt() ->> ''email'') then
    raise exception ''Su usuario no tiene acceso al panel''; end if;
  if not exists (select 1 from propuestas where id = p_propuesta_id) then
    raise exception ''La propuesta no existe''; end if;
  if not es_direccion() and mi_comercial() is distinct from (select comercial_asignado from propuestas where id = p_propuesta_id) then
    raise exception ''Esta propuesta no está en su cartera''; end if;
  if (select estado from propuestas where id = p_propuesta_id) <> ''en_seguimiento'' then
    raise exception ''Solo se registran toques de propuestas aprobadas y en seguimiento''; end if;
  if coalesce(p_tipo, ''x'') not in (''llamada'', ''correo'', ''reunion'') then
    raise exception ''Tipo de toque no válido: llamada, correo o reunion''; end if;
  if coalesce(p_resultado, ''x'') not in (''contactado'', ''no_contesta'', ''buzon_de_voz'', ''reunion_fijada'') then
    raise exception ''Resultado no válido: contactado, no_contesta, buzon_de_voz o reunion_fijada''; end if;
  update propuestas
     set ultimo_toque_en = now(),
         enviada_en = case when canal = ''llamada'' and enviada_en is null and p_tipo = ''llamada'' then now() else enviada_en end
   where id = p_propuesta_id;
  insert into eventos_propuesta (propuesta_id, accion, usuario, estado_antes, estado_despues, datos)
  values (p_propuesta_id, ''toque'', auth.jwt() ->> ''email'', ''en_seguimiento'', ''en_seguimiento'',
          jsonb_build_object(''tipo'', p_tipo, ''resultado'', p_resultado, ''nota'', left(p_nota, 1000)));
  return jsonb_build_object(''ok'', true, ''propuesta_id'', p_propuesta_id);
end';
revoke all on function registrar_toque(bigint, text, text, text) from public, anon;
grant execute on function registrar_toque(bigint, text, text, text) to authenticated, service_role;

-- Estado de cada seguimiento (todas las propuestas en seguimiento ya enviadas o llamadas).
-- toque_debido: el último toque que ya toca (4, 12 o 25). toque_pendiente: el más antiguo sin actividad posterior a su
-- fecha (una respuesta o un toque registrado después de la fecha de un toque lo atiende, y también a los anteriores).
-- sin_atender: el toque pendiente lleva 7 días o más vencido.
drop view if exists kpi_toques_por_grupo, seguimientos_sin_atender, seguimientos_estado;
create view seguimientos_estado with (security_invoker = true) as
with base as (
  select p.id, p.comercial_asignado, p.comercial_nombre, p.razon_social, p.etiqueta, p.canal, p.grupo_piloto, p.enviada_en,
         greatest(p.ultima_respuesta_en, p.ultimo_toque_en) as ultima_actividad,
         (p.enviada_en at time zone 'Europe/Madrid')::date as dia_envio,
         (greatest(p.ultima_respuesta_en, p.ultimo_toque_en) at time zone 'Europe/Madrid')::date as dia_actividad,
         current_date - (p.enviada_en at time zone 'Europe/Madrid')::date as dias_desde_envio
  from propuestas p
  where p.estado = 'en_seguimiento' and p.enviada_en is not null),
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
       coalesce(current_date - (t.dia_envio + t.toque_pendiente) >= 7, false) as sin_atender
from toque t;

-- H6 · Lo que se escala a dirección: toques con 7 días de retraso, fuera del grupo de control del piloto
create view seguimientos_sin_atender with (security_invoker = true) as
  select id, comercial_asignado, comercial_nombre, razon_social, etiqueta, canal, grupo_piloto,
         enviada_en, dias_desde_envio, toque_pendiente as toque_debido, fecha_toque, dias_vencido, ultima_actividad
  from seguimientos_estado
  where sin_atender and grupo_piloto is distinct from 'control';

-- KPI · seguimientos al día por grupo del piloto y comercial (propuestas que ya tienen algún toque debido)
create view kpi_toques_por_grupo with (security_invoker = true) as
  select coalesce(grupo_piloto, 'fuera del piloto') as grupo, comercial_asignado, comercial_nombre,
         count(*) as con_toque_debido,
         count(*) filter (where not sin_atender) as al_dia,
         round(100.0 * count(*) filter (where not sin_atender) / nullif(count(*), 0), 1) as pct_al_dia
  from seguimientos_estado
  where toque_debido is not null
  group by 1, 2, 3;

grant select on seguimientos_estado, seguimientos_sin_atender, kpi_toques_por_grupo to authenticated, service_role;

-- ---------------------------------------------------------------- Comprobación
select exists (select 1 from information_schema.columns where table_name = 'propuestas' and column_name = 'ultimo_toque_en') as columna_toque,
       (select count(*) from seguimientos_estado) as en_seguimiento,
       (select count(*) from seguimientos_sin_atender) as sin_atender,
       (select string_agg(distinct coalesce(grupo_piloto, '(sin grupo)'), ', ') from propuestas) as grupos_piloto;
