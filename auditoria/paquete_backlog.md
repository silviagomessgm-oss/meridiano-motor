# Meridiano · Paquete de auditoría del backlog y de la solución desplegada (paso 08 FORGEN)

Versión: backlog-v4 · 22-nov-2026 · Generado con Claude Opus (Claude Code). Para revisión por un modelo distinto y más capaz.
Caso ficticio de un trabajo fin de programa: datos, contactos y cifras son simulados. El diseño de los nodos N1–N9 está en
`paquete_diseno.md` (paso 05, versión diseno-v3, ya auditado dos veces); aquí se revisa si el backlog lo cubre y si lo
desplegado lo cumple. Cambios respecto a backlog-v1: historias nuevas o modificadas por las correcciones de las dos
auditorías del diseño (marcadas «A1» o «A2») y de la primera auditoría del backlog (sección 6).

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
| E2-H3 | Como dirección quiero saber si un comercial aprueba un texto con problemas, para revisarlo con él (A2) | Cada versión corregida guarda en `material_versiones.avisos` los avisos del validador (lista cerrada de patrones de `avisos_texto()`); si se aprueba con avisos queda el evento «aprobada_con_aviso» | N5 | Media | **Parcial**: base de datos desplegada; el aviso visual en el panel es historia futura (E2-H4) |
| E3-H1 | Como comercial quiero ver solo mi cartera, ordenada por estado | Pendientes, enviando, en seguimiento y cerradas en 7 días; contadores iguales a las tarjetas | N5 | Alta | Desplegada (Lovable) |
| E3-H2 | Como comercial quiero corregir el texto sin perder lo anterior | Cada corrección es una versión con autor y fecha; se puede ver el historial | N5 | Alta | Desplegada |
| E3-H3 | Como comercial quiero aprobar y que se envíe solo, una sola vez (A1, A2) | Al aprobar se congela el texto; se envía exactamente ese texto; reserva atómica antes de Gmail (dos ejecuciones simultáneas no duplican); correcto → En seguimiento; rechazo explícito de Gmail → Error de envío reintentable; respuesta ambigua → sin confirmar, aviso a dirección, sin reintento automático | N5, N6 | Alta | Desplegada (W5) |
| E3-H7 | Como contacto quiero poder darme de baja de las comunicaciones comerciales (A1) | Pie con enlace de baja en cada correo; baja en dos pasos (W8); lista de exclusión; la base de datos impide aprobar o enviar a un excluido; baja también desde el panel; plazos de conservación documentados | N5, N6 | Alta | Desplegada (W5, W8, panel) |
| E3-H8 | Como contacto quiero que los correos de Meridiano sean reconocibles (A1) | Correo HTML con la identidad de la marca (paleta y tipografías del panel), firma del comercial, base del envío y derechos | N6 | Media | Desplegada (W5) |
| E3-H9 | Como comercial no quiero escribir a un interlocutor que ya no está (A1) | Las propuestas por cambio de interlocutor se publican como llamada | N5 | Media | Desplegada |
| E3-H4 | Como comercial quiero rechazar con motivo y reabrir si me equivoco | Rechazar exige motivo; una rechazada se puede reabrir; todo queda en el historial | N5 | Media | Desplegada |
| E3-H5 | Como empresa interesada quiero pedir información desde la web | Formulario con consentimiento obligatorio; se guarda el texto aceptado y la fecha; se asigna comercial | N3 | Media | Desplegada (Lovable) |
| E3-H6 | Como comercial quiero dar de alta un lead de puerta fría | Alta desde el panel; sin consentimiento solo se le puede llamar | N3, N5 | Media | Desplegada |
| E4-H1 | Como comercial quiero saber a quién debo un toque, para que ninguna propuesta muera en silencio | Aviso a los 4, 12 y 25 días sin respuesta ni toque registrado, en el panel y en el correo del lunes; el grupo `control_avisos` del piloto no lo recibe | N7 | Alta | Desplegada |
| E4-H8 | Como comercial quiero registrar mis llamadas y toques (A1) | `registrar_toque` con tipo, resultado y nota; la primera llamada de una propuesta por teléfono cuenta como su envío | N7 | Alta | Desplegada (base de datos y panel) |
| E4-H9 | Como dirección quiero enterarme de los seguimientos que nadie atiende (A1, A2) | En el resumen de los lunes: propuestas cuyo toque pendiente más antiguo lleva 7 días vencido sin actividad, incluidas llamadas aprobadas y nunca iniciadas; sin el grupo de control; KPI de seguimientos al día por grupo | N7, N9 | Alta | Desplegada (W6) |
| E4-H2 | Como dirección quiero saber por qué se cierra cada propuesta | Cierre de riesgo con estado, motivo y diagnóstico obligatorios; otras con desenlace y motivo | N8 | Alta | Desplegada |
| E4-H3 | Como dirección quiero enterarme al momento de una cuenta clave perdida | Alerta por correo al cerrar: cuenta clave perdida, cuenta para escalar no recuperada o pérdida por reclamación | N8 | Alta | Desplegada (W2) |
| E4-H10 | Como dirección quiero saber el mismo día qué cuentas clave requieren mi intervención (A2) | Al publicar el ciclo del martes, correo a dirección con las propuestas «escalar a dirección»: cuenta, motivo, comercial y facturación en riesgo | N2, N8 | Alta | Desplegada (W1) |
| E4-H4 | Como comercial quiero un balance de mi semana cada lunes | Acciones, pendientes, toques, cuentas en riesgo y previsión; comentario de IA solo con cifras de los hechos | N9 | Media | Desplegada (W6) |
| E4-H5 | Como dirección quiero el resumen de todas las acciones de la semana | Por comercial y en total; sin IA; lunes 8:15 | N9 | Media | Desplegada (W6) |
| E4-H6 | Como dirección quiero saber si los avisos aumentan las ventas | Sorteo 50 % reproducible; métrica: ganadas a 90 días; 320 por grupo; regla de decisión registrada antes de empezar | N7 | Media | En marcha (piloto) |
| E4-H7 | Como equipo quiero que un modelo independiente audite el diseño | W7 lee paquete y rúbrica de GitHub, llama al modelo auditor, valida el JSON (también si la respuesta se corta por longitud) y guarda la evidencia inmutable | Transversal | Media | Desplegada (W7); dos auditorías del diseño ejecutadas: de 2 altas a 0 |

