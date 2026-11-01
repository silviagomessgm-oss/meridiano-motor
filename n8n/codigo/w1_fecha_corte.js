// Ciclo semanal (martes por la mañana): la fecha de corte es el lunes anterior, con los datos de la semana ya cerrados.
// Para una ejecución manual de prueba, cambiar por: return [{ json: { fecha_corte: '2026-09-28' } }];
const hoy = new Date();
const dia = hoy.getUTCDay();                               // 0 domingo … 2 martes
const atras = ((dia - 1) + 7) % 7 || 7;                    // días hasta el lunes anterior (un lunes, el de la semana pasada)
const lunes = new Date(Date.UTC(hoy.getUTCFullYear(), hoy.getUTCMonth(), hoy.getUTCDate() - atras));
return [{ json: { fecha_corte: lunes.toISOString().slice(0, 10) } }];
