-- =====================================================================================================
-- Meridiano · Registro de auditorías con un modelo auditor (pasos 05 y 08 de FORGEN) · flujo W7
-- Se ejecuta después de schema.sql. Se puede volver a ejecutar.
-- Cada fila es una ejecución del auditor: qué paquete y qué rúbrica revisó (ruta y versión en GitHub), con qué modelo,
-- su veredicto y sus hallazgos tal como los devolvió. Las filas no se modifican ni se borran: son la evidencia.
-- =====================================================================================================

create table if not exists auditorias (
  id               bigint generated always as identity primary key,
  creada_en        timestamptz not null default now(),
  tipo             text not null check (tipo in ('prueba', 'diseno', 'backlog')),
  modelo           text not null,
  paquete_ruta     text not null,
  paquete_sha      text,
  rubrica_ruta     text,
  rubrica_sha      text,
  estado           text not null check (estado in ('ok', 'formato_invalido', 'error')),
  veredicto        text check (veredicto in ('aprobado', 'aprobado con cambios', 'rechazado')),
  resumen          text,
  hallazgos        jsonb not null default '[]'::jsonb,
  puntos_fuertes   jsonb not null default '[]'::jsonb,
  n_altas          int not null default 0,
  n_medias         int not null default 0,
  n_bajas          int not null default 0,
  avisos           jsonb not null default '[]'::jsonb,
  error            text,
  respuesta_bruta  text,
  tokens_entrada   int,
  tokens_salida    int,
  constraint auditoria_ok_con_veredicto check (estado <> 'ok' or veredicto is not null)
);
comment on table auditorias is 'Ejecuciones del modelo auditor (W7). Inmutables: son la evidencia de los pasos 05 y 08 de FORGEN.';

-- Cuerpo entre comillas simples (sin $$): el editor SQL de Supabase puede cortar el texto pegado dentro de un bloque $$
create or replace function auditorias_inmutables() returns trigger language plpgsql
as 'begin raise exception ''Las auditorias no se modifican ni se borran''; end';
drop trigger if exists auditorias_inmutables on auditorias;
create trigger auditorias_inmutables before update or delete on auditorias
  for each row execute function auditorias_inmutables();

alter table auditorias enable row level security;
drop policy if exists auditorias_ver on auditorias;
create policy auditorias_ver on auditorias for select to authenticated using (es_direccion());

revoke all on auditorias from anon, authenticated;
grant select on auditorias to authenticated;
grant select, insert on auditorias to service_role;
grant usage, select on all sequences in schema public to service_role;

-- Vista para el panel de dirección: última auditoría de cada tipo
create or replace view auditorias_ultimas with (security_invoker = true) as
  select distinct on (tipo) id, creada_en, tipo, modelo, estado, veredicto, resumen, n_altas, n_medias, n_bajas, hallazgos
  from auditorias order by tipo, creada_en desc;
revoke all on auditorias_ultimas from anon, authenticated;
grant select on auditorias_ultimas to authenticated, service_role;

select 'auditorias.sql aplicado' as estado, to_regclass('auditorias') is not null as tabla,
       to_regclass('auditorias_ultimas') is not null as vista;
