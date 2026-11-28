# Demostración en directo · Meridiano, retención y venta a anunciantes (versión 28-nov-2026)

Duración: 18–20 minutos. Todo es real salvo lo marcado como **[simulacro]**. Los datos son ficticios (caso de estudio) y,
en modo demo, todos los correos llegan al buzón de pruebas.

El orden sigue el recorrido de una semana comercial: **entran los datos → el modelo elige → la IA redacta → el comercial
decide → se envía → se sigue y se cierra → dirección mide y corrige → todo queda trazado**.

## Antes de la demostración

**Una vez (si no está hecho):**
1. Supabase, SQL Editor, en este orden: `resultado_riesgo.sql`, `importe_ganado.sql`, `panel_direccion.sql`,
   `baja_cierra.sql` (cada uno devuelve sus `true`).
2. Lovable: `CORRECCION_CIERRE_RIESGO.md`, `CAMBIO_CONTADOR_GANADAS.md`, `CAMBIO_PANEL_DIRECCION.md`,
   `CAMBIO_IMPORTE_GANADO.md` y `CAMBIO_BAJA_CIERRA.md`.
3. n8n, W1: fecha de corte fija `2026-11-23` y W1 publicado.

**Justo antes de grabar o presentar:**
1. `supabase/limpiar_grabacion.sql` (la comprobación final devuelve seis ceros).
2. `demo/salida/cargar_simulacro.sql` **[simulacro]**, para el bloque «Resultado de las acciones».
3. Pestañas abiertas: la hoja de Google, n8n (W0, W1, W5), GitHub Actions, el panel con un usuario **comercial**, el
   panel con **dirección** (otra ventana), el buzón demo y el SQL Editor con la consulta de trazabilidad.
4. Elegir de antemano en el panel del comercial: una **ampliación** (para enviar y ganar) y otra propuesta pendiente con
   contacto `.example` (para la baja).

## Recorrido

| # | Qué enseñas | Dónde | Min |
|---|---|---|---|
| 1 | El problema | Diapositiva | 1 |
| 2 | Los datos entran solos (W0) | Hoja + n8n | 2 |
| 3 | El modelo elige las cuentas de la semana (W1 + motor) | n8n + GitHub Actions + buzón | 3 |
| 4 | Lo que ve el comercial y lo que redacta la IA | Panel comercial | 3 |
| 5 | Aprobar y enviar (W5) | Panel + buzón | 1,5 |
| 6 | Seguimiento y cierre: ganada con importe y cuenta de riesgo | Panel comercial | 2,5 |
| 7 | Baja de un contacto | Panel comercial | 1 |
| 8 | El panel de dirección: el equipo, no los clientes | Panel dirección | 3 |
| 9 | Trazabilidad | SQL Editor | 1 |
| 10 | Viabilidad y limitaciones | Diapositiva | 1,5 |

### 1 · El problema (1 min)
Meridiano vive de sus anunciantes: un anunciante que se va es facturación perdida, y nadie lo ve hasta que no renueva.
> «Hemos automatizado el ciclo comercial: detectar, proponer, aprobar, enviar, seguir y cerrar. El modelo prioriza, la
> IA redacta y el comercial decide.»

### 2 · Los datos entran solos · W0 (2 min)
- La hoja de Google: 8 pestañas, ene-2020 al 27-nov-2026.
- n8n, **W0 → ejecutar**. Termina en `carga_ok`: valida tipos, claves y referencias y carga en Supabase.
- Opcional: una fila con un anunciante inexistente se rechaza y llega un correo al responsable de datos con el motivo.
> «Si una fila está mal, avisa y no carga basura. Y si alguien borra clientes de la hoja, no se le escribe a nadie que
> ya no está.»

### 3 · El modelo elige las cuentas · W1 + motor (3 min)
- n8n, ejecutar **W1** (fecha de corte 23-nov-2026). Lanza el motor en GitHub Actions; en el registro:
  *puntuaciones del modelo* y *propuestas*.
- Cómo se eligen: probabilidad de abandono × valor de la cuenta = valor esperado; solo si supera el coste de la acción;
  las 12 de más valor, 4 por comercial; un 20 % del riesgo medio va al **grupo de control**; ninguna se repite en 90 días.
- Claude redacta el material de cada propuesta y un validador lo revisa.
- Buzón demo: llegan los correos de la semana (y el de escalado a dirección si hay cuentas clave).
> «El modelo no sustituye al comercial: le dice a qué cuatro cuentas dedicar la semana y por qué.» Cifra medida: AUC 0,883
> frente a 0,731 de la mejor regla sencilla.

