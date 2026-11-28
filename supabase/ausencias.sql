-- =====================================================================================================================
-- Filas borradas de la hoja (auditoría del diseño v5, H1 alta; antes H11, riesgo aceptado para la demo)
-- Se aplica DESPUÉS de envios.sql, bajas.sql, el esquema desplegado y auditoria3.sql. Se puede ejecutar varias veces.
-- Sin bloques $$, sin variables locales y sin cadenas vacías: el editor de Supabase parte el texto por los «;».
--
--  W0 carga por identificador: lo que se borra de la hoja seguía vivo en Supabase y podía recibir propuestas y correos.
--  · Cada carga correcta llama a marcar_presencia_carga() con los identificadores de clientes y contactos que hay en la hoja.
--    Los que faltan quedan «ausentes» (presente_en_ultima_carga = false, con fecha); si vuelven a aparecer, se reactivan.
--  · Salvaguarda: si faltaran más del 20 % de los clientes o de los contactos, no se marca nada (hoja recortada por error)
--    y W0 avisa al responsable de datos.
--  · Las propuestas pendientes, con error o aprobadas sin enviar de un cliente o contacto ausente se cierran como
--    rechazadas con el motivo «No está en la última carga de datos» y el evento «descartada_por_carga».
--  · La base de datos impide aprobar, reservar o enviar a un ausente y no crea propuestas nuevas para él (W4 y el motor
--    no pueden saltárselo); cada propuesta descartada al crearse queda en `ejecuciones`.
--  · Solo cuentan los contactos de clientes (los de la hoja). Los contactos de leads se dan de alta en el panel.
-- =====================================================================================================================

alter table dim_clientes add column if not exists presente_en_ultima_carga boolean not null default true;
alter table dim_clientes add column if not exists ausente_desde timestamptz;
alter table contactos add column if not exists presente_en_ultima_carga boolean not null default true;
alter table contactos add column if not exists ausente_desde timestamptz;

-- ¿Está ausente de la última carga el cliente o el contacto?
create or replace function ausente_de_la_carga(p_id_cliente text, p_id_contacto text) returns boolean
language sql stable security definer set search_path = public
as 'select exists (select 1 from dim_clientes where id_cliente = p_id_cliente and not presente_en_ultima_carga)
        or exists (select 1 from contactos where id_contacto = p_id_contacto and not presente_en_ultima_carga)';

-- W0, después de una carga sin errores: marca ausentes y presentes y cierra lo que ya no se puede trabajar
create or replace function marcar_presencia_carga(p_clientes text[], p_contactos text[]) returns jsonb
language sql volatile security definer set search_path = public
as 'with
  faltan_cli as (select id_cliente from dim_clientes where not (id_cliente = any(coalesce(p_clientes, array[]::text[])))),
  faltan_con as (select id_contacto from contactos
                 where id_lead is null and not (id_contacto = any(coalesce(p_contactos, array[]::text[])))),
  apto as (select coalesce(array_length(p_clientes, 1), 0) > 0 and coalesce(array_length(p_contactos, 1), 0) > 0
                  and (select count(*) from faltan_cli) <= 0.2 * greatest((select count(*) from dim_clientes), 1)
                  and (select count(*) from faltan_con) <= 0.2 * greatest((select count(*) from contactos where id_lead is null), 1)
                  as ok),
  vuelven_cli as (update dim_clientes set presente_en_ultima_carga = true, ausente_desde = null
                  where (select ok from apto) and id_cliente = any(p_clientes) and not presente_en_ultima_carga returning 1),
  vuelven_con as (update contactos set presente_en_ultima_carga = true, ausente_desde = null
                  where (select ok from apto) and id_contacto = any(p_contactos) and not presente_en_ultima_carga returning 1),
  nuevos_cli as (update dim_clientes set presente_en_ultima_carga = false, ausente_desde = now()
                 where (select ok from apto) and id_cliente in (select id_cliente from faltan_cli) and presente_en_ultima_carga
                 returning 1),
  nuevos_con as (update contactos set presente_en_ultima_carga = false, ausente_desde = now()
                 where (select ok from apto) and id_contacto in (select id_contacto from faltan_con) and presente_en_ultima_carga
                 returning 1),
  a_cerrar as (select p.id, p.estado from propuestas p
               where (select ok from apto)
                 and (p.estado_envio in (''pendiente_aprobacion'', ''error_envio'')
                      or (p.estado_envio = ''aprobada'' and p.canal = ''email'' and p.envio_reservado_en is null))
                 and (p.id_cliente in (select id_cliente from faltan_cli) or p.id_contacto in (select id_contacto from faltan_con))),
  cerradas as (update propuestas set estado_envio = ''rechazada'', estado_tarea = ''cerrada'',
                                     motivo_rechazo = ''No está en la última carga de datos''
               where id in (select id from a_cerrar) returning id),
  eventos as (insert into eventos_propuesta (propuesta_id, accion, usuario, estado_antes, estado_despues, datos)
              select a.id, ''descartada_por_carga'', ''W0'', a.estado, ''rechazada'',
                     jsonb_build_object(''motivo'', ''No está en la última carga de datos'')
              from a_cerrar a where a.id in (select id from cerradas)),
  registro as (insert into ejecuciones (origen, estado, detalle)
               select ''n8n'', case when ok then ''ausencias_marcadas'' else ''ausencias_no_marcadas'' end,
                      jsonb_build_object(''flujo'', ''W0_ausencias'',
                                         ''clientes_ausentes'', (select count(*) from faltan_cli),
                                         ''contactos_ausentes'', (select count(*) from faltan_con),
                                         ''propuestas_cerradas'', (select count(*) from a_cerrar))
               from apto)
  select jsonb_build_object(
    ''ok'', ok,
    ''clientes_ausentes'', (select count(*) from faltan_cli), ''contactos_ausentes'', (select count(*) from faltan_con),
    ''clientes_nuevos_ausentes'', (select count(*) from nuevos_cli), ''contactos_nuevos_ausentes'', (select count(*) from nuevos_con),
    ''clientes_que_vuelven'', (select count(*) from vuelven_cli), ''contactos_que_vuelven'', (select count(*) from vuelven_con),
    ''propuestas_cerradas'', (select count(*) from cerradas),
    ''motivo'', case when not ok then ''Faltan en la hoja más del 20 % de los clientes o de los contactos (o la lista llegó vacía): no se marca nada'' end)
  from apto';

