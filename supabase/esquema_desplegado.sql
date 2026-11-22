-- =====================================================================================================================
-- Meridiano · ESQUEMA DESPLEGADO en Supabase (volcado del 22-nov-2026)
-- Auditoría del backlog, H1 (reproducibilidad): funciones, vistas y triggers tal como están en producción, incluidas las
-- piezas cuyo SQL original se perdió con el contenedor de desarrollo: preparar_lunes(), balance_lunes(), el piloto
-- (sorteo_piloto, asignar_grupo_piloto, piloto_seguimiento), seguimientos_debidos, plan_vigente, alta de leads y consentimiento.
-- Generado con supabase/volcar_esquema.sql (consulta de catálogo) → CSV → este archivo.
--
-- SECRETOS: la URL de n8n y el token de los webhooks se han sustituido por <URL_N8N> y <TOKEN_WEBHOOK>. Al restaurar, poner
-- los valores reales en Supabase (Database → Webhooks), nunca en el repositorio.
-- LEGADO: las tablas y vistas de una iteración anterior del TFP (next_best_action, log_correcciones, v_catalogo…) no las usa
-- ningún flujo actual; se listan al final solo como inventario.
-- Orden de restauración: schema.sql → auditorias.sql → bajas.sql → envios.sql → controles.sql → seguimiento.sql → auditoria2.sql → este archivo
-- (las funciones y vistas son «create or replace»; los triggers se recrean).
-- =====================================================================================================================

-- ---------------------------------------------------------------- Columnas añadidas fuera de schema.sql
alter table propuestas add column if not exists grupo_piloto text;
alter table leads add column if not exists consentimiento_medio text;

-- ---------------------------------------------------------------- Funciones
-- accion_panel
CREATE OR REPLACE FUNCTION public.accion_panel(p_propuesta_id bigint, p_accion text, p_datos jsonb DEFAULT '{}'::jsonb)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
declare
  v_correo text := auth.jwt() ->> 'email';
  perfil perfiles;
  prop propuestas;
begin
  if coalesce(v_correo, '') = '' then raise exception 'Sesión no válida: vuelve a iniciar sesión'; end if;
  select * into perfil from perfiles where correo = v_correo;
  if not found then raise exception 'Tu usuario no tiene acceso al panel'; end if;
  select * into prop from propuestas where id = p_propuesta_id;
  if not found then raise exception 'La propuesta no existe'; end if;
  if perfil.rol <> 'direccion' and perfil.id_comercial is distinct from prop.comercial_asignado then
    raise exception 'Esta propuesta no está en tu cartera'; end if;
  -- registrar_envio es solo para n8n
  if p_accion not in ('guardar_material', 'aprobar', 'rechazar', 'registrar_respuesta', 'cerrar', 'reabrir') then
    raise exception 'Acción no permitida desde el panel: %', p_accion; end if;
  if p_accion = 'cerrar' and prop.etiqueta = 'riesgo' and (
       coalesce(p_datos ->> 'estado_confirmado_comercial', '') not in ('Perdido', 'Redujo mucho', 'Activo', 'Pausa: volvió después', 'No sé')
    or coalesce(p_datos ->> 'motivo_confirmado', '') not in ('rendimiento_campanas', 'relacion_interlocutor', 'perdida_contacto',
         'servicio_reclamacion', 'presupuesto_inversion', 'cobro_financiero', 'temporada', 'otro')
    or coalesce(p_datos ->> 'diagnostico_correcto', '') not in ('Sí', 'No')) then
    raise exception 'Para cerrar hay que indicar el estado del cliente, el motivo y si el diagnóstico era correcto';
  end if;
  if p_accion = 'cerrar' and prop.etiqueta <> 'riesgo' and (
       coalesce(p_datos ->> 'desenlace', '') not in ('ganada', 'perdida', 'descartada')
    or (p_datos ->> 'desenlace' <> 'ganada' and coalesce(btrim(p_datos ->> 'motivo_desenlace'), '') = '')) then
    raise exception 'Para cerrar hay que indicar si se ganó, se perdió o se descarta, y el motivo si no se ganó';
  end if;
  if p_accion = 'guardar_material' and length(coalesce(p_datos ->> 'material', '')) > 5000 then
    raise exception 'El material supera los 5.000 caracteres'; end if;
  -- Solo pasan los campos de cada acción (el panel no puede colar otros)
  return registrar_accion(p_propuesta_id, p_accion, v_correo, case p_accion
    when 'guardar_material' then jsonb_build_object('material', p_datos -> 'material')
    when 'rechazar' then jsonb_build_object('motivo', left(coalesce(p_datos ->> 'motivo', ''), 1000))
    when 'registrar_respuesta' then jsonb_build_object('resumen', left(coalesce(p_datos ->> 'resumen', ''), 2000))
    when 'cerrar' then case when prop.etiqueta = 'riesgo' then
        jsonb_build_object('estado_confirmado_comercial', p_datos -> 'estado_confirmado_comercial',
                           'motivo_confirmado', p_datos -> 'motivo_confirmado',
                           'diagnostico_correcto', p_datos -> 'diagnostico_correcto',
                           'comentario_comercial', left(coalesce(p_datos ->> 'comentario_comercial', ''), 2000))
      else jsonb_build_object('desenlace', p_datos -> 'desenlace',
                              'motivo_desenlace', left(coalesce(p_datos ->> 'motivo_desenlace', ''), 1000),
                              'comentario_comercial', left(coalesce(p_datos ->> 'comentario_comercial', ''), 2000)) end
    when 'reabrir' then jsonb_build_object('motivo', left(coalesce(p_datos ->> 'motivo', ''), 1000))
    else '{}'::jsonb end);
end $function$;

-- alta_lead_panel
CREATE OR REPLACE FUNCTION public.alta_lead_panel(p jsonb)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
declare
  v_correo text := auth.jwt() ->> 'email'; perfil perfiles; v_id text; v_com text; v_cons boolean;
begin
  if coalesce(v_correo, '') = '' then raise exception 'Sesión no válida: vuelve a iniciar sesión'; end if;
  select * into perfil from perfiles where correo = v_correo;
  if not found then raise exception 'Tu usuario no tiene acceso al panel'; end if;
  v_com := case when perfil.rol = 'direccion' then coalesce(p ->> 'comercial_asignado', comercial_para_lead()) else perfil.id_comercial end;
  if coalesce(btrim(p ->> 'razon_social'), '') = '' or coalesce(btrim(p ->> 'nombre'), '') = '' then
    raise exception 'Indica la empresa y la persona de contacto'; end if;
  v_cons := coalesce((p ->> 'consentimiento_comercial')::boolean, false);
  if v_cons and coalesce(p ->> 'consentimiento_medio', '') not in ('telefono', 'presencial', 'email') then
    raise exception 'Indica cómo se obtuvo el consentimiento (teléfono, presencial o email)'; end if;
  insert into leads (razon_social, categoria, provincia, tamano, web, origen, comercial_asignado, consentimiento_comercial,
                     consentimiento_fecha, consentimiento_medio, consentimiento_texto, mensaje, creado_por)
  values (left(btrim(p ->> 'razon_social'), 200), left(p ->> 'categoria', 100), left(p ->> 'provincia', 100), left(p ->> 'tamano', 50),
          left(p ->> 'web', 200), 'puerta_fria', v_com, v_cons, case when v_cons then now() end,
          case when v_cons then p ->> 'consentimiento_medio' end, case when v_cons then left(p ->> 'consentimiento_nota', 1000) end,
          left(p ->> 'mensaje', 2000), v_correo)
  returning id_lead into v_id;
  insert into contactos (id_contacto, id_lead, nombre, cargo, email, telefono, principal, ficticio)
  values ('CT-' || v_id || '-1', v_id, left(btrim(p ->> 'nombre'), 150), left(p ->> 'cargo', 100),
          nullif(lower(btrim(coalesce(p ->> 'email', ''))), ''), left(p ->> 'telefono', 30), true,
          coalesce((p ->> 'ficticio')::boolean, true));
  insert into eventos_lead (id_lead, accion, usuario, datos)
  values (v_id, 'alta_puerta_fria', v_correo, jsonb_build_object('consentimiento', v_cons));
  return (select to_jsonb(l) from leads l where id_lead = v_id);
end $function$;

-- alta_lead_web
CREATE OR REPLACE FUNCTION public.alta_lead_web(p jsonb)
 RETURNS text
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
declare v_id text; v_email text := lower(btrim(coalesce(p ->> 'email', '')));
begin
  if coalesce(btrim(p ->> 'razon_social'), '') = '' or coalesce(btrim(p ->> 'nombre'), '') = '' then
    raise exception 'Indica la empresa y tu nombre'; end if;
  if v_email !~ '^[^@\s]+@[^@\s]+\.[^@\s]+$' then raise exception 'El correo no es válido'; end if;
  if coalesce((p ->> 'acepta_comercial')::boolean, false) is not true or coalesce(btrim(p ->> 'texto_consentimiento'), '') = '' then
    raise exception 'Hay que aceptar recibir información comercial'; end if;
  if length(p::text) > 6000 then raise exception 'Datos demasiado largos'; end if;
  insert into leads (razon_social, categoria, provincia, tamano, web, origen, comercial_asignado, consentimiento_comercial,
                     consentimiento_fecha, consentimiento_medio, consentimiento_texto, mensaje, creado_por)
  values (left(btrim(p ->> 'razon_social'), 200), left(p ->> 'categoria', 100), left(p ->> 'provincia', 100), left(p ->> 'tamano', 50),
          left(p ->> 'web', 200), 'formulario_web', comercial_para_lead(), true, now(), 'formulario_web',
          left(p ->> 'texto_consentimiento', 1000), left(p ->> 'mensaje', 2000), 'formulario_web')
  returning id_lead into v_id;
  insert into contactos (id_contacto, id_lead, nombre, cargo, email, telefono, principal, ficticio)
  values ('CT-' || v_id || '-1', v_id, left(btrim(p ->> 'nombre'), 150), left(p ->> 'cargo', 100), v_email,
          left(p ->> 'telefono', 30), true, false);
  insert into eventos_lead (id_lead, accion, usuario, datos)
  values (v_id, 'alta_formulario_web', 'formulario_web', jsonb_build_object('texto_consentimiento', p ->> 'texto_consentimiento'));
  return v_id;
