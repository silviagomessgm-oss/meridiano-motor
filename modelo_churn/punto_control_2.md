# Punto de control 2 · Comparación de modelos (generado automáticamente)

Datos: `tablas`. Entrenamiento: 19 cortes (2020-12-31 a 2025-06-30, 1992 obs.); comparación «solo originales»: 4 cortes (477 obs.). Prueba: 2025-09-30, 2025-12-31 (251 obs., 142 anunciantes, 51.8 % de abandono). IC 95 %: bootstrap por anunciante (1000 remuestras, semilla 42).

Brier de referencia sin modelo (predecir siempre el 48.7 % de entrenamiento): 0.251.

## 1. Tabla comparativa (periodo de prueba)

| entrenamiento   | modelo                             | hiperparámetro        |   AUC | IC 95 % AUC    |   precisión top 12 · 2025-09-30 |   precisión top 12 · 2025-12-31 |   precisión top 12 · media |   precisión 25 % de más riesgo (top 31) |   Brier |
|:----------------|:-----------------------------------|:----------------------|------:|:---------------|--------------------------------:|--------------------------------:|---------------------------:|----------------------------------------:|--------:|
| ampliado        | (a) Referencia: valor de la cuenta | —                     | 0.518 | [0.431; 0.599] |                           0.417 |                           0.583 |                      0.500 |                                   0.548 |   0.257 |
| ampliado        | (b) Referencia: días sin campaña   | —                     | 0.731 | [0.659; 0.797] |                           0.833 |                           0.750 |                      0.792 |                                   0.742 |   0.212 |
| ampliado        | (c) Regresión logística            | C = 1.0               | 0.883 | [0.842; 0.920] |                           1.000 |                           1.000 |                      1.000 |                                   0.919 |   0.145 |
| ampliado        | (d) Árbol de decisión (3 niveles)  | min_samples_leaf = 10 | 0.861 | [0.818; 0.903] |                           1.000 |                           1.000 |                      1.000 |                                   0.774 |   0.146 |
| solo originales | (a) Referencia: valor de la cuenta | —                     | 0.518 | [0.431; 0.599] |                           0.417 |                           0.583 |                      0.500 |                                   0.548 |   0.259 |
| solo originales | (b) Referencia: días sin campaña   | —                     | 0.731 | [0.659; 0.797] |                           0.833 |                           0.750 |                      0.792 |                                   0.742 |   0.215 |
| solo originales | (c) Regresión logística            | C = 0.1               | 0.869 | [0.824; 0.909] |                           1.000 |                           1.000 |                      1.000 |                                   0.935 |   0.150 |
| solo originales | (d) Árbol de decisión (3 niveles)  | min_samples_leaf = 10 | 0.815 | [0.750; 0.873] |                           1.000 |                           1.000 |                      1.000 |                                   0.710 |   0.170 |

## 2. Diferencias de AUC emparejadas

| comparación                                                                                        |   dif. AUC | IC 95 %         |
|:---------------------------------------------------------------------------------------------------|-----------:|:----------------|
| (c) Regresión logística [ampliado] − (b) Referencia: días sin campaña [ampliado]                   |     +0.152 | [0.090; 0.213]  |
| (d) Árbol de decisión (3 niveles) [ampliado] − (b) Referencia: días sin campaña [ampliado]         |     +0.130 | [0.071; 0.185]  |
| (c) Regresión logística [ampliado] − (d) Árbol de decisión (3 niveles) [ampliado]                  |     +0.022 | [-0.017; 0.061] |
| (c) Regresión logística [ampliado] − (c) Regresión logística [solo originales]                     |     +0.014 | [0.000; 0.030]  |
| (d) Árbol de decisión (3 niveles) [ampliado] − (d) Árbol de decisión (3 niveles) [solo originales] |     +0.046 | [0.006; 0.086]  |

## 2 bis. AUC sin los casos fuera de temporada (entrenamiento ampliado)

Casos fuera de temporada en prueba: 50 de 251 (0.0 % de abandono). Resto: 201 obs., 64.7 % de abandono.

| modelo                             |   AUC | IC 95 % AUC    |
|:-----------------------------------|------:|:---------------|
| (a) Referencia: valor de la cuenta | 0.437 | [0.337; 0.531] |
| (b) Referencia: días sin campaña   | 0.665 | [0.573; 0.755] |
| (c) Regresión logística            | 0.853 | [0.801; 0.909] |
| (d) Árbol de decisión (3 niveles)  | 0.762 | [0.705; 0.820] |

## 3. Calibración por deciles (prueba, entrenamiento ampliado)

### (a) Referencia: valor de la cuenta

