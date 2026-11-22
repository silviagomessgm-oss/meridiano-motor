-- Volcado del esquema desplegado (auditoría del backlog, H1). Ejecutar en el SQL Editor de Supabase, exportar el resultado
-- como CSV y regenerar esquema_desplegado.sql (los secretos de los triggers se sustituyen por marcadores antes de versionar).
select 'tabla' as tipo, c.table_name as nombre,
       string_agg(c.column_name || ' ' || c.data_type, ', ' order by c.ordinal_position) as definicion
from information_schema.columns c
join information_schema.tables t on t.table_name = c.table_name and t.table_schema = c.table_schema and t.table_type = 'BASE TABLE'
where c.table_schema = 'public' group by c.table_name
union all
select 'vista', c.relname, 'create or replace view public.' || quote_ident(c.relname) || ' as ' || pg_get_viewdef(c.oid, true)
from pg_class c join pg_namespace n on n.oid = c.relnamespace where n.nspname = 'public' and c.relkind = 'v'
union all
select 'funcion', p.proname, pg_get_functiondef(p.oid)
from pg_proc p join pg_namespace n on n.oid = p.pronamespace where n.nspname = 'public' and p.prokind = 'f'
union all
select 'trigger', t.tgname, pg_get_triggerdef(t.oid)
from pg_trigger t join pg_class c on c.oid = t.tgrelid join pg_namespace n on n.oid = c.relnamespace
where n.nspname = 'public' and not t.tgisinternal
order by 1, 2;
