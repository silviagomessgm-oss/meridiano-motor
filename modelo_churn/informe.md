# Modelo de abandono de anunciantes · Meridiano

Informe final del modelo que estima, para cada anunciante activo, la probabilidad de que abandone en los 210 días
siguientes. Proyecto final del Programa Superior en IA Aplicada a Marketing y Ventas (ESIC). Datos sintéticos del TFP.
Todas las cifras salen de la ejecución del código de `modelo_churn/` (ver «Cómo reproducirlo»). Las decisiones, con quién
las tomó y por qué, están en `registro_decisiones.md`.

## 1. Resumen

- **Modelo elegido:** regresión logística con regularización, entrenada con los datos ampliados (decisión de la alumna).
- **Resultado en el periodo de prueba** (sep-25 y dic-25, solo datos originales): AUC 0,883 (IC 95 %: 0,842–0,920),
  frente a 0,731 ordenando por días sin campaña y 0,518 ordenando por valor de la cuenta. Brier 0,145 (0,251 sin modelo).
  Acierta las 12 cuentas de más riesgo en las dos fechas y el 92 % de las del 25 % de más riesgo.
- **Lo que más pesa:** días sin contacto comercial, tener un pedido firmado pendiente, lo comprado en el mismo periodo
  del año anterior y la tendencia de la facturación.
- **Salida:** `puntuar.py` genera `scores_modelo.csv` (`id_cliente`, `prob_abandono`) para cualquier fecha hasta el
  último dato disponible. Se ejecutará cada semana.

## 2. Datos usados

| | |
|---|---|
| Tablas | `dim_clientes`, `fact_campanas`, `fact_facturacion`, `fact_interacciones`, `oportunidades` (y `cobros_posteriores` en los datos ampliados). `dim_productos` y `contactos` no se usan. |
| Datos originales (`tablas_originales/`) | oct-2023 → sep-2026. Se conservan sin cambios para identificar el periodo de prueba y repetir la valoración. |
| Datos ampliados (`tablas_ampliadas/`) | ene-2020 → 27-nov-2026: los originales intactos más una ampliación sintética hacia atrás y hacia delante (versión 4), con su generador. |
| Datos operativos (`tablas/` y hoja de Google que carga n8n) | Los datos ampliados, con los cobros posteriores ya incorporados en `fact_facturacion` y la antigüedad recalculada al 27-nov-2026. Es lo que usa el resto del sistema. Para el modelo dan exactamente los mismos resultados que `tablas_ampliadas/`. |
| Columnas descartadas | `dim_clientes.antiguedad_meses`, `fact_facturacion.estado` y `dias_retraso`: son una foto del final del periodo y supondrían usar información posterior a la fecha de corte. Se recalculan desde las fechas. |
| Fechas de corte | Fin de trimestre con 12 meses de historia previa y con W terminando antes del 1-sep-2026: 21 cortes (dic-20 → dic-25). |
| Entrenamiento | 19 cortes (dic-20 → jun-25): 1.992 observaciones de 260 anunciantes, 48,7 % de abandono. 15 cortes contienen datos generados (1.515 obs.) y 4 solo originales (477 obs.). |
| Prueba | Los dos últimos cortes, sep-25 y dic-25, solo con datos originales: 251 observaciones de 142 anunciantes, 51,8 % de abandono. 123 de esos anunciantes también aparecen en entrenamiento (en otras fechas). |

**Sobre la ampliación.** La generó la misma herramienta que creó los datos originales, a petición de la alumna, con un
método documentado en `tablas_ampliadas/README.md`. Pasó por cuatro versiones con revisión (`valoracion_datos_ampliados.md`).
En la versión final las distribuciones coinciden con las originales y la calibración de las señales solo usa datos
originales hasta jun-2025, de modo que los cortes de prueba no intervienen. En la validación (cortes mar-25 y jun-25)
mejoró la regresión logística de AUC 0,820 a 0,829 y el árbol de 0,743 a 0,796; en la prueba, la logística entrenada con
datos ampliados supera a la entrenada solo con originales en +0,014 de AUC (IC 95 %: 0,000–0,030).

## 3. Definición de la etiqueta (E2)

Para cada fecha de corte T, con W = (T, T + 210 días] y W′ = el mismo periodo un año antes:

