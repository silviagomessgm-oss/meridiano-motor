# Punto de control 1 · Descripción del panel (generado automáticamente)

Datos: `tablas_ampliadas` (campañas de 2020-01-01 a 2026-11-01). Límite de W: 2026-09-01.

Fechas de corte (21): 2020-12-31, 2021-03-31, 2021-06-30, 2021-09-30, 2021-12-31, 2022-03-31, 2022-06-30, 2022-09-30, 2022-12-31, 2023-03-31, 2023-06-30, 2023-09-30, 2023-12-31, 2024-03-31, 2024-06-30, 2024-09-30, 2024-12-31, 2025-03-31, 2025-06-30, 2025-09-30, 2025-12-31.

Prueba: 2025-09-30, 2025-12-31 (solo datos originales).

## 1. Observaciones y abandonos por fecha de corte

|                     | datos                 |   observaciones |   abandonos |   % abandono |   perdida_total |   contraccion |   activo |
|:--------------------|:----------------------|----------------:|------------:|-------------:|----------------:|--------------:|---------:|
| 2020-12-31          | con datos generados   |              90 |          55 |         61.1 |              48 |             7 |       35 |
| 2021-03-31          | con datos generados   |              89 |          48 |         53.9 |              39 |             9 |       41 |
| 2021-06-30          | con datos generados   |              81 |          48 |         59.3 |              36 |            12 |       33 |
| 2021-09-30          | con datos generados   |              80 |          44 |         55   |              28 |            16 |       36 |
| 2021-12-31          | con datos generados   |              83 |          34 |         41   |              20 |            14 |       49 |
| 2022-03-31          | con datos generados   |              95 |          37 |         38.9 |              21 |            16 |       58 |
| 2022-06-30          | con datos generados   |             101 |          41 |         40.6 |              30 |            11 |       60 |
| 2022-09-30          | con datos generados   |             103 |          40 |         38.8 |              23 |            17 |       63 |
| 2022-12-31          | con datos generados   |             114 |          57 |         50   |              39 |            18 |       57 |
| 2023-03-31          | con datos generados   |             122 |          63 |         51.6 |              46 |            17 |       59 |
| 2023-06-30          | con datos generados   |             114 |          58 |         50.9 |              46 |            12 |       56 |
| 2023-09-30          | con datos generados   |             116 |          60 |         51.7 |              42 |            18 |       56 |
| 2023-12-31          | con datos generados   |             111 |          48 |         43.2 |              28 |            20 |       63 |
| 2024-03-31          | con datos generados   |             106 |          53 |         50   |              36 |            17 |       53 |
| 2024-06-30          | con datos generados   |             110 |          43 |         39.1 |              30 |            13 |       67 |
| 2024-09-30          | solo datos originales |             115 |          59 |         51.3 |              47 |            12 |       56 |
| 2024-12-31          | solo datos originales |             123 |          64 |         52   |              47 |            17 |       59 |
| 2025-03-31          | solo datos originales |             121 |          61 |         50.4 |              46 |            15 |       60 |
| 2025-06-30          | solo datos originales |             118 |          58 |         49.2 |              45 |            13 |       60 |
| 2025-09-30 (prueba) | solo datos originales |             123 |          62 |         50.4 |              46 |            16 |       61 |
| 2025-12-31 (prueba) | solo datos originales |             128 |          68 |         53.1 |              54 |            14 |       60 |
| TOTAL               |                       |            2243 |        1101 |         49.1 |             797 |           304 |     1142 |

## 2. Anunciantes distintos

|                                      |   anunciantes distintos |
|:-------------------------------------|------------------------:|
| Total panel                          |                     279 |
| Entrenamiento (19 cortes)            |                     260 |
| Prueba (2 cortes)                    |                     142 |
| En prueba y también en entrenamiento |                     123 |

