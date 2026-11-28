// Filas borradas de la hoja: solo si la carga terminó sin errores de Supabase, se envían a marcar_presencia_carga() los
// identificadores de clientes y contactos que hay en la hoja. Con errores no se marca nada (la hoja pudo cargarse a medias).
const r = $input.first().json;
if (!r.registro || r.registro.estado === 'carga_con_errores') return [];
const p = $('Preparar tablas').first().json.presentes || {};
return [{ json: { p_clientes: [...new Set(p.dim_clientes || [])], p_contactos: [...new Set(p.contactos || [])] } }];
