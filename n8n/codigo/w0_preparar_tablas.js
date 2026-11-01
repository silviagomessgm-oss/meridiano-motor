// Carga semanal: valida las pestañas de la hoja de datos y las prepara para Supabase, en orden de dependencias.
// Cada pestaña es la tabla COMPLETA (fila 1 = cabeceras con los mismos nombres de columna). Las filas se actualizan por su
// identificador: corregir una fila en la hoja la corrige en Supabase. Las filas no válidas no se cargan y se informan.
// Si falta una pestaña o una columna, o una tabla tiene demasiados errores, NO se carga nada.
const MAX_RECHAZO = 0.05;            // más de un 5 % de filas rechazadas en una tabla → no se carga nada
const LOTE = 1000;
const T = {   // tipos: t texto · d fecha · i entero · n número · b sí/no
  dim_comercial:      { pk: 'id_comercial', c: { id_comercial: 't', nombre: 't', correo: 't' } },
  dim_productos:      { pk: 'id_producto', c: { id_producto: 't', nombre: 't', familia: 't', unidad_venta: 't', tarifa_base_eur: 'n', margen: 'n',
                         capacidad_mensual: 'i', meses_disponible: 't', es_producto_entrada: 'b', es_producto_compromiso: 'b', capacidad_anual_eur: 'n' } },
  dim_clientes:       { pk: 'id_cliente', c: { id_cliente: 't', razon_social: 't', categoria: 't', provincia: 't', tamano: 't', fecha_alta: 'd',
                         antiguedad_meses: 'i', canal_captacion: 't', comercial_asignado: 't', cp_sede: 'i', tiene_web_propia: 'b', anio_fundacion: 'i' },
                        fk: { comercial_asignado: 'dim_comercial' } },
  fact_campanas:      { pk: 'id_orden', c: { id_orden: 't', id_cliente: 't', id_producto: 't', familia: 't', fecha_orden: 'd', fecha_emision: 'd',
                         mes_emision: 't', tarifa_base_eur: 'n', descuento_pct: 'n', importe_eur: 'n', impresiones: 'i', clics: 'i',
                         leads_entregados: 'i', comercial: 't', id_campana: 't' },
                        fk: { id_cliente: 'dim_clientes', id_producto: 'dim_productos' }, obligatorias: ['id_cliente', 'fecha_emision', 'importe_eur'] },
  fact_facturacion:   { pk: 'id_factura', c: { id_factura: 't', id_cliente: 't', id_orden: 't', importe_eur: 'n', fecha_emision: 'd',
                         condiciones_pago_dias: 'i', fecha_vencimiento: 'd', fecha_cobro: 'd', dias_retraso: 'n', estado: 't' },
                        fk: { id_cliente: 'dim_clientes', id_orden: 'fact_campanas' }, obligatorias: ['id_cliente', 'fecha_emision', 'importe_eur'] },
  fact_interacciones: { pk: 'id_interaccion', c: { id_interaccion: 't', id_cliente: 't', fecha: 'd', tipo: 't', canal: 't', resultado: 't',
                         comercial: 't', previa_al_alta: 't' }, fk: { id_cliente: 'dim_clientes' }, obligatorias: ['id_cliente', 'fecha'] },
  oportunidades:      { pk: 'id_oportunidad', c: { id_oportunidad: 't', id_cliente: 't', id_lead: 't', origen: 't', id_producto_propuesto: 't',
                         importe_propuesto_eur: 'n', fecha_envio: 'd', fecha_cierre: 'd', desenlace: 't', id_orden: 't',
                         n_toques_seguimiento: 'i', dias_hasta_cierre: 'i', comercial: 't', correccion: 't' } },
  contactos:          { pk: 'id_contacto', c: { id_contacto: 't', id_cliente: 't', nombre: 't', cargo: 't', email: 't', telefono: 't',
                         principal: 'b', ficticio: 'b' }, fk: { id_cliente: 'dim_clientes' }, obligatorias: ['id_cliente', 'nombre'] },
};

