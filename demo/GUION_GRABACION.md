# Grabación de la demostración · Meridiano (versión 28-nov-2026)

La presentación se apoya en un **vídeo grabado** para no depender de que n8n, GitHub Actions, el túnel o Supabase
respondan en directo. El contenido y el orden son los de `GUION_DEMO_EN_DIRECTO.md` (10 pasos, abrir y cerrar con la
diapositiva del proceso); aquí está **cómo grabarlo**. Duración final objetivo: 14–16 minutos, tras cortar esperas.

Regla de toda la grabación: separar lo **medido** (el modelo, evaluado con datos que no vio) de lo **simulado** y de lo
**supuesto**. Todos los datos son ficticios.

## 1. Preparación (el día antes)

1. Supabase, en este orden: `resultado_riesgo.sql`, `importe_ganado.sql`, `panel_direccion.sql`, `baja_cierra.sql`.
2. Lovable: los prompts pendientes (`CORRECCION_CIERRE_RIESGO`, `CAMBIO_CONTADOR_GANADAS`, `CAMBIO_PANEL_DIRECCION`,
   `CAMBIO_IMPORTE_GANADO`, `CAMBIO_BAJA_CIERRA`).
3. W1 publicado con la fecha de corte `2026-11-23`.
4. **Ensayo completo sin grabar** (pasos 2 a 9). Al terminar, `limpiar_grabacion.sql`. Si algo falla en el ensayo, se
   arregla antes del día de la grabación.

## 2. Preparación (justo antes de grabar)

| # | Comprobación |
|---|---|
| 1 | `supabase/limpiar_grabacion.sql` → seis ceros |
| 2 | `demo/salida/cargar_simulacro.sql` **[simulacro]** → tres grupos y una fila de efecto |
| 3 | n8n abierto y el **túnel (ngrok) activo**: sin él, W5 no recibe la aprobación y el correo no sale |
| 4 | Pestañas en este orden: hoja de Google · n8n (W0, W1, W5) · GitHub Actions · panel comercial · panel dirección (otra ventana) · buzón demo · SQL Editor con la consulta de trazabilidad |
| 5 | Elegidas en el panel del comercial: una **ampliación** (enviar y ganar) y otra propuesta con contacto `.example` (baja) |
| 6 | Pantalla: 1080p, zoom del navegador 110–125 %, notificaciones del sistema desactivadas, sin otras pestañas |
| 7 | **Nada secreto a la vista**: no abrir credenciales de n8n, claves de Supabase ni la URL o el token del túnel. En n8n, enseñar el lienzo y las ejecuciones, no el nodo de configuración |

## 3. Tomas

Grabar **por tomas**, no de un tirón: si una sale mal, se repite solo esa. Las tomas de los pasos 3 a 8 cambian datos y
**deben grabarse en este orden** (cada una parte del estado que deja la anterior).

| Toma | Pasos del guion | Se puede repetir sin más | Si sale mal |
|---|---|---|---|
| A | 1 · Diapositiva del proceso | Sí | Repetir |
| B | 2 · W0 carga la hoja | Sí (la carga es idempotente) | Repetir |
| C | 3 · W1 + motor + correos | No | `limpiar_grabacion.sql`, volver a ejecutar W1 y repetir |
| D | 4 a 7 · Panel del comercial (detalle, corrección, envío, cierre como ganada, riesgo recuperada, baja) | No | `limpiar_grabacion.sql` + W1 **sin grabar** y repetir desde D |
| E | 8 · Panel de dirección | Sí (solo lee) | Repetir |
| F | 9 · Consulta de trazabilidad | Sí (solo lee) | Repetir |
| G | 10 · Vuelta a la diapositiva: viabilidad y limitaciones | Sí | Repetir |

Consejos por toma:
- **C:** el motor tarda unos minutos en GitHub Actions. Grabar el arranque, cortar la espera en el montaje (rótulo
  «4 minutos después») y grabar el final del registro y los correos en el buzón.
- **D:** es la toma larga y la única delicada. Se puede partir en D1 (detalle y corrección), D2 (aprobar y ver el correo
  en el buzón), D3 (cierres) y D4 (baja), siempre en ese orden. Tras aprobar, esperar a que pase a «En seguimiento» antes
  de cambiar al buzón.
- **E:** grabar después de D, para que la ganada y su importe ya sumen. Detenerse 3–4 segundos en cada bloque.

## 4. Narración y montaje

- Narrar en directo durante cada toma o grabar la voz después sobre el vídeo montado; lo segundo da un resultado más
  limpio. Las frases de cada paso están en `GUION_DEMO_EN_DIRECTO.md`.
- Rótulos en el montaje: **[simulacro]** sobre el bloque «Resultado de las acciones»; «Datos ficticios» al principio;
  «Correo desviado al buzón de pruebas (modo demo)» en el buzón.
- Cortar esperas y cargas; no acelerar las pantallas en las que se lee.

## 5. Respaldo

1. Exportar en MP4 (1080p) y guardar **tres copias**: el portátil de la presentación, un USB y la nube.
2. Llevar el vídeo descargado: no depender de la conexión en la sala.
3. Hacer capturas de las pantallas clave (panel del comercial, correo en el buzón, panel de dirección) e incluirlas como
   diapositivas de reserva por si fallara el reproductor.
4. Después de grabar: `demo/salida/borrar_simulacro.sql` y, cuando todo esté cerrado, la auditoría final con W7.

## 6. Cómo decidir la viabilidad (paso 10)

1. **¿Sabe el sistema a quién llamar? Sí, medido.** Ordena el riesgo mucho mejor que las reglas sencillas (AUC 0,883
   frente a 0,731) y acierta en el 92 % del 25 % de más riesgo.
2. **¿Compensa actuar? Depende de un dato que aún no existe: cuántas cuentas en riesgo salva una acción.** Hoy el
   sistema decide con un supuesto: actúa si probabilidad de abandono × valor de la cuenta × 20 % de recuperación supera
   120 € de coste por acción (`propuestas/config/parametros.json`). Ese 20 % es un supuesto, no una medida.
3. **Cómo se mide:** con el grupo de control y la ventana de 210 días. Propuesta para la decisión:
   - piloto de 2 trimestres con el sistema tal como está;
   - medir el efecto en la banda media (acción frente a control) en el bloque «Resultado de las acciones»;
   - con la tasa de recuperación real, recalcular si el valor esperado compensa el coste comercial. Si no compensa,
     se ajustan el coste, la capacidad o las cuentas elegibles; si compensa, se amplía.

Mensaje final: «El modelo ya sabe dónde mirar. El piloto dirá si actuar compensa, y el sistema está preparado para
medirlo sin trabajo adicional».

## 7. Lo que NO se debe decir en la grabación

- Que el sistema «salva» un porcentaje de cuentas: las cifras de cuentas salvadas son del simulacro con efecto supuesto.
- Que los 12,8 puntos sin supuesto demuestran algo: con acciones simuladas no hay efecto que medir.
- Cifras de facturación recuperada o ganada como resultado: son los cierres de la propia demostración.