end $function$;

-- asignar_grupo_piloto
CREATE OR REPLACE FUNCTION public.asignar_grupo_piloto()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
begin
  if new.etiqueta in ('ampliacion', 'lead_nuevo') and new.grupo_piloto is null then
    new.grupo_piloto := sorteo_piloto(new.id);
  end if;
  return new;
end $function$;

-- auditorias_inmutables
CREATE OR REPLACE FUNCTION public.auditorias_inmutables()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$begin raise exception 'Las auditorias no se modifican ni se borran'; end$function$;

-- avisar_aprobacion
CREATE OR REPLACE FUNCTION public.avisar_aprobacion()
 RETURNS trigger
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$begin
  if new.estado_envio = 'aprobada' and old.estado_envio is distinct from 'aprobada'
     and cardinality(avisos_texto(new.texto_aprobado)) > 0 then
    insert into eventos_propuesta (propuesta_id, accion, usuario, estado_antes, estado_despues, datos)
    values (new.id, 'aprobada_con_aviso', coalesce(new.aprobada_por, 'panel'), old.estado, new.estado,
            jsonb_build_object('avisos', to_jsonb(avisos_texto(new.texto_aprobado))));
  end if;
  return null;
end$function$;

-- avisar_version
CREATE OR REPLACE FUNCTION public.avisar_version()
 RETURNS trigger
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$begin
  if new.origen = 'comercial' then new.avisos := avisos_texto(new.texto); end if;
  return new;
end$function$;

-- avisos_texto
CREATE OR REPLACE FUNCTION public.avisos_texto(t text)
 RETURNS text[]
 LANGUAGE sql
 IMMUTABLE
AS $function$select array_remove(array[
      case when t ~* '(\mriesgo|abandon|\mchurn\M|\mfuga\M)' then 'menciona el riesgo' end,
      case when t ~* '(hemos (notado|detectado|observado|visto)|nos preocupa|preocupaci[oó]n|inactiv|\mperder(le|les|la|lo)?\M|dejar de (anunciar|invertir|trabajar|contar))'
           then 'insinúa el riesgo' end,
      case when t ~* '(\d+\s*%|descuento|rebaja|gratis)' then 'condición económica' end,
      case when t ~* '(impago|\mmoros|facturas? (pendientes?|vencidas?|impagadas?))' then 'menciona cobros o impagos' end
    ]::text[], null)$function$;

-- baja_panel
CREATE OR REPLACE FUNCTION public.baja_panel(p_id_contacto text, p_motivo text DEFAULT 'solicitud_contacto'::text, p_nota text DEFAULT NULL::text)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$begin
  if not exists (select 1 from perfiles where correo = auth.jwt() ->> 'email') then
    raise exception 'Su usuario no tiene acceso al panel'; end if;
  if not exists (select 1 from contactos where id_contacto = p_id_contacto and email like '%@%') then
    raise exception 'El contacto no existe o no tiene correo electrónico'; end if;
  if not es_direccion() and mi_comercial() is distinct from comercial_del_contacto(p_id_contacto) then
    raise exception 'Este contacto no está en su cartera'; end if;
  if coalesce(p_motivo, 'x') not in ('solicitud_contacto', 'oposicion', 'rebote_permanente') then
    raise exception 'Motivo de baja no válido'; end if;
  insert into exclusiones (email, motivo, origen, registrado_por, id_contacto, nota)
  select lower(btrim(email)), p_motivo, 'panel', auth.jwt() ->> 'email', id_contacto, left(p_nota, 500)
  from contactos where id_contacto = p_id_contacto
  on conflict (email) do nothing;
  insert into eventos_lead (id_lead, accion, usuario, datos)
  select id_lead, 'baja_comunicaciones', auth.jwt() ->> 'email', jsonb_build_object('id_contacto', id_contacto, 'motivo', p_motivo)
  from contactos where id_contacto = p_id_contacto and id_lead is not null;
  return jsonb_build_object('ok', true, 'id_contacto', p_id_contacto);
end$function$;

-- balance_lunes
CREATE OR REPLACE FUNCTION public.balance_lunes(p_fecha date)
 RETURNS SETOF jsonb
 LANGUAGE sql
 STABLE SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
  with tasas as (
    select 'ampliacion' as etiqueta, round(avg((desenlace = 'Ganada')::int)::numeric, 3) as tasa
      from oportunidades where origen = 'Ampliacion de cartera'
    union all
    select 'lead_nuevo', round(avg((desenlace = 'Ganada')::int)::numeric, 3) from oportunidades where origen = 'Lead nuevo'
  )
  select jsonb_build_object(
    'id_comercial', dc.id_comercial, 'nombre', dc.nombre, 'correo', dc.correo,
    'semana_anterior', jsonb_build_object('desde', p_fecha - 7, 'hasta', p_fecha - 1) || (
      select jsonb_build_object(
        'aceptadas',          count(*) filter (where e.accion = 'aprobar'),
        'rechazadas',         count(*) filter (where e.accion = 'rechazar'),
        'enviadas',           count(*) filter (where e.accion = 'registrar_envio' and e.datos ->> 'ok' = 'true'),
        'respuestas',         count(*) filter (where e.accion = 'registrar_respuesta'),
        'ganadas',            count(*) filter (where e.accion = 'cerrar' and e.datos ->> 'desenlace' = 'ganada'),
        'perdidas',           count(*) filter (where e.accion = 'cerrar' and e.datos ->> 'desenlace' = 'perdida'),
        'riesgo_cerradas',    count(*) filter (where e.accion = 'cerrar' and p.etiqueta = 'riesgo'),
        'riesgo_recuperadas', count(*) filter (where e.accion = 'cerrar' and p.etiqueta = 'riesgo'
                                                 and e.datos ->> 'estado_confirmado_comercial' in ('Activo', 'Pausa: volvió después')))
      from eventos_propuesta e join propuestas p on p.id = e.propuesta_id
      where p.comercial_asignado = dc.id_comercial and e.creado_en >= p_fecha - 7 and e.creado_en < p_fecha),
    'leads_nuevos_semana', (select count(*) from leads l where l.comercial_asignado = dc.id_comercial
                             and l.creado_en >= p_fecha - 7 and l.creado_en < p_fecha),
    'pendientes', coalesce((select jsonb_object_agg(etiqueta, n) from (
                     select etiqueta, count(*) as n from propuestas
                     where comercial_asignado = dc.id_comercial and estado in ('pendiente_aprobacion', 'error_envio')
                     group by etiqueta) x), '{}'::jsonb),
    'nuevas_hoy', (select count(*) from propuestas where comercial_asignado = dc.id_comercial and fecha_corte = p_fecha
                    and etiqueta in ('lead_nuevo', 'ampliacion')),
    'en_seguimiento', (select count(*) from propuestas where comercial_asignado = dc.id_comercial and estado = 'en_seguimiento'),
    'seguimientos_debidos', coalesce((select jsonb_agg(jsonb_build_object('razon_social', razon_social, 'dias', dias, 'toque', toque) order by dias desc)
                     from (select p.razon_social,
                                  p_fecha - coalesce(p.enviada_en, p.aprobada_en)::date as dias,
                                  case when p_fecha - coalesce(p.enviada_en, p.aprobada_en)::date >= 25 then 'último toque o cierre'
                                       when p_fecha - coalesce(p.enviada_en, p.aprobada_en)::date >= 12 then 'segundo toque'
                                       else 'primer toque' end as toque
                           from propuestas p
                           where p.comercial_asignado = dc.id_comercial and p.estado = 'en_seguimiento'
                             and p.grupo_piloto is distinct from 'control'
                             and (p.ultima_respuesta_en is null or p.ultima_respuesta_en < coalesce(p.enviada_en, p.aprobada_en))
                             and p_fecha - coalesce(p.enviada_en, p.aprobada_en)::date >= 4) s), '[]'::jsonb),
    'riesgo_abiertas', (select jsonb_build_object('cuentas', count(*), 'facturacion_en_riesgo_eur', coalesce(round(sum(facturacion_en_riesgo)), 0))
                        from propuestas where comercial_asignado = dc.id_comercial and etiqueta = 'riesgo' and estado_tarea <> 'cerrada'
                          and estado <> 'rechazada'),
    'prevision', (select jsonb_build_object(
                     'propuestas_abiertas', count(*),
                     'importe_propuesto_eur', coalesce(round(sum(p.importe_propuesto_eur)), 0),
                     'valor_esperado_eur', coalesce(round(sum(p.importe_propuesto_eur * t.tasa)), 0),
                     'tasas_historicas', (select jsonb_object_agg(etiqueta, tasa) from tasas),
                     'metodo', 'importe propuesto × tasa histórica de éxito por origen (oportunidades)')
                  from propuestas p join tasas t on t.etiqueta = case when p.etiqueta = 'seguimiento' then 'ampliacion' else p.etiqueta end
                  where p.comercial_asignado = dc.id_comercial and p.etiqueta <> 'riesgo'
                    and p.estado in ('pendiente_aprobacion', 'error_envio', 'enviando', 'en_seguimiento'))
  )
  from dim_comercial dc
  order by dc.id_comercial
