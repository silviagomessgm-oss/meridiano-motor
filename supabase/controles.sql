-- =====================================================================================================================
-- H7 y H8 (auditoría del diseño). Se aplica DESPUÉS de schema.sql, bajas.sql y envios.sql. Se puede ejecutar varias veces.
--
--  H7 · ultima_carga(): W1 (martes) y W4 (lunes) no generan nada si la última carga de datos (W0) no terminó bien
--       (carga_ok o carga_con_avisos) o tiene más de 8 días. En su lugar avisan a dirección y al responsable de datos.
--  H8 · Con motivo «cambio de interlocutor» (acción reunion_nuevo_interlocutor) la propuesta pasa a canal llamada:
--       el contacto principal puede ser la persona que ya se fue, así que no se le escribe; el comercial llama a la empresa.
-- =====================================================================================================================

create or replace function ultima_carga() returns jsonb language sql stable security definer set search_path = public
as 'select coalesce(
      (select jsonb_build_object(
                ''apta'', coalesce(e.estado in (''carga_ok'', ''carga_con_avisos''), false) and e.fecha > now() - interval ''8 days'',
                ''estado'', e.estado, ''fecha'', e.fecha,
                ''motivo'', case when not coalesce(e.estado in (''carga_ok'', ''carga_con_avisos''), false)
                                   then ''la última carga de datos terminó en '' || coalesce(e.estado, ''estado desconocido'')
                                 when e.fecha <= now() - interval ''8 days''
                                   then ''la última carga de datos es de hace más de 8 días'' end)
       from ejecuciones e where e.detalle ->> ''flujo'' = ''W0'' order by e.fecha desc limit 1),
      jsonb_build_object(''apta'', false, ''motivo'', ''no hay ninguna carga de datos registrada''))';
revoke all on function ultima_carga() from public, anon;
grant execute on function ultima_carga() to authenticated, service_role;

-- Al publicar: canal según la acción y contacto principal de la empresa (reemplaza la versión de schema.sql)
create or replace function completar_propuesta() returns trigger language plpgsql security definer set search_path = public
as 'begin
  if new.accion_id in (''llamada_reactivacion'', ''reunion_nuevo_interlocutor'') then new.canal := ''llamada''; end if;
  if new.id_contacto is null then
    new.id_contacto := (select c.id_contacto from contactos c
                        where c.id_cliente = new.id_cliente or c.id_lead = new.id_lead
                        order by c.principal desc, c.id_contacto limit 1);
  end if;
  return new;
end';

-- Las ya publicadas y sin aprobar pasan también a llamada
update propuestas set canal = 'llamada', asunto_email = null
where accion_id = 'reunion_nuevo_interlocutor' and canal = 'email' and estado_envio in ('pendiente_aprobacion', 'error_envio');

-- ---------------------------------------------------------------- Comprobación
-- Debe devolver la última carga (apta true si W0 terminó bien hace menos de 8 días) y 0 propuestas de interlocutor por correo
select ultima_carga() as ultima_carga,
       (select count(*) from propuestas where accion_id = 'reunion_nuevo_interlocutor' and canal = 'email'
          and estado_envio in ('pendiente_aprobacion', 'error_envio')) as interlocutor_por_correo;