- **Población:** anunciantes con alguna campaña en los 12 meses anteriores a T (meses de calendario).
- **Pérdida total:** compró en W′ y no inicia ninguna campaña en W. («Un año sin comprar» se evalúa dentro de W.)
- **Contracción:** compra en W y en W′, pero factura en W menos del 50 % que en W′.
- **Activo:** el resto. Si no compró ni en W′ ni en W, está fuera de temporada: activo.
- **Abandono = 1** si pérdida total o contracción.
- «Compra» y «factura» = campañas por fecha de emisión e importe (no por fecha de cobro).
- Los anunciantes con menos de un año desde el alta en T **no se usan para entrenar ni evaluar**, pero sí se puntúan.

En el periodo de prueba, 50 de las 251 observaciones son «fuera de temporada» y, por definición, ninguna puede ser
abandono.

## 4. Variables

Todas se calculan solo con datos con fecha igual o anterior a T. Un test automático lo comprueba en cada fecha de corte
de los dos conjuntos de datos: calcula las variables, añade datos inventados posteriores a T (campañas, pedidos, facturas,
cobros, interacciones, propuestas y desenlaces) y verifica que nada cambia; un control comprueba que el test detecta una
fuga deliberada.

| Variable | Definición |
|---|---|
| `recencia_dias` | Días desde la última campaña emitida. |
| `frecuencia_12m` | Nº de campañas en los últimos 12 meses. |
| `antiguedad_meses` | Meses desde el alta. |
| `valor_12m` | Facturación de los últimos 12 meses. |
| `valor_mismo_periodo_anio_anterior` | Facturación en W′ (los mismos 210 días del año anterior; termina antes de T). |
| `tendencia` | (últimos 6 meses − 6 meses anteriores) / máx(6 meses anteriores; 1), acotada a [−1, 1]. |
| `n_familias_12m` | Nº de familias de producto compradas en 12 meses. |
| `ctr_relativo` | Clics reales / clics esperados de sus campañas Digital de 12 meses, con el CTR medio de cada producto hasta T. Sin campañas digitales = sin dato. |
| `cambio_interlocutor_12m` | Cambio de interlocutor en los últimos 12 meses (sí/no). |
| `dias_sin_contacto` | Días desde el último contacto comercial con respuesta (llamada, email, visita o videollamada). |
| `retraso_medio_cobro_12m` | Retraso medio (días tras el vencimiento) de las facturas cobradas en 12 meses. Sin cobros = sin dato. |
| `pedidos_firmados_pendientes` | Pedidos firmados hasta T con campaña aún no emitida. |
| `propuestas_abiertas` | Propuestas enviadas hasta T y sin cerrar en T. |
| `propuestas_perdidas_12m` | Propuestas perdidas o muertas en silencio, cerradas en los 12 meses anteriores. |

Se calculan pero **no entran en el modelo**: reclamación sin resolver (11 casos en los cortes originales de
entrenamiento) y facturas vencidas sin cobrar (sin relación con el abandono). Los datos que faltan se rellenan con la
mediana y una marca de «sin dato», que el modelo también usa.

## 5. Comparación de modelos

Hiperparámetros elegidos con validación temporal dentro de entrenamiento (sin mirar la prueba). Intervalos al 95 % por
bootstrap remuestreando anunciantes (no filas), porque el mismo anunciante aparece en las dos fechas de prueba
(1.000 remuestras, semilla 42). Entrenamiento con los datos ampliados.

| Modelo | AUC (IC 95 %) | AUC sin fuera de temporada (IC 95 %) | Precisión top 12 (sep-25 · dic-25) | Precisión 25 % de más riesgo | Brier |
|---|---|---|---|---|---|
| (a) Valor de la cuenta | 0,518 (0,431–0,599) | 0,437 (0,337–0,531) | 0,42 · 0,58 | 0,55 | 0,257 |
| (b) Días sin campaña | 0,731 (0,659–0,797) | 0,665 (0,573–0,755) | 0,83 · 0,75 | 0,74 | 0,212 |
| **(c) Regresión logística** (C = 1) | **0,883 (0,842–0,920)** | **0,853 (0,801–0,909)** | 1,00 · 1,00 | **0,92** | **0,145** |
| (d) Árbol de 3 niveles | 0,861 (0,818–0,903) | 0,762 (0,705–0,820) | 1,00 · 1,00 | 0,77 | 0,146 |
| (c) entrenada solo con originales (C = 0,1) | 0,869 (0,824–0,909) | — | 1,00 · 1,00 | 0,94 | 0,150 |

Diferencias de AUC emparejadas (mismas remuestras):