$function$;

-- bloquear_excluidos
CREATE OR REPLACE FUNCTION public.bloquear_excluidos()
 RETURNS trigger
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$begin
  if new.canal = 'email' and new.estado_envio in ('aprobada', 'enviada')
     and new.estado_envio is distinct from old.estado_envio
     and esta_excluido((select c.email from contactos c where c.id_contacto = new.id_contacto)) then
    raise exception 'El contacto se ha dado de baja de las comunicaciones comerciales: no se puede enviar por correo. Rechace la propuesta o contacte por teléfono.';
  end if;
  return new;
end$function$;

-- comercial_del_contacto
CREATE OR REPLACE FUNCTION public.comercial_del_contacto(p_id_contacto text)
 RETURNS text
 LANGUAGE sql
 STABLE SECURITY DEFINER
 SET search_path TO 'public'
AS $function$select coalesce((select d.comercial_asignado from contactos c join dim_clientes d on d.id_cliente = c.id_cliente
                     where c.id_contacto = p_id_contacto),
                    (select l.comercial_asignado from contactos c join leads l on l.id_lead = c.id_lead
                     where c.id_contacto = p_id_contacto))$function$;

-- comercial_para_lead
CREATE OR REPLACE FUNCTION public.comercial_para_lead()
 RETURNS text
 LANGUAGE sql
 STABLE SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
  select c.id_comercial from dim_comercial c
  left join leads l on l.comercial_asignado = c.id_comercial and l.estado in ('nuevo', 'en_curso')
  group by c.id_comercial order by count(l.id_lead), c.id_comercial limit 1
$function$;

-- completar_propuesta
CREATE OR REPLACE FUNCTION public.completar_propuesta()
 RETURNS trigger
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$begin
  if new.accion_id in ('llamada_reactivacion', 'reunion_nuevo_interlocutor') then new.canal := 'llamada'; end if;
  if new.id_contacto is null then
    new.id_contacto := (select c.id_contacto from contactos c
                        where c.id_cliente = new.id_cliente or c.id_lead = new.id_lead
                        order by c.principal desc, c.id_contacto limit 1);
  end if;
  return new;
end$function$;

-- control_envio
CREATE OR REPLACE FUNCTION public.control_envio()
 RETURNS trigger
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$begin
  if new.estado_envio = 'aprobada' and old.estado_envio is distinct from 'aprobada' then
    new.envio_reservado_en := null;
    new.envio_reserva := null;
  end if;
  if new.canal = 'email' and new.estado_envio = 'enviada' and old.estado_envio is distinct from 'enviada'
     and new.envio_reservado_en is null then
    raise exception 'Envío sin reserva: solo W5 marca una propuesta como enviada, después de reservarla';
  end if;
  return new;
end$function$;

-- es_direccion
CREATE OR REPLACE FUNCTION public.es_direccion()
 RETURNS boolean
 LANGUAGE sql
 STABLE SECURITY DEFINER
 SET search_path TO 'public'
AS $function$ select coalesce((select rol = 'direccion' from perfiles where correo = auth.jwt() ->> 'email'), false) $function$;

-- esta_excluido
CREATE OR REPLACE FUNCTION public.esta_excluido(p_email text)
 RETURNS boolean
 LANGUAGE sql
 STABLE SECURITY DEFINER
 SET search_path TO 'public'
AS $function$select exists (select 1 from exclusiones where email = lower(btrim(p_email)))$function$;

-- liberar_envio
CREATE OR REPLACE FUNCTION public.liberar_envio(p_id bigint)
 RETURNS jsonb
 LANGUAGE sql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$with r as (update propuestas set envio_reservado_en = null, envio_reserva = null
               where id = p_id and estado_envio = 'aprobada' and envio_reservado_en is not null
                 and (es_direccion() or auth.jwt() ->> 'email' is null)   -- dirección, n8n o el editor SQL
               returning id),
         t as (insert into eventos_propuesta (propuesta_id, accion, usuario, estado_antes, estado_despues, datos)
               select id, 'liberar_envio', coalesce(auth.jwt() ->> 'email', current_user), 'enviando', 'enviando',
                      '{}'::jsonb from r)
    select jsonb_build_object('ok', exists (select 1 from r))$function$;

-- mi_comercial
CREATE OR REPLACE FUNCTION public.mi_comercial()
 RETURNS text
 LANGUAGE sql
 STABLE SECURITY DEFINER
 SET search_path TO 'public'
AS $function$ select id_comercial from perfiles where correo = auth.jwt() ->> 'email' $function$;

-- preparar_lunes
CREATE OR REPLACE FUNCTION public.preparar_lunes(p_fecha date, p_ampliaciones_por_comercial integer DEFAULT 2)
 RETURNS SETOF jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
declare
  v_mes_sig text := to_char(p_fecha + 30, 'YYYY-MM');
  v_num_mes int := extract(month from p_fecha + 30)::int;
