# Meridiano · Evaluación de la regla de abandono de anunciantes

Repositorio para evaluar, con datos y de forma reproducible, qué regla de etiquetado de abandono usar antes de construir el modelo de churn de anunciantes del TFG (metodología FORGEN). Los datos son **sintéticos**.

## Qué decide

La definición de abandono del proyecto ("210 días sin nueva orden") solo estaba pensada para clientes con un ciclo de compra inferior a 150 días. Aquí se comparan dos reglas para **todos** los anunciantes:

| Regla | Abandono si… |
|---|---|
| **A** | han pasado más de 210 días desde su última actividad |
| **B** | han pasado más de MAX(210; 1,5 × su ciclo mediano de compra) días |

Decisiones ya cerradas: el ciclo de compra se mide entre **inicios de campaña** (`id_campana`), no entre filas de orden.

## Cómo se evita decidir por intuición

1. **El criterio se fija antes de ejecutar**, en `config/criterio.json`: F1 como métrica principal, precisión mínima de 0,80 y desempate por menor retraso de detección. El historial de git demuestra que no se ajustó después de ver resultados.
2. **Backtest sin fuga de información**: en cada uno de los 9 cortes trimestrales (sep-2024 → sep-2026) solo se usan datos anteriores al corte.
3. **Verdad externa**: se compara con la baja real de `data/validacion/aux_ground_truth.csv`, que **nunca** se usa como variable de entrada.
4. **Tests** (`tests/`) que comprueban la lógica de las reglas y la ausencia de fuga temporal.
5. **Ejecución independiente**: GitHub Actions o Google Colab, no quien diseñó el proceso (principio FORGEN: quien construye no audita).

### Dos definiciones de "abandono real"

La fecha de baja del archivo de validación es un momento latente que suele llegar meses después de la última compra. Por eso se evalúan dos verdades; la principal se indica en la configuración:

- **V1 · baja registrada**: el anunciante está de baja a fecha T si `fecha_baja_real` ≤ T.
- **V2 · última compra ya realizada** (principal): el anunciante tiene baja real y no vuelve a comprar después de T. Es lo que una regla basada en inactividad puede detectar.

## Iteración 2 (25-oct-2026)

La iteración 1 terminó **sin ganadora**: ninguna regla basada solo en días sin compra alcanzó la precisión mínima de 0,80 (máximo de la rejilla: 0,47). Además, el archivo de validación da por activos a anunciantes que no vuelven a comprar en años. El equipo decidió, **antes de volver a ejecutar**:

1. **Verdad principal observable** (`V3_sin_campana_210d`): el anunciante no inicia ninguna campaña en los 210 días siguientes al corte. Es un hecho medible en los datos. V1 y V2 quedan como controles. Solo se usan los 6 cortes con 210 días observables después.
2. **Reglas con señales**: S1 (210 días sin actividad y al menos 1 señal) y S2 (al menos 2 señales), frente a A y B. Señales a fecha de corte: CTR bajo, cambio de interlocutor, más de 90 días sin contacto, reclamación sin resolver y factura vencida. La caída de inversión se calcula, pero no cuenta: con 210 días sin actividad es verdadera por construcción (corrección previa a la ejecución, en su propio commit).
3. **Decisión por valor neto esperado** en tres escenarios de coste de la acción y tasa de recuperación. Si la ganadora del escenario central no lo es en los tres, la decisión se declara sensible a los supuestos.

El cambio está en el historial de git: el commit de la iteración 2 es anterior a cualquier ejecución con este criterio.

## Iteración 3 (25-oct-2026)

Se añade la candidata **C · BTYD P(vivo) < 0,5**, propuesta por el equipo. Es un modelo "Buy 'Til You Die" (MBG/NBD) que estima para cada anunciante la probabilidad de seguir activo a partir de **su propia** frecuencia de campañas y del tiempo que lleva sin actividad. Se ajusta en cada corte solo con datos anteriores. El criterio de decisión no cambia respecto a la iteración 2. El módulo `src/btyd.py` se valida con datos simulados de parámetros conocidos (`tests/`). Limitación conocida: el modelo supone un ritmo de compra estable y no recoge la estacionalidad. **Control de identificabilidad:** si los datos no determinan los parámetros del modelo (óptimo en el borde de la búsqueda), la candidata C se excluye de la decisión y `decision.md` lo explica. En la prueba de construcción ocurrió en todos los cortes; la ejecución independiente debe confirmarlo.