| Comparación | Diferencia | IC 95 % |
|---|---|---|
| (c) − (b) | +0,152 | 0,090–0,213 |
| (d) − (b) | +0,130 | 0,071–0,185 |
| (c) − (d) | +0,022 | −0,017–0,061 |
| (c) ampliado − (c) solo originales | +0,014 | 0,000–0,030 |

Calibración de (c) por deciles de probabilidad en la prueba:

| Decil | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |
|---|---|---|---|---|---|---|---|---|---|---|
| Probabilidad media (%) | 1,0 | 8,6 | 16,7 | 25,3 | 39,5 | 52,2 | 61,4 | 70,3 | 86,3 | 96,2 |
| Abandono real (%) | 0 | 8 | 28 | 40 | 32 | 64 | 76 | 80 | 92 | 100 |

## 6. Modelo elegido y por qué

**Regresión logística entrenada con los datos ampliados.** Es la mejor en todas las medidas. Frente al árbol, la
diferencia total no es concluyente (+0,022, IC −0,017–0,061), pero en los casos que de verdad hay que distinguir
(los que compraron el año anterior) la logística ordena mucho mejor (0,853 frente a 0,762): el árbol mete a 121 de los
251 anunciantes de prueba en un mismo grupo con la misma probabilidad. Además da una probabilidad distinta para cada
cuenta, útil para ordenar una lista semanal. Las reglas del árbol (en `punto_control_2.md`) sirven como resumen fácil de
explicar: «compró el año pasado, sin pedido firmado y más de 92 días sin contacto» tuvo un 95 % de abandono en
entrenamiento y un 97 % en prueba.

## 7. Qué variables pesan más

Modelo de producción a fecha 27-nov-2026 (`puntuar.py --detalle`): 22 cortes (dic-20 → mar-26), 2.369 observaciones,
C = 0,1. Variables estandarizadas: «× odds» es el factor por el que se multiplica la razón abandono/permanencia cuando
la variable sube una desviación típica, con el resto igual.

| Variable | Peso | × odds | 1 desviación típica | Lectura comercial |
|---|---|---|---|---|
| Días sin contacto comercial | +0,830 | 2,29 | 76 días | Un cliente al que nadie contacta se va. Es la señal más fuerte. |
| Pedidos firmados pendientes | −0,746 | 0,47 | 0,5 pedidos | Un pedido firmado protege mucho. |
| Compra en el mismo periodo del año anterior | +0,569 | 1,77 | 6.011 € | Cuanto más compró el año pasado, más tiene que mantener para no contar como contracción. |
| Tendencia de la facturación | −0,535 | 0,59 | 0,86 | Si la inversión cae, sube el riesgo. |
| Sin cobros en 12 meses | −0,521 | 0,59 | — | Suelen ser anunciantes de temporada, que la etiqueta no cuenta como abandono. |
| Frecuencia (12 meses) | +0,450 | 1,57 | 3 campañas | Junto con el valor: con la misma facturación, muchas campañas pequeñas indican más riesgo que pocas grandes. |
| Valor (12 meses) | −0,408 | 0,67 | 9.051 € | |
| Propuestas abiertas | −0,302 | 0,74 | 0,6 | Una propuesta en curso protege (efecto reforzado por los datos generados, ver limitaciones). |
| Cambio de interlocutor | +0,276 | 1,32 | — | Un nuevo responsable de marketing es un momento de riesgo. |
| Nº de familias | +0,253 | 1,29 | 0,6 | |
| Propuestas perdidas (12 meses) | +0,244 | 1,28 | 1 | Las propuestas rechazadas anticipan el abandono. |
| CTR relativo | −0,188 | 0,83 | 0,28 | Si sus campañas rinden más que la media de su producto, se queda. |
| Días sin campaña, antigüedad, retraso de cobro | < 0,09 | | | Su información ya la recogen las demás variables. |

Varias variables están muy relacionadas entre sí (frecuencia y valor; días sin campaña y días sin contacto), así que
sus pesos se interpretan en conjunto, no uno a uno.

## 8. Limitaciones

1. **Datos sintéticos.** Todo el caso es ficticio. La ampliación (2020–2023 y sep–nov 2026) se calibró con los datos
   originales: aporta más casos de los mismos patrones, no patrones nuevos. En ella las propuestas abiertas pesan unas
   tres veces más que con solo datos originales (−0,29 frente a −0,06 en el modelo del punto de control 2), y el abandono
   varía más entre cortes (39–61 %) que en los originales (49–53 %).
