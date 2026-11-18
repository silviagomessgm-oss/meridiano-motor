# Meridiano · Paquete de auditoría del diseño (paso 05 FORGEN)

Versión: diseno-v1 · 18-nov-2026 · Generado con Claude Opus (Claude Code). Para revisión por un modelo distinto y más capaz.
Caso ficticio de un trabajo fin de programa: datos, contactos y cifras son simulados.

## 1. Contexto y problema

Meridiano es un medio digital para el público senior (mayores de 60 y sus familias). Los lectores no pagan: el negocio son
267 anunciantes de 11 sectores, muy concentrados (el 20 % genera el 65 % de la facturación). Hay 3 comerciales y dirección.

Proceso actual (AS-IS) y sus tres fugas:
1. **Detectar tarde:** el comercial revisa su cartera cuando puede; dirección se entera de una baja cuando el anunciante no renueva.
2. **No seguir:** el 45 % de las propuestas no acaba ni ganada ni perdida y 1 de cada 3 no recibe ningún seguimiento.
   En un año, 2,18 M€ propuestos murieron en silencio frente a 0,42 M€ ganados.
3. **No registrar:** se redacta en Word o en el correo y se envía desde el buzón personal; correcciones y cierres no quedan.

Objetivos: detectar cada semana las cuentas con más riesgo y valor; que la IA prepare cada propuesta y el comercial solo
decida; que ninguna propuesta quede sin seguimiento ni cierre registrado.
KPI: tasa de ganadas a 90 días (23,7 % → +5 puntos, medida con grupo de control); propuestas sin seguimiento (37,5 % → 0 %);
cierres con motivo registrado (100 %).

## 2. Proceso objetivo (TO-BE)

Carriles: Sistema · Comercial · Dirección · Anunciante. Fases: detectar → preparar → decidir → enviar → seguir → cerrar y medir.
Única puerta humana: el comercial aprueba, corrige o rechaza; nada llega al anunciante sin aprobación.

Cadencia semanal:
- Lunes 7:00 · propuestas de leads nuevos y ampliación (N3 → N4).
- Lunes 8:15 · balance a cada comercial y resumen de todas las acciones a dirección (N9).
- Lunes 21:00 · carga de datos (N1).
- Martes 7:00 · cuentas en riesgo, 4 por comercial (N2 → N4).
- Cada día · envío al aceptar (N6), avisos de toque (N7), cierre y alertas (N8).

Stack: n8n Cloud (flujos W0, W1, W2, W4, W5, W6), motor Python en GitHub Actions, Claude (API), Supabase (Postgres con
permisos por fila y trazabilidad), panel y formulario web en Lovable, Google Sheets como fuente, Gmail como canal.

## 3. Reglas transversales

- **Trazabilidad:** el panel no escribe en tablas. Toda acción pasa por la función `accion_panel()`, que toma el usuario de la
  sesión, comprueba que la cuenta es de su cartera y, en una sola transacción, cambia la propuesta, registra el evento
  (quién, cuándo, estado antes y después) y guarda la versión del texto. n8n escribe con `registrar_accion()` (solo servicio).
- **Permisos:** cada comercial ve y actúa solo sobre su cartera; dirección ve todo. Claves de servicio solo en n8n y GitHub.
- **Una etiqueta por empresa:** una empresa no recibe a la vez propuesta de riesgo, ampliación o seguimiento. Enfriamiento
  común de 90 días. El ciclo del martes excluye a las empresas con propuesta del lunes.
- **Consentimiento:** un lead del formulario web exige aceptar la casilla (se guarda el texto y la fecha). A un lead sin
  consentimiento (puerta fría) la base de datos no le deja enviar correo comercial: solo llamada.
- **Modo demo:** todos los correos van a un buzón de pruebas con el asunto `[DEMO → destinatario]`; los contactos son
  ficticios (dominio .example) y un contacto ficticio no puede recibir correo fuera del modo demo.
- **Grupos de control:** riesgo, grupo de control estable por trimestre. Seguimiento (ampliación y lead), sorteo 50 % por
  hash reproducible; el control no recibe avisos de toque.

## 4. Nodos

### N1 · Cargar y validar los datos de la semana (W0, automático)
- Entrada: hoja de Google Sheets con 8 pestañas (clientes, comerciales, productos, campañas, facturación, interacciones,
  oportunidades, contactos). Salida: tablas en Supabase y registro en `ejecuciones`.
- Dentro: lectura en una sola llamada; validación de columnas, tipos, claves primarias repetidas, claves ajenas y formato de correo;
  carga por identificador en lotes de 1.000; aviso al responsable de datos con las filas rechazadas.
- Fuera: corregir datos; cargar parcialmente una tabla con errores graves.
- Criterios: si falta una pestaña o una columna, o una tabla supera el 5 % de filas rechazadas, no se carga nada; cada
  ejecución deja su resultado en `ejecuciones`.

### N2 · Calcular el riesgo y elegir 12 cuentas (W1 + motor, modelo predictivo)
- Entrada: tablas de Supabase con fecha de corte el lunes anterior. Salida: 12 propuestas de riesgo, asignaciones y KPIs.
- Modelo: regresión logística regularizada (L2) entrenada cada semana con los cortes cuyo resultado ya se conoce. Variables:
  recencia, frecuencia y antigüedad más seis señales (tendencia de inversión, CTR, cambio de interlocutor, tiempo sin contacto,
  reclamación, incidencia de factura). Etiqueta E2: pérdida total (se salta su temporada o un año sin comprar) o contracción
  (factura menos del 50 % que el año anterior).
