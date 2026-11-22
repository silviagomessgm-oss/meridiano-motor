-- =====================================================================================================================
-- H2 (auditoría del diseño) · Baja de comunicaciones comerciales, lista de exclusión y plazo de conservación
-- Se aplica DESPUÉS de schema.sql. Se puede ejecutar varias veces. Sin bloques $$ (el editor de Supabase los corta).
--
--  · contactos.token_baja: identificador aleatorio por contacto para el enlace de baja (no se puede adivinar)
--  · exclusiones: lista de correos que no deben recibir comunicaciones comerciales (se guarda solo el correo y el motivo)
--  · Ninguna propuesta por correo se aprueba ni se marca como enviada si su contacto está en la lista (trigger)
--  · registrar_baja(): la usa n8n (W8, enlace del correo) · baja_panel(): el comercial o dirección, si la piden por otra vía
--  · envios_pendientes: añade el token y si el contacto está excluido (W5 no envía a excluidos)
--  · conservacion_vencida: qué datos han superado el plazo de conservación (se revisan antes de borrar)
-- =====================================================================================================================

alter table contactos add column if not exists token_baja uuid not null default gen_random_uuid();
create unique index if not exists contactos_token_baja on contactos (token_baja);

create table if not exists exclusiones (
  email          text primary key check (email = lower(btrim(email)) and email like '%@%'),
  motivo         text not null check (motivo in ('enlace_baja', 'solicitud_contacto', 'oposicion', 'rebote_permanente')),
  origen         text not null check (origen in ('correo', 'panel')),
  registrado_por text not null,
  id_contacto    text,                    -- de qué ficha vino (informativo; el bloqueo va por correo electrónico)
  nota           text,
  creado_en      timestamptz not null default now()
);
comment on table exclusiones is 'Lista de exclusión de comunicaciones comerciales. Se conserva mientras exista el contacto para garantizar que no se le vuelve a escribir.';

-- ¿Está este correo en la lista de exclusión?  (Funciones sin variables locales ni cadenas vacías: el editor de
-- Supabase puede partir el texto por los «;» y así cada cuerpo se interpreta igual lo corte como lo corte.)
create or replace function esta_excluido(p_email text) returns boolean language sql stable security definer set search_path = public
as 'select exists (select 1 from exclusiones where email = lower(btrim(p_email)))';

-- Bloqueo en la propia tabla: da igual quién llame (panel, n8n o la consola), no se aprueba ni se envía a un excluido
create or replace function bloquear_excluidos() returns trigger language plpgsql security definer set search_path = public
as 'begin
  if new.canal = ''email'' and new.estado_envio in (''aprobada'', ''enviada'')
     and new.estado_envio is distinct from old.estado_envio
     and esta_excluido((select c.email from contactos c where c.id_contacto = new.id_contacto)) then
    raise exception ''El contacto se ha dado de baja de las comunicaciones comerciales: no se puede enviar por correo. Rechace la propuesta o contacte por teléfono.'';
  end if;
  return new;
end';
drop trigger if exists propuestas_bloquear_excluidos on propuestas;
create trigger propuestas_bloquear_excluidos before update of estado_envio on propuestas
  for each row execute function bloquear_excluidos();

-- Baja desde el enlace del correo (n8n, W8): una sola sentencia. Devuelve el correo enmascarado para la página de confirmación.
create or replace function registrar_baja(p_token uuid) returns jsonb language sql volatile security definer set search_path = public
as 'with c as (select id_contacto, id_lead, lower(btrim(email)) as email from contactos
               where token_baja = p_token and email like ''%@%''),
     alta as (insert into exclusiones (email, motivo, origen, registrado_por, id_contacto)
              select email, ''enlace_baja'', ''correo'', ''enlace del correo'', id_contacto from c
              on conflict (email) do nothing),
     traza as (insert into eventos_lead (id_lead, accion, usuario, datos)
               select id_lead, ''baja_comunicaciones'', ''enlace del correo'', jsonb_build_object(''id_contacto'', id_contacto)
               from c where id_lead is not null)
  select coalesce((select jsonb_build_object(''ok'', true, ''email'',
                            left(email, 2) || ''***'' || substr(email, position(''@'' in email))) from c),
                  jsonb_build_object(''ok'', false, ''motivo'', ''enlace_no_valido''))';

-- Comercial de la cartera a la que pertenece un contacto (cliente o lead)
create or replace function comercial_del_contacto(p_id_contacto text) returns text language sql stable security definer set search_path = public
as 'select coalesce((select d.comercial_asignado from contactos c join dim_clientes d on d.id_cliente = c.id_cliente
                     where c.id_contacto = p_id_contacto),
                    (select l.comercial_asignado from contactos c join leads l on l.id_lead = c.id_lead
                     where c.id_contacto = p_id_contacto))';

