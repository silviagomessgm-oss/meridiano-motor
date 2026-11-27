# Valoración de los datos ampliados · utilidad para predecir los datos originales (generado automáticamente)

Validación: cortes originales 2025-03-31, 2025-06-30 (239 obs., 134 anunciantes, 49.8 % de abandono). Cortes de prueba (sep-25, dic-25) sin tocar. Variables: las del modelo. Semilla 42.

## Observaciones de entrenamiento por variante

| entrenamiento           |   2025-03-31 |   2025-06-30 |
|:------------------------|-------------:|-------------:|
| A. solo originales      |          238 |          359 |
| B. ampliado completo    |         1712 |         1833 |
| C. solo generados       |         1474 |         1474 |
| D. ampliado sin costura |         1062 |         1183 |

## Resultados

| modelo              | entrenamiento           |   AUC |   precisión top 12 |   Brier |
|:--------------------|:------------------------|------:|-------------------:|--------:|
| regresión logística | A. solo originales      | 0.816 |              1.000 |   0.187 |
| regresión logística | B. ampliado completo    | 0.835 |              1.000 |   0.167 |
| regresión logística | C. solo generados       | 0.831 |              1.000 |   0.168 |
| regresión logística | D. ampliado sin costura | 0.832 |              1.000 |   0.168 |
| árbol (3 niveles)   | A. solo originales      | 0.727 |              0.875 |   0.234 |
| árbol (3 niveles)   | B. ampliado completo    | 0.792 |              1.000 |   0.165 |
| árbol (3 niveles)   | C. solo generados       | 0.807 |              1.000 |   0.164 |
| árbol (3 niveles)   | D. ampliado sin costura | 0.810 |              1.000 |   0.169 |

## Diferencia de AUC frente a entrenar solo con originales

| modelo              | comparación   |   dif. AUC | IC 95 % (bootstrap por anunciante)   |
|:--------------------|:--------------|-----------:|:-------------------------------------|
| regresión logística | B. − A        |     +0.019 | [-0.011, +0.049]                     |
| regresión logística | C. − A        |     +0.015 | [-0.021, +0.051]                     |
| regresión logística | D. − A        |     +0.016 | [-0.011, +0.043]                     |
| árbol (3 niveles)   | B. − A        |     +0.065 | [+0.010, +0.122]                     |
| árbol (3 niveles)   | C. − A        |     +0.080 | [+0.021, +0.135]                     |
| árbol (3 niveles)   | D. − A        |     +0.083 | [+0.013, +0.145]                     |

## Diagnóstico 0 · Fidelidad de las distribuciones (filas originales frente a añadidas)

| parte    |   campañas |   importe mediano (€) |   descuento medio (%) |   % Digital |   retraso medio de cobro (días) |   % ampliaciones ganadas |
|:---------|-----------:|----------------------:|----------------------:|------------:|--------------------------------:|-------------------------:|
| añadida  |       1534 |                  1098 |                     8 |        65.1 |                            10.5 |                     54.6 |
| original |       1432 |                  1158 |                     8 |        67.1 |                             9.6 |                     53.6 |

|                                                                  |   valor |
|:-----------------------------------------------------------------|--------:|
| anunciantes de dim_clientes sin campañas en los datos originales |      35 |
| … de ellos con alguna campaña en la ampliación                   |       0 |
| anunciantes con primera campaña anterior al alta                 |      16 |
| facturas originales sin cobrar al final de la ampliación         |      61 |
| … vencidas antes del 1-oct-2026                                  |       9 |

## Diagnóstico 1 · Abandono por corte según el origen del anunciante (efecto costura)

|            |   obs. anunciante nuevo (C0321+) |   obs. anunciante original |   % abandono anunciante nuevo (C0321+) |   % abandono anunciante original |   % abandono total |
|:-----------|---------------------------------:|---------------------------:|---------------------------------------:|---------------------------------:|-------------------:|
| 2020-12-31 |                               51 |                         34 |                                     71 |                               26 |               52.9 |
| 2021-03-31 |                               45 |                         44 |                                     64 |                               36 |               50.6 |
| 2021-06-30 |                               42 |                         46 |                                     62 |                               39 |               50   |
| 2021-09-30 |                               33 |                         45 |                                     64 |                               36 |               47.4 |
| 2021-12-31 |                               31 |                         52 |                                     52 |                               42 |               45.8 |
| 2022-03-31 |                               30 |                         63 |                                     57 |                               44 |               48.4 |
| 2022-06-30 |                               28 |                         72 |                                     61 |                               50 |               53   |
| 2022-09-30 |                               31 |                         72 |                                     61 |                               50 |               53.4 |
| 2022-12-31 |                               28 |                         77 |                                     64 |                               47 |               51.4 |
| 2023-03-31 |                               29 |                         75 |                                     79 |                               44 |               53.8 |
| 2023-06-30 |                               23 |                         75 |                                     74 |                               28 |               38.8 |
| 2023-09-30 |                               23 |                         77 |                                     87 |                               22 |               37   |
| 2023-12-31 |                               21 |                         86 |                                     95 |                               24 |               38.3 |
| 2024-03-31 |                               18 |                         95 |                                    100 |                               37 |               46.9 |
| 2024-06-30 |                               18 |                        110 |                                    100 |                               36 |               45.3 |
| 2024-09-30 |                              nan |                        115 |                                    nan |                               51 |               51.3 |
| 2024-12-31 |                              nan |                        123 |                                    nan |                               52 |               52   |
| 2025-03-31 |                              nan |                        121 |                                    nan |                               50 |               50.4 |
| 2025-06-30 |                              nan |                        118 |                                    nan |                               49 |               49.2 |
| 2025-09-30 |                              nan |                        123 |                                    nan |                               50 |               50.4 |
| 2025-12-31 |                              nan |                        128 |                                    nan |                               53 |               53.1 |

## Diagnóstico 2 · Propuestas abiertas según la etiqueta (cortes hasta jun-25)

| parte             |   % con propuesta abierta · sigue |   % con propuesta abierta · abandona |
|:------------------|----------------------------------:|-------------------------------------:|
| cortes generados  |                              40.5 |                                 15.7 |
| cortes originales |                              27.7 |                                 22.3 |

## Diagnóstico 3 · Pesos de la regresión logística (variables estandarizadas; entrenada con cortes anteriores a 2025-06-30)

|                                   |   A. solo originales |   B. ampliado completo |
|:----------------------------------|---------------------:|-----------------------:|
| tendencia                         |                -1.11 |                  -0.59 |
| pedidos_firmados_pendientes       |                -0.77 |                  -0.77 |
| valor_12m                         |                -0.66 |                  -0.16 |
| sin dato: retraso_medio_cobro_12m |                -0.63 |                  -0.79 |
| recencia_dias                     |                -0.6  |                   0.07 |
| ctr_relativo                      |                -0.4  |                  -0.15 |
| antiguedad_meses                  |                -0.18 |                  -0    |
| propuestas_abiertas               |                -0.1  |                  -0.4  |
| sin dato: ctr_relativo            |                -0.04 |                  -0.02 |
| retraso_medio_cobro_12m           |                 0.11 |                   0.05 |
| propuestas_perdidas_12m           |                 0.27 |                  -0.11 |
| n_familias_12m                    |                 0.29 |                   0.21 |
| cambio_interlocutor_12m           |                 0.36 |                   0.13 |
| frecuencia_12m                    |                 0.46 |                   0.56 |
| valor_mismo_periodo_anio_anterior |                 0.58 |                   0.4  |
| dias_sin_contacto                 |                 0.91 |                   1.08 |
