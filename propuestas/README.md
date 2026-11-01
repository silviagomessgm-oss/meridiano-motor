# Meridiano · Automatismo de propuestas de retención de anunciantes

Implementa los nodos N01–N07 del proceso FORGEN de churn de anunciantes (v2.0). Cada mes genera, para cada comercial, un **plan de propuestas de retención priorizado por facturación en riesgo**, con la ficha de la cuenta, la acción recomendada y el material preparado. Los datos son **sintéticos** (Meridiano_Datos_v3).

> **El sistema propone; el comercial decide.** Nada se envía al anunciante sin que el comercial lo apruebe, lo revise y lo envíe él mismo.

## Qué hace cada paso

| Nodo | Qué hace |
|---|---|
| N01 · Foto a fecha de corte | Usa solo lo conocido en la fecha de corte: un cobro o un cierre posterior cuentan como pendientes |
| N02 · Variables | Inversión por **campañas** (`id_campana`), tendencia, CTR relativo, contacto, cambio de interlocutor, reclamaciones, cobro, propuestas y **próxima temporada** de compra |
| N03 · Riesgo | **Decisión del equipo: actuar con L2 × valor.** Si existe `data/scores_modelo.csv` (generado por `generar_scores.py` en el repositorio de evaluación), propone acción cuando P(sin campaña) × valor de la cuenta × recuperación > coste, y prioriza por P × valor. Sin puntuaciones, aplica el **respaldo de señales** |
| N04 · Motivo | Rendimiento, cambio de interlocutor, pérdida de contacto, reclamación, presupuesto, cobro o inactividad, con sus evidencias |
| N05 · Plan | Matriz motivo → acción, prioridad por facturación en riesgo, capacidad semanal por comercial, grupo de control (20 % de la banda media, nunca cuentas clave) y revisión de dirección en cuentas clave |
| N06 · Materiales | Agenda de reunión, informe de resultados, reserva anticipada, invitación, guion de llamada… Por plantilla, o con LLM opcional pasando por un **validador** que rechaza cifras que no estén en los datos y cualquier condición económica |
| N07 · Exportación | Excel por comercial, CSV para importar tareas al CRM y log de ejecución (executionHistory) |

**Pausa estacional:** si la temporada habitual del anunciante llega en ≤ 60 días y no hay señales de relación, servicio o rendimiento, no se le trata como un abandono: se le propone una reserva anticipada para su temporada, sin rebajar su prioridad.

## Cómo ejecutarlo en Google Colab

1. En colab.research.google.com: **Archivo → Subir cuaderno** → `notebooks/propuestas_colab.ipynb`.
2. Ejecuta las celdas en orden. La primera pide el zip de este repositorio.
3. Sube `scores_modelo.csv` en la celda 4. Se descarga en la celda 7 del cuaderno de evaluación.
4. Opcional: activa la redacción con LLM introduciendo tu clave de API.
5. La última celda descarga `resultados.zip`.

En local: `pip install -r requirements.txt && pytest -q && python src/propuestas.py`.

## Resultados (`resultados/`)

| Archivo | Contenido |
|---|---|
| `propuestas_retencion.xlsx` | **Plan_por_comercial** (propuestas en orden de prioridad), Aplazados (sin capacidad este mes), Grupo_control, Resumen y Riesgo_todos |
| `crm_tareas.csv` | Tareas listas para importar al CRM, en estado "Pendiente de aprobación" |
| `exec_n02_n03_riesgo.csv` | Variables y riesgo de todos los anunciantes evaluados (historial de ejecución) |
| `log_ejecucion.json` | Identificador, fecha, versión, parámetros, volúmenes y estado de la ejecución |

## Dos tipos de abandono (etiqueta E2)

Cada propuesta indica `tipo_riesgo`:
- **Contracción prevista:** el anunciante sigue comprando (última campaña hace ≤ 120 días), pero su inversión cae más de un 30 %. La acción es un informe de resultados con propuesta de mejora, para volver a hacer crecer la cuenta.
- **Pérdida total prevista:** el resto. La acción depende del motivo (reunión, llamada de reactivación, reserva anticipada…).

Cambio de interlocutor, reclamación y cobro tienen siempre prioridad sobre el tipo de riesgo.

## Validación continua de la etiqueta

El plan de cada comercial incluye cuatro columnas a rellenar al cerrar cada propuesta, con listas cerradas:
- **estado_confirmado_comercial:** Perdido · Redujo mucho · Activo · Pausa: volvió después · No sé.
- **motivo_confirmado.**
- **diagnostico_correcto** (Sí/No), es decir, si el diagnóstico y la propuesta generados (incluido el material redactado con el LLM) eran acertados.
- **comentario_comercial.**

`src/confirmaciones.py` acumula las confirmaciones mes a mes y mide el acuerdo con la etiqueta y con el diagnóstico. Es la señal de feedback de Evolve.

## Límites conocidos (deuda técnica de Review #1)

- **El respaldo de señales es provisional.** Sus pesos son una heurística transparente. Se sustituye por el modelo de cálculo cuando la regla de abandono esté validada (evaluación en Colab) y el modelo supere su precision@k.
- **No hay modelo de venta cruzada** todavía: el producto sugerido sale de reglas trazables (mejor CTR de su familia o producto habitual de temporada).
- El cambio de interlocutor depende de que se registre en el CRM.
- El 30 % de las bajas desaparece de golpe y no es detectable con señales previas.

## Tests (`pytest -q`)

- **Sin fuga temporal:** los datos posteriores al corte no cambian ninguna variable; cobros y cierres posteriores cuentan como pendientes.
- **Límites:** capacidad por comercial, control solo en banda media y nunca en cuentas clave, prioridad por facturación en riesgo, una acción por cuenta y asignación reproducible.
- **Golden Dataset:** cambio de interlocutor en cuenta clave → reunión con revisión de dirección; pausa estacional → reserva anticipada; CTR bajo → motivo de rendimiento; sin campañas medibles → nunca se menciona el CTR.
- **Validador del LLM:** rechaza cifras inventadas y condiciones económicas; ningún material menciona descuentos ni "riesgo".