begin
  perform set_config('meridiano.usuario', 'n8n · lunes', true);

  -- 1a. Leads nuevos
  insert into propuestas (fecha_corte, etiqueta, id_lead, comercial_asignado, comercial_nombre, razon_social, categoria,
                          accion_id, canal, id_contacto, id_producto_propuesto, producto_sugerido_nombre, importe_propuesto_eur,
                          fecha_limite, justificacion, ficha_cuenta, material_titulo, asunto_email, material_cuerpo, fuente_material)
  select p_fecha, 'lead_nuevo', l.id_lead, l.comercial_asignado, dc.nombre, l.razon_social, l.categoria,
         case when envia then 'presentacion_lead' else 'llamada_presentacion' end,
         case when envia then 'email' else 'llamada' end,
         ct.id_contacto, pr.id_producto, pr.nombre, pr.tarifa_base_eur, p_fecha + 7,
         'Lead ' || case l.origen when 'formulario_web' then 'del formulario web' else 'de puerta fría' end
           || ' dado de alta el ' || to_char(l.creado_en, 'DD/MM/YYYY')
           || case when envia then '' else '. Sin consentimiento o sin correo: primer contacto por teléfono' end || '.',
         concat_ws(E'\n',
           'Empresa: ' || l.razon_social || coalesce(' (' || l.categoria || ')', ''),
           'Contacto: ' || coalesce(ct.nombre, 'sin contacto') || coalesce(', ' || ct.cargo, ''),
           'Mensaje del lead: ' || nullif(btrim(l.mensaje), ''),
           'Producto de entrada propuesto: ' || pr.nombre || ' (' || pr.familia || ')',
           'Anunciantes de su sector que lo contrataron en el último año: ' || pr.n_sector),
         'Presentación de Meridiano',
         'Meridiano · ' || coalesce(pr.nombre, 'propuesta') || ' para ' || l.razon_social,
         case when envia then
           'Estimado/a ' || coalesce(split_part(ct.nombre, ' ', 1), '') || E':\n\nGracias por su interés en Meridiano, el medio de referencia para el público senior. '
           || 'Para empezar le proponemos ' || coalesce(pr.nombre, 'un formato de entrada') || ', el formato de entrada más elegido por los anunciantes de su sector. '
           || E'¿Le parece que lo comentemos en una llamada breve esta semana?\n\nUn saludo,\n' || dc.nombre
         else
           'Guion de llamada para ' || coalesce(ct.nombre, 'el contacto') || ' (' || l.razon_social || E'):\n'
           || E'1. Presentarse y agradecer el interés en Meridiano.\n'
           || '2. Preguntar por sus objetivos con el público senior.' || E'\n'
           || '3. Proponer ' || coalesce(pr.nombre, 'un formato de entrada') || E' como primer paso.\n'
           || '4. Pedir permiso para enviar información comercial por correo y registrarlo en el panel.'
         end,
         'plantilla'
  from leads l
  join dim_comercial dc on dc.id_comercial = l.comercial_asignado
  left join lateral (select * from contactos c where c.id_lead = l.id_lead order by principal desc, id_contacto limit 1) ct on true
  left join lateral (
    select d.id_producto, d.nombre, d.familia, d.tarifa_base_eur,
           count(distinct f.id_cliente) filter (where cl.categoria = l.categoria) as n_sector
    from dim_productos d
    left join fact_campanas f on f.id_producto = d.id_producto and f.fecha_emision >= p_fecha - 365 and f.fecha_emision < p_fecha
    left join dim_clientes cl on cl.id_cliente = f.id_cliente
    where d.es_producto_entrada
    group by d.id_producto, d.nombre, d.familia, d.tarifa_base_eur
    order by 5 desc, count(distinct f.id_cliente) desc, d.tarifa_base_eur
    limit 1) pr on true
  cross join lateral (select (l.consentimiento_comercial and coalesce(ct.email, '') <> '') as envia) x
  where l.estado = 'nuevo' and not exists (select 1 from propuestas p where p.id_lead = l.id_lead)
  on conflict do nothing;

  -- 1b. Ampliación de cartera: siguiente mejor oferta para clientes activos y sanos
  insert into propuestas (fecha_corte, etiqueta, id_cliente, comercial_asignado, comercial_nombre, orden_comercial, razon_social,
                          categoria, valor_cuenta, accion_id, canal, id_producto_propuesto, producto_sugerido_nombre,
                          importe_propuesto_eur, fecha_limite, justificacion, ficha_cuenta, material_titulo, asunto_email,
                          material_cuerpo, fuente_material)
  select p_fecha, 'ampliacion', c.id_cliente, c.comercial_asignado, dc.nombre, c.orden, c.razon_social, c.categoria, c.fac12,
         'propuesta_ampliacion', 'email', nb.id_producto, nb.nombre, nb.tarifa_base_eur, p_fecha + 14,
         'Cliente activo y estable que no ha contratado ' || nb.nombre || ' en el último año; ' || nb.n_sector || ' de '
           || c.activos_sector || ' anunciantes activos de su sector sí lo hicieron.',
         concat_ws(E'\n',
           'Empresa: ' || c.razon_social || ' (' || c.categoria || ')',
           'Contacto: ' || coalesce(ct.nombre, 'sin contacto') || coalesce(', ' || ct.cargo, ''),
           'Campañas emitidas en los últimos 12 meses: ' || c.n12,
           'Producto que más contrata: ' || c.principal,
           'Producto propuesto: ' || nb.nombre || ' (' || nb.familia || '), disponible el mes que viene',
           'Anunciantes de su sector que lo contrataron en el último año: ' || nb.n_sector || ' de ' || c.activos_sector),
         'Propuesta de ampliación: ' || nb.nombre,
         'Meridiano · una idea para sus próximas campañas',
         'Estimado/a ' || coalesce(split_part(ct.nombre, ' ', 1), 'cliente') || E':\n\nGracias por seguir confiando en Meridiano para llegar al público senior. '
           || 'Varios anunciantes de su sector están obteniendo buenos resultados con ' || nb.nombre
           || ', un formato que complementa bien lo que ya hace con ' || c.principal || '. '
           || E'¿Le parece que le presente el formato y las fechas disponibles en una reunión breve?\n\nUn saludo,\n' || dc.nombre,
         'plantilla'
  from (
    select cand.*, row_number() over (partition by cand.comercial_asignado order by cand.fac12 desc, cand.id_cliente) as orden
    from (
      select cl.id_cliente, cl.razon_social, cl.categoria, cl.comercial_asignado, a.fac12, a.n12,
             (select d.nombre from fact_campanas f2 join dim_productos d using (id_producto)
               where f2.id_cliente = cl.id_cliente and f2.fecha_emision >= p_fecha - 365 and f2.fecha_emision < p_fecha
               group by d.nombre order by count(*) desc, d.nombre limit 1) as principal,
             (select count(distinct f3.id_cliente) from fact_campanas f3 join dim_clientes c3 using (id_cliente)
               where c3.categoria = cl.categoria and f3.fecha_emision >= p_fecha - 365 and f3.fecha_emision < p_fecha) as activos_sector
      from dim_clientes cl
      join (select id_cliente,
                   sum(importe_eur) filter (where fecha_emision >= p_fecha - 365) as fac12,
                   count(distinct id_campana) filter (where fecha_emision >= p_fecha - 365) as n12,
                   coalesce(sum(importe_eur) filter (where fecha_emision >= p_fecha - 180), 0) as fac6,
                   coalesce(sum(importe_eur) filter (where fecha_emision >= p_fecha - 360 and fecha_emision < p_fecha - 180), 0) as fac6p,
                   max(fecha_emision) as ultima
            from fact_campanas where fecha_emision < p_fecha group by id_cliente) a using (id_cliente)
      where a.ultima >= p_fecha - 180 and a.fac6 >= 0.7 * a.fac6p
        and not exists (select 1 from propuestas p where p.id_cliente = cl.id_cliente
                        and (p.fecha_corte >= p_fecha - 90 or p.estado_tarea <> 'cerrada'))
        and not exists (select 1 from asignaciones_ciclo s where s.id_cliente = cl.id_cliente and s.fecha_corte >= p_fecha - 90)
    ) cand
    where exists (select 1 from fact_campanas f where f.id_cliente = cand.id_cliente)
  ) c
  join dim_comercial dc on dc.id_comercial = c.comercial_asignado
  cross join lateral (
    select d.id_producto, d.nombre, d.familia, d.tarifa_base_eur, count(distinct f.id_cliente) as n_sector
    from dim_productos d
    join fact_campanas f on f.id_producto = d.id_producto and f.fecha_emision >= p_fecha - 365 and f.fecha_emision < p_fecha
    join dim_clientes cl2 on cl2.id_cliente = f.id_cliente and cl2.categoria = c.categoria
    where (',' || replace(d.meses_disponible, ' ', '') || ',') like '%,' || v_num_mes || ',%'
      and not exists (select 1 from fact_campanas f2 where f2.id_cliente = c.id_cliente and f2.id_producto = d.id_producto
                      and f2.fecha_emision >= p_fecha - 365)
      and (select count(*) from fact_campanas f4 where f4.id_producto = d.id_producto and f4.mes_emision = v_mes_sig)
          < coalesce(d.capacidad_mensual, 0)
    group by d.id_producto, d.nombre, d.familia, d.tarifa_base_eur
    order by 5 desc, d.tarifa_base_eur
    limit 1) nb
  left join lateral (select * from contactos ct where ct.id_cliente = c.id_cliente order by principal desc, id_contacto limit 1) ct on true
  where c.orden <= p_ampliaciones_por_comercial
    -- idempotente: si el lunes ya preparó las ampliaciones de este comercial, no añade más al volver a ejecutarlo
    and not exists (select 1 from propuestas e where e.fecha_corte = p_fecha and e.etiqueta = 'ampliacion'
                    and e.comercial_asignado = c.comercial_asignado)
  on conflict do nothing;

  -- 1c. Lo que n8n tiene que pasar por Claude: propuestas del lunes sin texto de la IA (plantilla o IA descartada en un
  --     intento anterior) y sin tocar por el comercial. Volver a ejecutar W4 reintenta solo esas.
  return query
  select jsonb_build_object(
    'id', p.id, 'fecha_corte', p.fecha_corte, 'etiqueta', p.etiqueta, 'canal', p.canal,
    'id_cliente', p.id_cliente, 'id_lead', p.id_lead, 'razon_social', p.razon_social,
    'comercial_asignado', p.comercial_asignado, 'comercial_nombre', p.comercial_nombre, 'correo_comercial', dc.correo,
    'material_cuerpo', p.material_cuerpo,
    'contexto_ia',
      case p.etiqueta when 'lead_nuevo' then 'Tipo: primer contacto con un lead nuevo. '
                      else 'Tipo: propuesta de ampliación a un cliente actual satisfecho. ' end
      || case p.canal when 'email' then 'Formato: correo breve al contacto, que termine proponiendo una llamada o reunión. '
                      else 'Formato: guion de llamada en 4 pasos para el comercial, que termine pidiendo permiso para enviar información por correo. ' end
      || 'Firma: ' || p.comercial_nombre || E'.\n' || p.ficha_cuenta || E'\n' || p.justificacion)
  from propuestas p join dim_comercial dc on dc.id_comercial = p.comercial_asignado
  where p.fecha_corte = p_fecha and p.etiqueta in ('lead_nuevo', 'ampliacion')
    and coalesce(p.fuente_material, '') <> 'llm' and p.estado = 'pendiente_aprobacion' and p.material_editado is null
  order by p.comercial_asignado, p.etiqueta, p.id;
end $function$;

-- registrar_accion
CREATE OR REPLACE FUNCTION public.registrar_accion(p_propuesta_id bigint, p_accion text, p_usuario text, p_datos jsonb DEFAULT '{}'::jsonb)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
declare
  p propuestas;
  antes text;
  version_material int;
  email_destino text;
  consentimiento boolean;
