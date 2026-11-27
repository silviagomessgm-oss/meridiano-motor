# Punto de control 1 · Descripción del panel (generado automáticamente)

Datos: `tablas` (campañas de 2023-10-01 a 2026-09-01). Límite de W: día 1 del último mes con campañas.

Fechas de corte (6): 2024-09-30, 2024-12-31, 2025-03-31, 2025-06-30, 2025-09-30, 2025-12-31.

Prueba: 2025-09-30, 2025-12-31 (solo datos originales).

## 1. Observaciones y abandonos por fecha de corte

|                     | datos                 |   observaciones |   abandonos |   % abandono |   perdida_total |   contraccion |   activo |
|:--------------------|:----------------------|----------------:|------------:|-------------:|----------------:|--------------:|---------:|
| 2024-09-30          | solo datos originales |             115 |          59 |         51.3 |              47 |            12 |       56 |
| 2024-12-31          | solo datos originales |             123 |          64 |         52   |              47 |            17 |       59 |
| 2025-03-31          | solo datos originales |             121 |          61 |         50.4 |              46 |            15 |       60 |
| 2025-06-30          | solo datos originales |             118 |          58 |         49.2 |              45 |            13 |       60 |
| 2025-09-30 (prueba) | solo datos originales |             123 |          62 |         50.4 |              46 |            16 |       61 |
| 2025-12-31 (prueba) | solo datos originales |             128 |          68 |         53.1 |              54 |            14 |       60 |
| TOTAL               |                       |             728 |         372 |         51.1 |             285 |            87 |      356 |

## 2. Anunciantes distintos

|                                      |   anunciantes distintos |
|:-------------------------------------|------------------------:|
| Total panel                          |                     180 |
| Entrenamiento (4 cortes)             |                     156 |
| Prueba (2 cortes)                    |                     142 |
| En prueba y también en entrenamiento |                     118 |

|   nº de fechas de corte en que aparece |   anunciantes |
|---------------------------------------:|--------------:|
|                                      1 |            24 |
|                                      2 |            21 |
|                                      3 |            24 |
|                                      4 |            26 |
|                                      5 |            24 |
|                                      6 |            61 |

## 3. Entrenamiento: cortes con datos generados frente a cortes con solo datos originales

| fecha_corte           |   cortes |   observaciones |   anunciantes |   abandonos |   % abandono |
|:----------------------|---------:|----------------:|--------------:|------------:|-------------:|
| solo datos originales |        4 |             477 |           156 |         242 |         50.7 |

## 4. Distribución de cada variable (todas las fechas de corte)

|                                   |   n |   sin dato |      media |      mín |       p10 |       p25 |   mediana |          p75 |         p90 |         máx |   nº con 1 |   clientes distintos con 1 |
|:----------------------------------|----:|-----------:|-----------:|---------:|----------:|----------:|----------:|-------------:|------------:|------------:|-----------:|---------------------------:|
| recencia_dias                     | 728 |          0 |  144.8     |  29      |   29      |   58      |  121      |  213         | 304.3       | 365         |        nan |                        nan |
| frecuencia_12m                    | 728 |          0 |    3.651   |   1      |    1      |    1      |    3      |    5         |   8         |  17         |        nan |                        nan |
| antiguedad_meses                  | 728 |          0 |   51.99    |  12.1    |   17.7    |   30.85   |   49.25   |   67.33      |  90.43      | 155.9       |        nan |                        nan |
| valor_12m                         | 728 |          0 | 8285       | 244.5    | 1007      | 1894      | 5239      |    1.028e+04 |   2.137e+04 |   5.407e+04 |        nan |                        nan |
| valor_mismo_periodo_anio_anterior | 728 |          0 | 4752       |   0      |    0      |  807.8    | 2257      | 6692         |   1.218e+04 |   3.703e+04 |        nan |                        nan |
| tendencia                         | 728 |          0 |   -0.06186 |  -1      |   -1      |   -1      |   -0.3075 |    1         |   1         |   1         |        nan |                        nan |
| n_familias_12m                    | 728 |          0 |    1.372   |   1      |    1      |    1      |    1      |    2         |   2         |   4         |        nan |                        nan |
| ctr_relativo                      | 514 |        214 |    0.9888  |   0.4114 |    0.6737 |    0.7929 |    0.9638 |    1.157     |   1.349     |   1.828     |        nan |                        nan |
| cambio_interlocutor_12m           | 728 |          0 |  nan       | nan      |  nan      |  nan      |  nan      |  nan         | nan         | nan         |        107 |                         48 |
| reclamacion_sin_resolver_12m      | 728 |          0 |  nan       | nan      |  nan      |  nan      |  nan      |  nan         | nan         | nan         |         14 |                          5 |
| dias_sin_contacto                 | 728 |          0 |   49.59    |   0      |    2      |    6      |   20      |   54.25      | 158         | 381         |        nan |                        nan |
| facturas_vencidas_impagadas       | 728 |          0 |    0.04121 |   0      |    0      |    0      |    0      |    0         |   0         |   1         |        nan |                        nan |
| retraso_medio_cobro_12m           | 698 |         30 |    9.89    |   0      |    1      |    4.5    |    8      |   12.67      |  19         |  95         |        nan |                        nan |
| pedidos_firmados_pendientes       | 728 |          0 |    0.2486  |   0      |    0      |    0      |    0      |    0         |   1         |   3         |        nan |                        nan |
| propuestas_abiertas               | 728 |          0 |    0.2706  |   0      |    0      |    0      |    0      |    0         |   1         |   3         |        nan |                        nan |
| propuestas_perdidas_12m           | 728 |          0 |    0.8255  |   0      |    0      |    0      |    1      |    1         |   2         |   4         |        nan |                        nan |