-- Baja registrada desde el panel (el contacto la pidió por teléfono, por correo o en persona). Solo sobre la propia cartera.
create or replace function baja_panel(p_id_contacto text, p_motivo text default 'solicitud_contacto', p_nota text default null)
returns jsonb language plpgsql security definer set search_path = public
as 'begin
  if not exists (select 1 from perfiles where correo = auth.jwt() ->> ''email'') then
    raise exception ''Su usuario no tiene acceso al panel''; end if;
  if not exists (select 1 from contactos where id_contacto = p_id_contacto and email like ''%@%'') then
    raise exception ''El contacto no existe o no tiene correo electrónico''; end if;
  if not es_direccion() and mi_comercial() is distinct from comercial_del_contacto(p_id_contacto) then
    raise exception ''Este contacto no está en su cartera''; end if;
  if coalesce(p_motivo, ''x'') not in (''solicitud_contacto'', ''oposicion'', ''rebote_permanente'') then
    raise exception ''Motivo de baja no válido''; end if;
  insert into exclusiones (email, motivo, origen, registrado_por, id_contacto, nota)
  select lower(btrim(email)), p_motivo, ''panel'', auth.jwt() ->> ''email'', id_contacto, left(p_nota, 500)
  from contactos where id_contacto = p_id_contacto
  on conflict (email) do nothing;
  insert into eventos_lead (id_lead, accion, usuario, datos)
  select id_lead, ''baja_comunicaciones'', auth.jwt() ->> ''email'', jsonb_build_object(''id_contacto'', id_contacto, ''motivo'', p_motivo)
  from contactos where id_contacto = p_id_contacto and id_lead is not null;
  return jsonb_build_object(''ok'', true, ''id_contacto'', p_id_contacto);
end';

-- Permisos: la baja por enlace solo la registra n8n; la del panel, un usuario con sesión
alter table exclusiones enable row level security;
drop policy if exists exclusiones_ver on exclusiones;
create policy exclusiones_ver on exclusiones for select to authenticated
  using (es_direccion() or email in (select lower(btrim(email)) from contactos));   -- contactos ya filtra por cartera (RLS)
revoke all on exclusiones from anon, authenticated;
grant select on exclusiones to authenticated;
revoke update, delete, truncate on exclusiones from service_role;
grant select, insert on exclusiones to service_role;            -- sin update ni delete: una baja no se deshace por error
-- (una reactivación solo la hace dirección desde el editor SQL, con el consentimiento nuevo registrado)
revoke all on function registrar_baja(uuid), bloquear_excluidos(), comercial_del_contacto(text) from public, anon, authenticated;
grant execute on function registrar_baja(uuid) to service_role;
revoke all on function baja_panel(text, text, text) from public, anon;
grant execute on function baja_panel(text, text, text), esta_excluido(text) to authenticated, service_role;

-- Lo que n8n tiene que enviar: ahora con el token de baja y la marca de excluido
drop view if exists envios_pendientes;
create view envios_pendientes with (security_invoker = true) as
  select p.id, p.etiqueta, p.comercial_asignado, p.razon_social, p.asunto_email, p.material_titulo, p.texto_aprobado,
         c.nombre as contacto_nombre, c.email as contacto_email, c.ficticio as contacto_ficticio, dc.nombre as comercial_nombre,
         c.token_baja, esta_excluido(c.email) as contacto_excluido, dc.correo as comercial_correo
  from propuestas p join contactos c on c.id_contacto = p.id_contacto join dim_comercial dc on dc.id_comercial = p.comercial_asignado
  where p.estado_envio = 'aprobada' and p.canal = 'email';
grant select on envios_pendientes to authenticated, service_role;

-- Para el panel: contactos con su estado de baja (respeta la RLS de contactos)
create or replace view contactos_estado with (security_invoker = true) as
  select c.id_contacto, c.id_cliente, c.id_lead, c.nombre, c.cargo, c.email, c.telefono, c.principal, c.ficticio,
         e.email is not null as dado_de_baja, e.motivo as motivo_baja, e.creado_en as baja_en
  from contactos c left join exclusiones e on e.email = lower(btrim(c.email));
grant select on contactos_estado to authenticated, service_role;

-- ---------------------------------------------------------------- Plazo de conservación (política documentada en auditoria/)
-- Leads no convertidos: 24 meses desde su última actividad · Cuentas que dejaron de ser clientes: 36 meses desde la última
-- factura (las facturas, el plazo que marque la normativa fiscal) · Lista de exclusión: mientras exista el contacto.
-- La vista solo señala; el borrado lo decide dirección (no se automatiza para no perder evidencia de una reclamación abierta).
create or replace view conservacion_vencida with (security_invoker = true) as
  select 'lead' as tipo, l.id_lead as id, l.estado,
         greatest(l.creado_en, (select max(creado_en) from eventos_lead e where e.id_lead = l.id_lead),
                  (select max(creado_en) from propuestas p where p.id_lead = l.id_lead)) as ultima_actividad
  from leads l
  where l.estado <> 'convertido'
    and greatest(l.creado_en, (select max(creado_en) from eventos_lead e where e.id_lead = l.id_lead),
                 (select max(creado_en) from propuestas p where p.id_lead = l.id_lead)) < now() - interval '24 months';
revoke all on conservacion_vencida from anon;
grant select on conservacion_vencida to service_role;

-- ---------------------------------------------------------------- Comprobación (debe devolver: true, true, true, true)
select to_regclass('public.exclusiones') is not null as tabla_exclusiones,
       exists (select 1 from information_schema.columns where table_name = 'contactos' and column_name = 'token_baja') as token_baja,
       exists (select 1 from pg_trigger where tgname = 'propuestas_bloquear_excluidos') as bloqueo,
       to_regclass('public.contactos_estado') is not null as vista_panel;