begin
  if coalesce(p_usuario, '') = '' then raise exception 'Falta el usuario que realiza la acción'; end if;
  perform set_config('meridiano.usuario', p_usuario, true);
  select * into p from propuestas where id = p_propuesta_id for update;
  if not found then raise exception 'La propuesta % no existe', p_propuesta_id; end if;
  antes := p.estado;

  if p_accion = 'guardar_material' then                       -- corregir
    if p.estado_tarea = 'cerrada' then raise exception 'La propuesta está cerrada: reábrela para corregir el material'; end if;
    if p.canal = 'email' and p.estado_envio in ('aprobada', 'enviada') then
      raise exception 'La propuesta ya está aprobada: el texto enviado no se modifica'; end if;
    if coalesce(btrim(p_datos ->> 'material'), '') = '' then raise exception 'El material no puede quedar vacío'; end if;
    if btrim(p_datos ->> 'material') = btrim(coalesce(p.material_editado, p.material_cuerpo, '')) then
      raise exception 'El material no tiene cambios'; end if;
    update propuestas set material_editado = p_datos ->> 'material' where id = p.id;
    select max(version) into version_material from material_versiones where propuesta_id = p.id;

  elsif p_accion = 'aprobar' then                             -- el botón «Aceptar»: si es un correo, n8n lo envía
    if p.estado_envio not in ('pendiente_aprobacion', 'error_envio') then
      raise exception 'Solo se puede aprobar una propuesta pendiente de aprobación (estado actual: %)', p.estado; end if;
    if p.canal = 'email' then
      select email into email_destino from contactos where id_contacto = p.id_contacto;
      if coalesce(email_destino, '') = '' then raise exception 'La empresa no tiene un contacto con correo: añádelo antes de aprobar'; end if;
      if p.id_lead is not null then
        select consentimiento_comercial into consentimiento from leads where id_lead = p.id_lead;
        if not consentimiento then
          raise exception 'Este lead no ha dado su consentimiento para recibir información comercial: regístralo antes de enviar'; end if;
      end if;
    end if;
    select max(version) into version_material from material_versiones where propuesta_id = p.id;
    update propuestas set estado_envio = 'aprobada', error_envio = null,
                          texto_aprobado = coalesce(material_editado, material_cuerpo),
                          version_aprobada = version_material, aprobada_por = p_usuario, aprobada_en = now(),
                          estado_tarea = case when canal = 'llamada' then 'en_curso' else estado_tarea end
    where id = p.id;

  elsif p_accion = 'rechazar' then
    if p.estado_envio not in ('pendiente_aprobacion', 'error_envio') then
      raise exception 'Solo se puede rechazar una propuesta pendiente de aprobación (estado actual: %)', p.estado; end if;
    if coalesce(btrim(p_datos ->> 'motivo'), '') = '' then raise exception 'Indica por qué se rechaza la propuesta'; end if;
    update propuestas set estado_envio = 'rechazada', motivo_rechazo = p_datos ->> 'motivo', estado_tarea = 'cerrada' where id = p.id;

  elsif p_accion = 'registrar_envio' then                     -- solo n8n (clave de servicio), tras intentar el envío
    if p.estado_envio <> 'aprobada' or p.canal <> 'email' then
      raise exception 'La propuesta no está aprobada para envío por correo (estado actual: %)', p.estado; end if;
    if (p_datos ->> 'ok')::boolean then
      update propuestas set estado_envio = 'enviada', enviada_en = now(), id_mensaje = p_datos ->> 'id_mensaje',
                            estado_tarea = 'en_curso' where id = p.id;
    else
      update propuestas set estado_envio = 'error_envio', error_envio = left(coalesce(p_datos ->> 'error', 'error desconocido'), 500)
      where id = p.id;
    end if;
    if p.id_lead is not null then update leads set estado = 'en_curso' where id_lead = p.id_lead and estado = 'nuevo'; end if;

  elsif p_accion = 'registrar_respuesta' then
    if p.estado <> 'en_seguimiento' then raise exception 'Solo se registran respuestas de propuestas enviadas o en curso'; end if;
    if coalesce(btrim(p_datos ->> 'resumen'), '') = '' then raise exception 'Resume la respuesta del cliente'; end if;
    update propuestas set ultima_respuesta_en = now() where id = p.id;

  elsif p_accion = 'cerrar' then
    if p.estado <> 'en_seguimiento' then
      raise exception 'Solo se cierra una propuesta aprobada y en seguimiento (estado actual: %)', p.estado; end if;
    update propuestas set estado_tarea = 'cerrada', fecha_confirmacion = now(),
                          comentario_comercial = nullif(btrim(coalesce(p_datos ->> 'comentario_comercial', '')), ''),
                          estado_confirmado_comercial = p_datos ->> 'estado_confirmado_comercial',
                          motivo_confirmado = p_datos ->> 'motivo_confirmado',
                          diagnostico_correcto = p_datos ->> 'diagnostico_correcto',
                          desenlace = p_datos ->> 'desenlace',
                          motivo_desenlace = nullif(btrim(coalesce(p_datos ->> 'motivo_desenlace', '')), '')
    where id = p.id;
    if p.id_lead is not null and p_datos ->> 'desenlace' = 'ganada' then
      update leads set estado = 'convertido' where id_lead = p.id_lead; end if;

  elsif p_accion = 'reabrir' then
    if p.estado_tarea <> 'cerrada' then raise exception 'Solo se puede reabrir una propuesta cerrada o rechazada'; end if;
    if coalesce(btrim(p_datos ->> 'motivo'), '') = '' then raise exception 'Indica por qué se reabre la propuesta'; end if;
    if p.estado_envio = 'rechazada' then
      update propuestas set estado_envio = 'pendiente_aprobacion', motivo_rechazo = null, estado_tarea = 'pendiente' where id = p.id;
    else
      update propuestas set estado_tarea = 'en_curso' where id = p.id;
    end if;

  else
    raise exception 'Acción no reconocida: %', p_accion;
  end if;

  insert into eventos_propuesta (propuesta_id, accion, usuario, estado_antes, estado_despues, datos)
  select p.id, p_accion, p_usuario, antes, x.estado,
         (p_datos - 'material') || case when version_material is null then '{}'::jsonb
                                       else jsonb_build_object('version_material', version_material) end
  from propuestas x where x.id = p.id;

  return (select to_jsonb(x) from propuestas x where x.id = p.id);
end $function$;

-- registrar_baja
CREATE OR REPLACE FUNCTION public.registrar_baja(p_token uuid)
 RETURNS jsonb
 LANGUAGE sql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$with c as (select id_contacto, id_lead, lower(btrim(email)) as email from contactos
               where token_baja = p_token and email like '%@%'),
     alta as (insert into exclusiones (email, motivo, origen, registrado_por, id_contacto)
              select email, 'enlace_baja', 'correo', 'enlace del correo', id_contacto from c
              on conflict (email) do nothing),
     traza as (insert into eventos_lead (id_lead, accion, usuario, datos)
               select id_lead, 'baja_comunicaciones', 'enlace del correo', jsonb_build_object('id_contacto', id_contacto)
               from c where id_lead is not null)
  select coalesce((select jsonb_build_object('ok', true, 'email',
                            left(email, 2) || '***' || substr(email, position('@' in email))) from c),
                  jsonb_build_object('ok', false, 'motivo', 'enlace_no_valido'))$function$;

-- registrar_consentimiento
CREATE OR REPLACE FUNCTION public.registrar_consentimiento(p_id_lead text, p_medio text, p_nota text DEFAULT NULL::text)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
declare v_correo text := auth.jwt() ->> 'email'; perfil perfiles; l leads;
begin
  select * into perfil from perfiles where correo = v_correo;
  if not found then raise exception 'Tu usuario no tiene acceso al panel'; end if;
  select * into l from leads where id_lead = p_id_lead for update;
  if not found then raise exception 'El lead no existe'; end if;
  if perfil.rol <> 'direccion' and perfil.id_comercial is distinct from l.comercial_asignado then
    raise exception 'Este lead no está en tu cartera'; end if;
  if p_medio not in ('telefono', 'presencial', 'email') then raise exception 'Indica cómo se obtuvo el consentimiento'; end if;
  if coalesce(btrim(p_nota), '') = '' then raise exception 'Anota en qué términos aceptó recibir información comercial'; end if;
  update leads set consentimiento_comercial = true, consentimiento_fecha = now(), consentimiento_medio = p_medio,
                   consentimiento_texto = left(p_nota, 1000) where id_lead = p_id_lead;
  insert into eventos_lead (id_lead, accion, usuario, datos)
  values (p_id_lead, 'consentimiento_registrado', v_correo, jsonb_build_object('medio', p_medio, 'nota', p_nota));
  return (select to_jsonb(x) from leads x where id_lead = p_id_lead);
end $function$;

-- registrar_toque
CREATE OR REPLACE FUNCTION public.registrar_toque(p_propuesta_id bigint, p_tipo text, p_resultado text, p_nota text DEFAULT NULL::text)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$begin
  if not exists (select 1 from perfiles where correo = auth.jwt() ->> 'email') then
    raise exception 'Su usuario no tiene acceso al panel'; end if;
  if not exists (select 1 from propuestas where id = p_propuesta_id) then
    raise exception 'La propuesta no existe'; end if;
  if not es_direccion() and mi_comercial() is distinct from (select comercial_asignado from propuestas where id = p_propuesta_id) then
    raise exception 'Esta propuesta no está en su cartera'; end if;
  if (select estado from propuestas where id = p_propuesta_id) <> 'en_seguimiento' then
    raise exception 'Solo se registran toques de propuestas aprobadas y en seguimiento'; end if;
  if coalesce(p_tipo, 'x') not in ('llamada', 'correo', 'reunion') then
    raise exception 'Tipo de toque no válido: llamada, correo o reunion'; end if;
  if coalesce(p_resultado, 'x') not in ('contactado', 'no_contesta', 'buzon_de_voz', 'reunion_fijada') then
    raise exception 'Resultado no válido: contactado, no_contesta, buzon_de_voz o reunion_fijada'; end if;
  update propuestas
     set ultimo_toque_en = now(),
         enviada_en = case when canal = 'llamada' and enviada_en is null and p_tipo = 'llamada' then now() else enviada_en end
   where id = p_propuesta_id;
  insert into eventos_propuesta (propuesta_id, accion, usuario, estado_antes, estado_despues, datos)
  values (p_propuesta_id, 'toque', auth.jwt() ->> 'email', 'en_seguimiento', 'en_seguimiento',
          jsonb_build_object('tipo', p_tipo, 'resultado', p_resultado, 'nota', left(p_nota, 1000)));
  return jsonb_build_object('ok', true, 'propuesta_id', p_propuesta_id);
end$function$;

-- reservar_envios
CREATE OR REPLACE FUNCTION public.reservar_envios(p_ids bigint[])
 RETURNS jsonb
 LANGUAGE sql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$with r as (
      update propuestas set envio_reservado_en = now(), envio_reserva = gen_random_uuid()
      where id = any(p_ids) and estado_envio = 'aprobada' and canal = 'email' and envio_reservado_en is null
      returning id)
    select jsonb_build_object('reservadas', coalesce(jsonb_agg(id order by id), '[]'::jsonb)) from r$function$;

-- sorteo_piloto
CREATE OR REPLACE FUNCTION public.sorteo_piloto(p_id bigint)
 RETURNS text
 LANGUAGE sql
 IMMUTABLE
AS $function$
  select case when ('x' || substr(md5('meridiano-piloto-seguimiento-1:' || p_id), 1, 8))::bit(32)::bigint % 2 = 0
              then 'tratamiento' else 'control' end
$function$;

