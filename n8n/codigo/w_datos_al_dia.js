// H7 · Puerta de datos: solo se sigue si la última carga de W0 terminó bien hace menos de 8 días (ultima_carga() en Supabase).
// Si Supabase no responde, tampoco se sigue: mejor no generar propuestas que generarlas con datos viejos.
const r = $input.first().json || {};
const c = (r.body && typeof r.body === 'object') ? r.body : {};
const ok = r.statusCode >= 200 && r.statusCode < 300 && c.apta === true;
return ok ? $('Fecha de corte').all() : [];
