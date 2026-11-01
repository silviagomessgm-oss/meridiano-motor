# Meridiano · Churn de anunciantes en producción (sobre tablas, sin CRM)

Paquete único para ejecutar **cada martes** el proceso FORGEN de churn de anunciantes. Como el caso es **ficticio y no hay CRM**, las tablas son el sistema de registro.

**Dos formas de ejecutarlo:**
- **Producción:** **n8n Cloud** (carga semanal de las tablas desde Google Sheets los lunes, ciclo de los martes, conexión con Claude, alertas y recordatorios) + motor Python en GitHub Actions (lo lanza n8n y espera su resultado) + **Supabase** (base de datos y trazabilidad) + **panel en Lovable**, que escribe en Supabase solo a través de `accion_panel()`, con historial de eventos y de versiones del material. Ver [`DESPLIEGUE.md`](DESPLIEGUE.md).
- **Evaluación y demostración:** el mismo ciclo sobre `tablas/*.csv` en Google Colab (`notebooks/ciclo_semanal_colab.ipynb`).

## El ciclo semanal (`ciclo_semanal.py`, martes por la mañana; corte el lunes anterior)

| Paso | Qué hace | Nodos FORGEN |
|---|---|---|
| 1 | Comprueba las tablas: columnas, integridad entre campañas y facturas, duplicados | N01 |
| 1b | Si hay un plan devuelto por los comerciales, registra sus confirmaciones en `historico/` | N07 |
| 2 | **Validación automática de E2:** compara E2 con lo confirmado por los comerciales cuando se cierran las ventanas de 210 días. Con ≥ 30 casos y un acuerdo < 70 %, vuelve sola a la regla A | N08 · Govern |
| 3 | Puntuaciones **L2** con la etiqueta vigente (E2 o A) | N02–N03 |
| 4 | **Propuestas:** las 12 acciones de la semana de mayor valor esperado (4 por comercial), sin repetir cuentas propuestas o en control en los últimos 90 días, plan por comercial, tipo de riesgo (contracción o pérdida total), grupo de control y columnas de confirmación | N04–N07 |
| 5 | **Cuadro de mando** en Excel: etiqueta vigente, churn E2, plan de la semana y confirmaciones | Govern |

Resultados en `salidas/<fecha_corte>/`: `propuestas_retencion.xlsx` (plan por comercial, con desplegables de confirmación), `crm_tareas.csv` (lista de tareas), `scores_modelo.csv`, `estado_etiqueta.json` y `cuadro_de_mando.xlsx`.

## Cómo se usa cada semana

1. **Actualizar las tablas** de `tablas/` con los datos de la semana (mismas columnas). Las tablas son la única fuente.
2. **Subir el histórico** de confirmaciones de meses anteriores (`historico/confirmaciones_historico.csv`), si existe.
3. **Ejecutar el ciclo** con la fecha de corte (el lunes) y, si lo hay, el plan devuelto por los comerciales.
4. **Repartir** el plan de `propuestas_retencion.xlsx` (una fila por propuesta; filtro por comercial).
5. Cada comercial **rellena las columnas de confirmación** al cerrar cada propuesta y devuelve el Excel para el ciclo siguiente.
6. **Descargar** `salidas/` e `historico/` (Colab no guarda nada entre sesiones).

## Simulación para la demostración

`simular_confirmaciones.py` **imita** las respuestas de los comerciales a partir de lo que ocurrió en las tablas, con un porcentaje de acierto configurable. **Solo sirve para demostrar que el circuito funciona.** El acuerdo que se obtiene viene dado por construcción (depende del acierto elegido) y **no valida E2**. Con tres semanas simuladas (36 confirmaciones): con acierto 0,8, el automatismo da E2 por validada (75,0 %); con 0,4, vuelve solo a la regla A (36,1 %). Ambos caminos están cubiertos por los tests.

## Estructura

```
tablas/                 sistema de registro (datos v3 en CSV)
historico/              confirmaciones acumuladas de los comerciales
ciclo_semanal.py        orquestador del ciclo
simular_confirmaciones.py   simulación para el TFG
evaluacion/             etiqueta E2, validación automática, modelo L2 (del repositorio meridiano-evaluacion-churn, commit 6d4ed30)
propuestas/             automatismo de propuestas N01–N07 (del repositorio meridiano-propuestas-retencion, commit ff9a24e)
notebooks/ciclo_semanal_colab.ipynb
motor/                  ejecutar_ciclo.py (GitHub Actions), servicio.py, sync_supabase.py y app.py (alternativa HTTP)
supabase/schema.sql     esquema, RLS, trazabilidad (eventos y versiones), accion_panel() y vista del plan vigente
despliegue/             preparar_hoja_datos.py (hoja de Google Sheets) y generar_contactos.py (contactos ficticios)
.github/workflows/motor.yml   acción de GitHub que ejecuta el motor
n8n/                    flujos W0 (carga de los lunes), W1 (martes), W2 (alertas de cierre) y W3 (recordatorio), importables y código de los nodos (codigo/*.js)
lovable/PROMPT_LOVABLE.md   especificación del panel comercial
tests/                  prueba de extremo a extremo
```

Las decisiones y la evaluación que justifican cada pieza están en los repositorios de origen y en el registro de decisiones del proyecto.
