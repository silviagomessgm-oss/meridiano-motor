# Punto de control 1 · Descripción del panel (generado automáticamente)

Fechas de corte: 2024-09-30, 2024-12-31, 2025-03-31, 2025-06-30, 2025-09-30, 2025-12-31. Prueba: 2025-09-30, 2025-12-31. Fin de datos de campañas: 2026-09-30.

## 1. Observaciones y abandonos por fecha de corte

|                     |   observaciones |   abandonos |   % abandono |   perdida_total |   contraccion |   nuevo_sin_campana |   activo |   nuevo_activo |
|:--------------------|----------------:|------------:|-------------:|----------------:|--------------:|--------------------:|---------:|---------------:|
| 2024-09-30          |             135 |          67 |         49.6 |              47 |            12 |                   8 |       56 |             12 |
| 2024-12-31          |             150 |          72 |         48   |              47 |            17 |                   8 |       59 |             19 |
| 2025-03-31          |             139 |          66 |         47.5 |              46 |            15 |                   5 |       60 |             13 |
| 2025-06-30          |             139 |          68 |         48.9 |              45 |            13 |                  10 |       60 |             11 |
| 2025-09-30 (prueba) |             139 |          69 |         49.6 |              46 |            16 |                   7 |       61 |              9 |
| 2025-12-31 (prueba) |             144 |          76 |         52.8 |              54 |            14 |                   8 |       60 |              8 |
| TOTAL               |             846 |         418 |         49.4 |             285 |            87 |                  46 |      356 |             72 |

## 2. Anunciantes distintos

|                                      |   anunciantes distintos |
|:-------------------------------------|------------------------:|
| Total panel                          |                     196 |
| Entrenamiento (4 cortes)             |                     177 |
| Prueba (2 cortes)                    |                     158 |
| En prueba y también en entrenamiento |                     139 |

|   nº de fechas de corte en que aparece |   anunciantes |
|---------------------------------------:|--------------:|
|                                      1 |            20 |
|                                      2 |            16 |
|                                      3 |            27 |
|                                      4 |            24 |
|                                      5 |            37 |
|                                      6 |            72 |

## 3. Distribución de cada variable (todas las fechas de corte)

|                              |   n |   sin dato |      media |      mín |      p10 |       p25 |    mediana |      p75 |         p90 |         máx |   nº con 1 |   clientes distintos con 1 |
|:-----------------------------|----:|-----------:|-----------:|---------:|---------:|----------:|-----------:|---------:|------------:|------------:|-----------:|---------------------------:|
| recencia_dias                | 846 |          0 |  137.6     |  29      |  29      |   30      |  121       |  213     | 303         | 365         |        nan |                        nan |
| frecuencia_12m               | 846 |          0 |    3.506   |   1      |   1      |    1      |    3       |    4.75  |   7         |  17         |        nan |                        nan |
| antiguedad_meses             | 846 |          0 |   45.82    |   2.2    |   9.65   |   20.12   |   44.3     |   64.17  |  86.5       | 155.9       |        nan |                        nan |
| valor_12m                    | 846 |          0 | 7698       | 244.5    | 873.2    | 1702      | 4520       | 9525     |   1.992e+04 |   5.407e+04 |        nan |                        nan |
| tendencia                    | 846 |          0 |    0.02943 |  -1      |  -1      |   -1      |   -0.03245 |    1     |   1         |   1         |        nan |                        nan |
| n_familias_12m               | 846 |          0 |    1.346   |   1      |   1      |    1      |    1       |    2     |   2         |   4         |        nan |                        nan |
| ctr_relativo                 | 598 |        248 |    0.9778  |   0.4114 |   0.6747 |    0.7911 |    0.9396  |    1.146 |   1.339     |   1.912     |        nan |                        nan |
| cambio_interlocutor_12m      | 846 |          0 |  nan       | nan      | nan      |  nan      |  nan       |  nan     | nan         | nan         |        133 |                         56 |
| reclamacion_sin_resolver_12m | 846 |          0 |  nan       | nan      | nan      |  nan      |  nan       |  nan     | nan         | nan         |         14 |                          5 |
| dias_sin_contacto            | 846 |          0 |   47.21    |   0      |   2      |    6      |   19       |   52.75  | 143         | 381         |        nan |                        nan |
| facturas_vencidas_impagadas  | 846 |          0 |    0.04019 |   0      |   0      |    0      |    0       |    0     |   0         |   1         |        nan |                        nan |
| retraso_medio_cobro_12m      | 797 |         49 |    9.62    |   0      |   1      |    4.429  |    7.75    |   12.29  |  18.8       |  95         |        nan |                        nan |
| pedidos_firmados_pendientes  | 846 |          0 |    0.2518  |   0      |   0      |    0      |    0       |    0     |   1         |   3         |        nan |                        nan |
| propuestas_abiertas          | 846 |          0 |    0.2707  |   0      |   0      |    0      |    0       |    0     |   1         |   3         |        nan |                        nan |
| propuestas_perdidas_12m      | 846 |          0 |    0.8381  |   0      |   0      |    0      |    1       |    1     |   2         |   4         |        nan |                        nan |

## 4. % de abandono por tramos de cada variable (solo entrenamiento)