## Iteración 4 (25-oct-2026)

La iteración 3 dio como ganadora la regla A, pero sensible a los supuestos. El equipo decidió evaluar antes modelos de **P(Activo)**: cada anunciante tiene una probabilidad de seguir activo, en lugar de un "abandona o no".

| Candidata | Qué hace |
|---|---|
| **P1 · ritmo propio** | Probabilidad de que un anunciante activo estuviera tanto tiempo sin comprar a su ritmo habitual. Con pocas compras, el ritmo se completa con el de su sector (peso de 1 compra) |
| **L1 · logística R + F + T** | Aprende del histórico qué recencia, frecuencia y antigüedad terminan sin campaña en 210 días |
| **L2 · L1 + señales** | Añade CTR bajo, cambio de interlocutor, falta de contacto, reclamación, factura vencida y caída de inversión |

L1 y L2 marcan a un anunciante cuando **P(sin campaña) × valor de su cuenta × tasa de recuperación > coste de la acción** (escenario central): es la regla de decisión que se deriva directamente del criterio de valor neto, sin umbral arbitrario.

**Validación temporal.** Todas las reglas, también A, B, S1 y S2, se evalúan en los mismos cortes de prueba (jun, sep y dic de 2025). Cada modelo se entrena solo con cortes cuyo resultado ya se conocía en la fecha de prueba. Se añade `calidad_probabilidades.csv` (Brier y AUC) como información; no decide.

## Decisión final y producción (25-oct-2026)

Tras la iteración 4, el equipo decide **separar medir y actuar**:
- **Medir** el churn (KPIs, cierre de casos) con la **regla A**: un anunciante ha abandonado si lleva 210 días sin nueva campaña. Es simple, estable y explicable.
- **Actuar** con **L2 × valor de la cuenta**: el automatismo de propuestas marca a quien cumple P(sin campaña) × valor × recuperación > coste, prioriza por P × valor y se limita a la capacidad del equipo.

`src/generar_scores.py` (configurado en `config/produccion.json`) entrena L2 con los 6 cortes de resultado conocido, **sin usar el archivo de validación**, y genera `resultados/scores_modelo.csv` a 30-sep-2026.

## Iteración 5 · modelo a medida (25-oct-2026)

Propuesta del equipo: **coger lo mejor de cada enfoque**. Como la capacidad comercial es la restricción real (48 acciones al mes), aquí solo deciden reglas que eligen **las 48 acciones de mayor valor esperado** en cada corte:

| Candidata | Qué combina |
|---|---|
| **L3a·48 · a medida con contacto** | R, F, T (L1) + silencio relativo a su propio ritmo (P1) + señales (S1, L2) + tendencia y CTR continuos + nº de familias y producto de compromiso + tamaño + temporada en ≤ 60 días + valor de la cuenta + días sin contacto |
| **L3b·48 · a medida sin contacto** | Igual que L3a, pero sin variables de contacto: el contacto lo controla el propio proceso y la señal se pierde si el automatismo hace llamar a todos |
| L2·48 | Modelo de producción actual |
| VALOR·48 | Solo el valor de la cuenta, sin modelo (referencia registrada de antemano) |
| A·48 | Inactivos más de 210 días, ordenados por valor |

Si un modelo L3 gana de forma robusta, sustituye a L2 en `config/produccion.json`. Se añade `coeficientes_por_corte.csv` para ver qué aporta cada variable.

## Estado actual (25-oct-2026): E2 en producción con validación automática

- **E2 es la etiqueta de abandono de producción** por decisión del equipo. `generar_scores.py` entrena L2 con E2 (pérdida total o contracción).
- **Validación automática** (`src/validacion_automatica.py`): compara E2 con el estado que confirman los comerciales cuando se cierra la ventana de 210 días de cada propuesta. Con al menos 30 casos y un acuerdo inferior al 70 %, escribe `estado_etiqueta.json` con la etiqueta A y la producción vuelve sola a la regla A.