Dependencias: E1-H1 → E1-H6 → E1-H2 → E2-H1 → E3-H3 → E4-H8 → E4-H1 → E4-H9 → E4-H2 → E4-H4. E1-H4 depende de E3-H5 y
E3-H6 (altas de leads). E1-H5 depende de E1-H2 y E1-H4.

Grupos de control (dos, con nombre propio): `control_riesgo` (E1-H3: cuentas en riesgo sin propuesta; columna
`grupo_experimental` del motor) y `control_avisos` (E4-H6: propuestas de ampliación y lead sin avisos de toque; columna
`grupo_piloto = 'control'`). E4-H1 y E4-H9 excluyen `control_avisos`.
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
  (GitHub). W4 y W6 se recuperaron exportándolos de n8n (`n8n/desplegados/`) y el SQL de los lunes, el piloto y el panel con
  un volcado del catálogo de Supabase (`supabase/esquema_desplegado.sql`, con los secretos de los webhooks sustituidos por
  marcadores).
- El editor SQL de Supabase partía las funciones por los «;» internos: parches reescritos sin variables locales ni `$$`.
- La primera ejecución del auditor se cortó por longitud (el modelo razona antes de responder): límite ampliado y detección
  del corte, que queda registrado como `formato_invalido`.
- Las credenciales de n8n no viajan en los JSON importados: se asignan por identificador tras importar.

## 4. Pendiente conocido

- n8n corre en local (decisión del equipo para un proyecto de formación, sección 6).
- Prompts de Lovable aplicados por el equipo sin pruebas automáticas de la interfaz; la seguridad que hay detrás sí está
  probada (permisos cruzados entre comerciales y acciones solo por función, en Postgres).
