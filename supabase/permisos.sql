-- =====================================================================================
-- Meridiano · Permisos explícitos para la API de Supabase (Data API / PostgREST).
-- Los proyectos nuevos de Supabase pueden crearse SIN los permisos automáticos sobre las tablas nuevas; entonces n8n y el
-- motor reciben "permission denied" (n8n lo muestra como «Authorization failed»). Este script los da de forma explícita.
-- Se puede ejecutar las veces que haga falta. Ya va incluido al final de schema.sql.
-- =====================================================================================
grant usage on schema public to anon, authenticated, service_role;

-- n8n y el motor (clave de servicio): todo
grant all on all tables in schema public to service_role;
grant all on all sequences in schema public to service_role;
grant execute on all functions in schema public to service_role;

-- Panel de Lovable (usuarios con sesión): solo LECTURA; lo que ve cada uno lo decide la RLS
grant select on all tables in schema public to authenticated;
revoke insert, update, delete on all tables in schema public from anon, authenticated;
grant execute on function accion_panel(bigint, text, jsonb), alta_lead_panel(jsonb), registrar_consentimiento(text, text, text)
  to authenticated;

-- Formulario web (público): solo el alta de leads
grant execute on function alta_lead_web(jsonb) to anon, authenticated;

-- Funciones internas: nadie salvo la clave de servicio
revoke execute on function registrar_accion(bigint, text, text, jsonb), trazar_propuesta(), completar_propuesta(), comercial_para_lead()
  from public, anon, authenticated;
