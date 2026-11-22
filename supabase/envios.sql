-- =====================================================================================================================
-- H1 (auditoría del diseño) · Envío idempotente: cada versión aprobada de una propuesta sale como mucho una vez
-- Se aplica DESPUÉS de schema.sql y bajas.sql. Se puede ejecutar varias veces. Sin bloques $$ y sin variables locales.
--
--  «enviando» es el estado derivado de una propuesta aprobada por correo (columna generada `estado`): lo pone aprobar()
--  y lo quita registrar_envio(). Lo que faltaba era impedir que dos ejecuciones de W5 la enviaran a la vez:
--  · reservar_envios(): W5 reserva en una sola sentencia las que va a enviar; si otra ejecución ya las reservó, no las recibe
--  · Sin reserva no se puede marcar «enviada» (trigger); al volver a aprobar se limpia la reserva anterior
--  · Una reserva que no se confirma no se reintenta sola (como mucho un envío): aparece en envios_sin_confirmar y
--    dirección la libera con liberar_envio() tras comprobar en Gmail que el correo no salió
-- =====================================================================================================================

alter table propuestas add column if not exists envio_reservado_en timestamptz;
alter table propuestas add column if not exists envio_reserva uuid;

create or replace function control_envio() returns trigger language plpgsql security definer set search_path = public
as 'begin
  if new.estado_envio = ''aprobada'' and old.estado_envio is distinct from ''aprobada'' then
    new.envio_reservado_en := null;
    new.envio_reserva := null;
  end if;
  if new.canal = ''email'' and new.estado_envio = ''enviada'' and old.estado_envio is distinct from ''enviada''
     and new.envio_reservado_en is null then
    raise exception ''Envío sin reserva: solo W5 marca una propuesta como enviada, después de reservarla'';
  end if;
  return new;
end';
drop trigger if exists propuestas_control_envio on propuestas;
create trigger propuestas_control_envio before update of estado_envio on propuestas
  for each row execute function control_envio();

-- W5: reserva atómica. Devuelve solo las que ha reservado ESTA llamada.
create or replace function reservar_envios(p_ids bigint[]) returns jsonb language sql volatile security definer set search_path = public
as 'with r as (
      update propuestas set envio_reservado_en = now(), envio_reserva = gen_random_uuid()
      where id = any(p_ids) and estado_envio = ''aprobada'' and canal = ''email'' and envio_reservado_en is null
      returning id)
    select jsonb_build_object(''reservadas'', coalesce(jsonb_agg(id order by id), ''[]''::jsonb)) from r';

-- Reservas sin resultado (n8n se paró entre la reserva y el registro): no se reenvían solas
create or replace view envios_sin_confirmar with (security_invoker = true) as
  select p.id, p.razon_social, p.comercial_asignado, p.asunto_email, p.envio_reservado_en
  from propuestas p
  where p.estado_envio = 'aprobada' and p.canal = 'email' and p.envio_reservado_en < now() - interval '15 minutes';

-- Dirección, tras comprobar en la carpeta Enviados de Gmail que el correo NO salió: vuelve a dejarla lista para W5
create or replace function liberar_envio(p_id bigint) returns jsonb language sql volatile security definer set search_path = public
as 'with r as (update propuestas set envio_reservado_en = null, envio_reserva = null
               where id = p_id and estado_envio = ''aprobada'' and envio_reservado_en is not null
                 and (es_direccion() or auth.jwt() ->> ''email'' is null)   -- dirección, n8n o el editor SQL
               returning id),
         t as (insert into eventos_propuesta (propuesta_id, accion, usuario, estado_antes, estado_despues, datos)
               select id, ''liberar_envio'', coalesce(auth.jwt() ->> ''email'', current_user), ''enviando'', ''enviando'',
                      ''{}''::jsonb from r)
    select jsonb_build_object(''ok'', exists (select 1 from r))';

-- Lo que n8n tiene que enviar: solo las aprobadas que nadie ha reservado
drop view if exists envios_pendientes;
create view envios_pendientes with (security_invoker = true) as
  select p.id, p.etiqueta, p.comercial_asignado, p.razon_social, p.asunto_email, p.material_titulo, p.texto_aprobado,
         c.nombre as contacto_nombre, c.email as contacto_email, c.ficticio as contacto_ficticio, dc.nombre as comercial_nombre,
         c.token_baja, esta_excluido(c.email) as contacto_excluido, dc.correo as comercial_correo
  from propuestas p join contactos c on c.id_contacto = p.id_contacto join dim_comercial dc on dc.id_comercial = p.comercial_asignado
  where p.estado_envio = 'aprobada' and p.canal = 'email' and p.envio_reservado_en is null;

-- Permisos
revoke all on function reservar_envios(bigint[]), control_envio() from public, anon, authenticated;
grant execute on function reservar_envios(bigint[]) to service_role;
revoke all on function liberar_envio(bigint) from public, anon;
grant execute on function liberar_envio(bigint) to authenticated, service_role;
grant select on envios_pendientes, envios_sin_confirmar to authenticated, service_role;

-- ---------------------------------------------------------------- Comprobación (debe devolver: true, true, true)
select exists (select 1 from information_schema.columns where table_name = 'propuestas' and column_name = 'envio_reservado_en') as columna_reserva,
       exists (select 1 from pg_trigger where tgname = 'propuestas_control_envio') as control,
       to_regclass('public.envios_sin_confirmar') is not null as vista_sin_confirmar;
