# Meridiano · Paquete de auditoría del diseño (paso 05 FORGEN)

Versión: diseno-v4 · 28-nov-2026 · Generado con Claude Opus (Claude Code). Para revisión por un modelo distinto y más capaz.
Cambios: diseno-v2 corrige la primera auditoría (H1–H12, sección 6); diseno-v3 corrige la segunda (sección 7); diseno-v4
sustituye el modelo de riesgo de N2 por el construido por la alumna (`modelo_churn/`) y amplía los datos (sección 8).
Caso ficticio de un trabajo fin de programa: datos, contactos y cifras son simulados.

## 1. Contexto y problema

Meridiano es un medio digital para el público senior (mayores de 60 y sus familias). Los lectores no pagan: el negocio son
346 anunciantes de 11 sectores con historia desde enero de 2020 (unos 146 activos al año), muy concentrados (el 20 % genera
el 65 % de la facturación). Hay 3 comerciales y dirección. Datos: 36 meses originales (oct-2023 → sep-2026) ampliados con
datos sintéticos documentados hasta ene-2020 y hasta el 27-nov-2026 (`tablas_ampliadas/README.md`).

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
- Lunes 8:15 · balance a cada comercial y resumen de todas las acciones a dirección, con escalado de seguimientos sin atender (N9).
- Lunes 21:00 · carga de datos (N1).
- Martes 7:00 · cuentas en riesgo, 4 por comercial (N2 → N4).
- Cada día · envío al aceptar (N6), avisos de toque (N7), cierre y alertas (N8).
- Siempre · baja de comunicaciones desde el enlace de cada correo (W8) o desde el panel.