-- trazar_propuesta
CREATE OR REPLACE FUNCTION public.trazar_propuesta()
 RETURNS trigger
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
declare
  quien text := coalesce(nullif(current_setting('meridiano.usuario', true), ''), 'motor');
  es_ia boolean := coalesce(new.fuente_material, '') = 'llm';
begin
  if tg_op = 'INSERT' then
    insert into eventos_propuesta (propuesta_id, accion, usuario, estado_despues, datos)
    values (new.id, 'publicada', quien, new.estado,
            jsonb_build_object('fecha_corte', new.fecha_corte, 'etiqueta', new.etiqueta, 'accion_id', new.accion_id,
                               'canal', new.canal, 'banda_riesgo', new.banda_riesgo));
  end if;
  if new.material_cuerpo is not null and (tg_op = 'INSERT' or new.material_cuerpo is distinct from old.material_cuerpo) then
    insert into material_versiones (propuesta_id, version, origen, autor, texto)
    select new.id, coalesce(max(version), 0) + 1, case when es_ia then 'llm' else 'plantilla' end,
           case when es_ia then 'n8n · Claude' else 'motor' end, new.material_cuerpo
    from material_versiones where propuesta_id = new.id;
    if tg_op = 'UPDATE' then
      insert into eventos_propuesta (propuesta_id, accion, usuario, estado_antes, estado_despues, datos)
      values (new.id, case when es_ia then 'material_ia' else 'material_plantilla' end, quien, old.estado, new.estado,
              jsonb_build_object('fuente_material', new.fuente_material));
    end if;
  end if;
  if tg_op = 'UPDATE' and new.material_editado is not null and new.material_editado is distinct from old.material_editado then
    insert into material_versiones (propuesta_id, version, origen, autor, texto)
    select new.id, coalesce(max(version), 0) + 1, 'comercial', quien, new.material_editado
    from material_versiones where propuesta_id = new.id;
  end if;
  return new;
end $function$;

-- ultima_carga
CREATE OR REPLACE FUNCTION public.ultima_carga()
 RETURNS jsonb
 LANGUAGE sql
 STABLE SECURITY DEFINER
 SET search_path TO 'public'
AS $function$select coalesce(
      (select jsonb_build_object(
                'apta', coalesce(e.estado in ('carga_ok', 'carga_con_avisos'), false) and e.fecha > now() - interval '8 days',
                'estado', e.estado, 'fecha', e.fecha,
                'motivo', case when not coalesce(e.estado in ('carga_ok', 'carga_con_avisos'), false)
                                   then 'la última carga de datos terminó en ' || coalesce(e.estado, 'estado desconocido')
                                 when e.fecha <= now() - interval '8 days'
                                   then 'la última carga de datos es de hace más de 8 días' end)
       from ejecuciones e where e.detalle ->> 'flujo' = 'W0' order by e.fecha desc limit 1),
      jsonb_build_object('apta', false, 'motivo', 'no hay ninguna carga de datos registrada'))$function$;

-- ---------------------------------------------------------------- Vistas
-- auditorias_ultimas
create or replace view public.auditorias_ultimas as  SELECT DISTINCT ON (tipo) id,
    creada_en,
    tipo,
    modelo,
    estado,
    veredicto,
    resumen,
    n_altas,
    n_medias,
    n_bajas,
    hallazgos
   FROM auditorias
  ORDER BY tipo, creada_en DESC;

-- conservacion_vencida
create or replace view public.conservacion_vencida as  SELECT 'lead'::text AS tipo,
    id_lead AS id,
    estado,
    GREATEST(creado_en, ( SELECT max(e.creado_en) AS max
           FROM eventos_lead e
          WHERE e.id_lead = l.id_lead), ( SELECT max(p.creado_en) AS max
           FROM propuestas p
          WHERE p.id_lead = l.id_lead)) AS ultima_actividad
   FROM leads l
  WHERE estado <> 'convertido'::text AND GREATEST(creado_en, ( SELECT max(e.creado_en) AS max
           FROM eventos_lead e
          WHERE e.id_lead = l.id_lead), ( SELECT max(p.creado_en) AS max
           FROM propuestas p
          WHERE p.id_lead = l.id_lead)) < (now() - '2 years'::interval);

-- contactos_estado
create or replace view public.contactos_estado as  SELECT c.id_contacto,
    c.id_cliente,
    c.id_lead,
    c.nombre,
    c.cargo,
    c.email,
    c.telefono,
    c.principal,
    c.ficticio,
    e.email IS NOT NULL AS dado_de_baja,
    e.motivo AS motivo_baja,
    e.creado_en AS baja_en
   FROM contactos c
     LEFT JOIN exclusiones e ON e.email = lower(btrim(c.email));

-- envios_pendientes
create or replace view public.envios_pendientes as  SELECT p.id,
    p.etiqueta,
    p.comercial_asignado,
    p.razon_social,
    p.asunto_email,
    p.material_titulo,
    p.texto_aprobado,
    c.nombre AS contacto_nombre,
    c.email AS contacto_email,
    c.ficticio AS contacto_ficticio,
    dc.nombre AS comercial_nombre,
    c.token_baja,
    esta_excluido(c.email) AS contacto_excluido,
    dc.correo AS comercial_correo
   FROM propuestas p
     JOIN contactos c ON c.id_contacto = p.id_contacto
     JOIN dim_comercial dc ON dc.id_comercial = p.comercial_asignado
  WHERE p.estado_envio = 'aprobada'::text AND p.canal = 'email'::text AND p.envio_reservado_en IS NULL;

-- envios_sin_confirmar
create or replace view public.envios_sin_confirmar as  SELECT id,
    razon_social,
    comercial_asignado,
    asunto_email,
    envio_reservado_en
   FROM propuestas p
  WHERE estado_envio = 'aprobada'::text AND canal = 'email'::text AND envio_reservado_en < (now() - '00:15:00'::interval);

-- kpi_toques_por_grupo
create or replace view public.kpi_toques_por_grupo as  SELECT COALESCE(grupo_piloto, 'fuera del piloto'::text) AS grupo,
    comercial_asignado,
    comercial_nombre,
    count(*) AS con_toque_debido,
    count(*) FILTER (WHERE NOT sin_atender) AS al_dia,
    round(100.0 * count(*) FILTER (WHERE NOT sin_atender)::numeric / NULLIF(count(*), 0)::numeric, 1) AS pct_al_dia
   FROM seguimientos_estado
  WHERE toque_debido IS NOT NULL
  GROUP BY (COALESCE(grupo_piloto, 'fuera del piloto'::text)), comercial_asignado, comercial_nombre;

-- leads_sin_propuesta
create or replace view public.leads_sin_propuesta as  SELECT id_lead,
    razon_social,
    categoria,
    provincia,
    tamano,
    web,
    origen,
    comercial_asignado,
    estado,
    consentimiento_comercial,
    consentimiento_fecha,
    consentimiento_medio,
    consentimiento_texto,
    mensaje,
    id_cliente_convertido,
    creado_por,
    creado_en
   FROM leads l
  WHERE estado = 'nuevo'::text AND NOT (EXISTS ( SELECT 1
           FROM propuestas p
          WHERE p.id_lead = l.id_lead));

-- piloto_seguimiento
create or replace view public.piloto_seguimiento as  WITH base AS (
         SELECT p.id,
            p.grupo_piloto,
            p.importe_propuesto_eur,
            COALESCE(p.enviada_en, p.aprobada_en) AS inicio,
            ( SELECT min(e.creado_en) AS min
                   FROM eventos_propuesta e
                  WHERE e.propuesta_id = p.id AND (e.accion = 'registrar_respuesta'::text OR e.accion = 'cerrar'::text AND ((e.datos ->> 'desenlace'::text) = ANY (ARRAY['ganada'::text, 'perdida'::text])))) AS primera_respuesta,
            ( SELECT min(e.creado_en) AS min
                   FROM eventos_propuesta e
                  WHERE e.propuesta_id = p.id AND e.accion = 'cerrar'::text AND (e.datos ->> 'desenlace'::text) = 'ganada'::text) AS ganada_en
           FROM propuestas p
          WHERE p.grupo_piloto IS NOT NULL AND COALESCE(p.enviada_en, p.aprobada_en) IS NOT NULL
        )
 SELECT grupo_piloto AS grupo,
    count(*) AS propuestas_enviadas,
    count(*) FILTER (WHERE inicio <= (now() - '30 days'::interval)) AS con_30_dias,
    round(avg(COALESCE(primera_respuesta <= (inicio + '30 days'::interval), false)::integer) FILTER (WHERE inicio <= (now() - '30 days'::interval)), 3) AS tasa_respuesta_30d,
    count(*) FILTER (WHERE inicio <= (now() - '90 days'::interval)) AS con_90_dias,
    round(avg(COALESCE(ganada_en <= (inicio + '90 days'::interval), false)::integer) FILTER (WHERE inicio <= (now() - '90 days'::interval)), 3) AS tasa_ganadas_90d,
    COALESCE(round(sum(importe_propuesto_eur) FILTER (WHERE ganada_en <= (inicio + '90 days'::interval) AND inicio <= (now() - '90 days'::interval))), 0::numeric) AS importe_ganado_90d_eur
   FROM base
  GROUP BY grupo_piloto;