## Etiqueta E2 y su validación (25-oct-2026)

Definición del equipo, registrada en `config/etiqueta.json` antes de calcularla. Con W = los 210 días siguientes al corte y W' = el mismo periodo un año antes:

| Tipo | Cuándo |
|---|---|
| **Pérdida total** | Compró en W' y no inicia campaña en W (**se salta su temporada**), o pasa **un año entero sin comprar** |
| **Contracción** | Compra en W y en W', pero factura **menos del 50 %** que en W' |
| **Activo** | El resto. Si no compró en W' ni compra en W, está fuera de temporada: **activo hasta su temporada** |

Anunciantes con menos de 1 año de historial: regla A. Validación:
1. **Muestra ciega** de 60 anunciantes (`muestra_comerciales.xlsx`, una hoja por comercial, 15 casos compartidos por los tres). Se acepta con un **acuerdo ≥ 70 %**. La clave va aparte y no se entrega. `src/evaluar_muestra.py` calcula el acuerdo y el kappa entre comerciales.
2. **Confirmación continua:** cada comercial confirma el estado real del cliente al cerrar la propuesta generada por el automatismo (repositorio de propuestas).
3. **Control:** reactivación posterior de las pérdidas totales y archivo de validación.

## Cómo ejecutarlo

### Opción 1 · GitHub Actions
1. Crea un repositorio en GitHub y sube todo el contenido de esta carpeta.
2. Pestaña **Actions** → *Evaluar regla de abandono* → **Run workflow** (también se ejecuta en cada push a `main`).
3. La decisión aparece en el resumen de la ejecución; los resultados completos, en el artefacto `resultados-evaluacion`.

### Opción 2 · Google Colab
En colab.research.google.com: Archivo → Subir cuaderno → `evaluacion_colab.ipynb`. Ejecuta las celdas en orden; la primera pide el zip del repositorio.

### Opción 3 · En local
```bash
pip install -r requirements.txt
pytest -q
python src/evaluar_umbral_abandono.py --datos data --config config/criterio.json --salida resultados
```

## Resultados que genera (`resultados/`)

| Archivo | Contenido |
|---|---|
| `decision.md` | Regla ganadora según el criterio fijado, o aviso de que ninguna lo cumple |
| `resumen.csv` | Precisión, recall, F1 y retraso de detección por regla y definición de verdad |
| `por_segmento.csv` | Lo mismo por segmento: ciclo < 150, ciclo ≥ 150, una sola campaña |
| `por_corte.csv` | Estabilidad de las métricas en cada corte |
| `sensibilidad.csv` | Rejilla de umbrales fijos (150–365 días) y factores (1,0–3,0) |
| `panel_backtest.csv` | Detalle por anunciante y corte, para auditar cualquier cifra |
| `resultados_evaluacion.xlsx` | Las cuatro primeras tablas en Excel |

**Cómo leerlo:** la precisión indica qué parte de las bajas que marca la regla son reales; si es baja, la etiqueta confundiría pausas estacionales con abandonos. El recall indica qué parte de las bajas reales detecta. El retraso es la diferencia en días entre la detección y la baja real.

## Si ninguna regla cumple el criterio

El script **no elige ganadora**. La salida correcta es revisar el criterio o las reglas con el equipo, registrar el cambio en `config/criterio.json` con un commit que explique el motivo, y volver a ejecutar.

## Estructura

```
config/criterio.json             criterio de decisión (fijar antes de ejecutar)
data/fact_campanas.csv           órdenes corregidas (Meridiano_Datos_v3), con id_campana
data/dim_clientes.csv            anunciantes
data/validacion/                 verdad de referencia: SOLO validación
src/evaluar_umbral_abandono.py   modelo de evaluación
tests/test_regla.py              tests de la lógica
notebooks/evaluacion_colab.ipynb ejecución en Colab
.github/workflows/evaluar.yml    ejecución en GitHub Actions
```
