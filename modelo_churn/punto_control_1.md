# Punto de control 1 · Descripción del panel (generado automáticamente)

Fechas de corte: 2024-09-30, 2024-12-31, 2025-03-31, 2025-06-30, 2025-09-30, 2025-12-31. Prueba: 2025-09-30, 2025-12-31. Fin de datos de campañas: 2026-09-30.

## 1. Observaciones y abandonos por fecha de corte

|                     |   observaciones |   abandonos |   % abandono |   perdida_total |   contraccion |   activo |
|:--------------------|----------------:|------------:|-------------:|----------------:|--------------:|---------:|
| 2024-09-30          |             115 |          59 |         51.3 |              47 |            12 |       56 |
| 2024-12-31          |             123 |          64 |         52   |              47 |            17 |       59 |
| 2025-03-31          |             121 |          61 |         50.4 |              46 |            15 |       60 |
| 2025-06-30          |             118 |          58 |         49.2 |              45 |            13 |       60 |
| 2025-09-30 (prueba) |             123 |          62 |         50.4 |              46 |            16 |       61 |
| 2025-12-31 (prueba) |             128 |          68 |         53.1 |              54 |            14 |       60 |
| TOTAL               |             728 |         372 |         51.1 |             285 |            87 |      356 |

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

## 3. Distribución de cada variable (todas las fechas de corte)

|                              |   n |   sin dato |      media |      mín |       p10 |       p25 |   mediana |         p75 |         p90 |         máx |   nº con 1 |   clientes distintos con 1 |
|:-----------------------------|----:|-----------:|-----------:|---------:|----------:|----------:|----------:|------------:|------------:|------------:|-----------:|---------------------------:|
| recencia_dias                | 728 |          0 |  144.8     |  29      |   29      |   58      |  121      | 213         | 304.3       | 365         |        nan |                        nan |
| frecuencia_12m               | 728 |          0 |    3.651   |   1      |    1      |    1      |    3      |   5         |   8         |  17         |        nan |                        nan |
| antiguedad_meses             | 728 |          0 |   51.99    |  12.1    |   17.7    |   30.85   |   49.25   |  67.33      |  90.43      | 155.9       |        nan |                        nan |
| valor_12m                    | 728 |          0 | 8285       | 244.5    | 1007      | 1894      | 5239      |   1.028e+04 |   2.137e+04 |   5.407e+04 |        nan |                        nan |
| tendencia                    | 728 |          0 |   -0.06186 |  -1      |   -1      |   -1      |   -0.3075 |   1         |   1         |   1         |        nan |                        nan |
| n_familias_12m               | 728 |          0 |    1.372   |   1      |    1      |    1      |    1      |   2         |   2         |   4         |        nan |                        nan |
| ctr_relativo                 | 514 |        214 |    0.9888  |   0.4114 |    0.6737 |    0.7929 |    0.9638 |   1.157     |   1.349     |   1.828     |        nan |                        nan |
| cambio_interlocutor_12m      | 728 |          0 |  nan       | nan      |  nan      |  nan      |  nan      | nan         | nan         | nan         |        107 |                         48 |
| reclamacion_sin_resolver_12m | 728 |          0 |  nan       | nan      |  nan      |  nan      |  nan      | nan         | nan         | nan         |         14 |                          5 |
| dias_sin_contacto            | 728 |          0 |   49.59    |   0      |    2      |    6      |   20      |  54.25      | 158         | 381         |        nan |                        nan |
| facturas_vencidas_impagadas  | 728 |          0 |    0.04121 |   0      |    0      |    0      |    0      |   0         |   0         |   1         |        nan |                        nan |
| retraso_medio_cobro_12m      | 698 |         30 |    9.89    |   0      |    1      |    4.5    |    8      |  12.67      |  19         |  95         |        nan |                        nan |
| pedidos_firmados_pendientes  | 728 |          0 |    0.2486  |   0      |    0      |    0      |    0      |   0         |   1         |   3         |        nan |                        nan |
| propuestas_abiertas          | 728 |          0 |    0.2706  |   0      |    0      |    0      |    0      |   0         |   1         |   3         |        nan |                        nan |
| propuestas_perdidas_12m      | 728 |          0 |    0.8255  |   0      |    0      |    0      |    1      |   1         |   2         |   4         |        nan |                        nan |

## 4. % de abandono por tramos de cada variable (solo entrenamiento)

