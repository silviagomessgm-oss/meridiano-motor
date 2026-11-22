# Meridiano · Paquete de auditoría del backlog y de la solución desplegada (paso 08 FORGEN)

Versión: backlog-v2 · 22-nov-2026 · Generado con Claude Opus (Claude Code). Para revisión por un modelo distinto y más capaz.
Caso ficticio de un trabajo fin de programa: datos, contactos y cifras son simulados. El diseño de los nodos N1–N9 está en
`paquete_diseno.md` (paso 05, versión diseno-v3, ya auditado dos veces); aquí se revisa si el backlog lo cubre y si lo
desplegado lo cumple. Cambios respecto a backlog-v1: historias nuevas o modificadas por las correcciones de las dos
auditorías del diseño (marcadas «A1» o «A2»).

## 1. Épicas

| Épica | Objetivo | Nodos |
|---|---|---|
| E1 · Datos y decisión | Datos de la semana fiables y selección de cuentas por valor esperado | N1, N2, N3 |
| E2 · Redacción con IA | Cada propuesta llega redactada y validada | N4 |
| E3 · Panel y envío | El comercial decide en un único sitio y lo aprobado se envía solo | N5, N6 |
| E4 · Seguimiento y medición | Ninguna propuesta muere en silencio; se mide si el sistema funciona | N7, N8, N9 |

## 2. Historias de usuario

