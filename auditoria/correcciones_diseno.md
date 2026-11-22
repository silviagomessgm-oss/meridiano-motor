# Correcciones tras la auditoría del diseño (W7 · tipo `diseno`)

Auditoría de referencia: ejecución n8n 95, modelo auditor `claude-fable-5-1`, paquete `diseno-v1`. Veredicto: **aprobado con cambios** (2 altas, 7 medias, 3 bajas). Evidencia completa en la tabla `auditorias` de Supabase.

| Hallazgo | Gravedad | Corrección aplicada | Dónde | Prueba |
|---|---|---|---|---|
| **H2** · Correos sin baja, sin lista de exclusión ni plazo de conservación | Alta | Pie con enlace de baja en cada correo (W5, HTML con la identidad de Meridiano); página de baja en dos pasos (W8); lista `exclusiones` con bloqueo en la base al aprobar y al enviar; baja desde el panel (`baja_panel`); plazo de conservación y vista `conservacion_vencida` | `supabase/bajas.sql`, W5, W8, panel, `auditoria/politica_correo.md` | 6 tests; W8 probado en n8n contra Supabase; prueba de principio a fin en el buzón de demostración |
| **H1** · Envío (N6) no idempotente; transición a «enviando» sin documentar | Alta | «Enviando» es el estado derivado de una propuesta aprobada por correo. W5 reserva cada propuesta de forma atómica (`reservar_envios`) antes de llamar a Gmail y solo envía las que ha reservado; sin reserva la base no permite marcarla enviada; al volver a aprobar se limpia la reserva. Una reserva sin resultado no se reenvía sola (como mucho un envío): aparece en `envios_sin_confirmar` y dirección la libera con `liberar_envio` tras comprobar Gmail. Además, los bloqueos se registran en una rama propia (antes se perdían si no había nada que enviar) | `supabase/envios.sql`, W5 | 4 tests de base de datos y 4 de W5 |

Pendientes, en este orden: H7, H8, H3 → H6, H5 → H9, H4 y bajas (H10–H12). Al terminar se actualiza `paquete_diseno.md` y se vuelve a pasar W7.
