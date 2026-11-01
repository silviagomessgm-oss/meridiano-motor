-- =====================================================================================
-- Meridiano · Base de datos común (Supabase / Postgres) para n8n, el motor de cálculo y el panel de Lovable
-- Circuito: n8n (motor + IA) → Supabase ↔ Lovable.  Lovable escribe directamente en Supabase, pero SOLO a través de
-- accion_panel(): comprueba la sesión y la cartera, cambia la propuesta y deja la traza (evento y versión del material)
-- en una sola transacción. El panel no puede tocar las tablas por otra vía. Los cierres disparan las alertas de n8n.
-- Panel comercial unificado (v2): cada empresa con su etiqueta (riesgo · ampliación · lead nuevo · seguimiento), propuesta
-- redactada por la IA, aprobación / corrección / rechazo en el panel y envío SOLO al aprobar (lo hace n8n y lo registra aquí).
-- Datos FICTICIOS del caso de estudio. Las tablas de datos replican las columnas de datos v3 (tablas/*.csv).
-- Ejecutar en el editor SQL de Supabase. Después, cargar los datos con:  python motor/sync_supabase.py cargar
-- =====================================================================================

-- ---------------------------------------------------------------- 1. Tablas de datos (sistema de registro)
create table if not exists dim_comercial (
  id_comercial text primary key,
  nombre       text not null,
  correo       text not null unique
);

create table if not exists dim_clientes (
  id_cliente text primary key, razon_social text, categoria text, provincia text, tamano text,
  fecha_alta date, antiguedad_meses int, canal_captacion text,
  comercial_asignado text references dim_comercial(id_comercial),
  cp_sede int, tiene_web_propia boolean, anio_fundacion int
);

create table if not exists dim_productos (
  id_producto text primary key, nombre text, familia text, unidad_venta text, tarifa_base_eur numeric,
  margen numeric, capacidad_mensual int, meses_disponible text, es_producto_entrada boolean,
  es_producto_compromiso boolean, capacidad_anual_eur numeric
);

create table if not exists fact_campanas (
  id_orden text primary key, id_cliente text references dim_clientes(id_cliente), id_producto text references dim_productos(id_producto),
  familia text, fecha_orden date, fecha_emision date, mes_emision text, tarifa_base_eur numeric, descuento_pct numeric,
  importe_eur numeric, impresiones int, clics int, leads_entregados int, comercial text, id_campana text
);

create table if not exists fact_facturacion (
  id_factura text primary key, id_cliente text references dim_clientes(id_cliente), id_orden text references fact_campanas(id_orden),
  importe_eur numeric, fecha_emision date, condiciones_pago_dias int, fecha_vencimiento date, fecha_cobro date,
  dias_retraso numeric, estado text
);

create table if not exists fact_interacciones (
  id_interaccion text primary key, id_cliente text references dim_clientes(id_cliente), fecha date, tipo text, canal text,
  resultado text, comercial text, previa_al_alta text
);

create table if not exists oportunidades (
  id_oportunidad text primary key, id_cliente text, id_lead text, origen text, id_producto_propuesto text,
  importe_propuesto_eur numeric, fecha_envio date, fecha_cierre date, desenlace text, id_orden text,
  n_toques_seguimiento int, dias_hasta_cierre int, comercial text, correccion text
);

-- ---------------------------------------------------------------- 2. Usuarios del panel
-- Cada persona que entra en el panel de Lovable (Supabase Auth) tiene un perfil por su correo.
create table if not exists perfiles (
  correo       text primary key,
  rol          text not null check (rol in ('comercial', 'direccion')),
  id_comercial text references dim_comercial(id_comercial)
);

-- ---------------------------------------------------------------- 2b. Leads y contactos (sistema de registro: Supabase)
-- Un lead entra por el formulario web (con consentimiento para recibir información comercial) o lo da de alta un comercial
-- desde el panel (puerta fría, sin consentimiento hasta que se registre cómo y cuándo se obtuvo).
create sequence if not exists leads_seq;
create table if not exists leads (
  id_lead                  text primary key default ('L' || lpad(nextval('leads_seq')::text, 5, '0')),
  razon_social             text not null,
  categoria                text,
  provincia                text,
  tamano                   text,
  web                      text,
  origen                   text not null check (origen in ('formulario_web', 'puerta_fria')),
  comercial_asignado       text not null references dim_comercial(id_comercial),
  estado                   text not null default 'nuevo' check (estado in ('nuevo', 'en_curso', 'convertido', 'descartado')),
  consentimiento_comercial boolean not null default false,
  consentimiento_fecha     timestamptz,
  consentimiento_medio     text,          -- 'formulario_web', 'telefono', 'presencial', 'email'
  consentimiento_texto     text,          -- texto exacto que aceptó (formulario) o nota del comercial
  mensaje                  text,
  id_cliente_convertido    text references dim_clientes(id_cliente),
  creado_por               text not null,
  creado_en                timestamptz not null default now(),
  constraint web_con_consentimiento check (origen <> 'formulario_web' or consentimiento_comercial),
  constraint consentimiento_trazable check (not consentimiento_comercial
                                            or (consentimiento_fecha is not null and consentimiento_medio is not null))
);

-- Personas de contacto. Las de clientes vienen de la hoja (W0); las de leads, del formulario o del panel.
-- En el caso de estudio son FICTICIAS (dominio .example, que no existe); n8n en modo demo desvía todo envío al buzón de pruebas.
create table if not exists contactos (
  id_contacto text primary key,            -- 'CT-<id_cliente>-n' (hoja) o 'CT-<id_lead>-n' (formulario / panel)
  id_cliente  text references dim_clientes(id_cliente),
  id_lead     text references leads(id_lead),
  nombre      text not null,
  cargo       text,
  email       text,
  telefono    text,
  principal   boolean not null default true,
  ficticio    boolean not null default true,
  constraint contacto_de_una_empresa check (num_nonnulls(id_cliente, id_lead) = 1)
);

create table if not exists eventos_lead (
  id        bigint generated always as identity primary key,
  id_lead   text not null references leads(id_lead),
  accion    text not null,                 -- alta_formulario_web, alta_puerta_fria, consentimiento_registrado
  usuario   text not null,
  datos     jsonb,
  creado_en timestamptz not null default now()
);

-- ---------------------------------------------------------------- 3. Salidas del proceso
-- Una fila por propuesta y semana (solo las 'propuesto'; el grupo de control no se muestra a los comerciales).
-- Cada propuesta es de un cliente (riesgo, ampliación, seguimiento) o de un lead (lead nuevo).
create table if not exists propuestas (
  id                    bigint generated always as identity primary key,
  fecha_corte           date not null,
  etiqueta              text not null default 'riesgo' check (etiqueta in ('riesgo', 'ampliacion', 'lead_nuevo', 'seguimiento')),
  id_cliente            text references dim_clientes(id_cliente),
  id_lead               text references leads(id_lead),
  comercial_asignado    text not null references dim_comercial(id_comercial),
  comercial_nombre      text,
  orden_comercial       int,
  razon_social          text,
  categoria             text,
  tipo_riesgo           text check (tipo_riesgo in ('perdida_total', 'contraccion')),
  banda_riesgo          text,
  prob_abandono         numeric,
  valor_esperado_accion numeric,
  facturacion_en_riesgo numeric,
  valor_cuenta          numeric,
  cuenta_clave          boolean,
  requiere_direccion    boolean,
  motivo_principal      text,
  motivo_secundario     text,
  accion_id             text,
  producto_sugerido_nombre text,
  fecha_limite          date,
  justificacion         text,
  ficha_cuenta          text,
  material_titulo       text,
  material_cuerpo       text,
  notas_internas        text,
  fuente_material       text,        -- 'plantilla' (motor) o 'llm' (n8n, tras pasar el validador)
  canal                 text not null default 'email' check (canal in ('email', 'llamada')),
  id_contacto           text references contactos(id_contacto),
  asunto_email          text,
  id_producto_propuesto text references dim_productos(id_producto),
  importe_propuesto_eur numeric,
  -- Aprobación y envío: solo lo cambian registrar_accion() / accion_panel(); el envío lo hace n8n al aprobar
  estado_envio          text not null default 'pendiente_aprobacion'
                        check (estado_envio in ('pendiente_aprobacion', 'aprobada', 'enviada', 'error_envio', 'rechazada')),
  texto_aprobado        text,          -- el texto exacto que se aprobó (y que se envía)
  version_aprobada      int,
  aprobada_por          text,
  aprobada_en           timestamptz,
  motivo_rechazo        text,
  enviada_en            timestamptz,
  id_mensaje            text,
  error_envio           text,
  ultima_respuesta_en   timestamptz,
  desenlace             text check (desenlace in ('ganada', 'perdida', 'descartada')),
  motivo_desenlace      text,
  -- Seguimiento del comercial: solo lo cambia registrar_accion() (desde el panel, a través de accion_panel())
  estado_tarea                text not null default 'pendiente' check (estado_tarea in ('pendiente', 'en_curso', 'cerrada')),
  estado_confirmado_comercial text check (estado_confirmado_comercial in ('Perdido', 'Redujo mucho', 'Activo', 'Pausa: volvió después', 'No sé')),
  motivo_confirmado           text check (motivo_confirmado in ('rendimiento_campanas', 'relacion_interlocutor', 'perdida_contacto',
                                     'servicio_reclamacion', 'presupuesto_inversion', 'cobro_financiero', 'temporada', 'otro')),
  diagnostico_correcto        text check (diagnostico_correcto in ('Sí', 'No')),
  comentario_comercial        text,
  material_editado            text,          -- última versión corregida por el comercial (todas en material_versiones)
  fecha_confirmacion          timestamptz,
  creado_en                   timestamptz not null default now(),
  -- Estado único que ve el panel
  estado text generated always as (case
      when estado_envio = 'rechazada' then 'rechazada'
      when estado_tarea = 'cerrada' then 'cerrada'
      when estado_envio in ('pendiente_aprobacion', 'error_envio') then estado_envio
      when estado_envio = 'aprobada' and canal = 'email' then 'enviando'
      else 'en_seguimiento' end) stored,
  unique (fecha_corte, id_cliente),
  unique (fecha_corte, id_lead),
  constraint propuesta_de_una_empresa check (num_nonnulls(id_cliente, id_lead) = 1),
  constraint lead_con_etiqueta check ((id_lead is null) = (etiqueta <> 'lead_nuevo')),
  -- Ninguna propuesta se cierra sin su información: rechazo con motivo; riesgo con estado, motivo y diagnóstico;
  -- el resto con desenlace (y motivo si no se ganó)
  constraint cierre_completo check (estado_tarea <> 'cerrada'
    or (estado_envio = 'rechazada' and motivo_rechazo is not null)
    or (estado_envio <> 'rechazada' and etiqueta = 'riesgo' and estado_confirmado_comercial is not null
        and motivo_confirmado is not null and diagnostico_correcto is not null)
    or (estado_envio <> 'rechazada' and etiqueta <> 'riesgo' and desenlace is not null
        and (desenlace = 'ganada' or motivo_desenlace is not null))),
  constraint aprobada_con_texto check (estado_envio not in ('aprobada', 'enviada') or
                                       (texto_aprobado is not null and aprobada_por is not null))
);

-- Cuentas de cada ciclo semanal (propuestas y grupo de control). El motor reconstruye con ellas el enfriamiento
-- de 90 días, así que no necesita guardar nada entre ejecuciones (puede correr en un servicio sin disco).
create table if not exists asignaciones_ciclo (
  fecha_corte date not null,
  id_cliente  text not null references dim_clientes(id_cliente),
  estado_plan text not null check (estado_plan in ('propuesto', 'control')),
  primary key (fecha_corte, id_cliente)
);

-- ---------------------------------------------------------------- 3b. Trazabilidad (solo se añaden filas; nunca se modifican ni se borran)
-- Cada versión del material: plantilla del motor, texto de Claude validado y cada corrección del comercial.
create table if not exists material_versiones (
  id           bigint generated always as identity primary key,
  propuesta_id bigint not null references propuestas(id),
  version      int not null,
  origen       text not null check (origen in ('plantilla', 'llm', 'comercial')),
  autor        text not null,            -- 'motor', 'n8n · Claude' o el correo del comercial
  texto        text not null,
  creado_en    timestamptz not null default now(),
  unique (propuesta_id, version)
);

-- Cada paso de la propuesta: publicada, material de la IA, en curso, material corregido, cerrada, reabierta.
create table if not exists eventos_propuesta (
  id             bigint generated always as identity primary key,
  propuesta_id   bigint not null references propuestas(id),
  accion         text not null,
  usuario        text not null,          -- 'motor', 'n8n' o el correo de quien actúa en el panel
  estado_antes   text,
  estado_despues text,
  datos          jsonb,
  creado_en      timestamptz not null default now()
);
create index if not exists eventos_propuesta_idx on eventos_propuesta (propuesta_id, creado_en);

create table if not exists estado_etiqueta (
  fecha_corte      date primary key,
  etiqueta_vigente text not null,
  estado           text,
  casos            int,
  acuerdo          numeric,
  calculado_en     timestamptz not null default now()
);

create table if not exists kpis_ciclo (
  fecha_corte date not null,
  indicador   text not null,
  valor       text,
  primary key (fecha_corte, indicador)
);

create table if not exists ejecuciones (
  id        bigint generated always as identity primary key,
  fecha     timestamptz not null default now(),
  origen    text,               -- 'motor' o 'n8n'
  estado    text,
  detalle   jsonb
);

-- ---------------------------------------------------------------- 4. Seguridad (RLS)
-- El motor y n8n usan la clave de servicio (sin RLS). El panel usa la clave pública + login de cada persona.
create or replace function mi_comercial() returns text language sql stable security definer set search_path = public as
$$ select id_comercial from perfiles where correo = auth.jwt() ->> 'email' $$;

create or replace function es_direccion() returns boolean language sql stable security definer set search_path = public as
$$ select coalesce((select rol = 'direccion' from perfiles where correo = auth.jwt() ->> 'email'), false) $$;

alter table propuestas         enable row level security;
alter table dim_clientes       enable row level security;
alter table fact_campanas      enable row level security;
alter table fact_interacciones enable row level security;
alter table fact_facturacion   enable row level security;
alter table oportunidades      enable row level security;
alter table dim_comercial      enable row level security;
alter table dim_productos      enable row level security;
alter table perfiles           enable row level security;
alter table estado_etiqueta    enable row level security;
alter table kpis_ciclo     enable row level security;
alter table ejecuciones        enable row level security;

-- Propuestas: cada comercial ve y confirma solo las suyas; dirección ve todas
drop policy if exists propuestas_ver on propuestas;
create policy propuestas_ver on propuestas for select to authenticated
  using (comercial_asignado = mi_comercial() or es_direccion());
-- El panel no puede insertar, modificar ni borrar en ninguna tabla: sus acciones van por la función accion_panel().
revoke insert, update, delete on all tables in schema public from anon, authenticated;

alter table leads               enable row level security;
alter table contactos           enable row level security;
alter table eventos_lead        enable row level security;
drop policy if exists leads_ver on leads;
create policy leads_ver on leads for select to authenticated using (comercial_asignado = mi_comercial() or es_direccion());
drop policy if exists contactos_ver on contactos;
create policy contactos_ver on contactos for select to authenticated using (es_direccion()
  or id_cliente in (select id_cliente from dim_clientes where comercial_asignado = mi_comercial())
  or id_lead in (select id_lead from leads where comercial_asignado = mi_comercial()));
drop policy if exists eventos_lead_ver on eventos_lead;
create policy eventos_lead_ver on eventos_lead for select to authenticated
  using (es_direccion() or id_lead in (select id_lead from leads where comercial_asignado = mi_comercial()));

alter table asignaciones_ciclo  enable row level security;
alter table material_versiones  enable row level security;
alter table eventos_propuesta   enable row level security;
drop policy if exists versiones_ver on material_versiones;
create policy versiones_ver on material_versiones for select to authenticated
  using (es_direccion() or propuesta_id in (select id from propuestas where comercial_asignado = mi_comercial()));
drop policy if exists eventos_ver on eventos_propuesta;
create policy eventos_ver on eventos_propuesta for select to authenticated
  using (es_direccion() or propuesta_id in (select id from propuestas where comercial_asignado = mi_comercial()));
drop policy if exists asignaciones_ver on asignaciones_ciclo;
create policy asignaciones_ver on asignaciones_ciclo for select to authenticated using (es_direccion());

-- Datos de cuentas: cada comercial ve las de su cartera; dirección, todas (solo lectura)
drop policy if exists clientes_ver on dim_clientes;
create policy clientes_ver on dim_clientes for select to authenticated using (comercial_asignado = mi_comercial() or es_direccion());
drop policy if exists campanas_ver on fact_campanas;
create policy campanas_ver on fact_campanas for select to authenticated
  using (es_direccion() or id_cliente in (select id_cliente from dim_clientes where comercial_asignado = mi_comercial()));
drop policy if exists interacciones_ver on fact_interacciones;
create policy interacciones_ver on fact_interacciones for select to authenticated
  using (es_direccion() or id_cliente in (select id_cliente from dim_clientes where comercial_asignado = mi_comercial()));
drop policy if exists facturas_ver on fact_facturacion;
create policy facturas_ver on fact_facturacion for select to authenticated
  using (es_direccion() or id_cliente in (select id_cliente from dim_clientes where comercial_asignado = mi_comercial()));
drop policy if exists oportunidades_ver on oportunidades;
create policy oportunidades_ver on oportunidades for select to authenticated
  using (es_direccion() or id_cliente in (select id_cliente from dim_clientes where comercial_asignado = mi_comercial()));
drop policy if exists productos_ver on dim_productos;
create policy productos_ver on dim_productos for select to authenticated using (true);
drop policy if exists comerciales_ver on dim_comercial;
create policy comerciales_ver on dim_comercial for select to authenticated using (true);
drop policy if exists perfil_propio on perfiles;
create policy perfil_propio on perfiles for select to authenticated using (correo = auth.jwt() ->> 'email' or es_direccion());

-- Indicadores y estado de la etiqueta: solo dirección
drop policy if exists etiqueta_ver on estado_etiqueta;
create policy etiqueta_ver on estado_etiqueta for select to authenticated using (es_direccion());
drop policy if exists kpis_ver on kpis_ciclo;
create policy kpis_ver on kpis_ciclo for select to authenticated using (es_direccion());
drop policy if exists ejecuciones_ver on ejecuciones;
create policy ejecuciones_ver on ejecuciones for select to authenticated using (es_direccion());

-- ---------------------------------------------------------------- 4b. Traza automática de publicaciones y versiones del material
create or replace function trazar_propuesta() returns trigger language plpgsql security definer set search_path = public as $$
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
end $$;

-- Al publicar: canal según la acción (la reactivación es una llamada) y contacto principal de la empresa
create or replace function completar_propuesta() returns trigger language plpgsql security definer set search_path = public as $$
begin
  if new.accion_id = 'llamada_reactivacion' then new.canal := 'llamada'; end if;
  if new.id_contacto is null then
    select id_contacto into new.id_contacto from contactos
    where (contactos.id_cliente = new.id_cliente or contactos.id_lead = new.id_lead)
    order by principal desc, id_contacto limit 1;
  end if;
  return new;
end $$;
drop trigger if exists completar_propuesta on propuestas;
create trigger completar_propuesta before insert on propuestas for each row execute function completar_propuesta();

drop trigger if exists trazar_propuesta on propuestas;
create trigger trazar_propuesta after insert or update on propuestas for each row execute function trazar_propuesta();

-- ---------------------------------------------------------------- 4c. Única puerta de escritura sobre el seguimiento
-- Cambia la propuesta y registra el evento en la misma transacción: si algo falla, no se guarda nada.
create or replace function registrar_accion(p_propuesta_id bigint, p_accion text, p_usuario text, p_datos jsonb default '{}'::jsonb)
returns jsonb language plpgsql security definer set search_path = public as $$
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
end $$;

-- registrar_accion() acepta cualquier usuario como parámetro, así que el panel no puede llamarla directamente
revoke all on function registrar_accion(bigint, text, text, jsonb) from public, anon, authenticated;
grant execute on function registrar_accion(bigint, text, text, jsonb) to service_role;

-- Lo que llama el panel de Lovable:  supabase.rpc('accion_panel', { p_propuesta_id, p_accion, p_datos })
-- El usuario sale de la sesión (no se puede suplantar) y solo puede actuar sobre su cartera; dirección, sobre todas.
create or replace function accion_panel(p_propuesta_id bigint, p_accion text, p_datos jsonb default '{}'::jsonb)
returns jsonb language plpgsql security definer set search_path = public as $$
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
end $$;
revoke all on function accion_panel(bigint, text, jsonb) from public, anon;
grant execute on function accion_panel(bigint, text, jsonb) to authenticated, service_role;
revoke all on function trazar_propuesta() from public, anon, authenticated;
revoke all on function completar_propuesta() from public, anon, authenticated;

-- ---------------------------------------------------------------- 4d. Alta de leads
-- Comercial con menos leads abiertos (reparto de los que llegan por la web)
create or replace function comercial_para_lead() returns text language sql stable security definer set search_path = public as $$
  select c.id_comercial from dim_comercial c
  left join leads l on l.comercial_asignado = c.id_comercial and l.estado in ('nuevo', 'en_curso')
  group by c.id_comercial order by count(l.id_lead), c.id_comercial limit 1
$$;

-- Formulario de la web (público): el lead acepta recibir información comercial, y se guarda el texto exacto que aceptó.
create or replace function alta_lead_web(p jsonb) returns text language plpgsql security definer set search_path = public as $$
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
end $$;

-- Puerta fría (panel): el comercial da de alta el lead en su cartera; sin consentimiento salvo que indique cómo lo obtuvo.
create or replace function alta_lead_panel(p jsonb) returns jsonb language plpgsql security definer set search_path = public as $$
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
end $$;

-- Consentimiento obtenido después (p. ej. tras una llamada a puerta fría): queda registrado quién, cuándo y cómo.
create or replace function registrar_consentimiento(p_id_lead text, p_medio text, p_nota text default null)
returns jsonb language plpgsql security definer set search_path = public as $$
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
end $$;

revoke all on function comercial_para_lead() from public, anon, authenticated;
revoke all on function alta_lead_web(jsonb) from public;
grant execute on function alta_lead_web(jsonb) to anon, authenticated, service_role;
revoke all on function alta_lead_panel(jsonb) from public, anon;
grant execute on function alta_lead_panel(jsonb) to authenticated, service_role;
revoke all on function registrar_consentimiento(text, text, text) from public, anon;
grant execute on function registrar_consentimiento(text, text, text) to authenticated, service_role;

-- ---------------------------------------------------------------- 5. Vista para el panel: plan vigente (ciclo semanal)
-- Las propuestas nuevas de la última semana y las de semanas anteriores que siguen sin cerrar.
create or replace view plan_vigente with (security_invoker = true) as
  select p.*, (p.fecha_corte = (select max(fecha_corte) from propuestas)) as nueva_esta_semana
  from propuestas p
  where p.estado_tarea <> 'cerrada' or p.fecha_corte = (select max(fecha_corte) from propuestas);

-- Leads que esperan su primera propuesta (los prepara el flujo de los lunes)
create or replace view leads_sin_propuesta with (security_invoker = true) as
  select l.* from leads l
  where l.estado = 'nuevo' and not exists (select 1 from propuestas p where p.id_lead = l.id_lead);

-- Propuestas aprobadas que n8n tiene que enviar (o reintentar)
create or replace view envios_pendientes with (security_invoker = true) as
  select p.id, p.etiqueta, p.comercial_asignado, p.razon_social, p.asunto_email, p.material_titulo, p.texto_aprobado,
         c.nombre as contacto_nombre, c.email as contacto_email, c.ficticio as contacto_ficticio, dc.nombre as comercial_nombre
  from propuestas p join contactos c on c.id_contacto = p.id_contacto join dim_comercial dc on dc.id_comercial = p.comercial_asignado
  where p.estado_envio = 'aprobada' and p.canal = 'email';

-- ---------------------------------------------------------------- 6. Usuarios de la DEMO (datos ficticios)
-- Para la demostración, cada usuario del panel es un alias de una misma cuenta de Gmail (TU-CUENTA+alias@gmail.com):
-- todos los enlaces de acceso llegan a ese buzón. Crear antes los usuarios en Authentication → Users con estos correos.
-- insert into perfiles (correo, rol, id_comercial) values
--   ('TU-CUENTA+martina@gmail.com',   'comercial', 'COM-01'),
--   ('TU-CUENTA+comercial2@gmail.com', 'comercial', 'COM-02'),
--   ('TU-CUENTA+comercial3@gmail.com', 'comercial', 'COM-03'),
--   ('TU-CUENTA+direccion@gmail.com', 'direccion', null);
