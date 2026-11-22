-- =====================================================================================================================
-- Correcciones de la SEGUNDA auditoría del backlog. Se aplica DESPUÉS de esquema_desplegado.sql (o en la base desplegada).
-- Se puede ejecutar varias veces. Sin bloques $$ y sin variables locales.
--
--  · Lead que ya es cliente (alta): una propuesta de lead nuevo no se crea si el lead coincide con un cliente actual (mismo
--    dominio de correo que un contacto del cliente, salvo correos genéricos tipo gmail, o misma razón social normalizada).
--    El lead se marca «descartado» con el cliente encontrado y queda el evento para gestionarlo como ampliación.
--  · Aprobadas con aviso (media): vista para el resumen de dirección de los lunes (W6).
-- =====================================================================================================================

-- Razón social normalizada: minúsculas, sin signos y sin la forma jurídica final (S.L., S.A., S.L.U.)
create or replace function razon_normalizada(t text) returns text language sql immutable
as 'select btrim(regexp_replace(btrim(regexp_replace(lower(coalesce(t, ''x'')), ''[^a-z0-9áéíóúüñ]+'', '' '', ''g'')),
                               '' (s l u|s l|s a|slu|sl|sa)$'', '' ''))';

-- ¿Es este lead un cliente actual? Devuelve el id_cliente o null
create or replace function cliente_de_lead(p_id_lead text) returns text language sql stable security definer set search_path = public
as 'select coalesce(
      (select cc.id_cliente
         from contactos cl join contactos cc on cc.id_cliente is not null
          and lower(split_part(cc.email, ''@'', 2)) = lower(split_part(cl.email, ''@'', 2))
        where cl.id_lead = p_id_lead and cl.email like ''%@%''
          and lower(split_part(cl.email, ''@'', 2)) not in (''gmail.com'', ''hotmail.com'', ''hotmail.es'', ''outlook.com'', ''outlook.es'',
              ''yahoo.com'', ''yahoo.es'', ''icloud.com'', ''live.com'', ''msn.com'', ''telefonica.net'', ''movistar.es'')
        order by cc.id_cliente limit 1),
      (select d.id_cliente from leads l join dim_clientes d on razon_normalizada(d.razon_social) = razon_normalizada(l.razon_social)
        where l.id_lead = p_id_lead order by d.id_cliente limit 1))';

create or replace function evitar_lead_cliente() returns trigger language plpgsql security definer set search_path = public
as 'begin
  if new.etiqueta = ''lead_nuevo'' and new.id_lead is not null and cliente_de_lead(new.id_lead) is not null then
    update leads set estado = ''descartado'', id_cliente_convertido = cliente_de_lead(new.id_lead) where id_lead = new.id_lead;
    insert into eventos_lead (id_lead, accion, usuario, datos)
    values (new.id_lead, ''ya_es_cliente'', coalesce(nullif(current_setting(''meridiano.usuario'', true), ''n8n''), ''n8n''),
            jsonb_build_object(''id_cliente'', cliente_de_lead(new.id_lead),
                               ''motivo'', ''El lead coincide con un cliente actual: se gestiona como ampliación de su cuenta''));
    return null;                       -- no se crea la propuesta de lead (una etiqueta por empresa)
  end if;
  return new;
end';
drop trigger if exists evitar_lead_cliente on propuestas;
create trigger evitar_lead_cliente before insert on propuestas for each row execute function evitar_lead_cliente();
revoke all on function cliente_de_lead(text), evitar_lead_cliente() from public, anon;
grant execute on function cliente_de_lead(text) to authenticated, service_role;

-- Aprobadas con aviso del validador en los últimos 7 días (resumen de dirección de W6)
create or replace view aprobadas_con_aviso with (security_invoker = true) as
  select e.propuesta_id as id, p.comercial_asignado, p.comercial_nombre, p.razon_social, p.etiqueta, e.usuario as aprobada_por,
         e.creado_en as aprobada_en, e.datos -> 'avisos' as avisos
  from eventos_propuesta e join propuestas p on p.id = e.propuesta_id
  where e.accion = 'aprobada_con_aviso' and e.creado_en >= now() - interval '7 days';
grant select on aprobadas_con_aviso to authenticated, service_role;

-- ---------------------------------------------------------------- Comprobación
-- Debe devolver: true · 'clínica sol' · número de leads nuevos que ya son clientes (se descartarán el lunes)
select exists (select 1 from pg_trigger where tgname = 'evitar_lead_cliente') as control_lead_cliente,
       razon_normalizada('Clínica Sol, S.L.') as ejemplo_normalizado,
       (select count(*) from leads l where l.estado = 'nuevo' and cliente_de_lead(l.id_lead) is not null) as leads_que_ya_son_clientes;
