# Flujos exportados desde el n8n desplegado

W4 y W6 se construyeron en una fase cuyo generador (`construir_flujos.py` de entonces) se perdió al reemplazarse el contenedor
de desarrollo. Estos JSON son la **fuente de verdad** de esos dos flujos: exportación directa de n8n (menú ⋯ → Download),
22-nov-2026, con todas las correcciones de las auditorías (puerta de datos, escalado, envíos sin confirmar) y W9 como flujo
de errores. Se importan en n8n con «Import from file»; las credenciales se reasignan por nombre.

| Archivo | Flujo | Depende de (Supabase) |
|---|---|---|
| `W4_preparacion_lunes.json` | Lunes 7:00 · leads nuevos y ampliaciones | `ultima_carga()`, `preparar_lunes()`, `propuestas`, `ejecuciones` |
| `W6_balance_lunes.json` | Lunes 8:15 · balance a comerciales y resumen a dirección | `balance_lunes()`, `seguimientos_sin_atender`, `kpi_toques_por_grupo`, `envios_sin_confirmar` |

El resto de flujos (W0–W3, W5, W7–W9) se generan con `construir_flujos.py`.
