-- =====================================================================================
-- Meridiano · BORRA todos los objetos del caso (tablas, vistas, funciones) para volver a ejecutar schema.sql desde cero.
-- Incluye nombres de versiones anteriores del esquema. No toca nada de Supabase (auth, storage, permisos por defecto).
-- ATENCIÓN: borra también los datos de esas tablas. Úsalo solo antes de la carga o si quieres empezar de nuevo.
-- =====================================================================================
drop view if exists plan_vigente, plan_mes_actual, leads_sin_propuesta, envios_pendientes cascade;
drop table if exists eventos_propuesta, material_versiones, propuestas, asignaciones_ciclo, eventos_lead, contactos, leads,
  estado_etiqueta, kpis_ciclo, kpis_mensuales, ejecuciones, perfiles, oportunidades, fact_interacciones, fact_facturacion,
  fact_campanas, dim_clientes, dim_productos, dim_comercial cascade;
drop sequence if exists leads_seq cascade;
drop function if exists registrar_accion(bigint, text, text, jsonb), accion_panel(bigint, text, jsonb), trazar_propuesta(),
  completar_propuesta(), comercial_para_lead(), alta_lead_web(jsonb), alta_lead_panel(jsonb),
  registrar_consentimiento(text, text, text), mi_comercial(), es_direccion() cascade;