|   decil |   obs |   prob_media |   abandono_real |
|--------:|------:|-------------:|----------------:|
|       1 |    26 |         45.8 |            46.2 |
|       2 |    25 |         46   |            56   |
|       3 |    25 |         48.4 |            44   |
|       4 |    25 |         48.4 |            52   |
|       5 |    25 |         48.4 |            64   |
|       6 |    25 |         48.4 |            32   |
|       7 |    25 |         48.4 |            72   |
|       8 |    25 |         48.4 |            40   |
|       9 |    25 |         48.8 |            56   |
|      10 |    25 |         63.3 |            56   |

### (b) Referencia: días sin campaña

|   decil |   obs |   prob_media |   abandono_real |
|--------:|------:|-------------:|----------------:|
|       1 |    26 |         30.2 |            34.6 |
|       2 |    25 |         31.7 |            16   |
|       3 |    25 |         35   |            28   |
|       4 |    25 |         38.4 |            36   |
|       5 |    25 |         40.7 |            44   |
|       6 |    25 |         43.8 |            64   |
|       7 |    25 |         59.5 |            64   |
|       8 |    25 |         69   |            60   |
|       9 |    25 |         69.1 |            96   |
|      10 |    25 |         73.3 |            76   |

### (c) Regresión logística

|   decil |   obs |   prob_media |   abandono_real |
|--------:|------:|-------------:|----------------:|
|       1 |    26 |          1   |               0 |
|       2 |    25 |          8.6 |               8 |
|       3 |    25 |         16.7 |              28 |
|       4 |    25 |         25.3 |              40 |
|       5 |    25 |         39.5 |              32 |
|       6 |    25 |         52.2 |              64 |
|       7 |    25 |         61.4 |              76 |
|       8 |    25 |         70.3 |              80 |
|       9 |    25 |         86.3 |              92 |
|      10 |    25 |         96.2 |             100 |

### (d) Árbol de decisión (3 niveles)

|   decil |   obs |   prob_media |   abandono_real |
|--------:|------:|-------------:|----------------:|
|       1 |    26 |          0   |               0 |
|       2 |    25 |          0.3 |               0 |
|       3 |    25 |         14.2 |              20 |
|       4 |    25 |         37.2 |              32 |
|       5 |    25 |         59.5 |              56 |
|       6 |    25 |         59.5 |              80 |
|       7 |    25 |         59.5 |              68 |
|       8 |    25 |         59.5 |              88 |
|       9 |    25 |         69.5 |              80 |
|      10 |    25 |         95.2 |              96 |

## 4. Regresión logística: pesos (entrenamiento ampliado; última columna, solo originales)

Variables estandarizadas: el peso indica cuánto sube (+) o baja (−) el riesgo cuando la variable aumenta una desviación típica, con el resto igual. La columna «× odds» es el factor por el que se multiplica la razón abandono/permanencia.

|                                   |   peso (por 1 desv. típica) |   × probabilidad relativa (odds) por 1 desv. típica |   1 desv. típica equivale a |   peso · solo originales |
|:----------------------------------|----------------------------:|----------------------------------------------------:|----------------------------:|-------------------------:|
| dias_sin_contacto                 |                       0.891 |                                                2.44 |                       75.6  |                    0.723 |
| sin_dato_retraso_medio_cobro_12m  |                      -0.777 |                                                0.46 |                        0.17 |                   -0.338 |
| pedidos_firmados_pendientes       |                      -0.761 |                                                0.47 |                        0.49 |                   -0.641 |
| tendencia                         |                      -0.53  |                                                0.59 |                        0.86 |                   -0.796 |
| valor_mismo_periodo_anio_anterior |                       0.527 |                                                1.69 |                     5766.1  |                    0.292 |
| frecuencia_12m                    |                       0.493 |                                                1.64 |                        3.08 |                    0.321 |
| valor_12m                         |                      -0.461 |                                                0.63 |                     8606.95 |                   -0.157 |
| n_familias_12m                    |                       0.326 |                                                1.39 |                        0.64 |                    0.186 |
| cambio_interlocutor_12m           |                       0.303 |                                                1.35 |                        0.35 |                    0.3   |
| propuestas_abiertas               |                      -0.287 |                                                0.75 |                        0.6  |                   -0.055 |
| propuestas_perdidas_12m           |                       0.256 |                                                1.29 |                        1.04 |                    0.113 |
| ctr_relativo                      |                      -0.19  |                                                0.83 |                        0.29 |                   -0.253 |
| retraso_medio_cobro_12m           |                       0.123 |                                                1.13 |                        8.8  |                    0.197 |
| antiguedad_meses                  |                       0.075 |                                                1.08 |                       22.77 |                   -0.048 |
| sin_dato_ctr_relativo             |                       0.053 |                                                1.05 |                        0.45 |                   -0.057 |
| recencia_dias                     |                       0.04  |                                                1.04 |                      104.75 |                   -0.245 |

## 5. Árbol de decisión: reglas (entrenamiento ampliado)