-- plan_vigente
create or replace view public.plan_vigente as  SELECT id,
    fecha_corte,
    etiqueta,
    id_cliente,
    id_lead,
    comercial_asignado,
    comercial_nombre,
    orden_comercial,
    razon_social,
    categoria,
    tipo_riesgo,
    banda_riesgo,
    prob_abandono,
    valor_esperado_accion,
    facturacion_en_riesgo,
    valor_cuenta,
    cuenta_clave,
    requiere_direccion,
    motivo_principal,
    motivo_secundario,
    accion_id,
    producto_sugerido_nombre,
    fecha_limite,
    justificacion,
    ficha_cuenta,
    material_titulo,
    material_cuerpo,
    notas_internas,
    fuente_material,
    canal,
    id_contacto,
    asunto_email,
    id_producto_propuesto,
    importe_propuesto_eur,
    estado_envio,
    texto_aprobado,
    version_aprobada,
    aprobada_por,
    aprobada_en,
    motivo_rechazo,
    enviada_en,
    id_mensaje,
    error_envio,
    ultima_respuesta_en,
    desenlace,
    motivo_desenlace,
    estado_tarea,
    estado_confirmado_comercial,
    motivo_confirmado,
    diagnostico_correcto,
    comentario_comercial,
    material_editado,
    fecha_confirmacion,
    creado_en,
    estado,
    nueva_esta_semana,
    cerrada_en
   FROM ( SELECT p.id,
            p.fecha_corte,
            p.etiqueta,
            p.id_cliente,
            p.id_lead,
            p.comercial_asignado,
            p.comercial_nombre,
            p.orden_comercial,
            p.razon_social,
            p.categoria,
            p.tipo_riesgo,
            p.banda_riesgo,
            p.prob_abandono,
            p.valor_esperado_accion,
            p.facturacion_en_riesgo,
            p.valor_cuenta,
            p.cuenta_clave,
            p.requiere_direccion,
            p.motivo_principal,
            p.motivo_secundario,
            p.accion_id,
            p.producto_sugerido_nombre,
            p.fecha_limite,
            p.justificacion,
            p.ficha_cuenta,
            p.material_titulo,
            p.material_cuerpo,
            p.notas_internas,
            p.fuente_material,
            p.canal,
            p.id_contacto,
            p.asunto_email,
            p.id_producto_propuesto,
            p.importe_propuesto_eur,
            p.estado_envio,
            p.texto_aprobado,
            p.version_aprobada,
            p.aprobada_por,
            p.aprobada_en,
            p.motivo_rechazo,
            p.enviada_en,
            p.id_mensaje,
            p.error_envio,
            p.ultima_respuesta_en,
            p.desenlace,
            p.motivo_desenlace,
            p.estado_tarea,
            p.estado_confirmado_comercial,
            p.motivo_confirmado,
            p.diagnostico_correcto,
            p.comentario_comercial,
            p.material_editado,
            p.fecha_confirmacion,
            p.creado_en,
            p.estado,
            p.fecha_corte = (( SELECT max(propuestas.fecha_corte) AS max
                   FROM propuestas)) AS nueva_esta_semana,
            ( SELECT max(e.creado_en) AS max
                   FROM eventos_propuesta e
                  WHERE e.propuesta_id = p.id AND (e.accion = ANY (ARRAY['cerrar'::text, 'rechazar'::text]))) AS cerrada_en
           FROM propuestas p) x
  WHERE estado_tarea <> 'cerrada'::text OR cerrada_en >= (now() - '7 days'::interval) OR cerrada_en IS NULL AND fecha_corte = (( SELECT max(propuestas.fecha_corte) AS max
           FROM propuestas));

-- seguimientos_debidos
create or replace view public.seguimientos_debidos as  SELECT id,
    etiqueta,
    canal,
    comercial_asignado,
    razon_social,
    COALESCE(enviada_en, aprobada_en) AS enviada_en,
    CURRENT_DATE - COALESCE(enviada_en, aprobada_en)::date AS dias_desde_envio,
        CASE
            WHEN (CURRENT_DATE - COALESCE(enviada_en, aprobada_en)::date) >= 25 THEN 'último toque o cierre'::text
            WHEN (CURRENT_DATE - COALESCE(enviada_en, aprobada_en)::date) >= 12 THEN 'segundo toque'::text
            ELSE 'primer toque'::text
        END AS toque
   FROM propuestas p
  WHERE estado = 'en_seguimiento'::text AND grupo_piloto IS DISTINCT FROM 'control'::text AND (ultima_respuesta_en IS NULL OR ultima_respuesta_en < COALESCE(enviada_en, aprobada_en)) AND (CURRENT_DATE - COALESCE(enviada_en, aprobada_en)::date) >= 4;

-- seguimientos_estado
create or replace view public.seguimientos_estado as  WITH base AS (
         SELECT p.id,
            p.comercial_asignado,
            p.comercial_nombre,
            p.razon_social,
            p.etiqueta,
            p.canal,
            p.grupo_piloto,
            p.enviada_en,
                CASE
                    WHEN p.enviada_en IS NULL THEN 'inicio'::text
                    ELSE 'seguimiento'::text
                END AS fase,
            GREATEST(p.ultima_respuesta_en, p.ultimo_toque_en) AS ultima_actividad,
            (COALESCE(p.enviada_en, p.aprobada_en) AT TIME ZONE 'Europe/Madrid'::text)::date AS dia_envio,
            (GREATEST(p.ultima_respuesta_en, p.ultimo_toque_en) AT TIME ZONE 'Europe/Madrid'::text)::date AS dia_actividad,
            CURRENT_DATE - (COALESCE(p.enviada_en, p.aprobada_en) AT TIME ZONE 'Europe/Madrid'::text)::date AS dias_desde_envio
           FROM propuestas p
          WHERE p.estado = 'en_seguimiento'::text AND (p.enviada_en IS NOT NULL OR p.canal = 'llamada'::text AND p.aprobada_en IS NOT NULL)
        ), toque AS (
         SELECT b.id,
            b.comercial_asignado,
            b.comercial_nombre,
            b.razon_social,
            b.etiqueta,
            b.canal,
            b.grupo_piloto,
            b.enviada_en,
            b.fase,
            b.ultima_actividad,
            b.dia_envio,
            b.dia_actividad,
            b.dias_desde_envio,
                CASE
                    WHEN b.dias_desde_envio >= 25 THEN 25
                    WHEN b.dias_desde_envio >= 12 THEN 12
                    WHEN b.dias_desde_envio >= 4 THEN 4
                    ELSE NULL::integer
                END AS toque_debido,
                CASE
                    WHEN b.dias_desde_envio >= 4 AND (b.dia_actividad IS NULL OR b.dia_actividad < (b.dia_envio + 4)) THEN 4
                    WHEN b.dias_desde_envio >= 12 AND (b.dia_actividad IS NULL OR b.dia_actividad < (b.dia_envio + 12)) THEN 12
                    WHEN b.dias_desde_envio >= 25 AND (b.dia_actividad IS NULL OR b.dia_actividad < (b.dia_envio + 25)) THEN 25
                    ELSE NULL::integer
                END AS toque_pendiente
           FROM base b
        )
 SELECT id,
    comercial_asignado,
    comercial_nombre,
    razon_social,
    etiqueta,
    canal,
    grupo_piloto,
    enviada_en,
    ultima_actividad,
    dias_desde_envio,
    toque_debido,
    toque_pendiente,
    dia_envio + toque_pendiente AS fecha_toque,
    CURRENT_DATE - (dia_envio + toque_pendiente) AS dias_vencido,
    COALESCE((CURRENT_DATE - (dia_envio + toque_pendiente)) >= 7, false) AS sin_atender,
    fase,
    dia_envio
   FROM toque t;

-- seguimientos_sin_atender
create or replace view public.seguimientos_sin_atender as  SELECT id,
    comercial_asignado,
    comercial_nombre,
    razon_social,
    etiqueta,
    canal,
    grupo_piloto,
    enviada_en,
    dias_desde_envio,
    toque_pendiente AS toque_debido,
    fecha_toque,
    dias_vencido,
    ultima_actividad,
    fase,
    dia_envio
   FROM seguimientos_estado
  WHERE sin_atender AND grupo_piloto IS DISTINCT FROM 'control'::text;

-- ---------------------------------------------------------------- Triggers
drop trigger if exists asignar_grupo_piloto on public.propuestas;
CREATE TRIGGER asignar_grupo_piloto BEFORE INSERT ON public.propuestas FOR EACH ROW EXECUTE FUNCTION asignar_grupo_piloto();

drop trigger if exists auditorias_inmutables on public.auditorias;
CREATE TRIGGER auditorias_inmutables BEFORE DELETE OR UPDATE ON public.auditorias FOR EACH ROW EXECUTE FUNCTION auditorias_inmutables();

drop trigger if exists completar_propuesta on public.propuestas;
CREATE TRIGGER completar_propuesta BEFORE INSERT ON public.propuestas FOR EACH ROW EXECUTE FUNCTION completar_propuesta();

drop trigger if exists envio_al_aceptar on public.eventos_propuesta;
CREATE TRIGGER envio_al_aceptar AFTER INSERT ON public.eventos_propuesta FOR EACH ROW EXECUTE FUNCTION supabase_functions.http_request('<URL_N8N>/webhook/meridiano-envio', 'POST', '{"x-webhook-token":"<TOKEN_WEBHOOK>","Content-type":"application/json"}', '{}', '5000');

drop trigger if exists eventos_propuesta on public.eventos_propuesta;
CREATE TRIGGER eventos_propuesta AFTER INSERT ON public.eventos_propuesta FOR EACH ROW EXECUTE FUNCTION supabase_functions.http_request('<URL_N8N>/webhook/meridiano-evento', 'POST', '{"Content-type":"application/json","x-webhook-token":"<TOKEN_WEBHOOK>"}', '{}', '5000');

drop trigger if exists material_versiones_avisos on public.material_versiones;
CREATE TRIGGER material_versiones_avisos BEFORE INSERT ON public.material_versiones FOR EACH ROW EXECUTE FUNCTION avisar_version();

