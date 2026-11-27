# Punto de control 1 · Descripción del panel (generado automáticamente)

Datos: `tablas_ampliadas` (campañas de 2020-01-01 a 2026-11-01). Límite de W: 2026-09-01.

Fechas de corte (21): 2020-12-31, 2021-03-31, 2021-06-30, 2021-09-30, 2021-12-31, 2022-03-31, 2022-06-30, 2022-09-30, 2022-12-31, 2023-03-31, 2023-06-30, 2023-09-30, 2023-12-31, 2024-03-31, 2024-06-30, 2024-09-30, 2024-12-31, 2025-03-31, 2025-06-30, 2025-09-30, 2025-12-31.

Prueba: 2025-09-30, 2025-12-31 (solo datos originales).

## 1. Observaciones y abandonos por fecha de corte

|                     | datos                 |   observaciones |   abandonos |   % abandono |   perdida_total |   contraccion |   activo |
|:--------------------|:----------------------|----------------:|------------:|-------------:|----------------:|--------------:|---------:|
| 2020-12-31          | con datos generados   |              85 |          45 |         52.9 |              40 |             5 |       40 |
| 2021-03-31          | con datos generados   |              89 |          45 |         50.6 |              38 |             7 |       44 |
| 2021-06-30          | con datos generados   |              88 |          44 |         50   |              31 |            13 |       44 |
| 2021-09-30          | con datos generados   |              78 |          37 |         47.4 |              26 |            11 |       41 |
| 2021-12-31          | con datos generados   |              83 |          38 |         45.8 |              24 |            14 |       45 |
| 2022-03-31          | con datos generados   |              93 |          45 |         48.4 |              36 |             9 |       48 |
| 2022-06-30          | con datos generados   |             100 |          53 |         53   |              39 |            14 |       47 |
| 2022-09-30          | con datos generados   |             103 |          55 |         53.4 |              37 |            18 |       48 |
| 2022-12-31          | con datos generados   |             105 |          54 |         51.4 |              41 |            13 |       51 |
| 2023-03-31          | con datos generados   |             104 |          56 |         53.8 |              40 |            16 |       48 |
| 2023-06-30          | con datos generados   |              98 |          38 |         38.8 |              26 |            12 |       60 |
| 2023-09-30          | con datos generados   |             100 |          37 |         37   |              24 |            13 |       63 |
| 2023-12-31          | con datos generados   |             107 |          41 |         38.3 |              28 |            13 |       66 |
| 2024-03-31          | con datos generados   |             113 |          53 |         46.9 |              39 |            14 |       60 |
| 2024-06-30          | con datos generados   |             128 |          58 |         45.3 |              48 |            10 |       70 |
| 2024-09-30          | solo datos originales |             115 |          59 |         51.3 |              47 |            12 |       56 |
| 2024-12-31          | solo datos originales |             123 |          64 |         52   |              47 |            17 |       59 |
| 2025-03-31          | solo datos originales |             121 |          61 |         50.4 |              46 |            15 |       60 |
| 2025-06-30          | solo datos originales |             118 |          58 |         49.2 |              45 |            13 |       60 |
| 2025-09-30 (prueba) | solo datos originales |             123 |          62 |         50.4 |              46 |            16 |       61 |
| 2025-12-31 (prueba) | solo datos originales |             128 |          68 |         53.1 |              54 |            14 |       60 |
| TOTAL               |                       |            2202 |        1071 |         48.6 |             802 |           269 |     1131 |

## 2. Anunciantes distintos

|                                      |   anunciantes distintos |
|:-------------------------------------|------------------------:|
| Total panel                          |                     282 |
| Entrenamiento (19 cortes)            |                     261 |
| Prueba (2 cortes)                    |                     142 |
| En prueba y también en entrenamiento |                     121 |

|   nº de fechas de corte en que aparece |   anunciantes |
|---------------------------------------:|--------------:|
|                                      1 |            48 |
|                                      2 |            24 |
|                                      3 |            26 |
|                                      4 |            23 |
|                                      5 |            14 |
|                                      6 |            11 |
|                                      7 |            11 |
|                                      8 |            15 |
|                                      9 |             4 |
|                                     10 |             9 |
|                                     11 |            15 |
|                                     12 |            11 |
|                                     13 |            14 |
|                                     14 |             5 |
|                                     15 |            11 |
|                                     16 |             9 |
|                                     17 |             4 |
|                                     18 |             6 |
|                                     19 |             5 |
|                                     20 |             9 |
|                                     21 |             8 |

