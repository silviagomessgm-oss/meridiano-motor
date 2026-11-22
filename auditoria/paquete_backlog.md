# Meridiano · Paquete de auditoría del backlog y de la solución desplegada (paso 08 FORGEN)

Versión: backlog-v1 · 22-nov-2026 · Generado con Claude Opus (Claude Code). Para revisión por un modelo distinto y más capaz.
Caso ficticio de un trabajo fin de programa: datos, contactos y cifras son simulados. El diseño de los nodos N1–N9 está en
`paquete_diseno.md` (paso 05); aquí se revisa si el backlog lo cubre y si lo desplegado lo cumple.

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
| E1-H2 | Como comercial quiero recibir cada martes mis 4 cuentas de más riesgo | 12 propuestas por semana; sin repetir cuenta en 90 días; cada una con motivo, tipo de riesgo y facturación en riesgo | N2 | Alta | Desplegada (W1 + motor) |
| E1-H3 | Como dirección quiero un grupo de control en las cuentas en riesgo | Sorteo estable por trimestre; las cuentas de control no reciben propuesta y se miden igual | N2 | Alta | Desplegada |
| E1-H4 | Como comercial quiero propuestas de ampliación y para leads nuevos cada lunes | 2 ampliaciones por comercial; todo lead nuevo con propuesta; volver a ejecutar no duplica | N3 | Alta | Desplegada (W4) |
| E1-H5 | Como cliente no quiero recibir dos propuestas a la vez | Una etiqueta por empresa; el ciclo del martes excluye las empresas con propuesta del lunes; 90 días de enfriamiento común | N2, N3 | Alta | Desplegada |
| E2-H1 | Como comercial quiero la propuesta ya redactada | Texto de Claude con el contexto de la cuenta; tono de usted; máximo 200 palabras | N4 | Alta | Desplegada (W1, W4) |
| E2-H2 | Como dirección quiero que la IA no invente ni prometa condiciones | El validador descarta cifras no trazables, %, €, descuentos y textos largos; si falla queda la plantilla con el motivo; el reintento solo rehace esas | N4 | Alta | Desplegada |
| E3-H1 | Como comercial quiero ver solo mi cartera, ordenada por estado | Pendientes, enviando, en seguimiento y cerradas en 7 días; contadores iguales a las tarjetas | N5 | Alta | Desplegada (Lovable) |
| E3-H2 | Como comercial quiero corregir el texto sin perder lo anterior | Cada corrección es una versión con autor y fecha; se puede ver el historial | N5 | Alta | Desplegada |
| E3-H3 | Como comercial quiero aprobar y que se envíe solo | Al aprobar se congela el texto; se envía exactamente ese texto; correcto → En seguimiento; fallo → Error de envío reintentable | N5, N6 | Alta | Desplegada (W5) |
| E3-H4 | Como comercial quiero rechazar con motivo y reabrir si me equivoco | Rechazar exige motivo; una rechazada se puede reabrir; todo queda en el historial | N5 | Media | Desplegada |
| E3-H5 | Como empresa interesada quiero pedir información desde la web | Formulario con consentimiento obligatorio; se guarda el texto aceptado y la fecha; se asigna comercial | N3 | Media | Desplegada (Lovable) |
| E3-H6 | Como comercial quiero dar de alta un lead de puerta fría | Alta desde el panel; sin consentimiento solo se le puede llamar | N3, N5 | Media | Desplegada |
| E4-H1 | Como comercial quiero saber a quién debo un toque | Aviso a los 4, 12 y 25 días sin respuesta en el panel y en el correo del lunes; el grupo de control del piloto no lo recibe | N7 | Alta | Desplegada |
| E4-H2 | Como dirección quiero saber por qué se cierra cada propuesta | Cierre de riesgo con estado, motivo y diagnóstico obligatorios; otras con desenlace y motivo | N8 | Alta | Desplegada |
| E4-H3 | Como dirección quiero enterarme al momento de una cuenta clave perdida | Alerta por correo al cerrar: cuenta clave perdida, cuenta para escalar no recuperada o pérdida por reclamación | N8 | Alta | Desplegada (W2) |
| E4-H4 | Como comercial quiero un balance de mi semana cada lunes | Acciones, pendientes, toques, cuentas en riesgo y previsión; comentario de IA solo con cifras de los hechos | N9 | Media | Desplegada (W6) |
| E4-H5 | Como dirección quiero el resumen de todas las acciones de la semana | Por comercial y en total; sin IA; lunes 8:15 | N9 | Media | Desplegada (W6) |
| E4-H6 | Como dirección quiero saber si los avisos aumentan las ventas | Sorteo 50 % reproducible; métrica: ganadas a 90 días; 320 por grupo; regla de decisión registrada antes de empezar | N7 | Media | En marcha (piloto) |
| E4-H7 | Como equipo quiero que un modelo independiente audite el diseño | W7 lee paquete y rúbrica de GitHub, llama al modelo auditor, valida el JSON y guarda la evidencia inmutable | Transversal | Media | Desplegada (W7) |

Dependencias: E1-H1 → E1-H2 → E2-H1 → E3-H3 → E4-H1 → E4-H2 → E4-H4. E1-H5 depende de E1-H2 y E1-H4.

## 3. Solución desplegada

| Pieza | Dónde | Cómo se accede |
|---|---|---|
| Flujos W0, W1, W2, W4, W5, W6 (programados o por webhook) y W7 (manual) | n8n (n8n Cloud; durante el desarrollo, réplica en Docker local) | Usuario de n8n |
| Motor de riesgo (Python, regresión logística) | GitHub Actions, repositorio `meridiano-motor` | Lanzado por W1 con token de GitHub |
| Base de datos, reglas, permisos y trazabilidad | Supabase (Postgres) | Panel con usuario; n8n y motor con clave de servicio |
| Panel comercial, vista de dirección y formulario web | Lovable | Usuario por comercial y dirección; formulario público |
| Redacción y auditoría | API de Claude | Credencial en n8n |
| Envío | Gmail | Modo demo: todo al buzón de pruebas |

Pruebas: tests automáticos del motor, de los nodos de código de n8n y de las funciones de Supabase en Postgres local.
Prueba de extremo a extremo hecha por el equipo: formulario → panel → aceptar → envío → seguimiento → cierre → alerta → correo del lunes.

Incidencias resueltas durante el despliegue:
- El alojamiento previsto para el motor pasó a ser de pago: se movió a GitHub Actions sin cambiar el resto.
- El servidor de correo SMTP rechazaba la conexión: se cambió a Gmail.
- El panel escribía en tablas directamente y la seguridad lo ignoraba sin error: se obligó a usar solo la función de acciones y a mostrar los errores.
- La vista del panel ocultaba las propuestas cerradas de semanas anteriores: se corrigió para mostrarlas 7 días.
- Un webhook sin la cabecera Content-Type anulaba las acciones del panel: cabecera obligatoria.
- «Cuenta clave» marcaba 9 de cada 12 propuestas: umbral sobre toda la cartera.

## 4. Pendiente conocido

- Auditoría del diseño (paso 05) con el modelo auditor: flujo listo y probado, ejecución pendiente.
- Efecto real en ventas: lo medirá el piloto con grupo de control (lectura final prevista hacia diciembre de 2027).
- Revisión legal del consentimiento de puerta fría (LSSI y RGPD).
