-- =====================================================================================================================
-- Importe ganado al cerrar una propuesta como ganada (28-nov-2026)
-- Se aplica DESPUÉS de resultado_riesgo.sql y ANTES de volver a ejecutar panel_direccion.sql. Se puede ejecutar varias
-- veces. Sin bloques $$, sin variables locales y sin cadenas vacías: el editor de Supabase parte el texto por los «;».
--
--  Hasta ahora una propuesta ganada no guardaba cuánto se había vendido, así que el panel de dirección sumaba 0 €.
--    · propuestas.importe_ganado_eur    → lo vendido. Al cerrar como ganada (o «Recuperada» en riesgo) se rellena solo
--                                         con el importe estimado de la propuesta; el comercial puede cambiarlo.
--    · propuestas.importe_ganado_origen → propuesta (estimado) o comercial (lo ha cambiado a mano).
--    · importe_estimado(propuesta)      → importe propuesto; si no hay, tarifa del producto propuesto o sugerido; si
--                                         tampoco, la facturación en riesgo de la cuenta.
--    · accion_panel: al cerrar acepta `importe_ganado_eur`, y la acción nueva `corregir_importe` lo cambia después.
--      Corrige además un fallo: en las propuestas de riesgo no reenviaba `desenlace`, y «Recuperada» no se guardaba.
--  Las propuestas ya cerradas como ganadas reciben el importe estimado.
-- =====================================================================================================================

alter table propuestas add column if not exists importe_ganado_eur numeric;
alter table propuestas add column if not exists importe_ganado_origen text;
alter table propuestas drop constraint if exists propuestas_importe_ganado_ok;
alter table propuestas add constraint propuestas_importe_ganado_ok
  check ((importe_ganado_eur is null or importe_ganado_eur >= 0) and importe_ganado_origen in ('propuesta', 'comercial'));
comment on column propuestas.importe_ganado_eur is 'Importe vendido al cerrar la propuesta como ganada (estimado de la propuesta o corregido por el comercial).';
comment on column propuestas.importe_ganado_origen is 'propuesta = importe estimado automáticamente; comercial = cambiado a mano.';

-- Importe estimado de una propuesta (también visible en el panel como columna calculada `importe_estimado`)
create or replace function importe_estimado(p propuestas) returns numeric language sql stable set search_path = public as '
  select coalesce(p.importe_propuesto_eur,
                  (select d.tarifa_base_eur from dim_productos d where d.id_producto = p.id_producto_propuesto),
                  (select d.tarifa_base_eur from dim_productos d where d.nombre = p.producto_sugerido_nombre order by d.id_producto limit 1),
                  p.facturacion_en_riesgo)';

-- Para el formulario de cierre: rpc importe_estimado_propuesta con p_propuesta_id. Respeta la cartera de cada comercial
create or replace function importe_estimado_propuesta(p_propuesta_id bigint) returns numeric language sql stable
  set search_path = public as 'select importe_estimado(p) from propuestas p where p.id = p_propuesta_id';
revoke all on function importe_estimado_propuesta(bigint) from public, anon;
grant execute on function importe_estimado_propuesta(bigint) to authenticated, service_role;

-- Al ganar se rellena el importe (el escrito por el comercial o el estimado); si deja de estar ganada, se borra
create or replace function fijar_importe_ganado() returns trigger language plpgsql security definer set search_path = public
as 'begin
  if new.desenlace = ''ganada'' then
    if new.importe_ganado_eur is null then
      -- Importe escrito por el comercial en el formulario de cierre (lo deja accion_panel en la transacción)
      if current_setting(''meridiano.importe_ganado'', true) ~ ''^[0-9]+([.][0-9]+)?$'' then
        new.importe_ganado_eur := current_setting(''meridiano.importe_ganado'', true)::numeric;
        new.importe_ganado_origen := case when new.importe_ganado_eur = importe_estimado(new) then ''propuesta'' else ''comercial'' end;
      else
        new.importe_ganado_eur := importe_estimado(new);
        new.importe_ganado_origen := ''propuesta'';
      end if;
    end if;
    if new.importe_ganado_eur is null and new.estado_tarea = ''cerrada'' and old.estado_tarea is distinct from ''cerrada'' then
      raise exception ''Indica el importe ganado: la propuesta no tiene un importe estimado'';
    end if;
  else
    new.importe_ganado_eur := null;
    new.importe_ganado_origen := null;
  end if;
  return new;