| ID | Historia | Criterios de aceptación | Nodo | Prioridad | Estado |
|---|---|---|---|---|---|
| E1-H1 | Como responsable de datos quiero que la carga semanal sea automática | Lee las 8 pestañas en una llamada; se detiene si falta una pestaña o columna o una tabla supera el 5 % de errores; registra el resultado en `ejecuciones`; avisa de las filas rechazadas | N1 | Alta | Desplegada (W0) |
| E1-H2 | Como comercial quiero recibir cada martes hasta 4 cuentas de más riesgo que compense trabajar (A1) | Hasta 4 por comercial, todas con valor neto positivo (también sin modelo); plazas sin cubrir informadas; sin repetir cuenta en 90 días; cada una con motivo, tipo de riesgo y facturación en riesgo | N2 | Alta | Desplegada (W1 + motor) |
| E1-H3 | Como dirección quiero un grupo de control en las cuentas en riesgo | Sorteo estable por trimestre, 20 % de la banda media, nunca cuentas clave; las cuentas de control no reciben propuesta y se miden igual | N2 | Alta | Desplegada |
| E1-H6 | Como dirección no quiero propuestas calculadas con datos viejos o rotos (A1) | W1 y W4 consultan `ultima_carga()`; si la última carga no terminó bien o tiene más de 8 días, no generan nada, avisan a dirección y datos y lo registran | N2, N3 | Alta | Desplegada |
| E1-H7 | Como equipo quiero que el modelo no aprenda de cuentas en las que ya actuamos (A1) | El reentrenamiento excluye observaciones con propuesta aprobada o enviada en su ventana; la validación de la etiqueta informa del acuerdo por comercial | N2 | Media | Desplegada (motor) |
| E1-H4 | Como comercial quiero propuestas de ampliación y para leads nuevos cada lunes | 2 ampliaciones por comercial; todo lead nuevo con propuesta; volver a ejecutar no duplica | N3 | Alta | Desplegada (W4) |
| E1-H5 | Como cliente no quiero recibir dos propuestas a la vez | Una etiqueta por empresa; el ciclo del martes excluye las empresas con propuesta del lunes; 90 días de enfriamiento común | N2, N3 | Alta | Desplegada |
| E2-H1 | Como comercial quiero la propuesta ya redactada | Texto de Claude con el contexto de la cuenta; tono de usted; máximo 200 palabras | N4 | Alta | Desplegada (W1, W4) |
| E2-H2 | Como dirección quiero que la IA no invente, no prometa condiciones ni deje ver que vemos riesgo (A1) | El validador descarta cifras no trazables, %, €, descuentos, textos largos y menciones o insinuaciones del riesgo; si falla queda la plantilla con el motivo; el reintento solo rehace esas | N4 | Alta | Desplegada |
| E2-H3 | Como dirección quiero saber si un comercial aprueba un texto con problemas (A2) | Cada versión corregida en el panel pasa por las reglas del validador como aviso no bloqueante; queda el evento «aprobada_con_aviso» | N5 | Media | Desplegada (base de datos; aviso visual en Lovable pendiente) |
| E3-H1 | Como comercial quiero ver solo mi cartera, ordenada por estado | Pendientes, enviando, en seguimiento y cerradas en 7 días; contadores iguales a las tarjetas | N5 | Alta | Desplegada (Lovable) |
| E3-H2 | Como comercial quiero corregir el texto sin perder lo anterior | Cada corrección es una versión con autor y fecha; se puede ver el historial | N5 | Alta | Desplegada |
| E3-H3 | Como comercial quiero aprobar y que se envíe solo, una sola vez (A1, A2) | Al aprobar se congela el texto; se envía exactamente ese texto; reserva atómica antes de Gmail (dos ejecuciones simultáneas no duplican); correcto → En seguimiento; rechazo explícito de Gmail → Error de envío reintentable; respuesta ambigua → sin confirmar, aviso a dirección, sin reintento automático | N5, N6 | Alta | Desplegada (W5) |
| E3-H7 | Como contacto quiero poder darme de baja de las comunicaciones comerciales (A1) | Pie con enlace de baja en cada correo; baja en dos pasos (W8); lista de exclusión; la base de datos impide aprobar o enviar a un excluido; baja también desde el panel; plazos de conservación documentados | N5, N6 | Alta | Desplegada (W5, W8, panel) |
| E3-H8 | Como contacto quiero que los correos de Meridiano sean reconocibles (A1) | Correo HTML con la identidad de la marca (paleta y tipografías del panel), firma del comercial, base del envío y derechos | N6 | Media | Desplegada (W5) |
| E3-H9 | Como comercial no quiero escribir a un interlocutor que ya no está (A1) | Las propuestas por cambio de interlocutor se publican como llamada | N5 | Media | Desplegada |
| E3-H4 | Como comercial quiero rechazar con motivo y reabrir si me equivoco | Rechazar exige motivo; una rechazada se puede reabrir; todo queda en el historial | N5 | Media | Desplegada |
| E3-H5 | Como empresa interesada quiero pedir información desde la web | Formulario con consentimiento obligatorio; se guarda el texto aceptado y la fecha; se asigna comercial | N3 | Media | Desplegada (Lovable) |
| E3-H6 | Como comercial quiero dar de alta un lead de puerta fría | Alta desde el panel; sin consentimiento solo se le puede llamar | N3, N5 | Media | Desplegada |
| E4-H1 | Como comercial quiero saber a quién debo un toque | Aviso a los 4, 12 y 25 días sin respuesta en el panel y en el correo del lunes; el grupo de control del piloto no lo recibe | N7 | Alta | Desplegada |
| E4-H8 | Como comercial quiero registrar mis llamadas y toques (A1) | `registrar_toque` con tipo, resultado y nota; la primera llamada de una propuesta por teléfono cuenta como su envío | N7 | Alta | Desplegada (base de datos y panel) |
| E4-H9 | Como dirección quiero enterarme de los seguimientos que nadie atiende (A1, A2) | En el resumen de los lunes: propuestas cuyo toque pendiente más antiguo lleva 7 días vencido sin actividad, incluidas llamadas aprobadas y nunca iniciadas; sin el grupo de control; KPI de seguimientos al día por grupo | N7, N9 | Alta | Desplegada (W6) |
| E4-H2 | Como dirección quiero saber por qué se cierra cada propuesta | Cierre de riesgo con estado, motivo y diagnóstico obligatorios; otras con desenlace y motivo | N8 | Alta | Desplegada |
| E4-H3 | Como dirección quiero enterarme al momento de una cuenta clave perdida | Alerta por correo al cerrar: cuenta clave perdida, cuenta para escalar no recuperada o pérdida por reclamación | N8 | Alta | Desplegada (W2) |
| E4-H10 | Como dirección quiero saber el mismo día qué cuentas clave requieren mi intervención (A2) | Al publicar el ciclo del martes, correo a dirección con las propuestas «escalar a dirección»: cuenta, motivo, comercial y facturación en riesgo | N2, N8 | Alta | Desplegada (W1) |
| E4-H4 | Como comercial quiero un balance de mi semana cada lunes | Acciones, pendientes, toques, cuentas en riesgo y previsión; comentario de IA solo con cifras de los hechos | N9 | Media | Desplegada (W6) |
| E4-H5 | Como dirección quiero el resumen de todas las acciones de la semana | Por comercial y en total; sin IA; lunes 8:15 | N9 | Media | Desplegada (W6) |
| E4-H6 | Como dirección quiero saber si los avisos aumentan las ventas | Sorteo 50 % reproducible; métrica: ganadas a 90 días; 320 por grupo; regla de decisión registrada antes de empezar | N7 | Media | En marcha (piloto) |
| E4-H7 | Como equipo quiero que un modelo independiente audite el diseño | W7 lee paquete y rúbrica de GitHub, llama al modelo auditor, valida el JSON (también si la respuesta se corta por longitud) y guarda la evidencia inmutable | Transversal | Media | Desplegada (W7); dos auditorías del diseño ejecutadas: de 2 altas a 0 |