## 3. Entrenamiento: cortes con datos generados frente a cortes con solo datos originales

| fecha_corte           |   cortes |   observaciones |   anunciantes |   abandonos |   % abandono |
|:----------------------|---------:|----------------:|--------------:|------------:|-------------:|
| con datos generados   |       15 |            1474 |           227 |         699 |         47.4 |
| solo datos originales |        4 |             477 |           156 |         242 |         50.7 |

## 4. Distribución de cada variable (todas las fechas de corte)

|                                   |    n |   sin dato |      media |      mín |      p10 |       p25 |   mediana |          p75 |         p90 |         máx |   nº con 1 |   clientes distintos con 1 |
|:----------------------------------|-----:|-----------:|-----------:|---------:|---------:|----------:|----------:|-------------:|------------:|------------:|-----------:|---------------------------:|
| recencia_dias                     | 2202 |          0 |  141.7     |  29      |  29      |   58      |  121      |  213         | 304.9       | 365         |        nan |                        nan |
| frecuencia_12m                    | 2202 |          0 |    3.622   |   1      |   1      |    1      |    3      |    5         |   8         |  21         |        nan |                        nan |
| antiguedad_meses                  | 2202 |          0 |   42.85    |  12      |  15.9    |   23.32   |   38.5    |   56.2       |  75.28      | 155.9       |        nan |                        nan |
| valor_12m                         | 2202 |          0 | 8447       | 231.1    | 962.6    | 2022      | 5346      |    1.118e+04 |   2.069e+04 |   6.528e+04 |        nan |                        nan |
| valor_mismo_periodo_anio_anterior | 2202 |          0 | 4868       |   0      |   0      |  735.9    | 2526      | 6993         |   1.23e+04  |   4.919e+04 |        nan |                        nan |
| tendencia                         | 2202 |          0 |   -0.03151 |  -1      |  -1      |   -1      |   -0.1955 |    1         |   1         |   1         |        nan |                        nan |
| n_familias_12m                    | 2202 |          0 |    1.444   |   1      |   1      |    1      |    1      |    2         |   2         |   4         |        nan |                        nan |
| ctr_relativo                      | 1574 |        628 |    0.9814  |   0.3505 |   0.6566 |    0.7707 |    0.9512 |    1.139     |   1.372     |   2.45      |        nan |                        nan |
| cambio_interlocutor_12m           | 2202 |          0 |  nan       | nan      | nan      |  nan      |  nan      |  nan         | nan         | nan         |        301 |                         94 |
| reclamacion_sin_resolver_12m      | 2202 |          0 |  nan       | nan      | nan      |  nan      |  nan      |  nan         | nan         | nan         |         33 |                         10 |
| dias_sin_contacto                 | 2202 |          0 |   54.07    |   0      |   3      |    8      |   21.5    |   56         | 166         | 450         |        nan |                        nan |
| facturas_vencidas_impagadas       | 2202 |          0 |    0.03588 |   0      |   0      |    0      |    0      |    0         |   0         |   2         |        nan |                        nan |
| retraso_medio_cobro_12m           | 2125 |         77 |   10.28    |   0      |   1.5    |    5      |    8.75   |   13.4       |  19.75      |  95         |        nan |                        nan |
| pedidos_firmados_pendientes       | 2202 |          0 |    0.2361  |   0      |   0      |    0      |    0      |    0         |   1         |   3         |        nan |                        nan |
| propuestas_abiertas               | 2202 |          0 |    0.3465  |   0      |   0      |    0      |    0      |    1         |   1         |   6         |        nan |                        nan |
| propuestas_perdidas_12m           | 2202 |          0 |    1.07    |   0      |   0      |    0      |    1      |    2         |   3         |   8         |        nan |                        nan |

## 5. % de abandono por tramos de cada variable (solo entrenamiento)