- Priorización: probabilidad × valor de la cuenta × recuperación esperada (20 %, supuesto) − coste por acción (120 €, supuesto).
  4 cuentas por comercial y semana; 90 días sin repetir; grupo de control por sorteo.
- Marcas: «cuenta clave» = 5 % de más valor de toda la cartera activa; «escalar a dirección» = cuenta clave con motivo de
  cambio de interlocutor, reclamación o cobro.
- Fuera: contactar al cliente; decidir la acción final; usar datos posteriores al corte.
- Criterios: 12 propuestas sin repetir en 90 días; cada una con motivo, tipo de riesgo y facturación en riesgo; si el acuerdo
  entre E2 y el estado confirmado por el comercial baja del 70 % con al menos 30 casos, vuelve a la regla simple A
  (210 días sin campaña).
- Evaluación previa: L2 superó a ordenar solo por valor en torno a un 5 %, de forma estable en 5 cortes; un modelo más
  complejo (L3) no mejoró.

### N3 · Elegir leads y ampliaciones de la semana (W4 + función SQL `preparar_lunes`, reglas)
- Entrada: leads, clientes, campañas y productos. Salida: propuestas de lead nuevo y de ampliación con texto de plantilla.
- Lead nuevo: todo lead en estado «nuevo» sin propuesta; producto de entrada más contratado en su sector; correo si tiene
  consentimiento y correo, si no, llamada.
- Ampliación (siguiente mejor oferta): cliente activo (campaña en 180 días) y estable (facturación de 6 meses ≥ 70 % de los 6
  anteriores), sin propuesta abierta ni en 90 días; producto más contratado por su sector, que el cliente no ha comprado en
  12 meses, disponible el mes que viene y con capacidad libre; 2 por comercial, los de mayor facturación.
- Criterios: idempotente (volver a ejecutarlo no duplica); el producto propuesto no se compró en el último año.

### N4 · Redactar la propuesta y validarla (W1 y W4, IA generativa)
- Entrada: contexto de la cuenta (ficha con cifras, motivo, producto, contacto, canal). Salida: texto validado o plantilla.
- Modelo: Claude por API. Sistema: «usa solo cifras del contexto, tal cual; nunca menciones que el cliente está en riesgo;
  no incluyas ninguna condición económica ni porcentaje; tono profesional y cercano, de usted; máximo 200 palabras».
- Validador (código, no IA): descarta el texto si aparece una cifra que no está en el contexto, un porcentaje, €, «euros»,
  «descuento», «rebaja» o «gratis», o si supera 200 palabras. Si falla o la IA no responde, queda la plantilla y se anota el
  motivo; volver a ejecutar reintenta solo esas.
- Fuera: enviar nada; decidir a quién se propone.

### N5 · Aprobar, corregir o rechazar (panel de Lovable, persona)
- Entrada: propuesta pendiente. Salida: propuesta aprobada con el texto congelado, rechazada con motivo, o nueva versión.
- Reglas de la base de datos: aprobar un correo exige contacto con correo; a un lead, consentimiento; al aprobar se guarda
  el texto exacto y su versión; una llamada aprobada pasa directamente a seguimiento. Rechazar exige motivo; una rechazada
  se puede reabrir.
- Fuera: enviar el correo (lo hace N6); escribir en tablas.

### N6 · Enviar el texto aprobado (W5, automático)
- Disparo: webhook de base de datos al registrarse el evento «aprobar» (cabecera con token) o reintento manual.
- Entrada: propuestas en estado «enviando». Salida: correo enviado por Gmail y registro del resultado.
- Criterios: se envía exactamente el texto aprobado; correcto → «En seguimiento» con identificador del mensaje; fallo →
  «Error de envío», visible en el panel y reintentable.

### N7 · Avisar del toque (vista SQL `seguimientos_debidos`, automático)
- Propuestas en seguimiento sin respuesta registrada: primer toque a los 4 días, segundo a los 12, último o cierre a los 25.
  Aviso en el panel y en el correo del lunes. El grupo de control del piloto no recibe avisos.
- Fuera: enviar recordatorios al cliente.

### N8 · Registrar respuesta y cerrar con motivo (panel + W2)
- El comercial registra respuestas y cierra. Riesgo: estado confirmado, motivo y si el diagnóstico fue correcto (los tres
  obligatorios). Otras etiquetas: desenlace (ganada, perdida, descartada) y motivo.
- Alerta a dirección (W2, por webhook del evento «cerrar») si: cuenta clave perdida; cuenta para escalar no recuperada;
  pérdida por reclamación.

### N9 · Balance, previsión y resumen a dirección (W6, IA + automático)
- Función SQL `balance_lunes`: por comercial, acciones de la semana anterior, pendientes, seguimientos que piden toque,
  cuentas en riesgo abiertas y previsión (importe propuesto × tasa histórica de éxito por origen: ampliación 53,6 %,
  lead nuevo 11,0 %).
- Correo a cada comercial con un comentario de Claude de 2–3 frases; validador: solo cifras presentes en los hechos y máximo
  70 palabras; si falla, el correo sale sin comentario.
- Correo a dirección con el resumen de todas las acciones por comercial y en total, sin IA.
- Evaluación previa: un modelo de probabilidad de ganar no se adoptó (ganó en un periodo y perdió en otro).

## 5. Riesgos que el equipo ya identificó

- La tasa de recuperación (20 %) y el coste por acción son supuestos hasta que lo mida el grupo de control.
- El modelo mejora poco (≈5 %) sobre ordenar por valor y depende de la señal de contacto.
- Los mismos comerciales trabajan los dos grupos del piloto (posible contaminación).
- El tratamiento del consentimiento de puerta fría debe validarlo una asesoría legal (LSSI y RGPD).