Dependencias: E1-H1 → E1-H6 → E1-H2 → E2-H1 → E3-H3 → E4-H1 → E4-H8 → E4-H9 → E4-H2 → E4-H4. E1-H5 depende de E1-H2 y E1-H4.
E3-H7 depende de E3-H3 (el bloqueo vive en la base de datos y el enlace en el correo de W5).

Historias de trabajo futuro (no construidas; declaradas en el diseño): caducidad de propuestas pendientes a 10 días
laborables; KPI semanal de textos de IA aceptados; versión del modelo, probabilidad y variables guardadas en cada propuesta;
reparto y tope semanal de leads con detección de leads que ya son clientes; marcar filas borradas de la hoja como «no
presentes» (W0).

## 3. Solución desplegada

| Pieza | Dónde | Cómo se accede |
|---|---|---|
| Flujos W0, W1, W2, W4, W5, W6 (programados o por webhook), W7 (manual) y W8 (página pública de baja) | n8n autoalojado en Docker en el equipo del equipo de proyecto (se empezó en n8n Cloud; se migró a local). Los cambios se guardan como borrador y se publican después de aplicar el SQL del que dependen | Usuario de n8n |
| Motor de riesgo (Python, regresión logística) | GitHub Actions, repositorio `meridiano-motor` | Lanzado por W1 con token de GitHub |
| Base de datos, reglas, permisos y trazabilidad | Supabase (Postgres): `schema.sql` y parches por cambio (`bajas.sql`, `envios.sql`, `controles.sql`, `seguimiento.sql`, `auditoria2.sql`), sin bloques `$$` para que el editor web no los corte | Panel con usuario; n8n y motor con clave de servicio |
| Panel comercial, vista de dirección y formulario web | Lovable | Usuario por comercial y dirección; formulario público |
| Redacción y auditoría | API de Claude | Credencial en n8n |
| Envío | Gmail | Modo demo: todo al buzón de pruebas |

Pruebas: 78 tests del sistema (nodos de código de n8n y funciones de Supabase en Postgres 16 local), 33 de evaluación y 21 del
motor de propuestas. Cada parche SQL se prueba también ejecutado sentencia a sentencia y dos veces seguidas.
Prueba de extremo a extremo hecha por el equipo: formulario → panel → aceptar → envío → seguimiento → cierre → alerta → correo del lunes.

Incidencias resueltas durante el despliegue:
- El alojamiento previsto para el motor pasó a ser de pago: se movió a GitHub Actions sin cambiar el resto.
- El servidor de correo SMTP rechazaba la conexión: se cambió a Gmail.
- El panel escribía en tablas directamente y la seguridad lo ignoraba sin error: se obligó a usar solo la función de acciones y a mostrar los errores.
- La vista del panel ocultaba las propuestas cerradas de semanas anteriores: se corrigió para mostrarlas 7 días.
- Un webhook sin la cabecera Content-Type anulaba las acciones del panel: cabecera obligatoria.
- «Cuenta clave» marcaba 9 de cada 12 propuestas: umbral sobre toda la cartera.
- El contenedor de desarrollo se reemplazó y se perdió el repositorio de trabajo principal: se siguió en `meridiano-motor`
  (GitHub). El código de W4 y W6 y el SQL de los lunes y del piloto siguen desplegados, pero no están en el repositorio.
- El editor SQL de Supabase partía las funciones por los «;» internos: parches reescritos sin variables locales ni `$$`.
- La primera ejecución del auditor se cortó por longitud (el modelo razona antes de responder): límite ampliado y detección
  del corte, que queda registrado como `formato_invalido`.
- Las credenciales de n8n no viajan en los JSON importados: se asignan por identificador tras importar.

## 4. Pendiente conocido

- Reproducibilidad: exportar W4 y W6 al repositorio y recuperar `preparar_lunes`, `balance_lunes`, la vista de seguimientos
  y el piloto con un volcado del esquema de Supabase.
- Despliegue para la entrega: n8n corre en local; la plantilla del TFP pide la solución en la nube (volver a n8n Cloud o a
  un servidor).
- Prompts de Lovable aplicados por el equipo sin pruebas automáticas del panel (solo prueba manual de extremo a extremo).
- Efecto real en ventas: lo medirá el piloto con grupo de control (lectura final prevista hacia diciembre de 2027).
- Revisión legal del consentimiento de puerta fría (LSSI y RGPD).
