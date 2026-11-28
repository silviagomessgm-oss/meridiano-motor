# Cambio en el panel: una baja de comunicaciones manda la propuesta a «Cerradas o rechazadas» (28-nov-2026)

Pegar en Lovable **después** de ejecutar `supabase/baja_cierra.sql` en el SQL Editor de Supabase (debe devolver
`true, true, true`). No crea tablas ni migraciones. La base de datos ya cierra sola las propuestas del contacto dado de baja;
el panel solo tiene que reflejarlo:

---

1. Después de llamar a `rpc('baja_panel', …)` con éxito, vuelve a cargar `plan_vigente` y cierra el detalle de la
   propuesta: la empresa tiene que desaparecer de «Pendientes de aprobar» / «En seguimiento» y aparecer en «Cerradas o
   rechazadas esta semana». Muestra el aviso «Baja registrada: sus propuestas abiertas se han cerrado».

2. En «Cerradas o rechazadas», las tarjetas con `motivo_rechazo = 'El contacto se ha dado de baja de las comunicaciones
   comerciales'` o `motivo_desenlace = 'Baja de comunicaciones comerciales'` llevan un distintivo gris «Baja de
   comunicaciones» y no muestran botones de acción (ni «Reabrir»).

Comprobación: dar de baja al contacto de una propuesta pendiente la lleva al final de la lista con el distintivo; una en
seguimiento pasa a cerrada con resultado «Sin decisión del cliente».