| variable                     | tramo                        |   obs |   % abandono |
|:-----------------------------|:-----------------------------|------:|-------------:|
| recencia_dias                | Q1 (bajo) [29 a 58]          |   120 |         40.8 |
| recencia_dias                | Q2 [58 a 121]                |   119 |         39.5 |
| recencia_dias                | Q3 [121 a 213]               |   119 |         53.8 |
| recencia_dias                | Q4 (alto) [213 a 365]        |   119 |         68.9 |
| frecuencia_12m               | Q1 (bajo) [1 a 1]            |   120 |         46.7 |
| frecuencia_12m               | Q2 [1 a 3]                   |   119 |         46.2 |
| frecuencia_12m               | Q3 [3 a 5]                   |   119 |         56.3 |
| frecuencia_12m               | Q4 (alto) [5 a 16]           |   119 |         53.8 |
| antiguedad_meses             | Q1 (bajo) [12.1 a 33.2]      |   120 |         56.7 |
| antiguedad_meses             | Q2 [33.2 a 48.1]             |   119 |         51.3 |
| antiguedad_meses             | Q3 [48.5 a 64.6]             |   119 |         53.8 |
| antiguedad_meses             | Q4 (alto) [64.9 a 152.9]     |   119 |         41.2 |
| valor_12m                    | Q1 (bajo) [244.5 a 2010]     |   120 |         57.5 |
| valor_12m                    | Q2 [2025 a 4973]             |   119 |         48.7 |
| valor_12m                    | Q3 [5029 a 9948]             |   119 |         47.9 |
| valor_12m                    | Q4 (alto) [9975 a 4.978e+04] |   119 |         48.7 |
| tendencia                    | Q1 (bajo) [-1 a -1]          |   120 |         67.5 |
| tendencia                    | Q2 [-1 a -0.385]             |   119 |         69.7 |
| tendencia                    | Q3 [-0.3839 a 1]             |   119 |         46.2 |
| tendencia                    | Q4 (alto) [1 a 1]            |   119 |         19.3 |
| n_familias_12m               | 1                            |   335 |         49   |
| n_familias_12m               | 2 o más                      |   142 |         54.9 |
| ctr_relativo                 | Q1 (bajo) [0.4114 a 0.7979]  |    83 |         61.4 |
| ctr_relativo                 | Q2 [0.7982 a 0.9761]         |    82 |         59.8 |
| ctr_relativo                 | Q3 [0.9782 a 1.156]          |    82 |         50   |
| ctr_relativo                 | Q4 (alto) [1.158 a 1.828]    |    82 |         41.5 |
| ctr_relativo                 | sin dato                     |   148 |         45.3 |
| cambio_interlocutor_12m      | no                           |   404 |         47.5 |
| cambio_interlocutor_12m      | sí                           |    73 |         68.5 |
| reclamacion_sin_resolver_12m | no                           |   466 |         50.2 |
| reclamacion_sin_resolver_12m | sí                           |    11 |         72.7 |
| dias_sin_contacto            | Q1 (bajo) [0 a 7]            |   120 |         34.2 |
| dias_sin_contacto            | Q2 [7 a 19]                  |   119 |         38.7 |
| dias_sin_contacto            | Q3 [19 a 55]                 |   119 |         49.6 |
| dias_sin_contacto            | Q4 (alto) [57 a 381]         |   119 |         80.7 |
| facturas_vencidas_impagadas  | 0                            |   457 |         51.2 |
| facturas_vencidas_impagadas  | 1                            |    20 |         40   |
| retraso_medio_cobro_12m      | Q1 (bajo) [0 a 5]            |   116 |         44   |
| retraso_medio_cobro_12m      | Q2 [5 a 8.2]                 |   116 |         45.7 |
| retraso_medio_cobro_12m      | Q3 [8.25 a 13]               |   115 |         53.9 |
| retraso_medio_cobro_12m      | Q4 (alto) [13 a 95]          |   116 |         65.5 |
| retraso_medio_cobro_12m      | sin dato                     |    14 |          0   |
| pedidos_firmados_pendientes  | 0                            |   377 |         58.9 |
| pedidos_firmados_pendientes  | 1                            |    94 |         19.1 |
| pedidos_firmados_pendientes  | 2 o más                      |     6 |         33.3 |
| propuestas_abiertas          | 0                            |   358 |         52.5 |
| propuestas_abiertas          | 1                            |   106 |         46.2 |
| propuestas_abiertas          | 2 o más                      |    13 |         38.5 |
| propuestas_perdidas_12m      | 0                            |   217 |         45.6 |
| propuestas_perdidas_12m      | 1                            |   176 |         51.1 |
| propuestas_perdidas_12m      | 2 o más                      |    84 |         63.1 |

## 5. Sensibilidad de la etiqueta y la población

| fecha_corte   |   obs |   abandonos E2 (regla W) | abandonos con regla 365 d   | cambian 0→1   |   nuevos (por alta) |   nuevos (por 1ª campaña) |   población 365 días |   población 12 meses |
|:--------------|------:|-------------------------:|:----------------------------|:--------------|--------------------:|--------------------------:|---------------------:|---------------------:|
| 2024-09-30    |   135 |                       67 | 70                          | 3             |                  20 |                       135 |                  131 |                  135 |
| 2024-12-31    |   150 |                       72 | 77                          | 5             |                  27 |                        97 |                  145 |                  150 |
| 2025-03-31    |   139 |                       66 | 69                          | 3             |                  18 |                        65 |                  139 |                  139 |
| 2025-06-30    |   139 |                       68 | 74                          | 6             |                  21 |                        54 |                  139 |                  139 |
| 2025-09-30    |   139 |                       69 | 76                          | 7             |                  16 |                        48 |                  139 |                  139 |
| 2025-12-31    |   144 |                       76 | no observable               | —             |                  16 |                        38 |                  144 |                  144 |