| variable                          | tramo                      |   obs |   % abandono | % con datos generados (obs)   | % solo datos originales (obs)   |
|:----------------------------------|:---------------------------|------:|-------------:|:------------------------------|:--------------------------------|
| recencia_dias                     | T1 [29 a 58]               |   530 |         31.9 | 28.9 (405)                    | 41.6 (125)                      |
| recencia_dias                     | T2 [59 a 121]              |   562 |         38.3 | 37.2 (435)                    | 41.7 (127)                      |
| recencia_dias                     | T3 [149 a 213]             |   401 |         55.9 | 57.1 (294)                    | 52.3 (107)                      |
| recencia_dias                     | T4 [241 a 365]             |   458 |         72.7 | 74.1 (340)                    | 68.6 (118)                      |
| frecuencia_12m                    | T1 [1 a 3]                 |  1182 |         44.7 | 43.5 (894)                    | 48.3 (288)                      |
| frecuencia_12m                    | T2 [4 a 5]                 |   370 |         51.9 | 51.3 (277)                    | 53.8 (93)                       |
| frecuencia_12m                    | T3 [6 a 21]                |   399 |         55.4 | 55.4 (303)                    | 55.2 (96)                       |
| antiguedad_meses                  | T1 [12 a 23.2]             |   489 |         50.1 | 49.9 (425)                    | 51.6 (64)                       |
| antiguedad_meses                  | T2 [23.3 a 37.4]           |   488 |         45.9 | 43.1 (401)                    | 58.6 (87)                       |
| antiguedad_meses                  | T3 [37.5 a 54.1]           |   489 |         46.6 | 44.1 (354)                    | 53.3 (135)                      |
| antiguedad_meses                  | T4 [54.2 a 152.9]          |   485 |         50.3 | 53.7 (294)                    | 45.0 (191)                      |
| valor_12m                         | T1 [231.1 a 2046]          |   488 |         46.5 | 43.3 (365)                    | 56.1 (123)                      |
| valor_12m                         | T2 [2050 a 5365]           |   488 |         46.1 | 44.4 (365)                    | 51.2 (123)                      |
| valor_12m                         | T3 [5392 a 1.118e+04]      |   487 |         48.5 | 49.2 (358)                    | 46.5 (129)                      |
| valor_12m                         | T4 [1.119e+04 a 6.528e+04] |   488 |         51.8 | 52.6 (386)                    | 49.0 (102)                      |
| valor_mismo_periodo_anio_anterior | T1 [0 a 751.2]             |   488 |         19.7 | 19.4 (386)                    | 20.6 (102)                      |
| valor_mismo_periodo_anio_anterior | T2 [759.8 a 2554]          |   488 |         52.5 | 51.2 (340)                    | 55.4 (148)                      |
| valor_mismo_periodo_anio_anterior | T3 [2562 a 6968]           |   487 |         60   | 58.1 (370)                    | 65.8 (117)                      |
| valor_mismo_periodo_anio_anterior | T4 [6988 a 4.919e+04]      |   488 |         60.9 | 62.2 (378)                    | 56.4 (110)                      |
| tendencia                         | T1 [-1 a -0.2046]          |   976 |         67.3 | 66.8 (719)                    | 68.9 (257)                      |
| tendencia                         | T2 [-0.2044 a 1]           |   975 |         29.1 | 29.0 (755)                    | 29.5 (220)                      |
| n_familias_12m                    | 1                          |  1237 |         46.3 | 45.3 (902)                    | 49.0 (335)                      |
| n_familias_12m                    | 2                          |   564 |         50.2 | 50.1 (449)                    | 50.4 (115)                      |
| n_familias_12m                    | 3 o más                    |   150 |         56.7 | 52.8 (123)                    | 74.1 (27)                       |
| ctr_relativo                      | T1 [0.3505 a 0.7692]       |   348 |         57.8 | 55.8 (278)                    | 65.7 (70)                       |
| ctr_relativo                      | T2 [0.7696 a 0.9512]       |   347 |         49.3 | 47.3 (273)                    | 56.8 (74)                       |
| ctr_relativo                      | T3 [0.9512 a 1.133]        |   347 |         46.7 | 42.9 (259)                    | 58.0 (88)                       |
| ctr_relativo                      | T4 [1.133 a 2.45]          |   347 |         40.9 | 42.4 (250)                    | 37.1 (97)                       |
| ctr_relativo                      | sin dato                   |   562 |         47.2 | 47.8 (414)                    | 45.3 (148)                      |
| cambio_interlocutor_12m           | no                         |  1684 |         46.4 | 46.1 (1280)                   | 47.5 (404)                      |
| cambio_interlocutor_12m           | sí                         |   267 |         59.6 | 56.2 (194)                    | 68.5 (73)                       |
| reclamacion_sin_resolver_12m      | no                         |  1921 |         48   | 47.4 (1455)                   | 50.2 (466)                      |
| reclamacion_sin_resolver_12m      | sí                         |    30 |         60   | 52.6 (19)                     | 72.7 (11)                       |
| dias_sin_contacto                 | T1 [0 a 9]                 |   535 |         33.8 | 33.2 (371)                    | 35.4 (164)                      |
| dias_sin_contacto                 | T2 [10 a 21]               |   443 |         37   | 35.7 (347)                    | 41.7 (96)                       |
| dias_sin_contacto                 | T3 [22 a 56]               |   487 |         43.3 | 41.9 (389)                    | 49.0 (98)                       |
| dias_sin_contacto                 | T4 [57 a 450]              |   486 |         79.2 | 78.7 (367)                    | 80.7 (119)                      |
| facturas_vencidas_impagadas       | 0                          |  1884 |         48.6 | 47.7 (1427)                   | 51.2 (457)                      |
| facturas_vencidas_impagadas       | 1                          |    65 |         40   | 40.0 (45)                     | 40.0 (20)                       |
| facturas_vencidas_impagadas       | 2                          |     2 |          0   | 0.0 (2)                       | —                               |
| retraso_medio_cobro_12m           | T1 [0 a 5]                 |   516 |         41.3 | 40.4 (396)                    | 44.2 (120)                      |
| retraso_medio_cobro_12m           | T2 [5.125 a 9]             |   470 |         49.8 | 49.2 (323)                    | 51.0 (147)                      |
| retraso_medio_cobro_12m           | T3 [9.083 a 13.5]          |   434 |         47.5 | 46.4 (343)                    | 51.6 (91)                       |
| retraso_medio_cobro_12m           | T4 [13.6 a 95]             |   470 |         61.3 | 60.5 (365)                    | 63.8 (105)                      |
| retraso_medio_cobro_12m           | sin dato                   |    61 |          0   | 0.0 (47)                      | 0.0 (14)                        |
| pedidos_firmados_pendientes       | 0                          |  1547 |         56.8 | 56.1 (1170)                   | 58.9 (377)                      |
| pedidos_firmados_pendientes       | 1                          |   366 |         15.8 | 14.7 (272)                    | 19.1 (94)                       |
| pedidos_firmados_pendientes       | 2                          |    34 |         14.7 | 10.3 (29)                     | 40.0 (5)                        |
| pedidos_firmados_pendientes       | 3 o más                    |     4 |          0   | 0.0 (3)                       | 0.0 (1)                         |
| propuestas_abiertas               | 0                          |  1408 |         55.2 | 56.1 (1050)                   | 52.5 (358)                      |
| propuestas_abiertas               | 1                          |   422 |         32.9 | 28.5 (316)                    | 46.2 (106)                      |
| propuestas_abiertas               | 2                          |    93 |         22.6 | 20.5 (83)                     | 40.0 (10)                       |
| propuestas_abiertas               | 3 o más                    |    28 |         14.3 | 12.0 (25)                     | 33.3 (3)                        |
| propuestas_perdidas_12m           | 0                          |   853 |         48.7 | 49.8 (641)                    | 45.3 (212)                      |
| propuestas_perdidas_12m           | 1                          |   504 |         44.6 | 40.9 (328)                    | 51.7 (176)                      |
| propuestas_perdidas_12m           | 2                          |   341 |         54.3 | 52.7 (273)                    | 60.3 (68)                       |
| propuestas_perdidas_12m           | 3 o más                    |   253 |         45.8 | 44.0 (232)                    | 66.7 (21)                       |