2. **Pocos anunciantes.** 279 anunciantes distintos en el panel y 142 en la prueba, que además se repiten entre fechas:
   los intervalos son anchos (AUC 0,842–0,920) y diferencias de pocas centésimas entre modelos no son concluyentes.
3. **Señales con pocos casos.** Reclamaciones sin resolver: 11 casos en los cortes originales de entrenamiento; quedan
   fuera del modelo. Las reclamaciones no tienen fecha de resolución: se asume que su resultado se conocía en su fecha.
4. **Parte del acierto viene de la definición.** Los anunciantes fuera de temporada (50 de 251 en prueba) no pueden ser
   abandono y todos los modelos los aciertan. Sin ellos, el AUC del modelo elegido es 0,853.
5. **La precisión entre las 12 cuentas de más riesgo se satura** (1,00 para la logística y el árbol): con unos 125
   anunciantes por fecha y la mitad abandonando, no sirve para distinguir modelos.
6. **Calibración.** El periodo de prueba tuvo más abandono (51,8 %) que el de entrenamiento (48,7 %): en los deciles
   3, 4, 6, 7 y 8 el modelo predice entre 10 y 15 puntos menos de lo real (en el 5, 7 puntos más). En los extremos
   acierta.
7. **Anunciantes nuevos.** Se puntúan con un modelo entrenado sin ellos (24 de los 132 puntuados el 27-nov-2026): su
   probabilidad es menos fiable.
8. **Puntuar después de sep-2026.** El último corte de entrenamiento (mar-26) tiene su resultado en meses generados
   (hasta oct-26). Y la fecha de puntuación nunca puede ser posterior al último dato: `puntuar.py` lo impide.
9. **Riesgo, no efecto.** El modelo dice quién es probable que abandone, no a quién le servirá una llamada. Eso solo lo
   mide el grupo de control.

## 9. Cómo se mide en producción (grupo de control)

1. **Cada semana** n8n carga la hoja de datos en Supabase (W0) y el motor ejecuta `ciclo_semanal.py`, cuyo paso 3 llama a `puntuar.py` con la fecha de corte (el lunes anterior). Los anunciantes que el modelo no puntúa (con 366–540 días sin campaña, que las propuestas todavía consideran) reciben el riesgo de respaldo por señales. La capa de selección elige las
   12 cuentas para el equipo comercial y no repite una cuenta propuesta o en control en los últimos 90 días (decisión de
   la alumna; hoy en `ciclo_semanal.py`).
2. **Grupo de control aleatorio.** De las cuentas que se habrían propuesto, una parte elegida al azar (con semilla
   registrada) no recibe ninguna acción de retención. Es la única forma de separar el efecto de la acción del acierto del
   modelo: si el equipo salva cuentas, el modelo parecería equivocarse en ellas. La proporción del control es una decisión
   pendiente; con 12 cuentas por semana, el grupo crece despacio y harán falta varios trimestres para sacar conclusiones.
3. **A los 210 días** de cada semana se calcula la etiqueta E2 de las cuentas puntuadas y se mide:
   - **efecto de la acción:** abandono de las cuentas contactadas frente al grupo de control;
   - **acierto del modelo:** AUC y calibración por deciles en las cuentas que no recibieron acción (control y no
     seleccionadas), comparados con los de este informe (AUC 0,883; deciles del apartado 5).
4. **Reentrenamiento:** automático en cada ejecución, con todos los cortes de resultado conocido. Conviene revisar
   trimestralmente que los pesos y la regularización elegida no cambian de forma brusca.

## 10. Cómo reproducirlo

```
python -m pytest modelo_churn/tests -q
python -m modelo_churn.control1 --datos tablas --limite-fin-w 2026-09-01 --inicio-originales 2023-10-01
python -m modelo_churn.valorar_ampliacion
python -m modelo_churn.control2 --datos tablas --limite-fin-w 2026-09-01
python modelo_churn/puntuar.py --datos tablas --fecha 2026-11-27 --salida <carpeta> --detalle
```

Entorno: Python 3.13, pandas 3.0.5, scikit-learn 1.9.1 (`requirements.txt`); con las versiones del resto del sistema (pandas 2.2.3, numpy 2.1.3) los resultados son los mismos. Semilla 42. Tests: no fuga de las variables
en todas las fechas de corte de `tablas_originales/` y `tablas/`, no fuga de la puntuación, probabilidades entre 0 y 1, sin
clientes duplicados, columnas exactas, una fila por anunciante activo, resultado idéntico en dos ejecuciones y rechazo de
fechas posteriores al último dato (37 tests).
