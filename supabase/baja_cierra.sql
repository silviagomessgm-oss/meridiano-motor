-- =====================================================================================================================
-- Una baja de comunicaciones cierra las propuestas abiertas del contacto (28-nov-2026)
-- Se aplica DESPUÉS de bajas.sql, auditoria3.sql e importe_ganado.sql. Se puede ejecutar varias veces. Sin bloques $$,
-- sin variables locales y sin cadenas vacías: el editor de Supabase parte el texto por los «;».
--
--  Hasta ahora la baja solo impedía aprobar o enviar por correo: la propuesta seguía en «Pendientes de aprobar» o «En
--  seguimiento» y el comercial perdía tiempo revisándola. Ahora, en cuanto el correo entra en la lista de exclusión
--  (desde el panel con baja_panel o desde el enlace del correo, W8), sus propuestas abiertas pasan a «Cerradas o rechazadas»:
--    · pendientes, con error de envío o aprobadas sin reservar → rechazadas, motivo «El contacto se ha dado de baja de las
--      comunicaciones comerciales»;
--    · en seguimiento → cerradas con resultado «descartada», motivo «Baja de comunicaciones comerciales» (en las de riesgo
--      no se inventa estado, motivo ni diagnóstico: quedan vacíos y no cuentan en la validación del modelo);
--    · cada una deja el evento «cerrada_por_baja».
--  Además, el motor y W4 ya no crean propuestas nuevas para un contacto dado de baja (quedan anotadas en `ejecuciones`).
--  Las bajas registradas antes de este cambio se aplican al ejecutar el parche.
-- =====================================================================================================================

-- El cierre por baja es completo sin los datos de riesgo (estado, motivo y diagnóstico no se conocen)
alter table propuestas drop constraint if exists cierre_completo;
alter table propuestas add constraint cierre_completo check (estado_tarea <> 'cerrada'
    or (estado_envio = 'rechazada' and motivo_rechazo is not null)
    or (estado_envio <> 'rechazada' and etiqueta = 'riesgo' and estado_confirmado_comercial is not null
        and motivo_confirmado is not null and diagnostico_correcto is not null)
    or (estado_envio <> 'rechazada' and etiqueta <> 'riesgo' and desenlace is not null
        and (desenlace = 'ganada' or motivo_desenlace is not null))
    or (estado_envio <> 'rechazada' and desenlace = 'descartada' and motivo_desenlace = 'Baja de comunicaciones comerciales'));

-- Cierra las propuestas abiertas de los contactos con ese correo
create or replace function cerrar_propuestas_de_baja(p_email text, p_usuario text) returns void
language plpgsql security definer set search_path = public
as 'begin
  perform set_config(''meridiano.usuario'', coalesce(p_usuario, ''baja''), true);
  insert into eventos_propuesta (propuesta_id, accion, usuario, estado_antes, estado_despues, datos)
  select p.id, ''cerrada_por_baja'', coalesce(p_usuario, ''baja''), p.estado,
         case when p.estado = ''en_seguimiento'' then ''cerrada'' else ''rechazada'' end,
         jsonb_build_object(''motivo'', ''Baja de comunicaciones comerciales'')
  from propuestas p join contactos c on c.id_contacto = p.id_contacto
  where lower(btrim(c.email)) = lower(btrim(p_email))
    and (p.estado in (''pendiente_aprobacion'', ''error_envio'', ''en_seguimiento'')
         or (p.estado = ''enviando'' and p.envio_reservado_en is null));

  update propuestas p set estado_envio = ''rechazada'', estado_tarea = ''cerrada'',
                          motivo_rechazo = ''El contacto se ha dado de baja de las comunicaciones comerciales''
  from contactos c
  where c.id_contacto = p.id_contacto and lower(btrim(c.email)) = lower(btrim(p_email))
    and (p.estado in (''pendiente_aprobacion'', ''error_envio'') or (p.estado = ''enviando'' and p.envio_reservado_en is null));

  update propuestas p set estado_tarea = ''cerrada'', fecha_confirmacion = now(), desenlace = ''descartada'',
                          motivo_desenlace = ''Baja de comunicaciones comerciales''
  from contactos c
  where c.id_contacto = p.id_contacto and lower(btrim(c.email)) = lower(btrim(p_email)) and p.estado = ''en_seguimiento'';
end';

create or replace function cerrar_por_baja() returns trigger language plpgsql security definer set search_path = public
as 'begin
  perform cerrar_propuestas_de_baja(new.email, new.registrado_por);
  return new;
end';
drop trigger if exists exclusiones_cerrar_propuestas on exclusiones;
create trigger exclusiones_cerrar_propuestas after insert on exclusiones
  for each row execute function cerrar_por_baja();

-- No se crean propuestas nuevas para un contacto dado de baja
create or replace function descartar_propuesta_excluida() returns trigger language plpgsql security definer set search_path = public
as 'begin
  if new.id_contacto is not null and esta_excluido((select c.email from contactos c where c.id_contacto = new.id_contacto)) then
    insert into ejecuciones (origen, estado, detalle)
    values (''n8n'', ''propuesta_descartada_baja'',
            jsonb_build_object(''id_cliente'', new.id_cliente, ''id_lead'', new.id_lead, ''id_contacto'', new.id_contacto,
                               ''etiqueta'', new.etiqueta, ''fecha_corte'', new.fecha_corte));
    return null;
  end if;
  return new;
end';
drop trigger if exists propuestas_descartar_excluidos on propuestas;
create trigger propuestas_descartar_excluidos before insert on propuestas
  for each row execute function descartar_propuesta_excluida();

revoke all on function cerrar_propuestas_de_baja(text, text), cerrar_por_baja(), descartar_propuesta_excluida()
  from public, anon, authenticated;

-- Bajas ya registradas: cerrar lo que siga abierto
select count(*) as correos_revisados from (select cerrar_propuestas_de_baja(e.email, e.registrado_por) from exclusiones e) x;

-- ---------------------------------------------------------------- Comprobación (debe devolver: true, true, true)
select exists (select 1 from pg_trigger where tgname = 'exclusiones_cerrar_propuestas') as cierre_por_baja,
       exists (select 1 from pg_trigger where tgname = 'propuestas_descartar_excluidos') as sin_propuestas_nuevas,
       not exists (select 1 from propuestas p join contactos c on c.id_contacto = p.id_contacto
                   where esta_excluido(c.email)
                     and p.estado in ('pendiente_aprobacion', 'error_envio', 'en_seguimiento')) as nada_abierto;
