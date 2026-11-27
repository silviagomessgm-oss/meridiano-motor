# Tablas ampliadas (ene-2020 → 27-nov-2026)

Ampliación de los datos sintéticos del TFP para entrenar el modelo de abandono con más historia. **Las tablas originales
(`tablas/`, oct-2023 → sep-2026) no se modifican**: en cada archivo de esta carpeta, las filas originales están copiadas
byte a byte al principio y las filas nuevas se añaden al final, con identificadores que continúan la numeración.

`tablas/` sigue siendo la fuente de la hoja de Google, de los tests y de la demo. Esta carpeta es solo para el modelo.

**Declaración:** la ampliación la ha generado una IA (Claude) a petición de la alumna, con el método que se describe a
continuación, calibrado con los datos originales. El modelo de abandono no forma parte de esta carpeta.

## Qué se ha añadido

| Tabla | Filas originales | Filas nuevas | Total |
|---|---|---|---|
| dim_clientes | 267 | 125 | 392 |
| contactos | 296 | 134 | 430 |
| fact_campanas | 1.432 | 1.534 | 2.966 |
| fact_facturacion | 1.432 | 1.534 | 2.966 |
| fact_interacciones | 9.620 | 10.150 | 19.770 |
| oportunidades | 2.076 | 2.889 | 4.965 |
| dim_comercial, dim_productos | sin cambios | — | — |

- **Hacia atrás (ene-2020 → sep-2023):** la historia previa de los anunciantes actuales dados de alta antes de oct-2023
  y 120 anunciantes antiguos (C0321 en adelante) que abandonaron antes de oct-2023, por lo que no aparecían en los datos.
- **Hacia delante (sep-2026 → 27-nov-2026):** la continuación de los anunciantes que seguían activos y 5 altas nuevas.

## Método

Pensado para no introducir reglas nuevas que luego «descubra» el modelo:

1. **Campañas:** cada campaña nueva es una copia de una campaña real de un anunciante del mismo tamaño (productos,
   importes, duración, impresiones y clics), desplazada en el tiempo y con un ±5 % de ruido. Los anunciantes actuales
   siguen su propio ritmo anual y su estacionalidad, mezclada con la de su sector.
2. **Abandono:** mecanismo documentado en el caso. El 70 % de las bajas va precedido de un descenso de la inversión
   (−40 %) y del CTR (−30 %) en los últimos 6 meses; el 30 % desaparece de golpe. Algunos anunciantes actuales se dan de
   baja antes de 2023 y vuelven en el periodo original (reactivación, como en los datos reales).
3. **Señales:** cambio de interlocutor y reclamaciones calibrados para que su relación con el abandono sea parecida a la
   original, sin superarla.
4. **Facturas, interacciones y oportunidades:** con las frecuencias y distribuciones medidas en los datos originales
   (condiciones de pago y retraso por cliente, ≈ 1,9 interacciones por cliente activo y mes, tasa de éxito de 53,6 % en
   ampliaciones y 11 % en leads). Las facturas aún no cobradas a 27-nov-2026 quedan como «Pendiente».

Supuestos: anunciantes activos por ejercicio de 98 (EF2020, año de la pandemia, solo ene–sep), 110, 122 y 130; tarifas
de los productos iguales a las actuales.

## Comprobaciones

- Filas originales idénticas byte a byte en las 8 tablas; identificadores únicos; todas las referencias enlazan
  (campaña → cliente, factura → orden, oportunidad → orden y cliente, todo cliente con contacto).
- Reproducible: semilla fija; dos ejecuciones dan archivos idénticos.

| Por ejercicio | EF2021 | EF2022 | EF2023 | EF2024* | EF2025* | EF2026* |
|---|---|---|---|---|---|---|
| Anunciantes activos | 110 | 122 | 130 | 135 | 139 | 146 |
| Retenidos del año anterior | 53 %** | 72 % | 66 % | 61 % | 67 % | 63 % |

\* Datos originales. \*\* EF2020 solo tiene nueve meses, lo que rebaja la retención de EF2021.

Fuerza de las señales (abandono = sin campaña en los 210 días siguientes; con la señal frente a sin ella):

| Señal | Parte nueva (cortes 2021–2022) | Parte original (cortes 2024–2025) |
|---|---|---|
| Abandono medio | 42 % | 45 % |
| Inversión a la baja | 49 % vs 35 % | 55 % vs 32 % |
| Cambio de interlocutor | 54 % vs 41 % | 66 % vs 41 % |
| Reclamación sin resolver | 89 % vs 42 % (n = 9) | 86 % vs 44 % (n = 14) |
| CTR bajo | 51 % vs 40 % | 50 % vs 43 % |
| Más de 180 días sin campaña | 62 % vs 33 % | 63 % vs 36 % |

En la parte nueva las señales son iguales o algo más débiles que en la original: el generador no regala ventaja al modelo.

## Qué cambia para el modelo

| | Solo originales | Ampliadas |
|---|---|---|
| Fechas de corte trimestrales con un año de historia y resultado a 210 días | 6 | 21 |
| Observaciones (anunciante × fecha de corte) | 837 | 2.675 |
| Abandonos | 374 | 1.181 |
| Anunciantes distintos | 232 | 356 |

**Recomendación de evaluación:** entrenar con las fechas de corte antiguas, incluida la parte generada, y **evaluar
solo con fechas de corte de los datos originales** (las dos últimas: sep-2025 y dic-2025). Así la cifra de acierto que
se presenta está medida sobre los datos del caso, no sobre los generados. Conviene informar también del resultado
entrenando solo con los datos originales, para que se vea qué aporta la ampliación.

## Regenerar

```
python tablas_ampliadas/generar_ampliacion.py
```