| variable                     | tramo                        |   obs |   % abandono |
|:-----------------------------|:-----------------------------|------:|-------------:|
| recencia_dias                | Q1 (bajo) [29 a 30]          |   141 |         34   |
| recencia_dias                | Q2 [30 a 120]                |   141 |         39   |
| recencia_dias                | Q3 [121 a 213]               |   140 |         52.1 |
| recencia_dias                | Q4 (alto) [213 a 365]        |   141 |         68.8 |
| frecuencia_12m               | Q1 (bajo) [1 a 1]            |   141 |         47.5 |
| frecuencia_12m               | Q2 [1 a 3]                   |   141 |         41.1 |
| frecuencia_12m               | Q3 [3 a 5]                   |   140 |         52.9 |
| frecuencia_12m               | Q4 (alto) [5 a 16]           |   141 |         52.5 |
| antiguedad_meses             | Q1 (bajo) [2.2 a 20.6]       |   141 |         41.8 |
| antiguedad_meses             | Q2 [20.8 a 43.4]             |   141 |         56   |
| antiguedad_meses             | Q3 [43.4 a 61.6]             |   140 |         54.3 |
| antiguedad_meses             | Q4 (alto) [62.1 a 152.9]     |   141 |         41.8 |
| valor_12m                    | Q1 (bajo) [244.5 a 1705]     |   141 |         53.9 |
| valor_12m                    | Q2 [1705 a 4340]             |   141 |         48.2 |
| valor_12m                    | Q3 [4346 a 9253]             |   140 |         43.6 |
| valor_12m                    | Q4 (alto) [9253 a 4.978e+04] |   141 |         48.2 |
| tendencia                    | Q1 (bajo) [-1 a -1]          |   141 |         68.8 |
| tendencia                    | Q2 [-1 a -0.1446]            |   141 |         68.1 |
| tendencia                    | Q3 [-0.1383 a 1]             |   140 |         35.7 |
| tendencia                    | Q4 (alto) [1 a 1]            |   141 |         21.3 |
| n_familias_12m               | 1                            |   404 |         47   |
| n_familias_12m               | 2 o más                      |   159 |         52.2 |
| ctr_relativo                 | Q1 (bajo) [0.4114 a 0.7868]  |    98 |         58.2 |
| ctr_relativo                 | Q2 [0.7884 a 0.937]          |    98 |         51   |
| ctr_relativo                 | Q3 [0.938 a 1.126]           |    98 |         55.1 |
| ctr_relativo                 | Q4 (alto) [1.133 a 1.828]    |    98 |         38.8 |
| ctr_relativo                 | sin dato                     |   171 |         43.3 |
| cambio_interlocutor_12m      | no                           |   476 |         45.2 |
| cambio_interlocutor_12m      | sí                           |    87 |         66.7 |
| reclamacion_sin_resolver_12m | no                           |   552 |         48   |
| reclamacion_sin_resolver_12m | sí                           |    11 |         72.7 |
| dias_sin_contacto            | Q1 (bajo) [0 a 6]            |   141 |         29.8 |
| dias_sin_contacto            | Q2 [6 a 18]                  |   141 |         36.2 |
| dias_sin_contacto            | Q3 [18 a 52]                 |   140 |         50   |
| dias_sin_contacto            | Q4 (alto) [52 a 381]         |   141 |         78   |
| facturas_vencidas_impagadas  | 0                            |   541 |         48.8 |
| facturas_vencidas_impagadas  | 1                            |    22 |         40.9 |
| retraso_medio_cobro_12m      | Q1 (bajo) [0 a 4.571]        |   135 |         37.8 |
| retraso_medio_cobro_12m      | Q2 [4.625 a 8]               |   134 |         49.3 |
| retraso_medio_cobro_12m      | Q3 [8 a 12.5]                |   134 |         53   |
| retraso_medio_cobro_12m      | Q4 (alto) [12.5 a 95]        |   135 |         61.5 |
| retraso_medio_cobro_12m      | sin dato                     |    25 |          8   |
| pedidos_firmados_pendientes  | 0                            |   441 |         57.4 |
| pedidos_firmados_pendientes  | 1                            |   115 |         15.7 |
| pedidos_firmados_pendientes  | 2 o más                      |     7 |         28.6 |
| propuestas_abiertas          | 0                            |   424 |         50.7 |
| propuestas_abiertas          | 1                            |   124 |         41.9 |
| propuestas_abiertas          | 2 o más                      |    15 |         40   |
| propuestas_perdidas_12m      | 0                            |   252 |         45.6 |
| propuestas_perdidas_12m      | 1                            |   213 |         46.9 |
| propuestas_perdidas_12m      | 2 o más                      |    98 |         59.2 |

## 5. Sensibilidad de la etiqueta y la población

| fecha_corte   |   obs |   abandonos E2 (regla W) | abandonos con regla 365 d   | cambian 0→1   |   nuevos (por alta) |   nuevos (por 1ª campaña) |   población 365 días |   población 12 meses |
|:--------------|------:|-------------------------:|:----------------------------|:--------------|--------------------:|--------------------------:|---------------------:|---------------------:|
| 2024-09-30    |   135 |                       67 | 70                          | 3             |                  20 |                       135 |                  131 |                  135 |
| 2024-12-31    |   150 |                       72 | 77                          | 5             |                  27 |                        97 |                  145 |                  150 |
| 2025-03-31    |   139 |                       66 | 69                          | 3             |                  18 |                        65 |                  139 |                  139 |
| 2025-06-30    |   139 |                       68 | 74                          | 6             |                  21 |                        54 |                  139 |                  139 |
| 2025-09-30    |   139 |                       69 | 76                          | 7             |                  16 |                        48 |                  139 |                  139 |
| 2025-12-31    |   144 |                       76 | no observable               | —             |                  16 |                        38 |                  144 |                  144 |