|   nº de fechas de corte en que aparece |   anunciantes |
|---------------------------------------:|--------------:|
|                                      1 |            48 |
|                                      2 |            29 |
|                                      3 |            24 |
|                                      4 |            19 |
|                                      5 |            13 |
|                                      6 |            10 |
|                                      7 |            10 |
|                                      8 |             9 |
|                                      9 |             8 |
|                                     10 |            14 |
|                                     11 |             8 |
|                                     12 |             6 |
|                                     13 |            10 |
|                                     14 |            10 |
|                                     15 |            11 |
|                                     16 |            14 |
|                                     17 |             8 |
|                                     18 |             3 |
|                                     19 |             9 |
|                                     20 |             6 |
|                                     21 |            10 |

## 3. Entrenamiento: cortes con datos generados frente a cortes con solo datos originales

| fecha_corte           |   cortes |   observaciones |   anunciantes |   abandonos |   % abandono |
|:----------------------|---------:|----------------:|--------------:|------------:|-------------:|
| con datos generados   |       15 |            1515 |           231 |         729 |         48.1 |
| solo datos originales |        4 |             477 |           156 |         242 |         50.7 |

## 4. Distribución de cada variable (todas las fechas de corte)

|                                   |    n |   sin dato |      media |      mín |      p10 |       p25 |   mediana |          p75 |         p90 |         máx |   nº con 1 |   clientes distintos con 1 |
|:----------------------------------|-----:|-----------:|-----------:|---------:|---------:|----------:|----------:|-------------:|------------:|------------:|-----------:|---------------------------:|
| recencia_dias                     | 2243 |          0 |  141.6     |  29      |  29      |   30      |  121      |  213         | 305         | 365         |        nan |                        nan |
| frecuencia_12m                    | 2243 |          0 |    3.804   |   1      |   1      |    1      |    3      |    5         |   8         |  17         |        nan |                        nan |
| antiguedad_meses                  | 2243 |          0 |   42.75    |  12      |  15.9    |   23.35   |   38.4    |   57.25      |  74.2       | 155.9       |        nan |                        nan |
| valor_12m                         | 2243 |          0 | 8254       | 169.3    | 998      | 2080      | 5390      |    1.063e+04 |   1.992e+04 |   5.407e+04 |        nan |                        nan |
| valor_mismo_periodo_anio_anterior | 2243 |          0 | 4816       |   0      |   0      |  787.4    | 2594      | 7086         |   1.209e+04 |   3.703e+04 |        nan |                        nan |
| tendencia                         | 2243 |          0 |   -0.03926 |  -1      |  -1      |   -1      |   -0.2124 |    1         |   1         |   1         |        nan |                        nan |
| n_familias_12m                    | 2243 |          0 |    1.438   |   1      |   1      |    1      |    1      |    2         |   2         |   4         |        nan |                        nan |
| ctr_relativo                      | 1634 |        609 |    0.9728  |   0.1822 |   0.6008 |    0.7355 |    0.9395 |    1.15      |   1.386     |   3.285     |        nan |                        nan |
| cambio_interlocutor_12m           | 2243 |          0 |  nan       | nan      | nan      |  nan      |  nan      |  nan         | nan         | nan         |        328 |                         94 |
| reclamacion_sin_resolver_12m      | 2243 |          0 |  nan       | nan      | nan      |  nan      |  nan      |  nan         | nan         | nan         |         66 |                         26 |
| dias_sin_contacto                 | 2243 |          0 |   52.72    |   0      |   3      |    9      |   22      |   57         | 160         | 447         |        nan |                        nan |
| facturas_vencidas_impagadas       | 2243 |          0 |    0.04146 |   0      |   0      |    0      |    0      |    0         |   0         |   2         |        nan |                        nan |
| retraso_medio_cobro_12m           | 2168 |         75 |   10.55    |   0      |   2      |    5      |    9      |   14         |  20         | 126         |        nan |                        nan |
| pedidos_firmados_pendientes       | 2243 |          0 |    0.2461  |   0      |   0      |    0      |    0      |    0         |   1         |   5         |        nan |                        nan |
| propuestas_abiertas               | 2243 |          0 |    0.3232  |   0      |   0      |    0      |    0      |    1         |   1         |   4         |        nan |                        nan |
| propuestas_perdidas_12m           | 2243 |          0 |    0.9015  |   0      |   0      |    0      |    1      |    1         |   2         |   6         |        nan |                        nan |

## 5. % de abandono por tramos de cada variable (solo entrenamiento)

