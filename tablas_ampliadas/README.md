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
| dim_clientes | 267 | 79 | 346 |
| contactos | 296 | 85 | 381 |
| fact_campanas | 1.432 | 1.661 | 3.093 |
| fact_facturacion | 1.432 | 1.661 | 3.093 |
| fact_interacciones | 9.620 | 10.260 | 19.880 |
| oportunidades | 2.076 | 2.986 | 5.062 |
| dim_comercial, dim_productos | sin cambios | — | — |
| `cobros_posteriores.csv` (nueva) | — | 61 | 61 |

- **Hacia atrás (ene-2020 → sep-2023):**
  - la historia previa de los anunciantes actuales dados de alta antes de oct-2023. Los **31 anunciantes antiguos que no
    vuelven a comprar hasta después de abr-2024** compran por última vez entre oct-2022 y sep-2023 (antes solo 6 lo hacían).
    Así el abandono de los cortes de 2023 ronda el 50 %;
  - la historia de los **35 anunciantes de `dim_clientes` que no tenían campañas**, como anunciantes que abandonaron antes
    de oct-2023 (en los datos originales solo reciben propuestas de recuperación);
  - 74 anunciantes antiguos más (C0321 en adelante) que también abandonaron antes de oct-2023.
- **Hacia delante (sep-2026 → 27-nov-2026):** la continuación de los anunciantes que seguían activos y 5 altas nuevas.

## Separación entrenamiento / prueba

Todo lo que el generador mide en los datos originales usa **solo datos hasta el 30-jun-2025**, el último corte de
entrenamiento: las campañas que se copian, los ritmos y la estacionalidad, las frecuencias de interacciones, facturas y
propuestas, y la calibración de las señales. **Los cortes de prueba (sep-2025 y dic-2025) no intervienen en la
generación.** La única excepción es la continuación de sep-2026 a nov-2026, que parte de la situación de cada anunciante en
2026, pero es posterior a las ventanas de resultado de todos los cortes.

## Reglas que cumple

- Mismos nombres de tablas y columnas, en el mismo orden. Todas las campañas se emiten el día 1 de mes.
- Coherencia entre tablas: cada campaña tiene su factura; cada propuesta ganada, su pedido del mismo cliente; las perdidas y
  las que se quedaron sin respuesta no tienen pedido. Todo anunciante tiene contacto y al menos una campaña.
- **La fecha de alta es igual o anterior a la primera campaña** de todos los anunciantes, también en la historia añadida a
  los anunciantes originales (si una campaña quedaba antes del alta, se retrasa al mes siguiente).
- Los anunciantes que abandonan antes de oct-2023 tienen su última campaña como muy tarde el 30-jun-2023. Así la población
  de los cortes de evaluación del motor (≤ 540 días sin campaña) sigue siendo la misma (811 observaciones).
- Semilla fija (2020): dos ejecuciones dan archivos idénticos.

### Facturas pendientes

Las 61 facturas originales en estado «Pendiente» reflejan la situación a 30-sep-2026, la fecha de los datos originales, y
no se modifican. Su situación a 27-nov-2026 está en **`cobros_posteriores.csv`** (50 cobradas y 11 todavía pendientes),
con el retraso de cobro habitual. Ningún corte con resultado la necesita. Solo hace falta si se puntúa a 27-nov-2026.

## Método

Pensado para no introducir reglas nuevas que luego «descubra» el modelo:

1. **Campañas:** cada campaña nueva es una copia de una campaña real de un anunciante del mismo tamaño (productos,
   importes, duración, impresiones y clics), desplazada en el tiempo y con un ±5 % de ruido. Los anunciantes actuales
   siguen su propio ritmo anual y su estacionalidad, mezclada con la de su sector.
2. **Abandono:** el 70 % de las bajas va precedido de un descenso de la inversión (−40 %) y del CTR (−30 %) en los últimos
   6 meses; el 30 % desaparece de golpe. Algunos anunciantes actuales se dan de baja y vuelven en el periodo original.
3. **Propuestas:** las propuestas de ampliación no ganadas se envían **a cualquier anunciante con el mismo ritmo, siga
   comprando o no** (en los datos originales: 0,070 al mes a los activos y 0,066 a los que llevan más de un año sin comprar).
   Las ganadas salen de las campañas (84 %). En los meses previos a un episodio de abandono se añaden algunas propuestas
   que no prosperan, que es la relación que muestran los datos originales.