- Efecto real en ventas: lo medirá el piloto con grupo de control (lectura final prevista hacia diciembre de 2027).
- Revisión legal del consentimiento de puerta fría (LSSI y RGPD).


## 6. Respuesta a la primera auditoría del backlog (aprobado con cambios: 3 altas, 6 medias, 3 bajas)

### Despliegue en local (H2) · decisión del equipo
n8n se mantiene en Docker en un equipo del proyecto: es un proyecto de formación sin clientes reales. Consecuencias
aceptadas y declaradas: los flujos programados y la página de baja solo funcionan con el equipo encendido. Paso a producción
(no ejecutado): n8n en la nube o en un servidor con disponibilidad continua, W8 bajo un dominio estable de Meridiano y una
comprobación con el equipo local apagado.

### Encargados del tratamiento y minimización (H3)
| Encargado | Qué recibe | Minimización |
|---|---|---|
| Anthropic (API de Claude) | Datos de empresa: razón social, sector, acción, motivo, producto y cifras de campaña | Nunca datos del contacto |
| GitHub (Actions) | Las tablas de Supabase durante la ejecución del motor | El artefacto publicado es solo el cuadro de mando agregado (7 días); el plan por cuenta queda en Supabase |
| Supabase | Toda la base de datos | Permisos por fila; claves de servicio solo en n8n y GitHub |
| Google (Sheets, Gmail) | Hoja fuente; correos enviados | Hoja con permisos nominales |
| Lovable | Nada propio: lee Supabase con la sesión del usuario | — |
Contrato de encargado (art. 28 RGPD) necesario con cada uno en producción. **Repositorio público:** las tablas de
`tablas/` son datos simulados; en producción el repositorio sería privado y las tablas no se versionarían.

### Errores y costes (H7)
- W9 «Aviso de error» es el flujo de errores de todos los demás: cualquier ejecución fallida avisa a dirección y datos con
  el flujo, el nodo, el error, el enlace y qué hacer.
- Si Claude no responde, la propuesta se publica con la plantilla y el motivo en `fuente_material` (ya en E2-H2).
- Volumen de IA por semana: hasta 12 textos de riesgo (W1), los leads y 6 ampliaciones (W4), 3 comentarios (W6), con
  `max_tokens` de 600 por texto. Gmail: unas decenas de correos por semana, muy por debajo de su límite diario.