| variable                          | tramo                      |   obs |   % abandono | % con datos generados (obs)   | % solo datos originales (obs)   |
|:----------------------------------|:---------------------------|------:|-------------:|:------------------------------|:--------------------------------|
| recencia_dias                     | T1 [29 a 58]               |   542 |         32.5 | 29.7 (417)                    | 41.6 (125)                      |
| recencia_dias                     | T2 [59 a 121]              |   575 |         40.5 | 40.2 (448)                    | 41.7 (127)                      |
| recencia_dias                     | T3 [149 a 213]             |   402 |         56.2 | 57.6 (295)                    | 52.3 (107)                      |
| recencia_dias                     | T4 [241 a 365]             |   473 |         71   | 71.8 (355)                    | 68.6 (118)                      |
| frecuencia_12m                    | T1 [1 a 3]                 |  1163 |         46.9 | 46.5 (875)                    | 48.3 (288)                      |
| frecuencia_12m                    | T2 [4 a 5]                 |   394 |         50.3 | 49.2 (301)                    | 53.8 (93)                       |
| frecuencia_12m                    | T3 [6 a 17]                |   435 |         52.2 | 51.3 (339)                    | 55.2 (96)                       |
| antiguedad_meses                  | T1 [12 a 23.2]             |   498 |         49.8 | 49.5 (434)                    | 51.6 (64)                       |
| antiguedad_meses                  | T2 [23.3 a 37.2]           |   499 |         45.7 | 42.9 (413)                    | 59.3 (86)                       |
| antiguedad_meses                  | T3 [37.3 a 55.2]           |   498 |         48.4 | 46.4 (351)                    | 53.1 (147)                      |
| antiguedad_meses                  | T4 [55.3 a 152.9]          |   497 |         51.1 | 54.9 (317)                    | 44.4 (180)                      |
| valor_12m                         | T1 [169.3 a 2133]          |   498 |         48.4 | 45.9 (368)                    | 55.4 (130)                      |
| valor_12m                         | T2 [2145 a 5415]           |   498 |         47.8 | 46.7 (381)                    | 51.3 (117)                      |
| valor_12m                         | T3 [5427 a 1.066e+04]      |   498 |         49.8 | 50.1 (379)                    | 48.7 (119)                      |
| valor_12m                         | T4 [1.069e+04 a 5.057e+04] |   498 |         49   | 49.6 (387)                    | 46.8 (111)                      |
| valor_mismo_periodo_anio_anterior | T1 [0 a 802]               |   498 |         20.1 | 19.5 (389)                    | 22.0 (109)                      |
| valor_mismo_periodo_anio_anterior | T2 [802.1 a 2623]          |   498 |         54.2 | 53.7 (354)                    | 55.6 (144)                      |
| valor_mismo_periodo_anio_anterior | T3 [2627 a 7082]           |   499 |         59.3 | 57.2 (381)                    | 66.1 (118)                      |
| valor_mismo_periodo_anio_anterior | T4 [7090 a 3.703e+04]      |   497 |         61.4 | 62.7 (391)                    | 56.6 (106)                      |
| tendencia                         | T1 [-1 a -0.2288]          |   996 |         67.5 | 66.9 (740)                    | 69.1 (256)                      |
| tendencia                         | T2 [-0.2273 a 1]           |   996 |         30   | 30.2 (775)                    | 29.4 (221)                      |
| n_familias_12m                    | 1                          |  1264 |         46   | 45.0 (929)                    | 49.0 (335)                      |
| n_familias_12m                    | 2                          |   583 |         51.8 | 52.1 (468)                    | 50.4 (115)                      |
| n_familias_12m                    | 3 o más                    |   145 |         60   | 56.8 (118)                    | 74.1 (27)                       |
| ctr_relativo                      | T1 [0.1822 a 0.7311]       |   363 |         61.2 | 60.3 (305)                    | 65.5 (58)                       |
| ctr_relativo                      | T2 [0.7323 a 0.9392]       |   362 |         48.6 | 45.6 (274)                    | 58.0 (88)                       |
| ctr_relativo                      | T3 [0.9399 a 1.151]        |   362 |         47   | 45.6 (263)                    | 50.5 (99)                       |
| ctr_relativo                      | T4 [1.152 a 3.285]         |   362 |         40.6 | 39.9 (278)                    | 42.9 (84)                       |
| ctr_relativo                      | sin dato                   |   543 |         47.1 | 47.8 (395)                    | 45.3 (148)                      |
| cambio_interlocutor_12m           | no                         |  1698 |         45.1 | 44.4 (1294)                   | 47.5 (404)                      |
| cambio_interlocutor_12m           | sí                         |   294 |         69.7 | 70.1 (221)                    | 68.5 (73)                       |
| reclamacion_sin_resolver_12m      | no                         |  1929 |         47.3 | 46.4 (1463)                   | 50.2 (466)                      |
| reclamacion_sin_resolver_12m      | sí                         |    63 |         92.1 | 96.2 (52)                     | 72.7 (11)                       |
| dias_sin_contacto                 | T1 [0 a 9]                 |   535 |         36.4 | 36.9 (371)                    | 35.4 (164)                      |
| dias_sin_contacto                 | T2 [10 a 22]               |   493 |         43   | 42.8 (388)                    | 43.8 (105)                      |
| dias_sin_contacto                 | T3 [23 a 57]               |   466 |         39.9 | 38.3 (376)                    | 46.7 (90)                       |
| dias_sin_contacto                 | T4 [58 a 447]              |   498 |         75.9 | 74.2 (380)                    | 81.4 (118)                      |
| facturas_vencidas_impagadas       | 0                          |  1914 |         49.2 | 48.6 (1457)                   | 51.2 (457)                      |
| facturas_vencidas_impagadas       | 1                          |    73 |         35.6 | 34.0 (53)                     | 40.0 (20)                       |
| facturas_vencidas_impagadas       | 2                          |     5 |         60   | 60.0 (5)                      | —                               |
| retraso_medio_cobro_12m           | T1 [0 a 5.25]              |   488 |         38.7 | 37.0 (362)                    | 43.7 (126)                      |
| retraso_medio_cobro_12m           | T2 [5.286 a 9]             |   501 |         54.1 | 56.0 (359)                    | 49.3 (142)                      |
| retraso_medio_cobro_12m           | T3 [9.1 a 14]              |   468 |         49.1 | 48.1 (374)                    | 53.2 (94)                       |
| retraso_medio_cobro_12m           | T4 [14.12 a 126]           |   476 |         59   | 57.1 (375)                    | 66.3 (101)                      |
| retraso_medio_cobro_12m           | sin dato                   |    59 |          0   | 0.0 (45)                      | 0.0 (14)                        |
| pedidos_firmados_pendientes       | 0                          |  1561 |         57.1 | 56.6 (1184)                   | 58.9 (377)                      |
| pedidos_firmados_pendientes       | 1                          |   390 |         19   | 18.9 (296)                    | 19.1 (94)                       |
| pedidos_firmados_pendientes       | 2                          |    37 |         13.5 | 9.4 (32)                      | 40.0 (5)                        |
| pedidos_firmados_pendientes       | 3 o más                    |     4 |          0   | 0.0 (3)                       | 0.0 (1)                         |
| propuestas_abiertas               | 0                          |  1442 |         54   | 54.5 (1084)                   | 52.5 (358)                      |
| propuestas_abiertas               | 1                          |   458 |         36.2 | 33.2 (352)                    | 46.2 (106)                      |
| propuestas_abiertas               | 2                          |    74 |         31.1 | 29.7 (64)                     | 40.0 (10)                       |
| propuestas_abiertas               | 3 o más                    |    18 |         16.7 | 13.3 (15)                     | 33.3 (3)                        |
| propuestas_perdidas_12m           | 0                          |   876 |         41.8 | 40.1 (670)                    | 47.1 (206)                      |
| propuestas_perdidas_12m           | 1                          |   671 |         49.8 | 50.1 (487)                    | 48.9 (184)                      |
| propuestas_perdidas_12m           | 2                          |   288 |         58.7 | 58.4 (226)                    | 59.7 (62)                       |
| propuestas_perdidas_12m           | 3 o más                    |   157 |         65   | 63.6 (132)                    | 72.0 (25)                       |
