# Cambio en el panel: resultado de la acción al cerrar una propuesta de riesgo (28-nov-2026)

Pegar en Lovable **después** de ejecutar `supabase/resultado_riesgo.sql` en el SQL Editor de Supabase. No crea tablas ni
migraciones: el panel sigue escribiendo solo con `rpc('accion_panel', …)`.

---

Al cerrar una propuesta de riesgo, el comercial tiene que poder decir si la acción ha recuperado la cuenta, y dirección
tiene que poder medirlo. Haz estos cambios en el panel, manteniendo el estilo actual:

1. **Formulario de cierre de una propuesta con etiqueta `riesgo`:** además de los tres desplegables que ya tiene
   (estado confirmado, motivo y diagnóstico), añade un cuarto desplegable obligatorio, **«Resultado de la acción»**, que
   se guarda en `desenlace`:
   - `ganada` → «Recuperada: ha firmado un pedido»
   - `perdida` → «No recuperada»
   - `descartada` → «Sin decisión del cliente»

   Envíalo en la misma llamada de siempre: `accion_panel(p_propuesta_id, 'cerrar', { estado_confirmado_comercial,
   motivo_confirmado, diagnostico_correcto, desenlace, comentario_comercial })`. El botón «Cerrar» sigue desactivado
   hasta que estén los cuatro desplegables. Si el estado confirmado es «Perdido» o «Redujo mucho», no ofrezcas
   «Recuperada» (la base de datos lo rechaza con un mensaje; muéstralo si llega).

2. **Resumen de una propuesta de riesgo cerrada:** muestra también «Resultado de la acción: …» con el texto de arriba. En
   las cerradas antes de este cambio (`desenlace` vacío) muestra «Resultado de la acción: no registrado».

3. **Dirección · nueva tarjeta y tabla «Recuperación de cuentas en riesgo»**, debajo de «Resultado de las acciones (210
   días)», de la vista `recuperacion_riesgo(fecha_corte, comercial_asignado, comercial_nombre, cerradas, recuperadas,
   no_recuperadas, sin_decision, sin_resultado_anterior_al_cambio, pct_recuperadas, con_pedido_60_dias,
   recuperadas_sin_pedido_aun, importe_pedidos_60_dias, facturacion_en_riesgo)`, filtrada por el selector de semana o
   para todas las semanas:
   - tarjetas: «Cuentas recuperadas» (`recuperadas` de `cerradas`, con `pct_recuperadas` %), «Con pedido en 60 días»
     (`con_pedido_60_dias`) e «Importe de esos pedidos» (`importe_pedidos_60_dias`, en euros);
   - tabla por comercial con todas las columnas, y en ámbar las filas con `recuperadas_sin_pedido_aun` > 0 y el texto
     «Declaradas como recuperadas sin pedido todavía en los datos»;
   - nota fija bajo el bloque: «Lo que declara el comercial al cerrar. La prueba de que la acción funciona es el resultado a
     210 días frente al grupo de control (bloque anterior)».

4. **Tabla por comercial de dirección:** cambia «facturación … recuperada (cerradas como `Activo` o `Pausa: volvió
   después`)» por la facturación en riesgo de las cerradas como «Recuperada» (`desenlace = 'ganada'`), y mantén aparte la
   de `Activo` y `Pausa: volvió después` para las cerradas antes de este cambio.

5. **Listas cerradas:** para las propuestas de riesgo, `desenlace` se muestra con los textos del punto 1 (para el resto de
   etiquetas no cambia: «Ganada», «Perdida», «Descartada»).

Comprobación: cerrar una propuesta de riesgo sin «Resultado de la acción» no es posible; cerrar como «Perdido» +
«Recuperada» muestra el error de la base de datos; tras cerrar una como «Activo» + «Recuperada», la tarjeta de
dirección suma una cuenta recuperada.
