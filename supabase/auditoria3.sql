-- =====================================================================================================================
-- Auditoría del diseño v4 (W7, ejecución 108, 28-nov-2026): corrección de los dos hallazgos altos
-- Se aplica DESPUÉS de envios.sql, bajas.sql y el esquema desplegado. Se puede ejecutar varias veces.
-- Sin bloques $$, sin variables locales y sin cadenas vacías: el editor de Supabase parte el texto por los «;».
--
--  H1 · Envío que sí salió pero no consta. Una reserva en envios_sin_confirmar solo se podía liberar (lo que permite
--       reenviar). Ahora dirección, tras ver el correo en la carpeta Enviados de Gmail, lo registra con
--       confirmar_envio_manual(id, id_mensaje, fecha_real): la propuesta pasa a «En seguimiento» con la fecha real de
--       envío (desde ella corren los toques de los días 4, 12 y 25) y queda el evento «confirmar_envio_manual». Una vez
--       confirmada ya no se puede liberar (liberar_envio solo actúa sobre aprobadas sin enviar).
--  H2 · La lista de exclusión dependía del contacto. Ahora se conserva por correo electrónico de forma indefinida,
--       aunque se borre el contacto, y no se puede modificar ni borrar (salvo las bajas ficticias de la demo, .example,
--       y la reactivación expresa de dirección con un consentimiento nuevo).
--       El bloqueo ya comparaba por correo normalizado, no por identificador de contacto.
-- =====================================================================================================================

-- ---------------------------------------------------------------- H1 · confirmar a mano un envío que sí salió
create or replace function confirmar_envio_manual(p_id bigint, p_id_mensaje text, p_enviado_en timestamptz)
returns jsonb language sql volatile security definer set search_path = public
as 'with r as (update propuestas set estado_envio = ''enviada'', enviada_en = p_enviado_en, id_mensaje = btrim(p_id_mensaje),
                                    estado_tarea = ''en_curso''
               where id = p_id and estado_envio = ''aprobada'' and canal = ''email'' and envio_reservado_en is not null
                 and coalesce(length(btrim(p_id_mensaje)), 0) > 0
                 and p_enviado_en >= envio_reservado_en - interval ''5 minutes'' and p_enviado_en <= now()
                 and (es_direccion() or auth.jwt() ->> ''email'' is null)   -- dirección o el editor SQL
               returning id, id_lead),
         l as (update leads set estado = ''en_curso'' where id_lead in (select id_lead from r) and estado = ''nuevo''
               returning id_lead),
         t as (insert into eventos_propuesta (propuesta_id, accion, usuario, estado_antes, estado_despues, datos)
               select id, ''confirmar_envio_manual'', coalesce(auth.jwt() ->> ''email'', current_user), ''enviando'', ''en_seguimiento'',
                      jsonb_build_object(''id_mensaje'', btrim(p_id_mensaje), ''enviado_en'', p_enviado_en) from r)
    select jsonb_build_object(''ok'', exists (select 1 from r))';
comment on function confirmar_envio_manual(bigint, text, timestamptz) is
  'Dirección: registra como enviado un correo de envios_sin_confirmar que sí aparece en Enviados de Gmail. Exige el identificador del mensaje y una fecha entre la reserva y ahora.';

revoke all on function confirmar_envio_manual(bigint, text, timestamptz) from public, anon;
grant execute on function confirmar_envio_manual(bigint, text, timestamptz) to authenticated, service_role;

-- ---------------------------------------------------------------- H2 · lista de exclusión independiente del contacto
comment on table exclusiones is
  'Lista de exclusión de comunicaciones comerciales. Se conserva de forma indefinida por correo electrónico normalizado, aunque se borre el contacto, para que una dirección dada de baja no vuelva a recibir correo si reaparece. Solo correo, motivo, origen y fecha (interés legítimo en respetar la oposición, art. 6.1.f RGPD). id_contacto es informativo.';
comment on column exclusiones.id_contacto is 'Ficha de la que vino la baja (informativo). El bloqueo va por correo electrónico y la baja sobrevive al borrado del contacto.';

-- Reactivación (solo dirección, desde el editor SQL y con un consentimiento nuevo registrado), en una sola ejecución:
--   select set_config('meridiano.reactivar', 'correo@empresa.es', false); delete from exclusiones where email = 'correo@empresa.es';
create or replace function proteger_exclusiones() returns trigger language plpgsql set search_path = public
as 'begin
  if old.email not like ''%.example''
     and not (tg_op = ''DELETE'' and coalesce(current_setting(''meridiano.reactivar'', true), ''no'') = old.email) then
    raise exception ''La lista de exclusión no se modifica ni se borra: una baja se conserva aunque se borre el contacto'';
  end if;
  if tg_op = ''DELETE'' then return old; end if;
  return new;
end';
drop trigger if exists exclusiones_proteger on exclusiones;
create trigger exclusiones_proteger before update or delete on exclusiones
  for each row execute function proteger_exclusiones();
revoke all on function proteger_exclusiones() from public, anon, authenticated;

-- ---------------------------------------------------------------- Comprobación (debe devolver: true, true, true)
select to_regprocedure('public.confirmar_envio_manual(bigint, text, timestamptz)') is not null as confirmar_envio,
       exists (select 1 from pg_trigger where tgname = 'exclusiones_proteger') as exclusiones_protegidas,
       obj_description('public.exclusiones'::regclass) like '%indefinida%' as conservacion_indefinida;
