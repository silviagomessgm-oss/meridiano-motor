# Cambio en el panel: importe ganado al cerrar y facturación aprobada y ganada en Dirección (28-nov-2026)

Pegar en Lovable **después** de ejecutar en el SQL Editor de Supabase, por este orden, `supabase/importe_ganado.sql` y
`supabase/panel_direccion.sql` (los dos deben devolver `true, true, true`). No crea tablas ni migraciones: el panel sigue
escribiendo solo con `rpc('accion_panel', …)`.

---

Cuando un comercial gana una propuesta, el panel tiene que guardar cuánto ha vendido, y dirección tiene que ver la
facturación aprobada y la ganada. Haz estos cambios manteniendo el estilo actual:

1. **Formulario de cierre (todas las etiquetas).** Cuando el resultado elegido sea «Ganada» (o «Recuperada: ha firmado un
   pedido» en las de riesgo), muestra un campo numérico obligatorio **«Importe ganado (€)»**:
   - rellénalo al abrir con `rpc('importe_estimado_propuesta', { p_propuesta_id })` y debajo, en gris: «Importe estimado
     de la propuesta. Cámbialo si el pedido ha sido distinto»;
   - si la función devuelve `null`, el campo queda vacío y hay que escribirlo;
   - envíalo en la llamada de siempre como `importe_ganado_eur`: `accion_panel(p_propuesta_id, 'cerrar', { …lo de
     siempre…, desenlace, importe_ganado_eur })`. Acepta coma o punto decimal y no admite negativos;
   - si el resultado no es «Ganada»/«Recuperada», oculta el campo y **no envíes** `importe_ganado_eur`.
   En las de riesgo envía también `desenlace` (el desplegable «Resultado de la acción»), que ahora sí se guarda.

2. **Resumen de una propuesta ganada:** muestra «Importe ganado: X €» (`importe_ganado_eur`) con la nota «estimado de la
   propuesta» si `importe_ganado_origen = 'propuesta'` o «indicado por el comercial» si es `'comercial'`. Al lado, un
   botón **«Cambiar importe»** (para el comercial de la propuesta y para dirección) que abre un campo numérico y llama a
   `accion_panel(p_propuesta_id, 'corregir_importe', { importe_ganado_eur })`. Muestra los errores de la base de datos tal
   cual llegan.

3. **Dirección · Resumen del equipo:** sustituye la tarjeta «Facturación recuperada» por dos tarjetas:
   - «Facturación aprobada» (`importe_aprobado` en euros, suma del periodo), con debajo «importe estimado de las propuestas
     aprobadas»;
   - «Facturación ganada» (`importe_ganado` en euros), con debajo «N % de la aprobada» y, en pequeño, «de las cuentas en
     riesgo: X € recuperados de Y € en riesgo» (`facturacion_recuperada` y `facturacion_en_riesgo` de la etiqueta `riesgo`).

4. **Dirección · Por comercial:** en las columnas del periodo, cambia «Facturación recuperada» por **«Facturación
   aprobada»** (`importe_aprobado`) y **«Facturación ganada»** (`importe_ganado`), en euros sin decimales, y añade
   «Importes cambiados» (`ganadas_importe_cambiado`, número de ganadas cuyo importe escribió el comercial). La fila
   «Equipo» suma las tres.

5. **Cabecera del panel:** bajo el contador «Ganadas», muestra en pequeño la suma de `importe_ganado_eur` de las
   propuestas ganadas que ve el usuario («X € ganados»).

Comprobación: cerrar una propuesta de ampliación como «Ganada» sin tocar el importe guarda el estimado y suma en
«Facturación ganada»; cerrarla con otro importe lo guarda como «indicado por el comercial» y suma 1 en «Importes
cambiados»; cerrar una de riesgo como «Activo» + «Recuperada» se guarda (antes daba error); «Cambiar importe» en una
perdida muestra «Solo se cambia el importe de una propuesta ganada».
