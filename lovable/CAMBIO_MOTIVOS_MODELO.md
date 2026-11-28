# Cambio en el panel: motivos del modelo de abandono (28-nov-2026)

Pegar en Lovable (después de `CAMBIO_MODELO_ABANDONO.md` si aún no se había aplicado). No hace falta tocar Supabase.

---

El motivo de las propuestas de riesgo ahora lo decide el modelo de abandono, y la validación de la etiqueta ya no cambia
de etiqueta. Haz estos dos cambios en el panel, manteniendo el estilo actual:

1. **Motivo en tarjetas y detalle (comerciales y dirección):** muestra `motivo_principal` y `motivo_secundario` con
   este texto (si llega un valor que no está en la lista, sustituye `_` por espacios y pon la primera letra en mayúscula):
   `relacion_interlocutor` → «Cambio o relación con el interlocutor» · `servicio_reclamacion` → «Reclamación sin
   resolver» · `cobro_financiero` → «Cobro o factura vencida» · `perdida_contacto` → «Sin contacto comercial reciente» ·
   `presupuesto_inversion` → «Baja la inversión» · `rendimiento_campanas` → «Bajo rendimiento de las campañas» ·
   `temporada` → «Su temporada, sin reservar» · `sin_pedido_firmado` → «Sin pedidos firmados pendientes» ·
   `patron_compra` → «Compra menos y en menos productos» · `propuestas_perdidas` → «Propuestas perdidas recientes» ·
   `inactividad` → «Inactividad» · `desconocido` → «Sin motivo claro».
   El desplegable «Motivo confirmado» del formulario de cierre NO cambia (sigue con sus 8 opciones).

2. **Dirección · validación de la etiqueta:** `etiqueta_vigente` es ahora siempre `E2`, así que el aviso ya no puede
   depender de que valga `A`. Muestra siempre el texto de `estado` con `casos` y `acuerdo` (en %). Si `estado` empieza
   por «E2 NO VALIDADA» (o, en semanas antiguas, `etiqueta_vigente` es `A`), muestra en ámbar: «Las confirmaciones de
   los comerciales no respaldan la etiqueta E2 (casos: {casos}, acuerdo: {acuerdo}). El modelo sigue usando E2:
   revisad la definición con el equipo».
