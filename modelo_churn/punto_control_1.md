# Punto de control 1 · Descripción del panel (generado automáticamente)

Datos: `tablas_ampliadas` (campañas de 2020-01-01 a 2026-11-01). Límite de W: 2026-09-01.

Fechas de corte (21): 2020-12-31, 2021-03-31, 2021-06-30, 2021-09-30, 2021-12-31, 2022-03-31, 2022-06-30, 2022-09-30, 2022-12-31, 2023-03-31, 2023-06-30, 2023-09-30, 2023-12-31, 2024-03-31, 2024-06-30, 2024-09-30, 2024-12-31, 2025-03-31, 2025-06-30, 2025-09-30, 2025-12-31.

Prueba: 2025-09-30, 2025-12-31 (solo datos originales).

## 1. Observaciones y abandonos por fecha de corte

|                     | datos                 |   observaciones |   abandonos |   % abandono |   perdida_total |   contraccion |   activo |
|:--------------------|:----------------------|----------------:|------------:|-------------:|----------------:|--------------:|---------:|
| 2020-12-31          | con datos generados   |              86 |          52 |         60.5 |              46 |             6 |       34 |
| 2021-03-31          | con datos generados   |              83 |          45 |         54.2 |              35 |            10 |       38 |
| 2021-06-30          | con datos generados   |              86 |          42 |         48.8 |              31 |            11 |       44 |
| 2021-09-30          | con datos generados   |              82 |          34 |         41.5 |              23 |            11 |       48 |
| 2021-12-31          | con datos generados   |              85 |          40 |         47.1 |              27 |            13 |       45 |
| 2022-03-31          | con datos generados   |              95 |          48 |         50.5 |              40 |             8 |       47 |
| 2022-06-30          | con datos generados   |             100 |          52 |         52   |              41 |            11 |       48 |
| 2022-09-30          | con datos generados   |             101 |          54 |         53.5 |              38 |            16 |       47 |
| 2022-12-31          | con datos generados   |             112 |          57 |         50.9 |              38 |            19 |       55 |
| 2023-03-31          | con datos generados   |             110 |          55 |         50   |              35 |            20 |       55 |
| 2023-06-30          | con datos generados   |             107 |          46 |         43   |              35 |            11 |       61 |
| 2023-09-30          | con datos generados   |             109 |          47 |         43.1 |              34 |            13 |       62 |
| 2023-12-31          | con datos generados   |             118 |          53 |         44.9 |              40 |            13 |       65 |
| 2024-03-31          | con datos generados   |             120 |          60 |         50   |              46 |            14 |       60 |
| 2024-06-30          | con datos generados   |             110 |          40 |         36.4 |              30 |            10 |       70 |
| 2024-09-30          | solo datos originales |             115 |          59 |         51.3 |              47 |            12 |       56 |
| 2024-12-31          | solo datos originales |             123 |          64 |         52   |              47 |            17 |       59 |
| 2025-03-31          | solo datos originales |             121 |          61 |         50.4 |              46 |            15 |       60 |
| 2025-06-30          | solo datos originales |             118 |          58 |         49.2 |              45 |            13 |       60 |
| 2025-09-30 (prueba) | solo datos originales |             123 |          62 |         50.4 |              46 |            16 |       61 |
| 2025-12-31 (prueba) | solo datos originales |             128 |          68 |         53.1 |              54 |            14 |       60 |
| TOTAL               |                       |            2232 |        1097 |         49.1 |             824 |           273 |     1135 |

## 2. Anunciantes distintos

|                                      |   anunciantes distintos |
|:-------------------------------------|------------------------:|
| Total panel                          |                     297 |
| Entrenamiento (19 cortes)            |                     276 |
| Prueba (2 cortes)                    |                     142 |
| En prueba y también en entrenamiento |                     121 |

|   nº de fechas de corte en que aparece |   anunciantes |
|---------------------------------------:|--------------:|
|                                      1 |            52 |
|                                      2 |            28 |
|                                      3 |            24 |
|                                      4 |            29 |
|                                      5 |            21 |
|                                      6 |             7 |
|                                      7 |            10 |
|                                      8 |            20 |
|                                      9 |             4 |
|                                     10 |             8 |
|                                     11 |            13 |
|                                     12 |             9 |
|                                     13 |            14 |
|                                     14 |             8 |
|                                     15 |             9 |
|                                     16 |             9 |
|                                     17 |             4 |
|                                     18 |             6 |
|                                     19 |             5 |
|                                     20 |             9 |
|                                     21 |             8 |

