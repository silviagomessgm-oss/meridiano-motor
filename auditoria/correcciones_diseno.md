# Correcciones tras la auditoría del diseño (W7 · tipo `diseno`)

Auditoría de referencia: ejecución n8n 95, modelo auditor `claude-fable-5-1`, paquete `diseno-v1`. Veredicto: **aprobado con cambios** (2 altas, 7 medias, 3 bajas). Evidencia completa en la tabla `auditorias` de Supabase.

| Hallazgo | Gravedad | Corrección aplicada | Dónde | Prueba |
|---|---|---|---|---|
| **H2** · Correos sin baja, sin lista de exclusión ni plazo de conservación | Alta | Pie con enlace de baja en cada correo (W5, HTML con la identidad de Meridiano); página de baja en dos pasos (W8); lista `exclusiones` con bloqueo en la base al aprobar y al enviar; baja desde el panel (`baja_panel`); plazo de conservación y vista `conservacion_vencida` | `supabase/bajas.sql`, W5, W8, panel, `auditoria/politica_correo.md` | 6 tests; W8 probado en n8n contra Supabase; prueba de principio a fin en el buzón de demostración |
| **H1** · Envío (N6) no idempotente; transición a «enviando» sin documentar | Alta | «Enviando» es el estado derivado de una propuesta aprobada por correo. W5 reserva cada propuesta de forma atómica (`reservar_envios`) antes de llamar a Gmail y solo envía las que ha reservado; sin reserva la base no permite marcarla enviada; al volver a aprobar se limpia la reserva. Una reserva sin resultado no se reenvía sola (como mucho un envío): aparece en `envios_sin_confirmar` y dirección la libera con `liberar_envio` tras comprobar Gmail. Además, los bloqueos se registran en una rama propia (antes se perdían si no había nada que enviar) | `supabase/envios.sql`, W5 | 4 tests de base de datos y 4 de W5 |

| **H7** · W1 y W4 no comprobaban la carga de datos | `ultima_carga()`; W1 y W4 se detienen si la última carga no terminó bien o tiene más de 8 días, avisan y lo registran | `supabase/controles.sql`, W1, W4 | 5 tests; publicado |
| **H8** · Correo a un interlocutor que ya no está | `reunion_nuevo_interlocutor` pasa a canal llamada al publicar (y las pendientes) | `supabase/controles.sql` | 1 test |
| **H3** · No mencionar el riesgo dependía del prompt | El validador rechaza la mención directa y las fórmulas que lo insinúan | `n8n/codigo/w1_validador.js` | 6 casos |
| **H5** · Llamadas sin registrar | `registrar_toque()` (tipo, resultado, nota); la primera llamada cuenta como envío | `supabase/seguimiento.sql`, panel | 1 test |
| **H6** · Avisos de toque ignorados sin escalado | `seguimientos_sin_atender` (toque pendiente más antiguo con 7 días de retraso, sin el grupo de control) en el resumen de dirección de W6; KPI por grupo | `supabase/seguimiento.sql`, W6 | 2 tests; publicado |
| **H9** · 12 propuestas fijas y valor neto negativo | Valor neto positivo también sin modelo; «hasta» 4 por comercial; plazas sin cubrir en el cuadro de mando | `propuestas/src/propuestas.py` | 2 tests |
| **H4** · Reentrenamiento con cuentas intervenidas; control dependiente del comercial | Exclusión de observaciones con intervención en su ventana; acuerdo por comercial con aviso a 20 puntos; limitación declarada | `evaluacion/src/generar_scores.py`, `validacion_automatica.py`, `motor/sync_supabase.py` | 2 tests |
| **H10** · Datos enviados a la IA | Comprobado: solo datos de empresa, nunca del contacto. Documentado | Paquete (reglas) | Revisión de W1 y W4 |
| **H11** · Filas borradas en la hoja | Pendiente: riesgo aceptado para la demo, corrección prevista | Paquete (riesgos) | — |
| **H12** · Nodos sin criterios o con varias responsabilidades | Criterios en N4, N5, N7, N8 y N9; N4 y N9 divididos en pasos | Paquete | — |

Siguiente paso: segunda ejecución de W7 sobre `paquete_diseno.md` versión diseno-v2.

## Segunda auditoría (22-nov-2026 · ejecución n8n 98 · paquete diseno-v2, sha `acba874`)

| | 1.ª auditoría (diseno-v1) | 2.ª auditoría (diseno-v2) |
|---|---|---|
| Veredicto | Aprobado con cambios | Aprobado con cambios |
| Altas | 2 | **0** |
| Medias | 7 | 8 (nuevas; ninguna repetida) |
| Bajas | 3 | 4 |

Resumen del auditor: «El diseño v2 resuelve bien los dos riesgos altos de la v1 (duplicidad de envío y baja/exclusión) y apoya los bloqueos críticos en la base de datos, no en el flujo. No se detecta ningún hallazgo alto nuevo».

Ninguno de los 12 hallazgos de la primera auditoría reaparece. Los nuevos son de mayor profundidad (base jurídica por etiqueta, caducidad de propuestas, versión del modelo por propuesta, llamadas nunca iniciadas). Lectura: el auditor tiene un tope de 12 hallazgos y en cada pasada profundiza; lo relevante es que desaparecen las altas y no se repite ningún hallazgo.

Hallazgos de la segunda auditoría: N7 llamadas nunca iniciadas (media) · base jurídica de correos a clientes y exclientes (media) · alerta inmediata de «escalar a dirección» (media) · caducidad de pendientes (media) · criterio verificable del validador y tasa de descarte (media) · versión del modelo y variables por propuesta (media) · diseño del control de riesgo con cuentas clave (media) · asignación y tope de leads (media) · buzón remitente y respuestas (baja) · timeout de Gmail tratado como error reintentable (baja) · encargados de tratamiento (baja) · validador sobre el texto editado por el comercial (baja).
