# Valoración de los datos ampliados · utilidad para predecir los datos originales (generado automáticamente)

Validación: cortes originales 2025-03-31, 2025-06-30 (239 obs., 134 anunciantes, 49.8 % de abandono). Cortes de prueba (sep-25, dic-25) sin tocar. Variables: las del modelo. Semilla 42.

## Observaciones de entrenamiento por variante

| entrenamiento           |   2025-03-31 |   2025-06-30 |
|:------------------------|-------------:|-------------:|
| A. solo originales      |          238 |          359 |
| B. ampliado completo    |         1742 |         1863 |
| C. solo generados       |         1504 |         1504 |
| D. ampliado sin costura |         1068 |         1189 |

## Resultados

| modelo              | entrenamiento           |   AUC |   precisión top 12 |   Brier |
|:--------------------|:------------------------|------:|-------------------:|--------:|
| regresión logística | A. solo originales      | 0.813 |              1.000 |   0.190 |
| regresión logística | B. ampliado completo    | 0.831 |              1.000 |   0.169 |
| regresión logística | C. solo generados       | 0.831 |              1.000 |   0.170 |
| regresión logística | D. ampliado sin costura | 0.829 |              1.000 |   0.169 |
| árbol (3 niveles)   | A. solo originales      | 0.716 |              0.708 |   0.234 |
| árbol (3 niveles)   | B. ampliado completo    | 0.799 |              1.000 |   0.165 |
| árbol (3 niveles)   | C. solo generados       | 0.810 |              1.000 |   0.164 |
| árbol (3 niveles)   | D. ampliado sin costura | 0.815 |              1.000 |   0.167 |

## Diferencia de AUC frente a entrenar solo con originales

| modelo              | comparación   |   dif. AUC | IC 95 % (bootstrap por anunciante)   |
|:--------------------|:--------------|-----------:|:-------------------------------------|
| regresión logística | B. − A        |     +0.018 | [-0.007, +0.044]                     |
| regresión logística | C. − A        |     +0.018 | [-0.015, +0.050]                     |
| regresión logística | D. − A        |     +0.016 | [-0.006, +0.039]                     |
| árbol (3 niveles)   | B. − A        |     +0.083 | [+0.025, +0.142]                     |
| árbol (3 niveles)   | C. − A        |     +0.094 | [+0.031, +0.156]                     |
| árbol (3 niveles)   | D. − A        |     +0.099 | [+0.025, +0.166]                     |

## Diagnóstico 0 · Fidelidad de las distribuciones (filas originales frente a añadidas)

| parte    |   campañas |   importe mediano (€) |   descuento medio (%) |   % Digital |   retraso medio de cobro (días) |   % ampliaciones ganadas |
|:---------|-----------:|----------------------:|----------------------:|------------:|--------------------------------:|-------------------------:|
| añadida  |       1501 |                  1088 |                     8 |        65   |                            10.4 |                     48.4 |
| original |       1432 |                  1158 |                     8 |        67.1 |                             9.7 |                     53.6 |

|                                                                  |   valor |
|:-----------------------------------------------------------------|--------:|
| anunciantes de dim_clientes sin campañas en los datos originales |      35 |
| … de ellos con alguna campaña en la ampliación                   |      35 |
| anunciantes con primera campaña anterior al alta                 |       0 |
| facturas originales sin cobrar al final de la ampliación         |       9 |
| … vencidas antes del 1-oct-2026                                  |       0 |

## Diagnóstico 1 · Abandono por corte según el origen del anunciante (efecto costura)

|            |   obs. anunciante nuevo (C0321+) |   obs. anunciante original |   % abandono anunciante nuevo (C0321+) |   % abandono anunciante original |   % abandono total |
|:-----------|---------------------------------:|---------------------------:|---------------------------------------:|---------------------------------:|-------------------:|
| 2020-12-31 |                               43 |                         43 |                                     84 |                               37 |               60.5 |
| 2021-03-31 |                               33 |                         50 |                                     76 |                               40 |               54.2 |
| 2021-06-30 |                               32 |                         54 |                                     56 |                               44 |               48.8 |
| 2021-09-30 |                               26 |                         56 |                                     54 |                               36 |               41.5 |
| 2021-12-31 |                               23 |                         62 |                                     48 |                               47 |               47.1 |
| 2022-03-31 |                               17 |                         78 |                                     59 |                               49 |               50.5 |
| 2022-06-30 |                               16 |                         84 |                                     44 |                               54 |               52   |
| 2022-09-30 |                               17 |                         84 |                                     53 |                               54 |               53.5 |
| 2022-12-31 |                               21 |                         91 |                                     52 |                               51 |               50.9 |
| 2023-03-31 |                               19 |                         91 |                                     53 |                               49 |               50   |
| 2023-06-30 |                               19 |                         88 |                                     79 |                               35 |               43   |
| 2023-09-30 |                               23 |                         86 |                                     91 |                               30 |               43.1 |
| 2023-12-31 |                               25 |                         93 |                                    100 |                               30 |               44.9 |
| 2024-03-31 |                               24 |                         96 |                                    100 |                               38 |               50   |
| 2024-06-30 |                              nan |                        110 |                                    nan |                               36 |               36.4 |
| 2024-09-30 |                              nan |                        115 |                                    nan |                               51 |               51.3 |
| 2024-12-31 |                              nan |                        123 |                                    nan |                               52 |               52   |
| 2025-03-31 |                              nan |                        121 |                                    nan |                               50 |               50.4 |
| 2025-06-30 |                              nan |                        118 |                                    nan |                               49 |               49.2 |
| 2025-09-30 |                              nan |                        123 |                                    nan |                               50 |               50.4 |
| 2025-12-31 |                              nan |                        128 |                                    nan |                               53 |               53.1 |

## Diagnóstico 2 · Propuestas abiertas según la etiqueta (cortes hasta jun-25)

| parte             |   % con propuesta abierta · sigue |   % con propuesta abierta · abandona |
|:------------------|----------------------------------:|-------------------------------------:|
| cortes generados  |                              35.7 |                                 20   |
| cortes originales |                              27.7 |                                 22.3 |

## Diagnóstico 3 · Pesos de la regresión logística (variables estandarizadas; entrenada con cortes anteriores a 2025-06-30)

|                                   |   A. solo originales |   B. ampliado completo |
|:----------------------------------|---------------------:|-----------------------:|
| tendencia                         |                -1.11 |                  -0.62 |
| pedidos_firmados_pendientes       |                -0.76 |                  -0.75 |
| valor_12m                         |                -0.66 |                  -0.28 |
| sin dato: retraso_medio_cobro_12m |                -0.63 |                  -0.79 |
| recencia_dias                     |                -0.59 |                   0.09 |
| ctr_relativo                      |                -0.43 |                  -0.22 |
| antiguedad_meses                  |                -0.17 |                  -0.04 |
| propuestas_abiertas               |                -0.1  |                  -0.21 |
| sin dato: ctr_relativo            |                -0.03 |                   0.01 |
| retraso_medio_cobro_12m           |                 0.1  |                  -0.05 |
| propuestas_perdidas_12m           |                 0.28 |                   0.06 |
| n_familias_12m                    |                 0.3  |                   0.16 |
| cambio_interlocutor_12m           |                 0.36 |                   0.2  |
| frecuencia_12m                    |                 0.46 |                   0.64 |
| valor_mismo_periodo_anio_anterior |                 0.58 |                   0.43 |
| dias_sin_contacto                 |                 0.91 |                   1.12 |