end';
drop trigger if exists propuestas_importe_ganado on propuestas;
create trigger propuestas_importe_ganado before insert or update on propuestas
  for each row execute function fijar_importe_ganado();
revoke all on function fijar_importe_ganado() from public, anon, authenticated;

-- Panel: cierre con importe, corrección del importe y desenlace también en riesgo
create or replace function accion_panel(p_propuesta_id bigint, p_accion text, p_datos jsonb default '{}'::jsonb)
returns jsonb language plpgsql security definer set search_path = public
as 'begin
  if coalesce(length(btrim(auth.jwt() ->> ''email'')), 0) = 0 then raise exception ''Sesión no válida: vuelve a iniciar sesión''; end if;
  if not exists (select 1 from perfiles where correo = auth.jwt() ->> ''email'') then
    raise exception ''Tu usuario no tiene acceso al panel''; end if;
  if not exists (select 1 from propuestas where id = p_propuesta_id) then raise exception ''La propuesta no existe''; end if;
  if not exists (select 1 from perfiles f join propuestas p on p.id = p_propuesta_id
                 where f.correo = auth.jwt() ->> ''email'' and (f.rol = ''direccion'' or f.id_comercial = p.comercial_asignado)) then
    raise exception ''Esta propuesta no está en tu cartera''; end if;
  -- registrar_envio es solo para n8n
  if p_accion not in (''guardar_material'', ''aprobar'', ''rechazar'', ''registrar_respuesta'', ''cerrar'', ''reabrir'', ''corregir_importe'') then
    raise exception ''Acción no permitida desde el panel: %'', p_accion; end if;
  if p_accion = ''cerrar'' and (select etiqueta from propuestas where id = p_propuesta_id) = ''riesgo'' and (
       coalesce(p_datos ->> ''estado_confirmado_comercial'', ''-'') not in (''Perdido'', ''Redujo mucho'', ''Activo'', ''Pausa: volvió después'', ''No sé'')
    or coalesce(p_datos ->> ''motivo_confirmado'', ''-'') not in (''rendimiento_campanas'', ''relacion_interlocutor'', ''perdida_contacto'',
         ''servicio_reclamacion'', ''presupuesto_inversion'', ''cobro_financiero'', ''temporada'', ''otro'')
    or coalesce(p_datos ->> ''diagnostico_correcto'', ''-'') not in (''Sí'', ''No'')
    or coalesce(p_datos ->> ''desenlace'', ''ganada'') not in (''ganada'', ''perdida'', ''descartada'')) then
    raise exception ''Para cerrar hay que indicar el estado del cliente, el motivo y si el diagnóstico era correcto'';
  end if;
  if p_accion = ''cerrar'' and (select etiqueta from propuestas where id = p_propuesta_id) <> ''riesgo'' and (
       coalesce(p_datos ->> ''desenlace'', ''-'') not in (''ganada'', ''perdida'', ''descartada'')
    or (p_datos ->> ''desenlace'' <> ''ganada'' and coalesce(length(btrim(p_datos ->> ''motivo_desenlace'')), 0) = 0)) then
    raise exception ''Para cerrar hay que indicar si se ganó, se perdió o se descarta, y el motivo si no se ganó'';
  end if;
  if p_accion in (''cerrar'', ''corregir_importe'') and p_datos ? ''importe_ganado_eur''
     and jsonb_typeof(p_datos -> ''importe_ganado_eur'') <> ''null''
     and not (p_datos ->> ''importe_ganado_eur'') ~ ''^[0-9]{1,9}([.,][0-9]{1,2})?$'' then
    raise exception ''El importe ganado tiene que ser un número de euros, sin signo (por ejemplo 1250 o 1250,50)''; end if;
  if p_accion = ''cerrar'' and p_datos ? ''importe_ganado_eur'' and jsonb_typeof(p_datos -> ''importe_ganado_eur'') <> ''null''
     and p_datos ->> ''desenlace'' is distinct from ''ganada'' then
    raise exception ''El importe ganado solo se indica si la propuesta se gana''; end if;
  if p_accion = ''guardar_material'' and length(p_datos ->> ''material'') > 5000 then
    raise exception ''El material supera los 5.000 caracteres''; end if;

  -- Cambiar el importe de una propuesta ya ganada
  if p_accion = ''corregir_importe'' then
    if (select desenlace from propuestas where id = p_propuesta_id) is distinct from ''ganada'' then
      raise exception ''Solo se cambia el importe de una propuesta ganada''; end if;
    if coalesce(jsonb_typeof(p_datos -> ''importe_ganado_eur''), ''null'') = ''null'' then
      raise exception ''Indica el importe ganado''; end if;
    perform set_config(''meridiano.usuario'', auth.jwt() ->> ''email'', true);
    insert into eventos_propuesta (propuesta_id, accion, usuario, estado_antes, estado_despues, datos)
    select id, ''corregir_importe'', auth.jwt() ->> ''email'', estado, estado,
           jsonb_build_object(''importe_anterior'', importe_ganado_eur,
                              ''importe_ganado_eur'', replace(p_datos ->> ''importe_ganado_eur'', '','', ''.'')::numeric)
    from propuestas where id = p_propuesta_id;
    update propuestas set importe_ganado_eur = replace(p_datos ->> ''importe_ganado_eur'', '','', ''.'')::numeric,
                          importe_ganado_origen = ''comercial''
    where id = p_propuesta_id;
    return (select to_jsonb(x) from propuestas x where x.id = p_propuesta_id);
  end if;

  -- Importe escrito al cerrar: lo recoge el trigger fijar_importe_ganado (si no se escribe, queda el estimado)
  if p_accion = ''cerrar'' and coalesce(jsonb_typeof(p_datos -> ''importe_ganado_eur''), ''null'') <> ''null'' then
    perform set_config(''meridiano.importe_ganado'', replace(p_datos ->> ''importe_ganado_eur'', '','', ''.''), true);
  end if;

  -- Solo pasan los campos de cada acción (el panel no puede colar otros)
  perform registrar_accion(p_propuesta_id, p_accion, auth.jwt() ->> ''email'', case p_accion
    when ''guardar_material'' then jsonb_build_object(''material'', p_datos -> ''material'')
    when ''rechazar'' then jsonb_build_object(''motivo'', left(p_datos ->> ''motivo'', 1000))
    when ''registrar_respuesta'' then jsonb_build_object(''resumen'', left(p_datos ->> ''resumen'', 2000))
    when ''cerrar'' then case when (select etiqueta from propuestas where id = p_propuesta_id) = ''riesgo'' then
        jsonb_build_object(''estado_confirmado_comercial'', p_datos -> ''estado_confirmado_comercial'',
                           ''motivo_confirmado'', p_datos -> ''motivo_confirmado'',
                           ''diagnostico_correcto'', p_datos -> ''diagnostico_correcto'',
                           ''desenlace'', p_datos -> ''desenlace'',
                           ''motivo_desenlace'', left(p_datos ->> ''motivo_desenlace'', 1000),
                           ''comentario_comercial'', left(p_datos ->> ''comentario_comercial'', 2000),
                           ''importe_ganado_eur'', p_datos -> ''importe_ganado_eur'')
      else jsonb_build_object(''desenlace'', p_datos -> ''desenlace'',
                              ''motivo_desenlace'', left(p_datos ->> ''motivo_desenlace'', 1000),
                              ''comentario_comercial'', left(p_datos ->> ''comentario_comercial'', 2000),
                              ''importe_ganado_eur'', p_datos -> ''importe_ganado_eur'') end
    when ''reabrir'' then jsonb_build_object(''motivo'', left(p_datos ->> ''motivo'', 1000))
    else ''{}''::jsonb end);

  return (select to_jsonb(x) from propuestas x where x.id = p_propuesta_id);
end';
revoke all on function accion_panel(bigint, text, jsonb) from public, anon;
grant execute on function accion_panel(bigint, text, jsonb) to authenticated, service_role;

-- Propuestas ya ganadas: importe estimado
update propuestas p set importe_ganado_eur = importe_estimado(p), importe_ganado_origen = 'propuesta'
where p.desenlace = 'ganada' and p.importe_ganado_eur is null;

-- ---------------------------------------------------------------- Comprobación (debe devolver: true, true, true)
select exists (select 1 from information_schema.columns where table_name = 'propuestas' and column_name = 'importe_ganado_eur') as columna,
       exists (select 1 from pg_trigger where tgname = 'propuestas_importe_ganado') as trigger_importe,
       not exists (select 1 from propuestas where desenlace = 'ganada' and importe_ganado_eur is null
                     and importe_estimado(propuestas) is not null) as ganadas_con_importe;