-- No se aprueba, reserva ni envía nada a un cliente o contacto ausente (da igual quién lo intente)
create or replace function bloquear_ausentes() returns trigger language plpgsql security definer set search_path = public
as 'begin
  if new.estado_envio in (''aprobada'', ''enviada'') and new.estado_envio is distinct from old.estado_envio
     and ausente_de_la_carga(new.id_cliente, new.id_contacto) then
    raise exception ''El cliente o el contacto no está en la última carga de datos (se borró de la hoja): no se puede aprobar ni enviar'';
  end if;
  return new;
end';
drop trigger if exists propuestas_bloquear_ausentes on propuestas;
create trigger propuestas_bloquear_ausentes before update of estado_envio on propuestas
  for each row execute function bloquear_ausentes();

-- No se crean propuestas nuevas para un ausente (W4 y el motor): la fila se descarta y queda registrada
create or replace function descartar_propuesta_ausente() returns trigger language plpgsql security definer set search_path = public
as 'begin
  if ausente_de_la_carga(new.id_cliente, new.id_contacto) then
    insert into ejecuciones (origen, estado, detalle)
    values (''n8n'', ''propuesta_descartada_ausente'',
            jsonb_build_object(''flujo'', ''W0_ausencias'', ''id_cliente'', new.id_cliente, ''id_contacto'', new.id_contacto,
                               ''etiqueta'', new.etiqueta, ''fecha_corte'', new.fecha_corte));
    return null;
  end if;
  return new;
end';
drop trigger if exists propuestas_descartar_ausentes on propuestas;
create trigger propuestas_descartar_ausentes before insert on propuestas
  for each row execute function descartar_propuesta_ausente();

-- W5 no recibe para reservar ninguna propuesta de un ausente
create or replace function reservar_envios(p_ids bigint[]) returns jsonb language sql volatile security definer set search_path = public
as 'with r as (
      update propuestas set envio_reservado_en = now(), envio_reserva = gen_random_uuid()
      where id = any(p_ids) and estado_envio = ''aprobada'' and canal = ''email'' and envio_reservado_en is null
        and not ausente_de_la_carga(id_cliente, id_contacto)
      returning id)
    select jsonb_build_object(''reservadas'', coalesce(jsonb_agg(id order by id), ''[]''::jsonb)) from r';

revoke all on function marcar_presencia_carga(text[], text[]), bloquear_ausentes(), descartar_propuesta_ausente()
  from public, anon, authenticated;
grant execute on function marcar_presencia_carga(text[], text[]) to service_role;
revoke all on function ausente_de_la_carga(text, text) from public, anon;
grant execute on function ausente_de_la_carga(text, text) to authenticated, service_role;
revoke all on function reservar_envios(bigint[]) from public, anon, authenticated;
grant execute on function reservar_envios(bigint[]) to service_role;

-- ---------------------------------------------------------------- Comprobación (debe devolver: true, true, true, true)
select exists (select 1 from information_schema.columns where table_name = 'contactos' and column_name = 'presente_en_ultima_carga') as columnas,
       to_regprocedure('public.marcar_presencia_carga(text[], text[])') is not null as marcar,
       exists (select 1 from pg_trigger where tgname = 'propuestas_bloquear_ausentes') as bloqueo,
       exists (select 1 from pg_trigger where tgname = 'propuestas_descartar_ausentes') as descarte;