const vacio = v => v === null || v === undefined || String(v).trim() === '';
function convertir(v, tipo) {
  if (vacio(v)) return [null, null];
  const s = String(v).trim();
  if (tipo === 't') return [s, null];
  if (tipo === 'b') {
    const m = { true: true, verdadero: true, 'sí': true, si: true, '1': true, false: false, falso: false, no: false, '0': false };
    return s.toLowerCase() in m ? [m[s.toLowerCase()], null] : [null, `"${s}" no es sí/no`];
  }
  if (tipo === 'n' || tipo === 'i') {
    let t = s.replace(/\s/g, '').replace(/€/g, '');
    if (t.includes(',') && t.includes('.')) t = t.replace(/\./g, '').replace(',', '.');   // 1.234,56
    else if (t.includes(',')) t = t.replace(',', '.');                                        // 0,15
    const x = typeof v === 'number' ? v : Number(t);
    if (!Number.isFinite(x)) return [null, `"${s}" no es un número`];
    if (tipo === 'i' && !Number.isInteger(x)) return [null, `"${s}" no es un número entero`];
    return [x, null];
  }
  if (tipo === 'd') {
    let m = s.match(/^(\d{4})-(\d{2})-(\d{2})/), a, me, d;
    if (m) [a, me, d] = [m[1], m[2], m[3]];
    else if ((m = s.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})$/))) [a, me, d] = [m[3], m[2].padStart(2, '0'), m[1].padStart(2, '0')];
    else return [null, `"${s}" no es una fecha (AAAA-MM-DD o DD/MM/AAAA)`];
    const f = new Date(`${a}-${me}-${d}T00:00:00Z`);
    if (isNaN(f) || f.toISOString().slice(0, 10) !== `${a}-${me}-${d}`) return [null, `"${s}" no es una fecha válida`];
    return [`${a}-${me}-${d}`, null];
  }
}

// Pestañas leídas con una sola llamada de SOLO LECTURA a la API de Google Sheets (values:batchGet):
// cada pestaña llega como una matriz; la fila 1 son las cabeceras.
const pestanas = {};
for (const vr of ($('Google Sheets: leer pestañas').first().json.valueRanges || [])) {
  const nombre = String(vr.range || '').split('!')[0].replace(/^'|'$/g, '');
  const [cab = [], ...resto] = vr.values || [];
  pestanas[nombre] = resto.map(fila => Object.fromEntries(cab.map((c, k) => [String(c).trim(), fila[k] === undefined ? '' : fila[k]])));
}

const salida = [], resumen = [], fatales = [], ids = {};
for (const [tabla, def] of Object.entries(T)) {
  let filas = pestanas[tabla];
  if (!filas) { fatales.push(`${tabla}: no está la pestaña en la hoja`); continue; }
  filas = filas.filter(f => Object.values(f).some(v => !vacio(v)));
  if (!filas.length) { fatales.push(`${tabla}: la pestaña está vacía`); continue; }
  const faltan = Object.keys(def.c).filter(c => !(c in filas[0]));
  if (faltan.length) { fatales.push(`${tabla}: faltan las columnas ${faltan.join(', ')}`); continue; }
  const buenas = [], rechazadas = [], vistos = new Set();
  filas.forEach((f, k) => {
    const fila = {}, errores = [];
    for (const [col, tipo] of Object.entries(def.c)) {
      const [v, err] = convertir(f[col], tipo);
      if (err) errores.push(`${col}: ${err}`); fila[col] = v;
    }
    for (const col of [def.pk, ...(def.obligatorias || [])]) if (fila[col] === null && !errores.some(e => e.startsWith(col))) errores.push(`${col}: vacío`);
    if (fila[def.pk] !== null && vistos.has(fila[def.pk])) errores.push(`${def.pk} ${fila[def.pk]} repetido`);
    if (fila.email && !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(fila.email)) errores.push(`email: "${fila.email}" no es un correo válido`);
    for (const [col, ref] of Object.entries(def.fk || {}))
      if (fila[col] !== null && ids[ref] && !ids[ref].has(fila[col])) errores.push(`${col} ${fila[col]} no existe en ${ref}`);
    if (errores.length) rechazadas.push({ fila: k + 2, id: fila[def.pk], motivo: errores.join('; ') });
    else { vistos.add(fila[def.pk]); buenas.push(fila); }
  });
  ids[tabla] = vistos;
  const tasa = rechazadas.length / filas.length;
  if (tasa > MAX_RECHAZO) fatales.push(`${tabla}: ${rechazadas.length} de ${filas.length} filas con errores (${(tasa * 100).toFixed(1)} %)`);
  resumen.push({ tabla, leidas: filas.length, validas: buenas.length, rechazadas: rechazadas.length, ejemplos_rechazo: rechazadas.slice(0, 20) });
  for (let i = 0; i < buenas.length; i += LOTE)
    salida.push({ json: { tabla, pk: def.pk, lote: i / LOTE + 1, filas: buenas.slice(i, i + LOTE) } });
}
if (fatales.length) return [{ json: { abortar: true, fatales, resumen } }];
return salida.map((s, k) => ({ json: { ...s.json, abortar: false, ...(k === 0 ? { resumen } : {}) } }));
