# Cambio en el panel: contador «Ganadas» en la cabecera (28-nov-2026)

Pegar en Lovable **después** de `CAMBIO_RESULTADO_RIESGO.md`. No hace falta tocar Supabase: solo lee `plan_vigente`.

---

Añade un quinto contador en la cabecera del panel, junto a «Pendientes de aprobar», «En seguimiento», «Cerradas esta
semana» y «Errores de envío», manteniendo exactamente su estilo (cifra en Fraunces 500, rótulo en IBM Plex Mono mayúsculas
y filete vertical de 1 px entre contadores):

- **Rótulo:** «GANADAS».
- **Cifra:** propuestas de `plan_vigente` del usuario (todas si es dirección) con `estado = 'cerrada'` y
  `desenlace = 'ganada'`, cerradas en la misma semana que cuenta «Cerradas esta semana». Incluye las tres etiquetas: en
  ampliación y lead nuevo es «Ganada» y en riesgo es «Recuperada: ha firmado un pedido».
- **Debajo de la cifra, en pequeño:** «de N cerradas», con N = la cifra de «Cerradas esta semana».
- **Al hacer clic:** filtra la lista de propuestas para mostrar solo las ganadas (igual que hacen los demás contadores si
  ya filtran; si no filtran, no añadas el clic).
- Con 0 ganadas, el contador se muestra igual con la cifra 0.
- En móvil, los cinco contadores pasan a dos filas como el resto de rejillas.

No cambies los otros cuatro contadores ni el orden de la lista.

Comprobación: cerrar una propuesta de ampliación como «Ganada» o una de riesgo como «Recuperada» suma 1 a «Ganadas» y a
«Cerradas esta semana»; cerrar una como «Perdida» o «No recuperada» solo suma a «Cerradas esta semana».