drop trigger if exists propuestas_avisar_aprobacion on public.propuestas;
CREATE TRIGGER propuestas_avisar_aprobacion AFTER UPDATE OF estado_envio ON public.propuestas FOR EACH ROW EXECUTE FUNCTION avisar_aprobacion();

drop trigger if exists propuestas_bloquear_excluidos on public.propuestas;
CREATE TRIGGER propuestas_bloquear_excluidos BEFORE UPDATE OF estado_envio ON public.propuestas FOR EACH ROW EXECUTE FUNCTION bloquear_excluidos();

drop trigger if exists propuestas_control_envio on public.propuestas;
CREATE TRIGGER propuestas_control_envio BEFORE UPDATE OF estado_envio ON public.propuestas FOR EACH ROW EXECUTE FUNCTION control_envio();

drop trigger if exists trazar_propuesta on public.propuestas;
CREATE TRIGGER trazar_propuesta AFTER INSERT OR UPDATE ON public.propuestas FOR EACH ROW EXECUTE FUNCTION trazar_propuesta();

-- ---------------------------------------------------------------- Inventario de tablas (columnas desplegadas)
-- asignaciones_ciclo: fecha_corte date, id_cliente text, estado_plan text
-- auditorias: id bigint, creada_en timestamp with time zone, tipo text, modelo text, paquete_ruta text, paquete_sha text, rubrica_ruta text, rubrica_sha text, estado text, veredicto text, resumen text, hallazgos jsonb, puntos_fuertes jsonb, n_altas integer, n_medias integer, n_bajas integer, avisos jsonb, error text, respuesta_bruta text, tokens_entrada integer, tokens_salida integer
-- [legado] campanas: id_orden text, id_cliente text, id_producto text, familia text, fecha_orden date, fecha_emision date, mes_emision date, tarifa_base_eur numeric, descuento_pct numeric, importe_eur numeric, impresiones bigint, clics bigint, ctr numeric, leads_entregados bigint, comercial text
-- [legado] churn: id_cliente text, segmento text, probabilidad numeric, banda text, facturacion_en_riesgo numeric, principales_factores text
-- [legado] clientes: id_cliente text, razon_social text, categoria text, provincia text, tamano text, fecha_alta date, antiguedad_meses bigint, canal_captacion text, comercial_asignado text, cp_sede text, tiene_web_propia text, anio_fundacion bigint
-- [legado] comerciales: id_comercial text, nombre text, correo text
-- contactos: id_contacto text, id_cliente text, id_lead text, nombre text, cargo text, email text, telefono text, principal boolean, ficticio boolean, token_baja uuid
-- [legado] demanda: id bigint, mes text, familia text, importe_previsto numeric, minimo numeric, maximo numeric, ocupacion_prevista numeric
-- dim_clientes: id_cliente text, razon_social text, categoria text, provincia text, tamano text, fecha_alta date, antiguedad_meses integer, canal_captacion text, comercial_asignado text, cp_sede integer, tiene_web_propia boolean, anio_fundacion integer
-- dim_comercial: id_comercial text, nombre text, correo text
-- dim_productos: id_producto text, nombre text, familia text, unidad_venta text, tarifa_base_eur numeric, margen numeric, capacidad_mensual integer, meses_disponible text, es_producto_entrada boolean, es_producto_compromiso boolean, capacidad_anual_eur numeric
-- ejecuciones: id bigint, fecha timestamp with time zone, origen text, estado text, detalle jsonb
-- estado_etiqueta: fecha_corte date, etiqueta_vigente text, estado text, casos integer, acuerdo numeric, calculado_en timestamp with time zone
-- eventos_lead: id bigint, id_lead text, accion text, usuario text, datos jsonb, creado_en timestamp with time zone
-- eventos_propuesta: id bigint, propuesta_id bigint, accion text, usuario text, estado_antes text, estado_despues text, datos jsonb, creado_en timestamp with time zone
-- exclusiones: email text, motivo text, origen text, registrado_por text, id_contacto text, nota text, creado_en timestamp with time zone
-- fact_campanas: id_orden text, id_cliente text, id_producto text, familia text, fecha_orden date, fecha_emision date, mes_emision text, tarifa_base_eur numeric, descuento_pct numeric, importe_eur numeric, impresiones integer, clics integer, leads_entregados integer, comercial text, id_campana text
-- fact_facturacion: id_factura text, id_cliente text, id_orden text, importe_eur numeric, fecha_emision date, condiciones_pago_dias integer, fecha_vencimiento date, fecha_cobro date, dias_retraso numeric, estado text
-- [legado] fact_informes: id bigint, id_cliente text, id_orden text, fecha_envio date, impresiones bigint, ctr numeric, ctr_relativo numeric, cumple_umbral boolean, tono text, reviso text, fecha_apertura timestamp with time zone, genero_conversacion boolean
-- fact_interacciones: id_interaccion text, id_cliente text, fecha date, tipo text, canal text, resultado text, comercial text, previa_al_alta text
-- [legado] historial_propuesta: id bigint, id_propuesta bigint, fase text, actor_tipo text, actor_nombre text, motivo text, creado_en timestamp with time zone
-- [legado] kpis_ciclo: fecha_corte date, indicador text, valor text
-- leads: id_lead text, razon_social text, categoria text, provincia text, tamano text, web text, origen text, comercial_asignado text, estado text, consentimiento_comercial boolean, consentimiento_fecha timestamp with time zone, consentimiento_medio text, consentimiento_texto text, mensaje text, id_cliente_convertido text, creado_por text, creado_en timestamp with time zone
-- [legado] leadscore: id_lead text, fecha_creacion date, canal_origen text, categoria text, score numeric, banda text, estado text
-- [legado] log_correcciones: id bigint, punto text, modelo_afectado text, valor_propuesto text, valor_corregido text, validado_en timestamp with time zone, id_objeto text, validado_por text, id_propuesta bigint, producto_original text, producto_corregido text, descuento_original numeric, descuento_corregido numeric, precio_corregido numeric, mensaje_original text, mensaje_corregido text, motivo text, corregido_por text, corregido_en timestamp with time zone
-- [legado] log_validaciones: id bigint, punto text, id_objeto text, veredicto text, motivo text, validado_por text, validado_en timestamp with time zone
-- material_versiones: id bigint, propuesta_id bigint, version integer, origen text, autor text, texto text, creado_en timestamp with time zone, avisos ARRAY
-- [legado] next_best_action: id bigint, id_cliente text, segmento text, accion text, prioridad integer, producto_sugerido text, motivo text, valor_estimado numeric, probabilidad_churn numeric, estado text, motivo_validacion text, validado_por text, validado_en timestamp with time zone, valor_en_riesgo numeric, descuento numeric, precio_final numeric, argumento text, mensaje text, estado_oferta text, negociacion_directa boolean, origen_valor_riesgo text, oferta_generada_en timestamp with time zone, gmail_draft_id text, enviado_en timestamp with time zone, error_envio text, email_destinatario text
-- oportunidades: id_oportunidad text, id_cliente text, id_lead text, origen text, id_producto_propuesto text, importe_propuesto_eur numeric, fecha_envio date, fecha_cierre date, desenlace text, id_orden text, n_toques_seguimiento integer, dias_hasta_cierre integer, comercial text, correccion text
-- [legado] parametros: clave text, valor numeric, valor_texto text
-- perfiles: correo text, rol text, id_comercial text
-- [legado] productos: id_producto text, nombre text, familia text, unidad_venta text, tarifa_base_eur numeric, margen numeric, capacidad_mensual numeric, meses_disponible text, es_producto_entrada text, es_producto_compromiso text, capacidad_anual_eur numeric
-- propuestas: id bigint, fecha_corte date, etiqueta text, id_cliente text, id_lead text, comercial_asignado text, comercial_nombre text, orden_comercial integer, razon_social text, categoria text, tipo_riesgo text, banda_riesgo text, prob_abandono numeric, valor_esperado_accion numeric, facturacion_en_riesgo numeric, valor_cuenta numeric, cuenta_clave boolean, requiere_direccion boolean, motivo_principal text, motivo_secundario text, accion_id text, producto_sugerido_nombre text, fecha_limite date, justificacion text, ficha_cuenta text, material_titulo text, material_cuerpo text, notas_internas text, fuente_material text, canal text, id_contacto text, asunto_email text, id_producto_propuesto text, importe_propuesto_eur numeric, estado_envio text, texto_aprobado text, version_aprobada integer, aprobada_por text, aprobada_en timestamp with time zone, motivo_rechazo text, enviada_en timestamp with time zone, id_mensaje text, error_envio text, ultima_respuesta_en timestamp with time zone, desenlace text, motivo_desenlace text, estado_tarea text, estado_confirmado_comercial text, motivo_confirmado text, diagnostico_correcto text, comentario_comercial text, material_editado text, fecha_confirmacion timestamp with time zone, creado_en timestamp with time zone, estado text, grupo_piloto text, envio_reservado_en timestamp with time zone, envio_reserva uuid, ultimo_toque_en timestamp with time zone
-- [legado] reglas_propuestas: id bigint, creada_en timestamp with time zone, ambito text, producto text, categoria text, regla text, evidencia text, n_casos integer, estado text, revisada_por text, revisada_en timestamp with time zone
-- [legado] segmentos: id_cliente text, segmento text, monetario_anual numeric, frecuencia_anual numeric, ticket_medio numeric, recencia_dias integer
-- Vistas de legado: v_catalogo, v_contexto_cliente, v_correcciones_contexto, v_reglas_activas, v_tasa_correccion
