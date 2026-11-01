-- Meridiano · Comprobación del esquema: devuelve los objetos que FALTAN (ninguna fila = todo correcto)
with esperado(nombre, tipo) as (values
  ('dim_comercial','BASE TABLE'), ('dim_clientes','BASE TABLE'), ('dim_productos','BASE TABLE'), ('fact_campanas','BASE TABLE'),
  ('fact_facturacion','BASE TABLE'), ('fact_interacciones','BASE TABLE'), ('oportunidades','BASE TABLE'), ('perfiles','BASE TABLE'),
  ('leads','BASE TABLE'), ('contactos','BASE TABLE'), ('eventos_lead','BASE TABLE'), ('propuestas','BASE TABLE'),
  ('asignaciones_ciclo','BASE TABLE'), ('material_versiones','BASE TABLE'), ('eventos_propuesta','BASE TABLE'),
  ('estado_etiqueta','BASE TABLE'), ('kpis_ciclo','BASE TABLE'), ('ejecuciones','BASE TABLE'),
  ('plan_vigente','VIEW'), ('leads_sin_propuesta','VIEW'), ('envios_pendientes','VIEW'))
select 'FALTA: ' || e.nombre || ' (' || e.tipo || ')' as resultado from esperado e
where not exists (select 1 from information_schema.tables t where t.table_schema = 'public' and t.table_name = e.nombre and t.table_type = e.tipo)
union all
select 'FALTA la columna propuestas.estado_envio (esquema antiguo)' where not exists
  (select 1 from information_schema.columns where table_schema = 'public' and table_name = 'propuestas' and column_name = 'estado_envio')
union all
select 'SOBRA (versión anterior): ' || table_name from information_schema.tables
where table_schema = 'public' and table_name in ('plan_mes_actual', 'kpis_mensuales');