## 3. Entrenamiento: cortes con datos generados frente a cortes con solo datos originales

| fecha_corte           |   cortes |   observaciones |   anunciantes |   abandonos |   % abandono |
|:----------------------|---------:|----------------:|--------------:|------------:|-------------:|
| con datos generados   |       15 |            1504 |           242 |         725 |         48.2 |
| solo datos originales |        4 |             477 |           156 |         242 |         50.7 |

## 4. Distribución de cada variable (todas las fechas de corte)

|                                   |    n |   sin dato |      media |      mín |      p10 |       p25 |   mediana |          p75 |         p90 |         máx |   nº con 1 |   clientes distintos con 1 |
|:----------------------------------|-----:|-----------:|-----------:|---------:|---------:|----------:|----------:|-------------:|------------:|------------:|-----------:|---------------------------:|
| recencia_dias                     | 2232 |          0 |  144.5     |  29      |  29      |   58      |  121      |  241         | 305         | 365         |        nan |                        nan |
| frecuencia_12m                    | 2232 |          0 |    3.52    |   1      |   1      |    1      |    3      |    5         |   7         |  21         |        nan |                        nan |
| antiguedad_meses                  | 2232 |          0 |   42.03    |  12      |  15.8    |   22.6    |   37.1    |   55.1       |  74.69      | 155.9       |        nan |                        nan |
| valor_12m                         | 2232 |          0 | 8249       | 231.1    | 908.1    | 2022      | 5239      |    1.054e+04 |   2.048e+04 |   6.528e+04 |        nan |                        nan |
| valor_mismo_periodo_anio_anterior | 2232 |          0 | 4772       |   0      |   0      |  683.6    | 2496      | 6801         |   1.228e+04 |   4.919e+04 |        nan |                        nan |
| tendencia                         | 2232 |          0 |   -0.04353 |  -1      |  -1      |   -1      |   -0.2291 |    1         |   1         |   1         |        nan |                        nan |
| n_familias_12m                    | 2232 |          0 |    1.424   |   1      |   1      |    1      |    1      |    2         |   2         |   4         |        nan |                        nan |
| ctr_relativo                      | 1574 |        658 |    0.992   |   0.2268 |   0.6199 |    0.7636 |    0.9661 |    1.181     |   1.417     |   2.673     |        nan |                        nan |
| cambio_interlocutor_12m           | 2232 |          0 |  nan       | nan      | nan      |  nan      |  nan      |  nan         | nan         | nan         |        338 |                        103 |
| reclamacion_sin_resolver_12m      | 2232 |          0 |  nan       | nan      | nan      |  nan      |  nan      |  nan         | nan         | nan         |         31 |                         11 |
| dias_sin_contacto                 | 2232 |          0 |   55.47    |   0      |   3      |    9      |   22      |   57         | 177         | 439         |        nan |                        nan |
| facturas_vencidas_impagadas       | 2232 |          0 |    0.0336  |   0      |   0      |    0      |    0      |    0         |   0         |   2         |        nan |                        nan |
| retraso_medio_cobro_12m           | 2151 |         81 |   10.26    |   0      |   2      |    5      |    8.5    |   13.24      |  20         |  95         |        nan |                        nan |
| pedidos_firmados_pendientes       | 2232 |          0 |    0.2298  |   0      |   0      |    0      |    0      |    0         |   1         |   3         |        nan |                        nan |
| propuestas_abiertas               | 2232 |          0 |    0.315   |   0      |   0      |    0      |    0      |    1         |   1         |   3         |        nan |                        nan |
| propuestas_perdidas_12m           | 2232 |          0 |    0.8535  |   0      |   0      |    0      |    1      |    1         |   2         |   6         |        nan |                        nan |

## 5. % de abandono por tramos de cada variable (solo entrenamiento)