Stack: n8n (flujos W0, W1, W2, W4, W5, W6, W8; en la demo, autoalojado en Docker), motor Python en GitHub Actions con el modelo de abandono `modelo_churn` (scikit-learn), Claude (API), Supabase (Postgres con
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
- **Comunicaciones comerciales (H2):** cada correo lleva la base del envío, un canal para ejercer derechos y un enlace de
  baja (token aleatorio por contacto; baja en dos pasos con confirmación, para que los filtros de seguridad del correo no den
  de baja a nadie). Lista de exclusión `exclusiones` (solo correo y motivo; sin modificar ni borrar desde el panel ni n8n).
  La base de datos impide aprobar o marcar como enviado un correo a un contacto excluido (trigger), y W5 no envía ningún
  correo sin enlace de baja. Plazos de conservación (supuestos de diseño): leads no convertidos, 24 meses desde su última
  actividad; contactos de excliente, 36 meses; lista de exclusión, mientras exista el contacto. Vista `conservacion_vencida`;
  el borrado lo decide dirección.
- **Base de cada envío (2.ª auditoría):** riesgo y ampliación se dirigen a clientes y exclientes con relación contractual
  previa, sobre productos de la misma oferta publicitaria que contrataron, con oposición en cada correo (art. 21.2 LSSI). Los
  exclientes solo entran si facturaron en los últimos 18 meses (horizonte de actividad del motor). Lead del formulario:
  consentimiento expreso con texto y fecha. Lead de puerta fría: se registra el origen del dato y, sin consentimiento, solo
  llamada; la información del art. 14 RGPD se da en la primera llamada y se anota en el panel. La etiqueta de la propuesta
  determina su base, y la base se muestra en el pie de cada correo.
- **Encargados de tratamiento:** Anthropic (API de Claude; solo datos de empresa), Supabase (base de datos; región UE),
  Google (Sheets y Gmail), Lovable (panel; sin datos propios: lee Supabase con la sesión de cada usuario), GitHub (motor; las
  tablas se procesan en la ejecución y no se guardan). Requieren contrato de encargado (art. 28 RGPD). La hoja fuente tiene
  permisos nominales (responsable de datos y dirección) y Google registra quién la edita. Los anunciantes son empresas; si
  alguno es autónomo, su razón social es un dato personal y se trata con la misma base que el resto de contactos.
- **Remitente y respuestas:** en producción, cada correo sale de un remitente del dominio de Meridiano con *reply-to* del
  comercial asignado, así que la respuesta llega a su buzón y la registra en el panel (`registrar_respuesta`). El
  identificador del mensaje de Gmail queda en la propuesta para localizar el hilo. En la demo todo va a un buzón de pruebas.
- **Datos que recibe la IA (H10):** solo datos de empresa: razón social, sector, acción, motivo, producto y cifras de
  campaña. Nunca el nombre, el correo ni el teléfono del contacto. El saludo es genérico («responsable de marketing de…»);
  el comercial puede personalizarlo al revisar el texto en el panel.
- **Modo demo:** todos los correos van a un buzón de pruebas con el asunto `[DEMO → destinatario]`; los contactos son
  ficticios (dominio .example) y un contacto ficticio no puede recibir correo fuera del modo demo.
- **Grupos de control:** riesgo, grupo de control estable por trimestre, solo en banda media y **nunca con cuentas clave**
  (las cuentas clave y la banda alta siempre reciben acción); 20 % de la banda media, decidido por dirección y revisable cada
  trimestre. Seguimiento (ampliación y lead), sorteo 50 % por
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

### N2 · Calcular el riesgo y elegir hasta 12 cuentas (W1 + motor, modelo predictivo)
- Puerta de datos (H7): antes de lanzar el motor, W1 consulta `ultima_carga()`. Si la última carga de N1 no terminó en
  `carga_ok` o `carga_con_avisos`, tiene más de 8 días o Supabase no responde, no se genera nada: aviso a dirección y al
  responsable de datos, registro `detenido_por_datos` y el panel conserva el plan anterior.
- Entrada: tablas de Supabase con fecha de corte el lunes anterior. Salida: hasta 12 propuestas de riesgo, asignaciones y KPIs.
- Modelo (`modelo_churn/puntuar.py`, construido por la alumna con Claude Code): regresión logística con regularización L2
  (scikit-learn), elegida entre cuatro opciones. Se entrena cada martes con todos los cortes trimestrales cuyo resultado ya
  se conoce (población: anunciantes con campaña en los 12 meses anteriores al corte; sin anunciantes con menos de un año desde
  el alta) y puntúa a todos los activos: `scores_modelo.csv` con `id_cliente` y `prob_abandono`. 14 variables calculadas solo
  con datos hasta la fecha: días sin campaña, frecuencia y valor en 12 meses, compra en el mismo periodo del año anterior,
  tendencia, antigüedad, familias de producto, CTR relativo, cambio de interlocutor, días sin contacto comercial, retraso
  medio de cobro, pedidos firmados pendientes, propuestas abiertas y propuestas perdidas en 12 meses. Etiqueta E2 (siempre):
  pérdida total (compró en W' = (T − 1 año, T − 1 año + 210 días] y no compra en W = (T, T + 210 días]) o contracción
  (factura en W menos del 50 % que en W'). Reentrenamiento sin sesgo de intervención (H4): una observación (cliente, corte)
  no se usa si hubo una propuesta aprobada o enviada a ese cliente entre 90 días antes del corte y el final de W (solo
  intervenciones registradas hasta la fecha de puntuación); las cuentas del grupo de control se conservan. Los anunciantes
  del universo de propuestas que el modelo no puntúa (sin campaña en 12 meses) reciben el riesgo de respaldo por señales.
  Si el modelo falla, el ciclo se detiene, W1 recibe el error y el panel conserva el plan anterior.
- Priorización: probabilidad × valor de la cuenta × recuperación esperada (20 %, supuesto) − coste por acción (120 €, supuesto).
  Solo se proponen cuentas con valor neto positivo, también en el modo de respaldo sin modelo (H9). **Hasta** 4 cuentas por
  comercial y semana: si no hay suficientes con valor neto positivo, las plazas quedan libres y el cuadro de mando informa de
  cuántas («plazas sin cubrir»). 90 días sin repetir; grupo de control por sorteo.
- Marcas: «cuenta clave» = 5 % de más valor de toda la cartera activa; «escalar a dirección» = cuenta clave con motivo de
  cambio de interlocutor, reclamación o cobro. Al publicarse, W1 avisa a dirección el mismo día (cuenta, motivo, comercial y
  facturación en riesgo); no espera al resumen del lunes.
- Fuera: contactar al cliente; decidir la acción final; usar datos posteriores al corte.
- Criterios: como máximo 4 por comercial, todas con valor neto positivo y sin repetir en 90 días; cada una con motivo, tipo de
  riesgo, facturación en riesgo y el modelo que la generó (`propuestas.modelo`); añadir datos posteriores a la fecha no cambia
  ninguna variable ni la puntuación (tests de no fuga); misma puntuación en dos ejecuciones.
- Validación con los cierres (H4): el acuerdo entre E2 y el estado confirmado por el comercial se calcula cada semana, también
  por comercial (aviso si uno se aparta más de 20 puntos), y se muestra como **indicador** en el cuadro de mando y el panel.
  Ya no cambia la etiqueta ni vuelve a la regla simple: el modelo aprobado usa siempre E2 (decisión de la alumna).
- Resultado de las acciones: cada cuenta propuesta o del grupo de control, al cerrarse su ventana de 210 días, registra su
  grupo (acción, propuesta sin acción, control), el resultado E2 y si se salvó (`resultado_acciones`, solo dirección). El
  efecto se mide solo dentro de la banda media, la única con control (`efecto_accion`, con `banda_riesgo` en cada asignación).
  Con las variables en la fecha de la propuesta se guarda una tabla de aprendizaje para un futuro modelo de qué cuentas se
  pueden salvar.
- Evaluación del modelo (informe en `modelo_churn/informe.md`): entrenamiento en 19 cortes (dic-2020 → jun-2025, 1.992
  observaciones); prueba en sep-2025 y dic-2025 solo con datos originales (251 observaciones). AUC 0,883 (IC 95 %
  0,842–0,920) frente a 0,731 ordenando por días sin campaña y 0,518 por valor; Brier 0,145; acierta las 12 cuentas de más
  riesgo en las dos fechas. Un árbol de decisión quedó por debajo (AUC 0,861).

### N3 · Elegir leads y ampliaciones de la semana (W4 + función SQL `preparar_lunes`, reglas)
- Puerta de datos (H7): la misma comprobación de `ultima_carga()` que N2, antes de preparar nada.
- Entrada: leads, clientes, campañas y productos. Salida: propuestas de lead nuevo y de ampliación con texto de plantilla.
- Lead nuevo: todo lead en estado «nuevo» sin propuesta; producto de entrada más contratado en su sector; correo si tiene
  consentimiento y correo, si no, llamada.
- Ampliación (siguiente mejor oferta): cliente activo (campaña en 180 días) y estable (facturación de 6 meses ≥ 70 % de los 6
  anteriores), sin propuesta abierta ni en 90 días; producto más contratado por su sector, que el cliente no ha comprado en
  12 meses, disponible el mes que viene y con capacidad libre; 2 por comercial, los de mayor facturación.
- Criterios: idempotente (volver a ejecutarlo no duplica); el producto propuesto no se compró en el último año.

### N4 · Redactar la propuesta y validarla (W1 y W4, IA generativa)
Dos pasos con responsabilidad y criterio propios (H12): N4a redacta (IA), N4b valida (código).
- Entrada: contexto de la empresa (ficha con cifras, motivo, producto, canal; sin datos del contacto). Salida: texto validado o plantilla.
- Modelo: Claude por API. Sistema: «usa solo cifras del contexto, tal cual; nunca menciones que el cliente está en riesgo;
  no incluyas ninguna condición económica ni porcentaje; tono profesional y cercano, de usted; máximo 200 palabras».
- Validador (código, no IA): descarta el texto si aparece una cifra que no está en el contexto, un porcentaje, €, «euros»,
  «descuento», «rebaja» o «gratis», o si supera 200 palabras. No mencionar el riesgo (H3) no depende solo del prompt: el
  validador rechaza la mención directa («riesgo», «abandono», «fuga», «churn») y las fórmulas que lo insinúan («hemos
  notado/detectado», «perderle», «dejar de anunciar», «nos preocupa», «inactiva», «caída de su inversión», «facturas
  pendientes», «impago»). Si falla o la IA no responde, queda la plantilla y se anota el
  motivo; volver a ejecutar reintenta solo esas.
- Fuera: enviar nada; decidir a quién se propone.
- Criterios N4a: 100 % de las propuestas con texto (de la IA o plantilla). Criterios N4b: 0 cifras no trazables, 0
  condiciones económicas y 0 menciones o insinuaciones del riesgo en los textos aceptados (Golden Dataset en tests); el
  motivo de cada descarte queda en `fuente_material`.

### N5 · Aprobar, corregir o rechazar (panel de Lovable, persona)
- Entrada: propuesta pendiente. Salida: propuesta aprobada con el texto congelado, rechazada con motivo, o nueva versión.
- Reglas de la base de datos: aprobar un correo exige contacto con correo; a un lead, consentimiento; al aprobar se guarda
  el texto exacto y su versión; una llamada aprobada pasa directamente a seguimiento. Rechazar exige motivo; una rechazada
  se puede reabrir.
- Texto editado por el comercial: cada versión corregida pasa por las mismas reglas del validador (salvo cifras trazables,
  porque el comercial puede añadir cifras que conoce) como aviso **no bloqueante**; la versión guarda los avisos y, si se
  aprueba con avisos, queda el evento «aprobada_con_aviso». Decide la persona.
- Bloqueos: no se aprueba un correo a un contacto dado de baja (H2). Con motivo «cambio de interlocutor», la propuesta se
  publica como llamada (H8): el contacto principal puede ser quien ya se fue.
- Fuera: enviar el correo (lo hace N6); escribir en tablas.
- Criterios (H12): 100 % de las aprobaciones con texto y versión congelados; 100 % de los rechazos con motivo; ninguna acción
  fuera de la cartera del usuario; plazo objetivo de decisión, 3 días laborables desde la publicación.

### N6 · Enviar el texto aprobado (W5, automático)
- Disparo: webhook de base de datos al registrarse el evento «aprobar» (cabecera con token) o reintento manual.
- Estado «enviando»: es el estado derivado de una propuesta aprobada por correo (lo pone `aprobar` y lo quita
  `registrar_envio`); no hay transición manual.
- Idempotencia (H1): W5 lee solo las aprobadas sin reservar y las reserva con `reservar_envios()` en una sola sentencia; solo
  envía las que ha reservado esa ejecución, así que dos ejecuciones simultáneas no envían dos veces. La base de datos no
  deja marcar «enviada» sin reserva y, al volver a aprobar, limpia la reserva anterior. Una reserva sin resultado no se
  reintenta sola (como mucho un envío): aparece en `envios_sin_confirmar` y dirección la libera con `liberar_envio()` tras
  comprobar en Gmail que el correo no salió.
- Correo en HTML con la identidad de la marca y pie de baja (H2); no se envía a excluidos ni sin enlace de baja. Los bloqueos
  se registran como error con su motivo.
- Respuesta de Gmail: solo un rechazo explícito (4xx) pasa a «Error de envío» reintentable. Un timeout, un error de red, un
  5xx o una respuesta vacía no se registran: la reserva queda en `envios_sin_confirmar`, se avisa a dirección en el momento y
  figura en el resumen del lunes hasta que se libera.
- Criterios: se envía exactamente el texto aprobado y como mucho una vez por aprobación; correcto → «En seguimiento» con
  identificador del mensaje; fallo → «Error de envío», visible en el panel y reintentable.

### N7 · Avisar del toque y registrarlo (vistas SQL `seguimientos_debidos` y `seguimientos_estado`, panel)
- Propuestas en seguimiento: primer toque a los 4 días, segundo a los 12, último o cierre a los 25. Aviso en el panel y en el
  correo del lunes. El grupo de control del piloto no recibe avisos.
- Llamada nunca iniciada: una propuesta por llamada aprobada sin ninguna llamada registrada cuenta desde la aprobación
  (fase «inicio»); si a los 4 días no hay actividad vence el toque y a los 7 días de retraso se escala como los demás.
- Registro (H5): el comercial anota cada toque en el panel (`registrar_toque`: llamada, correo propio o reunión, con
  resultado y nota). En una propuesta por llamada, la primera llamada registrada cuenta como su envío y desde ella corren los
  días 4, 12 y 25.
- Fuera: enviar recordatorios al cliente.
- Criterios (H12): un toque se considera atendido si hay respuesta del cliente o toque registrado después de su fecha; KPI
  «seguimientos al día» por grupo del piloto (`kpi_toques_por_grupo`).

### N8 · Registrar respuesta y cerrar con motivo (panel + W2)
- El comercial registra respuestas y cierra. Riesgo: estado confirmado, motivo y si el diagnóstico fue correcto (los tres
  obligatorios). Otras etiquetas: desenlace (ganada, perdida, descartada) y motivo.
- Alerta a dirección (W2, por webhook del evento «cerrar») si: cuenta clave perdida; cuenta para escalar no recuperada;
  pérdida por reclamación.
- Criterios (H12): 100 % de los cierres con los campos obligatorios (lo impone la base de datos); 100 % de las alertas
  definidas enviadas en el mismo día del cierre.

### N9 · Balance, previsión y resumen a dirección (W6, IA + automático)
Tres pasos con criterio propio (H12): N9a balance (SQL), N9b comentario (IA + validador), N9c resumen y escalado a dirección.
- Función SQL `balance_lunes`: por comercial, acciones de la semana anterior, pendientes, seguimientos que piden toque,
  cuentas en riesgo abiertas y previsión (importe propuesto × tasa histórica de éxito por origen: ampliación 53,6 %,
  lead nuevo 11,0 %).
- Correo a cada comercial con un comentario de Claude de 2–3 frases; validador: solo cifras presentes en los hechos y máximo
  70 palabras; si falla, el correo sale sin comentario.
- Correo a dirección con el resumen de todas las acciones por comercial y en total, sin IA.
- Escalado (H6): bloque «Seguimientos sin atender» con las propuestas cuyo toque pendiente más antiguo lleva 7 días o más
  vencido sin actividad, por comercial (`seguimientos_sin_atender`; el grupo de control queda fuera para no contaminar el
  piloto), y el KPI de seguimientos al día por grupo. Si Supabase no responde, el correo lo dice.
- Criterios: N9a, cifras iguales a las de la base de datos; N9b, 0 cifras no presentes en los hechos (si falla, sin
  comentario); N9c, el correo sale cada lunes aunque falle el comentario.
- Evaluación previa: un modelo de probabilidad de ganar no se adoptó (ganó en un periodo y perdió en otro).

## 5. Riesgos que el equipo ya identificó

- La tasa de recuperación (20 %) y el coste por acción son supuestos hasta que lo mida el grupo de control.
- Datos sintéticos: el modelo se valida en datos originales, pero 15 de sus 19 cortes de entrenamiento contienen datos
  generados. La variable que más pesa es los días sin contacto comercial.
- Las propuestas solo constan en los datos cuando se cierran: en la fecha más reciente casi ninguna figura como abierta y la
  puntuación sale algo más alta (el 23-nov-2026, 56 % de cuentas por encima de 0,5 frente al 43 % un año antes).
- El grupo de control solo existe en la banda media; si las cuentas propuestas son todas de banda alta, el efecto no se puede
  medir esa semana.
- Los mismos comerciales trabajan los dos grupos del piloto (posible contaminación).
- El tratamiento del consentimiento de puerta fría y los plazos de conservación deben validarlos una asesoría legal
  (LSSI y RGPD).
- Filas borradas en la hoja (H11, pendiente): W0 carga por identificador y no marca las filas que desaparecen de la hoja.
  Riesgo aceptado para la demo; corrección prevista: marcar «no presente en la última carga» y excluirlas del motor.
- Un envío cuya reserva no se confirma se libera a mano (preferimos no duplicar a reenviar solos).

## 6. Correcciones respecto a diseno-v1 (primera auditoría: aprobado con cambios, 2 altas, 7 medias, 3 bajas)

| Hallazgo | Corrección | Nodo |
|---|---|---|
| H1 (alta) · envío no idempotente | Reserva atómica, sin reserva no hay «enviada», liberación manual | N6 |
| H2 (alta) · sin baja, exclusión ni conservación | Enlace de baja en dos pasos, lista de exclusión con bloqueo en base, plazos | Reglas, N5, N6 |
| H3 · riesgo solo en el prompt | Validador con mención directa e insinuaciones | N4 |
| H4 · sesgo de reentrenamiento y juicio del comercial | Exclusión de intervenidas; acuerdo por comercial | N2 |
| H5 · llamadas sin registrar | `registrar_toque`; la primera llamada cuenta como envío | N7 |
| H6 · avisos ignorados sin escalado | Escalado a dirección a los 7 días; KPI por grupo | N9 |
| H7 · sin comprobar la carga | Puerta de datos en W1 y W4 | N2, N3 |
| H8 · correo a interlocutor que se fue | Canal llamada | N5 |
| H9 · 12 fijas y valor negativo | Hasta 4 con valor neto positivo; plazas sin cubrir | N2 |
| H10 · datos a la IA | Solo datos de empresa (documentado) | Reglas |
| H11 · filas borradas | Pendiente; riesgo aceptado | Riesgos |
| H12 · criterios y responsabilidades | Criterios en N4, N5, N7, N8 y N9; N4 y N9 divididos en pasos | N4–N9 |


## 7. Correcciones respecto a diseno-v2 (segunda auditoría: aprobado con cambios, 0 altas, 8 medias, 4 bajas)

| Hallazgo | Corrección | Estado |
|---|---|---|
| Llamada nunca iniciada sin escalado (media) | Fase «inicio» desde la aprobación, escalado a 7 días | Implantado |
| Base jurídica por etiqueta (media) | Base de cada envío documentada en las reglas | Documentado |
| «Escalar a dirección» tarda hasta 6 días (media) | Aviso a dirección el mismo día desde W1 | Implantado |
| Propuestas pendientes sin caducidad (media) | Trabajo futuro: caducidad a 10 días laborables, con KPI y regeneración | Declarado |
| Criterio del validador no verificable y sin tasa de descarte (media) | Trabajo futuro: lista versionada y KPI semanal «% de texto IA aceptado» | Declarado |
| Versión del modelo y variables por propuesta (media) | Cada propuesta guarda el modelo que la generó (diseno-v4); las variables de cada cuenta en la fecha de la propuesta quedan en la tabla de aprendizaje | Implantado en parte |
| Control de riesgo con cuentas clave (media) | Aclarado: las cuentas clave nunca van al control | Documentado |
| Asignación y tope de leads (media) | Trabajo futuro: reparto y tope semanal; detección de leads que ya son clientes | Declarado |
| Remitente y respuestas (baja) | Remitente del dominio con *reply-to* del comercial | Documentado |
| Timeout de Gmail como error reintentable (baja) | Solo 4xx es error; lo ambiguo queda sin confirmar y avisa | Implantado |
| Encargados de tratamiento (baja) | Lista de encargados y permisos de la hoja | Documentado |
| Validador sobre el texto del comercial (baja) | Avisos no bloqueantes y evento «aprobada_con_aviso» | Implantado |

## 8. Cambios de diseno-v4 (modelo de abandono nuevo)

| Cambio | Antes (diseno-v3) | Ahora | Dónde |
|---|---|---|---|
| Modelo de N2 | Logística L2 del motor de evaluación con 3 variables básicas y 6 señales | Logística L2 de `modelo_churn` (construida por la alumna), 14 variables, elegida entre 4 modelos | N2 |
| Etiqueta | E2 con «un año sin comprar»; vuelta a la regla simple A si el acuerdo baja del 70 % | E2 solo dentro de W y siempre E2; el acuerdo es un indicador | N2 |
| Datos | 36 meses | 83 meses (ampliación sintética documentada); prueba solo en datos originales | Contexto, N2 |
| Evaluación | ≈ 5 % mejor que ordenar por valor | AUC 0,883 frente a 0,731 (días sin campaña) y 0,518 (valor) | N2 |
| Trazabilidad | Sin modelo por propuesta | `propuestas.modelo` y `plan_vigente.modelo` | N2, N5 |
| Medición | Grupo de control en banda media | Además: `resultado_acciones` a 210 días y `efecto_accion` en la banda media | N2, N9 |

Tests: 99 del sistema (base de datos, n8n, ciclo y simulacro), 45 del modelo de abandono (no fuga de variables y de la
puntuación, contrato de salida, reproducibilidad, exclusión de intervenidas, resultado de las acciones), 33 de evaluación y
21 de propuestas. El parche `supabase/modelo_churn.sql` se prueba sentencia a sentencia y dos veces seguidas.