## 5. % de abandono por tramos de cada variable (solo entrenamiento)

| variable                          | tramo                 |   obs |   % abandono | % con datos generados (obs)   | % solo datos originales (obs)   |
|:----------------------------------|:----------------------|------:|-------------:|:------------------------------|:--------------------------------|
| recencia_dias                     | T1 [29 a 58]          |   125 |         41.6 | —                             | 41.6 (125)                      |
| recencia_dias                     | T2 [60 a 121]         |   127 |         41.7 | —                             | 41.7 (127)                      |
| recencia_dias                     | T3 [149 a 213]        |   107 |         52.3 | —                             | 52.3 (107)                      |
| recencia_dias                     | T4 [241 a 365]        |   118 |         68.6 | —                             | 68.6 (118)                      |
| frecuencia_12m                    | T1 [1 a 3]            |   288 |         48.3 | —                             | 48.3 (288)                      |
| frecuencia_12m                    | T2 [4 a 5]            |    93 |         53.8 | —                             | 53.8 (93)                       |
| frecuencia_12m                    | T3 [6 a 16]           |    96 |         55.2 | —                             | 55.2 (96)                       |
| antiguedad_meses                  | T1 [12.1 a 33.2]      |   122 |         57.4 | —                             | 57.4 (122)                      |
| antiguedad_meses                  | T2 [33.4 a 48.1]      |   117 |         50.4 | —                             | 50.4 (117)                      |
| antiguedad_meses                  | T3 [48.5 a 64.6]      |   119 |         53.8 | —                             | 53.8 (119)                      |
| antiguedad_meses                  | T4 [64.9 a 152.9]     |   119 |         41.2 | —                             | 41.2 (119)                      |
| valor_12m                         | T1 [244.5 a 2010]     |   120 |         57.5 | —                             | 57.5 (120)                      |
| valor_12m                         | T2 [2025 a 4973]      |   119 |         48.7 | —                             | 48.7 (119)                      |
| valor_12m                         | T3 [5029 a 9948]      |   119 |         47.9 | —                             | 47.9 (119)                      |
| valor_12m                         | T4 [9975 a 4.978e+04] |   119 |         48.7 | —                             | 48.7 (119)                      |
| valor_mismo_periodo_anio_anterior | T1 [0 a 860.6]        |   120 |         25   | —                             | 25.0 (120)                      |
| valor_mismo_periodo_anio_anterior | T2 [866.5 a 2275]     |   121 |         56.2 | —                             | 56.2 (121)                      |
| valor_mismo_periodo_anio_anterior | T3 [2294 a 6603]      |   117 |         64.1 | —                             | 64.1 (117)                      |
| valor_mismo_periodo_anio_anterior | T4 [6667 a 3.703e+04] |   119 |         58   | —                             | 58.0 (119)                      |
| tendencia                         | T1 [-1 a -0.385]      |   239 |         68.6 | —                             | 68.6 (239)                      |
| tendencia                         | T2 [-0.3839 a 1]      |   238 |         32.8 | —                             | 32.8 (238)                      |
| n_familias_12m                    | 1                     |   335 |         49   | —                             | 49.0 (335)                      |
| n_familias_12m                    | 2                     |   115 |         50.4 | —                             | 50.4 (115)                      |
| n_familias_12m                    | 3 o más               |    27 |         74.1 | —                             | 74.1 (27)                       |
| ctr_relativo                      | T1 [0.4114 a 0.7979]  |    83 |         61.4 | —                             | 61.4 (83)                       |
| ctr_relativo                      | T2 [0.7982 a 0.9761]  |    82 |         59.8 | —                             | 59.8 (82)                       |
| ctr_relativo                      | T3 [0.9782 a 1.156]   |    82 |         50   | —                             | 50.0 (82)                       |
| ctr_relativo                      | T4 [1.158 a 1.828]    |    82 |         41.5 | —                             | 41.5 (82)                       |
| ctr_relativo                      | sin dato              |   148 |         45.3 | —                             | 45.3 (148)                      |
| cambio_interlocutor_12m           | no                    |   404 |         47.5 | —                             | 47.5 (404)                      |
| cambio_interlocutor_12m           | sí                    |    73 |         68.5 | —                             | 68.5 (73)                       |
| reclamacion_sin_resolver_12m      | no                    |   466 |         50.2 | —                             | 50.2 (466)                      |
| reclamacion_sin_resolver_12m      | sí                    |    11 |         72.7 | —                             | 72.7 (11)                       |
| dias_sin_contacto                 | T1 [0 a 7]            |   137 |         36.5 | —                             | 36.5 (137)                      |
| dias_sin_contacto                 | T2 [8 a 19]           |   107 |         37.4 | —                             | 37.4 (107)                      |
| dias_sin_contacto                 | T3 [20 a 55]          |   114 |         49.1 | —                             | 49.1 (114)                      |
| dias_sin_contacto                 | T4 [57 a 381]         |   119 |         80.7 | —                             | 80.7 (119)                      |
| facturas_vencidas_impagadas       | 0                     |   457 |         51.2 | —                             | 51.2 (457)                      |
| facturas_vencidas_impagadas       | 1                     |    20 |         40   | —                             | 40.0 (20)                       |
| retraso_medio_cobro_12m           | T1 [0 a 5]            |   123 |         43.9 | —                             | 43.9 (123)                      |
| retraso_medio_cobro_12m           | T2 [5.125 a 8.2]      |   109 |         45.9 | —                             | 45.9 (109)                      |
| retraso_medio_cobro_12m           | T3 [8.25 a 13]        |   116 |         54.3 | —                             | 54.3 (116)                      |
| retraso_medio_cobro_12m           | T4 [13.24 a 95]       |   115 |         65.2 | —                             | 65.2 (115)                      |
| retraso_medio_cobro_12m           | sin dato              |    14 |          0   | —                             | 0.0 (14)                        |
| pedidos_firmados_pendientes       | 0                     |   377 |         58.9 | —                             | 58.9 (377)                      |
| pedidos_firmados_pendientes       | 1                     |    94 |         19.1 | —                             | 19.1 (94)                       |
| pedidos_firmados_pendientes       | 2                     |     5 |         40   | —                             | 40.0 (5)                        |
| pedidos_firmados_pendientes       | 3 o más               |     1 |          0   | —                             | 0.0 (1)                         |
| propuestas_abiertas               | 0                     |   358 |         52.5 | —                             | 52.5 (358)                      |
| propuestas_abiertas               | 1                     |   106 |         46.2 | —                             | 46.2 (106)                      |
| propuestas_abiertas               | 2                     |    10 |         40   | —                             | 40.0 (10)                       |
| propuestas_abiertas               | 3 o más               |     3 |         33.3 | —                             | 33.3 (3)                        |
| propuestas_perdidas_12m           | 0                     |   217 |         45.6 | —                             | 45.6 (217)                      |
| propuestas_perdidas_12m           | 1                     |   176 |         51.1 | —                             | 51.1 (176)                      |
| propuestas_perdidas_12m           | 2                     |    63 |         61.9 | —                             | 61.9 (63)                       |
| propuestas_perdidas_12m           | 3 o más               |    21 |         66.7 | —                             | 66.7 (21)                       |