4. **Señales:** se calibran sobre los episodios de abandono de la etiqueta E2 (`evaluacion/src/etiqueta_e2.py`), con la
   **población de `modelo_churn/etiqueta.py`**: campaña en los 12 meses anteriores al corte y al menos un año desde el alta.
   - **Cambio de interlocutor:** en los 60 días previos al 30 % de los episodios, más 0,015 al año a cualquier anunciante.
   - **Reclamación sin resolver:** antes del 30 % de las pérdidas definitivas, solo en anunciantes que no aparecen en los
     datos originales. Esta señal cuenta para siempre y alteraría los cortes originales. Las demás reclamaciones están
     resueltas.
   - **CTR un 25–55 % más bajo:** en el año previo al 35 % de los episodios. Después se reajusta la parte añadida para que
     la mediana de CTR de cada producto (la referencia de la señal) sea la de los datos originales hasta jun-2025.
5. **Facturas e interacciones:** con las frecuencias y distribuciones medidas en los datos originales hasta jun-2025.

Supuestos: anunciantes activos por ejercicio de 98 (EF2020, año de la pandemia, solo ene–sep), 110, 122 y 130; tarifas
de los productos iguales a las actuales.

## Comprobaciones

| Por ejercicio (oct–sep) | EF2020 | EF2021 | EF2022 | EF2023 | EF2024* | EF2025* | EF2026* |
|---|---|---|---|---|---|---|---|
| Anunciantes activos | 99 | 111 | 127 | 130 | 135 | 139 | 146 |
| Retenidos del año anterior | — | 53 %** | 75 % | 76 % | 71 % | 67 % | 63 % |
| Facturación (M€) | 0,60** | 0,75 | 1,06 | 1,02 | 0,97 | 1,19 | 1,11 |

\* Datos originales (la retención de EF2024 compara con EF2023, que es generado). \*\* EF2020 solo tiene nueve meses.

La retención de EF2022–EF2024 (71–76 %) es más alta que la de los ejercicios originales (63–67 %). Es la consecuencia
de que los 31 anunciantes que vuelven después de abr-2024 compren ahora en EF2023.

**Abandono por corte** (E2, población del modelo):

| Corte | jun-22 | sep-22 | dic-22 | mar-23 | jun-23 | sep-23 | dic-23 | mar-24 | jun-24 | sep-24 | dic-24* | mar-25* | jun-25* |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Abandono | 41 % | 39 % | 53 % | 57 % | 54 % | 49 % | 46 % | 48 % | 42 % | 49 % | 52 % | 51 % | 50 % |

**Relación de las señales con el abandono** (E2, población del modelo; señales calculadas como en
`evaluar_umbral_abandono.py`; con la señal frente a sin ella):

| | Originales, cortes de entrenamiento (dic-24 → jun-25) | Parte añadida (mar-21 → sep-24) |
|---|---|---|
| Observaciones · abandono medio | 357 · 50,4 % | 1.532 · 47,8 % |
| Cambio de interlocutor | 67,3 % vs 47,4 % (15 % de los casos) | 67,1 % vs 43,2 % (19 %) |
| Reclamación sin resolver | 90,0 % vs 49,3 % (2,8 %) | 91,2 % vs 46,9 % (2,2 %) |
| CTR bajo | 63,8 % vs 47,8 % (16 %) | 59,2 % vs 44,9 % (21 %) |
| Caída de inversión | 61,7 % vs 37,9 % | 62,6 % vs 32,3 % |
| Más de 90 días sin contacto | 100 % vs 41,8 % | 95,2 % vs 42,9 % |
| Con propuesta abierta: siguen · abandonan | 31,6 % · 22,8 % | 37,5 % · 18,7 % |
| Abandono con 0 · 1–2 · 3+ propuestas no ganadas en el último año | 43 % · 55 % · 72 % | 43 % · 50 % · 59 % |

`comprobar_senales.py` reproduce esta tabla.

## Qué cambia para el modelo

| E2, población del modelo, cortes trimestrales | Solo originales | Ampliadas |
|---|---|---|
| Cortes de entrenamiento | 3 (dic-24 → jun-25) | 18 (mar-21 → jun-25) |
| Observaciones de entrenamiento | 357 | 1.889 |
| Abandonos | 180 | 915 |
| Anunciantes distintos | 145 | 243 |
| Prueba (sep-25 y dic-25) | 251 observaciones · 139 abandonos | igual |

## Regenerar

```
python tablas_ampliadas/generar_ampliacion.py
```
Las variables de entorno `CAL_*` solo sirven para recalibrar. Sin ellas se generan exactamente los CSV publicados.