| regla                                                                                                                    |   obs. entrenamiento |   % abandono entrenamiento |   obs. prueba |   % abandono prueba |
|:-------------------------------------------------------------------------------------------------------------------------|---------------------:|---------------------------:|--------------:|--------------------:|
| valor_mismo_periodo_anio_anterior > 84.65 y pedidos_firmados_pendientes ≤ 0.5 y dias_sin_contacto > 92                   |                  310 |                       95.2 |            32 |                96.9 |
| valor_mismo_periodo_anio_anterior > 84.65 y pedidos_firmados_pendientes ≤ 0.5 y dias_sin_contacto ≤ 92                   |                 1004 |                       59.5 |           121 |                71.9 |
| valor_mismo_periodo_anio_anterior > 84.65 y pedidos_firmados_pendientes > 0.5 y valor_mismo_periodo_anio_anterior > 3502 |                  193 |                       34.2 |            28 |                28.6 |
| valor_mismo_periodo_anio_anterior > 84.65 y pedidos_firmados_pendientes > 0.5 y valor_mismo_periodo_anio_anterior ≤ 3502 |                  166 |                        7.8 |            20 |                20   |
| valor_mismo_periodo_anio_anterior ≤ 84.65                                                                                |                  319 |                        0   |            50 |                 0   |

```
|--- valor_mismo_periodo_anio_anterior <= 84.650
|   |--- class: 0
|--- valor_mismo_periodo_anio_anterior >  84.650
|   |--- pedidos_firmados_pendientes <= 0.500
|   |   |--- dias_sin_contacto <= 92.000
|   |   |   |--- class: 1
|   |   |--- dias_sin_contacto >  92.000
|   |   |   |--- class: 1
|   |--- pedidos_firmados_pendientes >  0.500
|   |   |--- valor_mismo_periodo_anio_anterior <= 3502.425
|   |   |   |--- class: 0
|   |   |--- valor_mismo_periodo_anio_anterior >  3502.425
|   |   |   |--- class: 0
```

## 6. Elección de hiperparámetros (validación temporal dentro de entrenamiento)

### (c) Regresión logística · ampliado · elegido {'C': 1.0}

|     C |   AUC medio |   AUC 2024-09-30 |   AUC 2024-12-31 |   AUC 2025-03-31 |   AUC 2025-06-30 |
|------:|------------:|-----------------:|-----------------:|-----------------:|-----------------:|
| 0.010 |       0.837 |            0.832 |            0.876 |            0.810 |            0.832 |
| 0.030 |       0.838 |            0.831 |            0.876 |            0.815 |            0.831 |
| 0.100 |       0.840 |            0.834 |            0.875 |            0.821 |            0.831 |
| 0.300 |       0.840 |            0.835 |            0.874 |            0.823 |            0.830 |
| 1.000 |       0.841 |            0.836 |            0.874 |            0.824 |            0.830 |
| 3.000 |       0.841 |            0.836 |            0.873 |            0.824 |            0.830 |

### (d) Árbol de decisión (3 niveles) · ampliado · elegido {'min_samples_leaf': 10}

|   min_samples_leaf |   AUC medio |   AUC 2024-09-30 |   AUC 2024-12-31 |   AUC 2025-03-31 |   AUC 2025-06-30 |
|-------------------:|------------:|-----------------:|-----------------:|-----------------:|-----------------:|
|             10.000 |       0.814 |            0.836 |            0.807 |            0.800 |            0.815 |
|             20.000 |       0.814 |            0.836 |            0.807 |            0.800 |            0.815 |
|             40.000 |       0.814 |            0.836 |            0.807 |            0.800 |            0.815 |
|             80.000 |       0.814 |            0.836 |            0.807 |            0.800 |            0.815 |

### (c) Regresión logística · solo originales · elegido {'C': 0.1}

|     C |   AUC medio |   AUC 2024-12-31 |   AUC 2025-03-31 |   AUC 2025-06-30 |
|------:|------------:|-----------------:|-----------------:|-----------------:|
| 0.010 |       0.827 |            0.853 |            0.805 |            0.822 |
| 0.030 |       0.831 |            0.855 |            0.812 |            0.826 |
| 0.100 |       0.833 |            0.851 |            0.819 |            0.828 |
| 0.300 |       0.830 |            0.846 |            0.822 |            0.821 |
| 1.000 |       0.826 |            0.837 |            0.822 |            0.818 |
| 3.000 |       0.823 |            0.829 |            0.824 |            0.817 |

### (d) Árbol de decisión (3 niveles) · solo originales · elegido {'min_samples_leaf': 10}

|   min_samples_leaf |   AUC medio |   AUC 2024-12-31 |   AUC 2025-03-31 |   AUC 2025-06-30 |
|-------------------:|------------:|-----------------:|-----------------:|-----------------:|
|             10.000 |       0.768 |            0.785 |            0.754 |            0.764 |
|             20.000 |       0.748 |            0.772 |            0.694 |            0.777 |
|             40.000 |       0.760 |            0.752 |            0.761 |            0.766 |
|             80.000 |       0.623 |            0.500 |            0.686 |            0.683 |