| variable                          | tramo                      |   obs |   % abandono | % con datos generados (obs)   | % solo datos originales (obs)   |
|:----------------------------------|:---------------------------|------:|-------------:|:------------------------------|:--------------------------------|
| recencia_dias                     | T1 [29 a 58]               |   524 |         31.9 | 28.8 (399)                    | 41.6 (125)                      |
| recencia_dias                     | T2 [59 a 121]              |   558 |         37.3 | 36.0 (431)                    | 41.7 (127)                      |
| recencia_dias                     | T3 [149 a 241]             |   448 |         56.7 | 58.1 (334)                    | 52.6 (114)                      |
| recencia_dias                     | T4 [242 a 365]             |   451 |         74.9 | 76.8 (340)                    | 69.4 (111)                      |
| frecuencia_12m                    | T1 [1 a 3]                 |  1231 |         45.1 | 44.1 (943)                    | 48.3 (288)                      |
| frecuencia_12m                    | T2 [4 a 5]                 |   385 |         54   | 54.1 (292)                    | 53.8 (93)                       |
| frecuencia_12m                    | T3 [6 a 21]                |   365 |         55.9 | 56.1 (269)                    | 55.2 (96)                       |
| antiguedad_meses                  | T1 [12 a 22.4]             |   498 |         51.6 | 51.8 (438)                    | 50.0 (60)                       |
| antiguedad_meses                  | T2 [22.5 a 35.7]           |   493 |         51.1 | 49.0 (414)                    | 62.0 (79)                       |
| antiguedad_meses                  | T3 [35.8 a 52.8]           |   498 |         44.2 | 40.7 (356)                    | 52.8 (142)                      |
| antiguedad_meses                  | T4 [52.9 a 152.9]          |   492 |         48.4 | 50.7 (296)                    | 44.9 (196)                      |
| valor_12m                         | T1 [231.1 a 2046]          |   496 |         49.6 | 47.5 (373)                    | 56.1 (123)                      |
| valor_12m                         | T2 [2050 a 5214]           |   495 |         48.1 | 47.1 (376)                    | 51.3 (119)                      |
| valor_12m                         | T3 [5227 a 1.053e+04]      |   495 |         47.9 | 47.8 (372)                    | 48.0 (123)                      |
| valor_12m                         | T4 [1.054e+04 a 6.528e+04] |   495 |         49.7 | 50.4 (383)                    | 47.3 (112)                      |
| valor_mismo_periodo_anio_anterior | T1 [0 a 699.8]             |   496 |         18.8 | 18.9 (397)                    | 18.2 (99)                       |
| valor_mismo_periodo_anio_anterior | T2 [712.9 a 2526]          |   495 |         54.7 | 54.2 (347)                    | 56.1 (148)                      |
| valor_mismo_periodo_anio_anterior | T3 [2530 a 6763]           |   495 |         60.8 | 59.3 (376)                    | 65.5 (119)                      |
| valor_mismo_periodo_anio_anterior | T4 [6800 a 4.919e+04]      |   495 |         61   | 62.2 (384)                    | 56.8 (111)                      |
| tendencia                         | T1 [-1 a -0.2575]          |   991 |         68.8 | 68.8 (736)                    | 69.0 (255)                      |
| tendencia                         | T2 [-0.2528 a 1]           |   990 |         28.8 | 28.5 (768)                    | 29.7 (222)                      |
| n_familias_12m                    | 1                          |  1280 |         47   | 46.2 (945)                    | 49.0 (335)                      |
| n_familias_12m                    | 2                          |   571 |         51.8 | 52.2 (456)                    | 50.4 (115)                      |
| n_familias_12m                    | 3 o más                    |   130 |         53.8 | 48.5 (103)                    | 74.1 (27)                       |
| ctr_relativo                      | T1 [0.2268 a 0.7614]       |   348 |         57.2 | 55.3 (282)                    | 65.2 (66)                       |
| ctr_relativo                      | T2 [0.7631 a 0.9663]       |   347 |         56.8 | 55.6 (252)                    | 60.0 (95)                       |
| ctr_relativo                      | T3 [0.9671 a 1.183]        |   347 |         44.4 | 42.7 (255)                    | 48.9 (92)                       |
| ctr_relativo                      | T4 [1.185 a 2.673]         |   347 |         40.3 | 40.6 (271)                    | 39.5 (76)                       |
| ctr_relativo                      | sin dato                   |   592 |         46.8 | 47.3 (444)                    | 45.3 (148)                      |
| cambio_interlocutor_12m           | no                         |  1677 |         46   | 45.6 (1273)                   | 47.5 (404)                      |
| cambio_interlocutor_12m           | sí                         |   304 |         64.1 | 62.8 (231)                    | 68.5 (73)                       |
| reclamacion_sin_resolver_12m      | no                         |  1953 |         48.4 | 47.9 (1487)                   | 50.2 (466)                      |
| reclamacion_sin_resolver_12m      | sí                         |    28 |         75   | 76.5 (17)                     | 72.7 (11)                       |
| dias_sin_contacto                 | T1 [0 a 9]                 |   521 |         34.4 | 33.9 (357)                    | 35.4 (164)                      |
| dias_sin_contacto                 | T2 [10 a 22]               |   487 |         38.8 | 37.4 (382)                    | 43.8 (105)                      |
| dias_sin_contacto                 | T3 [23 a 58]               |   481 |         43.5 | 42.7 (391)                    | 46.7 (90)                       |
| dias_sin_contacto                 | T4 [59 a 439]              |   492 |         79.3 | 78.6 (374)                    | 81.4 (118)                      |
| facturas_vencidas_impagadas       | 0                          |  1917 |         49.2 | 48.6 (1460)                   | 51.2 (457)                      |
| facturas_vencidas_impagadas       | 1                          |    63 |         36.5 | 34.9 (43)                     | 40.0 (20)                       |
| facturas_vencidas_impagadas       | 2                          |     1 |        100   | 100.0 (1)                     | —                               |
| retraso_medio_cobro_12m           | T1 [0 a 5]                 |   482 |         45.2 | 45.1 (359)                    | 45.5 (123)                      |
| retraso_medio_cobro_12m           | T2 [5.1 a 8.667]           |   483 |         49.3 | 49.0 (353)                    | 50.0 (130)                      |
| retraso_medio_cobro_12m           | T3 [8.7 a 13.33]           |   473 |         49   | 48.2 (371)                    | 52.0 (102)                      |
| retraso_medio_cobro_12m           | T4 [13.38 a 95]            |   478 |         58.4 | 57.0 (370)                    | 63.0 (108)                      |
| retraso_medio_cobro_12m           | sin dato                   |    65 |          0   | 0.0 (51)                      | 0.0 (14)                        |
| pedidos_firmados_pendientes       | 0                          |  1580 |         56.8 | 56.1 (1203)                   | 58.9 (377)                      |
| pedidos_firmados_pendientes       | 1                          |   366 |         17.8 | 17.3 (272)                    | 19.1 (94)                       |
| pedidos_firmados_pendientes       | 2                          |    32 |         15.6 | 11.1 (27)                     | 40.0 (5)                        |
| pedidos_firmados_pendientes       | 3 o más                    |     3 |          0   | 0.0 (2)                       | 0.0 (1)                         |
| propuestas_abiertas               | 0                          |  1439 |         53.4 | 53.7 (1081)                   | 52.5 (358)                      |
| propuestas_abiertas               | 1                          |   459 |         38.1 | 35.7 (353)                    | 46.2 (106)                      |
| propuestas_abiertas               | 2                          |    67 |         26.9 | 24.6 (57)                     | 40.0 (10)                       |
| propuestas_abiertas               | 3 o más                    |    16 |         37.5 | 38.5 (13)                     | 33.3 (3)                        |
| propuestas_perdidas_12m           | 0                          |   889 |         47.5 | 48.2 (679)                    | 45.2 (210)                      |
| propuestas_perdidas_12m           | 1                          |   673 |         46.1 | 44.4 (498)                    | 50.9 (175)                      |
| propuestas_perdidas_12m           | 2                          |   295 |         55.6 | 54.2 (227)                    | 60.3 (68)                       |
| propuestas_perdidas_12m           | 3 o más                    |   124 |         57.3 | 54.0 (100)                    | 70.8 (24)                       |