### 4 · Lo que ve el comercial (3 min) · usuario comercial
- Cabecera con contadores (pendientes, en seguimiento, cerradas, **ganadas**, errores) y las propuestas agrupadas.
- Abrir una de **riesgo**: «Por qué está aquí» (motivo, tipo de riesgo, facturación en riesgo), ficha y contacto.
- Material redactado por Claude: corregir una frase → **Guardar** → «Ver versiones» (IA y corrección con su autor).
> «La IA solo redacta: si el texto trae una cifra que no está en los datos, un descuento o habla de abandono, se descarta.»

### 5 · Aprobar y enviar · W5 (1,5 min)
- La **ampliación** elegida → **Aceptar y enviar** → «Enviando» → «En seguimiento».
- Buzón demo: llega `[DEMO → …example]` con el texto aprobado, idéntico al del panel.
> «Nada sale sin aprobación y se envía exactamente lo aprobado.»

### 6 · Seguimiento y cierre (2,5 min)
- En la ampliación: **Registrar respuesta** («Acepta el presupuesto»). **Cerrar → Ganada**: el importe ganado aparece
  relleno con el de la propuesta; cambiarlo (p. ej. un pedido algo mayor) y cerrar.
- El contador «Ganadas» sube y la propuesta muestra «Importe ganado … indicado por el comercial».
- En la propuesta de riesgo: **Aprobar llamada** → **Cerrar** con estado «Activo», motivo, diagnóstico y resultado
  «Recuperada» (también pide el importe).
> «El cierre alimenta dos cosas: el diagnóstico mide si el modelo acierta, y el importe dice cuánto vende el equipo.»

### 7 · Baja de un contacto (1 min)
- En la propuesta elegida para la baja: **Dar de baja** (lo pidió por teléfono).
- La empresa pasa a «Cerradas o rechazadas» con el distintivo «Baja de comunicaciones».
> «Una baja cierra todo lo abierto de ese contacto y el sistema no le vuelve a proponer nada: no se pierde tiempo ni se
> incumple la normativa.»

### 8 · El panel de dirección (3 min) · usuario dirección
En este orden, de arriba abajo:
1. **Resumen del equipo**: publicadas, aprobadas, días hasta decidir, ganadas, **facturación aprobada y ganada**.
2. **Qué mejorar**: avisos con reglas fijas (capacidad, medición, ritmo, seguimiento…). Leer uno en voz alta.
3. **Embudo** y **Por comercial**: dónde se queda cada uno; la ganada del paso 6 ya suma.
4. **Motor y medición** → «Resultado de las acciones (210 días)» **[simulacro]**, con el aviso ámbar: acción frente a
   grupo de control. Decir que el efecto es supuesto (30 %) y que lo medirá el piloto.
> «Dirección no ve clientes: ve cómo trabaja el equipo y qué conviene cambiar.»

### 9 · Trazabilidad (1 min)
Consulta en el SQL Editor (al final): cada paso de la demo con quién, cuándo y estado antes y después, incluidos
`cerrar`, `corregir_importe` y `cerrada_por_baja`.

### 10 · Viabilidad y limitaciones (1,5 min)
- **Medido:** el modelo sabe a quién llamar (AUC 0,883; 92 % de acierto en el 25 % de más riesgo).
- **Supuesto:** cuántas cuentas salva una acción (20 % en el cálculo, 30 % en el simulacro). Lo medirá un piloto de dos
  trimestres con el grupo de control.
- **Limitaciones:** datos ficticios, pocos anunciantes, y hoy el grupo de control solo existe en riesgo medio (si las 12
  propuestas son de riesgo alto, la semana no tiene control).
> «El modelo ya sabe dónde mirar. El piloto dirá si actuar compensa, y el sistema está preparado para medirlo.»

## Lo que no se debe decir
- Que el sistema «salva» un porcentaje de cuentas: es el simulacro con efecto supuesto.
- Que la facturación ganada del panel es un resultado: son los cierres de la demostración.

## Consulta de trazabilidad

```sql
select coalesce(p.razon_social, p.id_lead) as empresa, e.accion, e.usuario, e.estado_antes, e.estado_despues,
       to_char(e.creado_en, 'DD/MM HH24:MI') as cuando
from eventos_propuesta e join propuestas p on p.id = e.propuesta_id
where e.usuario not in ('motor', 'n8n · lunes')
order by e.creado_en desc
limit 15;
```

## Al terminar
1. `demo/salida/borrar_simulacro.sql` **[simulacro]** (el último `select` devuelve 0).
2. Para repetir: `supabase/limpiar_grabacion.sql` y volver a ejecutar W1.
3. Cuando todo esté cerrado: auditoría final con W7.
