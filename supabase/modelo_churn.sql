-- Meridiano · Modelo de abandono de modelo_churn (27-nov-2026)
-- Ejecutar una vez en el SQL Editor de Supabase, después de los demás ficheros. Se puede ejecutar varias veces.
--   1. propuestas.modelo: qué modelo de abandono generó cada propuesta. Las propuestas anteriores al cambio quedan sin
--      valor (el panel las muestra como «Modelo anterior»): al cambiar el modelo pueden cambiar las cuentas propuestas.
--   2. resultado_acciones: para cada cuenta propuesta o en el grupo de control, cuando su ventana de 210 días ha terminado,
--      si abandonó (etiqueta E2) y si se salvó (hubo acción del comercial y no abandonó). Solo la ve dirección.
--   3. resumen_resultado_acciones: abandono y cuentas salvadas por grupo (acción, propuesta sin acción, control).
--   4. efecto_accion: abandono con acción frente al grupo de control DENTRO de la banda de riesgo media. El control se
--      sortea solo en la banda media, así que es la única comparación justa (la banda alta no tiene control).

-- ---------------------------------------------------------------- 1. Modelo de cada propuesta
alter table propuestas add column if not exists modelo text;
comment on column propuestas.modelo is
  'Modelo de abandono que generó la propuesta (p. ej. «E2 · regresión logística (modelo_churn)»). Vacío: modelo anterior.';

-- ---------------------------------------------------------------- 1b. plan_vigente con la columna modelo
-- Misma definición que la desplegada (esquema_desplegado.sql) con «modelo» al final. Se borra y se crea de nuevo porque
-- schema.sql y la versión desplegada tienen columnas distintas; security_invoker = true para que cada comercial siga
-- viendo solo sus propuestas (RLS de propuestas).
drop view if exists public.plan_vigente;
create view public.plan_vigente with (security_invoker = true) as  SELECT id,
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
    cerrada_en,
    modelo
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
            p.modelo,
            p.fecha_corte = (( SELECT max(propuestas.fecha_corte) AS max
                   FROM propuestas)) AS nueva_esta_semana,
            ( SELECT max(e.creado_en) AS max
                   FROM eventos_propuesta e
                  WHERE e.propuesta_id = p.id AND (e.accion = ANY (ARRAY['cerrar'::text, 'rechazar'::text]))) AS cerrada_en
           FROM propuestas p) x
  WHERE estado_tarea <> 'cerrada'::text OR cerrada_en >= (now() - '7 days'::interval) OR cerrada_en IS NULL AND fecha_corte = (( SELECT max(propuestas.fecha_corte) AS max
           FROM propuestas));
grant select on public.plan_vigente to authenticated;
grant all on public.plan_vigente to service_role;

-- ---------------------------------------------------------------- 1c. Banda de riesgo de cada asignación semanal
alter table asignaciones_ciclo add column if not exists banda_riesgo text;

-- ---------------------------------------------------------------- 2. Resultado de las acciones
create table if not exists resultado_acciones (
  fecha_corte                 date not null,          -- ciclo en que la cuenta se propuso o quedó en control
  id_cliente                  text not null references dim_clientes(id_cliente),
  grupo                       text not null check (grupo in ('accion', 'propuesta_sin_accion', 'control')),
  banda_riesgo                text,                   -- banda de riesgo cuando se asignó (alta, media, baja)
  resultado                   text not null,          -- perdida_total, contraccion, activo… (etiqueta E2 en fecha_corte)
  abandono                    boolean not null,
  salvada                     boolean not null,       -- grupo 'accion' y sin abandono
  estado_confirmado_comercial text,                   -- lo que confirmó el comercial al cerrar (si cerró)
  fecha_resultado             date not null,          -- fin de la ventana de 210 días
  calculado_en                timestamptz not null default now(),
  primary key (fecha_corte, id_cliente),
  constraint salvada_coherente check (salvada = (grupo = 'accion' and not abandono))
);
comment on table resultado_acciones is
  'Qué cuentas salva el equipo comercial: abandono con acción, sin acción y en el grupo de control (lo escribe el motor).';

alter table resultado_acciones enable row level security;
drop policy if exists resultado_acciones_ver on resultado_acciones;
create policy resultado_acciones_ver on resultado_acciones for select to authenticated using (es_direccion());

-- ---------------------------------------------------------------- 3. Resumen por grupo (para las tarjetas del panel)
create or replace view resumen_resultado_acciones with (security_invoker = true) as
  select grupo,
         count(*)                                         as cuentas,
         count(*) filter (where abandono)                  as abandonos,
         round(100.0 * avg(abandono::int), 1)              as pct_abandono,
         count(*) filter (where salvada)                   as salvadas,
         min(fecha_corte)                                  as desde,
         max(fecha_corte)                                  as hasta
  from resultado_acciones
  group by grupo;

alter table resultado_acciones add column if not exists banda_riesgo text;   -- por si la tabla ya existía

create or replace view efecto_accion with (security_invoker = true) as
  select 'media'::text                                                              as banda,
         count(*) filter (where grupo = 'accion')                                   as cuentas_accion,
         round(100.0 * avg(abandono::int) filter (where grupo = 'accion'), 1)      as pct_abandono_accion,
         count(*) filter (where grupo = 'control')                                  as cuentas_control,
         round(100.0 * avg(abandono::int) filter (where grupo = 'control'), 1)     as pct_abandono_control,
         round(100.0 * avg(abandono::int) filter (where grupo = 'control')
             - 100.0 * avg(abandono::int) filter (where grupo = 'accion'), 1)      as diferencia_puntos
  from resultado_acciones
  where banda_riesgo = 'media';

-- ---------------------------------------------------------------- 4. Permisos (como el resto del esquema)
grant all on resultado_acciones to service_role;
grant select on resultado_acciones, resumen_resultado_acciones, efecto_accion to authenticated;
revoke insert, update, delete on resultado_acciones from anon, authenticated;