### Trazabilidad criterio → test (H8)
| Criterio | Test |
|---|---|
| E3-H3 · dos ejecuciones simultáneas no duplican | `test_reserva_concurrente_con_dos_transacciones` (dos conexiones reales), `test_reserva_atomica_solo_una_ejecucion_envia`, `test_w5_solo_envia_lo_que_ha_reservado` |
| E3-H3 · respuesta ambigua sin reintento | `test_w5_respuesta_ambigua_no_se_registra_y_avisa` |
| E3-H7 · no se aprueba ni envía a excluidos | `test_baja_por_enlace_bloquea_aprobar_y_enviar`, `test_w5_no_envia_a_excluidos_ni_sin_enlace_de_baja` |
| E3-H7 · baja en dos pasos | `test_w8_pagina_pide_confirmacion_y_muestra_resultado`, `test_w8_token_invalido_no_da_de_baja` |
| E1-H2 · hasta 4, valor neto positivo | `test_capacidad_por_comercial`, `test_solo_se_propone_con_valor_neto_positivo`, `test_huecos_cuando_no_hay_cuentas_suficientes` |
| E1-H2 / E1-H5 · sin repetir en 90 días | `test_ciclos_semanales_enfriamiento_y_vuelta_automatica_a_regla_` |
| E1-H3 · control nunca con cuentas clave | `test_control_solo_banda_media_y_nunca_cuentas_clave`, `test_asignacion_de_control_reproducible` |
| E1-H6 · puerta de datos | `test_ultima_carga_apta_solo_si_w0_termino_bien_y_es_reciente`, `test_w1_puerta_de_datos` |
| E1-H7 · sin cuentas intervenidas | `test_excluye_solo_observaciones_con_intervencion_en_su_ventana`, `test_acuerdo_por_comercial_y_aviso` |
| E2-H2 · validador | `test_validador_descarta_y_conserva_plantilla`, `test_validador_rechaza_insinuar_el_riesgo` |
| E2-H3 · avisos del texto | `test_avisos_del_texto_no_bloquean_y_quedan_registrados` |
| E3-H1 · solo mi cartera (H6) | `test_permisos_cruzados_entre_comerciales`, `test_panel_solo_lee_y_actua_con_accion_panel` |
| E3-H2, E3-H4 · versiones, rechazo y reapertura | `test_corregir_aprobar_enviar_seguir_y_cerrar`, `test_rechazo_con_motivo_y_reapertura` |
| E3-H5, E3-H6 · consentimiento | `test_leads_formulario_con_consentimiento_y_puerta_fria_sin_el` |
| E4-H8 · toques | `test_toque_registrado_y_llamada_cuenta_como_envio` |
| E4-H9 · escalado | `test_seguimiento_sin_atender_se_escala_salvo_control`, `test_llamada_aprobada_sin_iniciar_se_escala`, `test_w6_escalado_a_direccion` |
| E4-H3, E4-H10 · alertas a dirección | `test_w2_alerta_solo_en_cierres_que_lo_requieren`, `test_w1_escalado_inmediato_a_direccion` |
| W9 · aviso de error | `test_w9_aviso_de_error` |
| E1-H4 · lunes idempotente; lead con consentimiento por correo | `test_preparar_lunes_es_idempotente_y_respeta_una_etiqueta` |
| E4-H4, E4-H5 · balance por comercial | `test_balance_lunes_una_fila_por_comercial` |
| E4-H6 · sorteo reproducible al 50 % | `test_sorteo_del_piloto_reproducible` |
Todos los tests de base de datos se ejecutan sobre el esquema desplegado: `schema.sql`, los parches y el volcado de producción.
Sin prueba automática: la interfaz de Lovable (contadores, historial visible) y la comprobación visual del correo en Gmail; se
comprueban a mano en la demo.

### Paso a producción del envío (H9)
`modo_demo = false` en Configuración; remitente del dominio de Meridiano con *reply-to* del comercial; SPF, DKIM y DMARC del
dominio; límite diario de la cuenta de envío; W8 en una URL pública estable; prueba de un envío real a un buzón externo con
el enlace de baja funcionando.

### Reglas transversales → historias (H12)
| Regla | Historias |
|---|---|
| Trazabilidad (acciones solo por función) | E3-H1, E3-H2, E3-H4 |
| Permisos por cartera | E3-H1 |
| Una etiqueta por empresa | E1-H5 |
| Consentimiento | E3-H5, E3-H6 |
| Comunicaciones comerciales: baja, exclusión y conservación (plazos en `politica_correo.md`) | E3-H7 |
| Datos que recibe la IA | E2-H1, E2-H2 |
| Modo demo | E3-H3 |
| Grupos de control | E1-H3, E4-H6 |

### Trabajo futuro añadido
E2-H4 aviso visual de los avisos del validador en el panel; versión del modelo, probabilidad y variables por propuesta (H4).

### Reproducibilidad (H1) · resuelto
- W4 y W6: `n8n/desplegados/` (exportación directa de n8n; el resto de flujos se generan con `construir_flujos.py`).
- Base de datos: `supabase/esquema_desplegado.sql` (28 funciones, 17 vistas, 10 triggers y el inventario de 35 tablas, 16 de
  ellas de una iteración anterior marcadas como legado), generado con `supabase/volcar_esquema.sql`.
- Comprobación: el esquema se restaura desde cero sobre Postgres 16 (`schema.sql` → `auditorias.sql` → parches → volcado) y
  los 85 tests de la base de datos y de n8n se ejecutan sobre esa copia, incluidos `preparar_lunes`, `balance_lunes` y el
  sorteo del piloto, que antes no tenían prueba.
- Los webhooks de Supabase hacia n8n usan un túnel (ngrok) hacia el n8n local; su URL y su token no se versionan.
