# Cambio en el panel: nuevo modelo de abandono (27-nov-2026)

Pegar en Lovable **después** de ejecutar `supabase/modelo_churn.sql` en el SQL Editor de Supabase. No cambia nada de lo
que ya funciona: solo añade información.

---

Desde esta semana las propuestas de riesgo las genera un modelo de abandono nuevo, y el sistema registra qué cuentas
salva el equipo comercial. Haz estos cambios en el panel, manteniendo el estilo actual:

1. **Datos nuevos (solo lectura):**
   - `plan_vigente` y `propuestas` tienen la columna `modelo` (texto). Vacía en las propuestas anteriores al cambio.
   - Solo dirección: tabla `resultado_acciones(fecha_corte, id_cliente, grupo, banda_riesgo, resultado, abandono,
     salvada, estado_confirmado_comercial, fecha_resultado)`, vista `resumen_resultado_acciones(grupo, cuentas,
     abandonos, pct_abandono, salvadas, desde, hasta)` y vista `efecto_accion(banda, cuentas_accion,
     pct_abandono_accion, cuentas_control, pct_abandono_control, diferencia_puntos)` (una sola fila).

2. **Tarjetas y detalle de propuesta (comerciales y dirección):** en las propuestas con etiqueta `riesgo` y `modelo`
   vacío, añade un distintivo gris «Modelo anterior». En el detalle, muestra «Modelo: {modelo}» o «Modelo anterior».
   No muestres `prob_abandono` como porcentaje (como hasta ahora).

3. **Dirección · validación de la etiqueta:** sustituye el aviso actual de `estado_etiqueta`. El modelo usa siempre E2;
   la validación es solo un indicador. Si `etiqueta_vigente` es `A`, muestra: «Las confirmaciones de los comerciales no
   respaldan la etiqueta E2 (casos: {casos}, acuerdo: {acuerdo}). El modelo sigue usando E2: revisad la definición con
   el equipo». Si es `E2`, no muestres ningún aviso.

4. **Dirección · nuevo bloque «Resultado de las acciones (210 días)»**, debajo de los indicadores:
   - Tres tarjetas a partir de `resumen_resultado_acciones`: «Con acción del comercial» (`accion`), «Propuestas sin
     acción» (`propuesta_sin_accion`) y «Grupo de control» (`control`). Cada una: cuentas y % de abandono; la primera,
     además, cuentas salvadas.
   - **Efecto de la acción**, de `efecto_accion` (no de las tres tarjetas): el grupo de control solo se sortea entre
     cuentas de riesgo medio, así que el efecto se mide comparando cuentas de riesgo medio con acción y en control.
     Si `diferencia_puntos` no es nulo: «Efecto de la acción (riesgo medio): {diferencia_puntos} puntos menos de
     abandono que el grupo de control ({cuentas_accion} cuentas con acción y {cuentas_control} en control)» (si es
     negativo: «puntos más»). Si es nulo: «Aún no hay cuentas de riesgo medio suficientes para medir el efecto».
     Debajo, en pequeño: «Con pocas cuentas la diferencia puede deberse al azar».
   - Bajo las tres tarjetas, en pequeño: «Los grupos tienen riesgos distintos: no comparar sus porcentajes entre sí».
   - Si no hay filas: «Todavía no ha terminado ninguna ventana de 210 días».
   - Tabla de `resultado_acciones` con la empresa (`dim_clientes.razon_social`), semana (`fecha_corte`), grupo,
     banda de riesgo, resultado, «Salvada» (sí/no) y lo que confirmó el comercial, con filtro por grupo y orden por semana descendente.
   - Textos: grupo `accion` → «Con acción del comercial», `propuesta_sin_accion` → «Propuesta sin acción», `control` →
     «Grupo de control»; resultado `perdida_total` → «Pérdida total», `contraccion` → «Contracción», `activo` → «Siguió
     comprando», `fuera_de_poblacion_volvio` → «Volvió a comprar», `fuera_de_poblacion_sin_compra` → «Sin compras»,
     `salvada_escenario` → «Salvada (escenario supuesto)».
   - **Simulacro:** si alguna fila de `resultado_acciones` tiene `resultado = 'salvada_escenario'`, muestra arriba del
     bloque un aviso ámbar fijo: «Simulacro para la presentación: datos ficticios con un escenario supuesto de efecto de
     la acción. No es un resultado». Esas filas se cargan con `demo/salida/cargar_simulacro.sql` y se borran con
     `demo/salida/borrar_simulacro.sql`.

Comprobación: con un usuario comercial, el menú de dirección y `resultado_acciones` no aparecen; con dirección, el
bloque nuevo aparece (vacío hasta que termine la primera ventana de 210 días).
