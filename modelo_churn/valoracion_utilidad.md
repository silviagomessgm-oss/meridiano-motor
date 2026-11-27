# Valoración de los datos ampliados · utilidad para predecir los datos originales (generado automáticamente)

Validación: cortes originales 2025-03-31, 2025-06-30 (239 obs., 134 anunciantes, 49.8 % de abandono). Cortes de prueba (sep-25, dic-25) sin tocar. Variables: las del modelo. Semilla 42.

## Observaciones de entrenamiento por variante

| entrenamiento           |   2025-03-31 |   2025-06-30 |
|:------------------------|-------------:|-------------:|
| A. solo originales      |          238 |          359 |
| B. ampliado completo    |         1753 |         1874 |
| C. solo generados       |         1515 |         1515 |
| D. ampliado sin costura |         1074 |         1195 |

## Resultados

| modelo              | entrenamiento           |   AUC |   precisión top 12 |   Brier |
|:--------------------|:------------------------|------:|-------------------:|--------:|
| regresión logística | A. solo originales      | 0.818 |              1.000 |   0.186 |
| regresión logística | B. ampliado completo    | 0.837 |              1.000 |   0.167 |
| regresión logística | C. solo generados       | 0.836 |              1.000 |   0.166 |
| regresión logística | D. ampliado sin costura | 0.833 |              1.000 |   0.168 |
| árbol (3 niveles)   | A. solo originales      | 0.743 |              0.958 |   0.226 |
| árbol (3 niveles)   | B. ampliado completo    | 0.802 |              1.000 |   0.161 |
| árbol (3 niveles)   | C. solo generados       | 0.813 |              1.000 |   0.161 |
| árbol (3 niveles)   | D. ampliado sin costura | 0.802 |              1.000 |   0.161 |

## Diferencia de AUC frente a entrenar solo con originales

| modelo              | comparación   |   dif. AUC | IC 95 % (bootstrap por anunciante)   |
|:--------------------|:--------------|-----------:|:-------------------------------------|
| regresión logística | B. − A        |     +0.019 | [-0.009, +0.044]                     |
| regresión logística | C. − A        |     +0.018 | [-0.014, +0.048]                     |
| regresión logística | D. − A        |     +0.015 | [-0.011, +0.043]                     |
| árbol (3 niveles)   | B. − A        |     +0.059 | [+0.003, +0.114]                     |
| árbol (3 niveles)   | C. − A        |     +0.069 | [+0.013, +0.125]                     |
| árbol (3 niveles)   | D. − A        |     +0.059 | [+0.003, +0.114]                     |

## Diagnóstico 0 · Fidelidad de las distribuciones (filas originales frente a añadidas)

| parte    |   campañas |   importe mediano (€) |   descuento medio (%) |   % Digital |   retraso medio de cobro (días) |   % ampliaciones ganadas |
|:---------|-----------:|----------------------:|----------------------:|------------:|--------------------------------:|-------------------------:|
| añadida  |       1661 |                  1039 |                   7.9 |        68.7 |                            10.9 |                     50.7 |
| original |       1432 |                  1158 |                   8   |        67.1 |                             9.8 |                     53.6 |

|                                                                  |   valor |
|:-----------------------------------------------------------------|--------:|
| anunciantes de dim_clientes sin campañas en los datos originales |      35 |
| … de ellos con alguna campaña en la ampliación                   |      35 |
| anunciantes con primera campaña anterior al alta                 |       0 |
| facturas originales sin cobrar al final de la ampliación         |      11 |
| … vencidas antes del 1-oct-2026                                  |       0 |

## Diagnóstico 1 · Abandono por corte según el origen del anunciante (efecto costura)

|            |   obs. anunciante nuevo (C0321+) |   obs. anunciante original |   % abandono anunciante nuevo (C0321+) |   % abandono anunciante original |   % abandono total |
|:-----------|---------------------------------:|---------------------------:|---------------------------------------:|---------------------------------:|-------------------:|
| 2020-12-31 |                               47 |                         43 |                                     81 |                               40 |               61.1 |
| 2021-03-31 |                               37 |                         52 |                                     78 |                               37 |               53.9 |
| 2021-06-30 |                               26 |                         55 |                                     77 |                               51 |               59.3 |
| 2021-09-30 |                               19 |                         61 |                                     84 |                               46 |               55   |
| 2021-12-31 |                               15 |                         68 |                                     53 |                               38 |               41   |
| 2022-03-31 |                               14 |                         81 |                                     50 |                               37 |               38.9 |
| 2022-06-30 |                               15 |                         86 |                                     47 |                               40 |               40.6 |
| 2022-09-30 |                               12 |                         91 |                                     33 |                               40 |               38.8 |
| 2022-12-31 |                               14 |                        100 |                                     57 |                               49 |               50   |
| 2023-03-31 |                               13 |                        109 |                                     54 |                               51 |               51.6 |
| 2023-06-30 |                               12 |                        102 |                                     83 |                               47 |               50.9 |
| 2023-09-30 |                               10 |                        106 |                                     90 |                               48 |               51.7 |
| 2023-12-31 |                               12 |                         99 |                                    100 |                               36 |               43.2 |
| 2024-03-31 |                               10 |                         96 |                                    100 |                               45 |               50   |
| 2024-06-30 |                              nan |                        110 |                                    nan |                               39 |               39.1 |
| 2024-09-30 |                              nan |                        115 |                                    nan |                               51 |               51.3 |
| 2024-12-31 |                              nan |                        123 |                                    nan |                               52 |               52   |
| 2025-03-31 |                              nan |                        121 |                                    nan |                               50 |               50.4 |
| 2025-06-30 |                              nan |                        118 |                                    nan |                               49 |               49.2 |
| 2025-09-30 |                              nan |                        123 |                                    nan |                               50 |               50.4 |
| 2025-12-31 |                              nan |                        128 |                                    nan |                               53 |               53.1 |

## Diagnóstico 2 · Propuestas abiertas según la etiqueta (cortes hasta jun-25)

| parte             |   % con propuesta abierta · sigue |   % con propuesta abierta · abandona |
|:------------------|----------------------------------:|-------------------------------------:|
| cortes generados  |                              38.9 |                                 19.1 |
| cortes originales |                              27.7 |                                 22.3 |

## Diagnóstico 3 · Pesos de la regresión logística (variables estandarizadas; entrenada con cortes anteriores a 2025-06-30)

|                                   |   A. solo originales |   B. ampliado completo |
|:----------------------------------|---------------------:|-----------------------:|
| tendencia                         |                -1.11 |                  -0.56 |
| pedidos_firmados_pendientes       |                -0.76 |                  -0.73 |
| valor_12m                         |                -0.66 |                  -0.53 |
| recencia_dias                     |                -0.62 |                  -0.02 |
| sin dato: retraso_medio_cobro_12m |                -0.62 |                  -0.76 |
| ctr_relativo                      |                -0.36 |                  -0.21 |
| antiguedad_meses                  |                -0.17 |                   0.08 |
| propuestas_abiertas               |                -0.1  |                  -0.31 |
| sin dato: ctr_relativo            |                -0.04 |                   0.05 |
| retraso_medio_cobro_12m           |                 0.19 |                   0.11 |
| n_familias_12m                    |                 0.29 |                   0.37 |
| propuestas_perdidas_12m           |                 0.31 |                   0.06 |
| cambio_interlocutor_12m           |                 0.37 |                   0.27 |
| frecuencia_12m                    |                 0.44 |                   0.49 |
| valor_mismo_periodo_anio_anterior |                 0.58 |                   0.59 |
| dias_sin_contacto                 |                 0.91 |                   1.06 |
