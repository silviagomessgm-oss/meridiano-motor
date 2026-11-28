# Corrección en el panel: cierre de propuestas de riesgo (28-nov-2026)

---

Al cerrar una propuesta de riesgo, el panel no está enviando el «Resultado de la acción» y la base de datos devuelve
«Indica el resultado de la acción…». Corrígelo así, sin cambiar nada más:

1. En el formulario de cierre de las propuestas con etiqueta `riesgo`, el desplegable **«Resultado de la acción»** se
   muestra **siempre**, sea cual sea el estado confirmado elegido. Opciones y valor que se guarda en `desenlace`:
   - «Recuperada: ha firmado un pedido» → `ganada` (solo si el estado confirmado es «Activo», «Pausa: volvió después» o
     «No sé»);
   - «No recuperada» → `perdida`;
   - «Sin decisión del cliente» → `descartada`.
   Si el estado confirmado es «Perdido» o «Redujo mucho», preselecciona «No recuperada».
2. La llamada de cierre envía siempre el campo `desenlace` junto con los demás:
   `rpc('accion_panel', { p_propuesta_id, p_accion: 'cerrar', p_datos: { estado_confirmado_comercial, motivo_confirmado,
   diagnostico_correcto, desenlace, comentario_comercial } })`.
3. El botón «Cerrar» se activa solo cuando están elegidos los cuatro desplegables.
4. Si la base de datos devuelve un error, muéstralo tal cual bajo el botón.

Comprobación: cerrar una propuesta de riesgo como «Perdido» funciona y queda «Resultado de la acción: No recuperada».
