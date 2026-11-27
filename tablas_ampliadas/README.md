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
| dim_clientes | 267 | 100 | 367 |
| contactos | 296 | 109 | 405 |
| fact_campanas | 1.432 | 1.501 | 2.933 |
| fact_facturacion | 1.432 | 1.501 | 2.933 |
| fact_interacciones | 9.620 | 10.370 | 19.990 |
| oportunidades | 2.076 | 2.982 | 5.058 |
| dim_comercial, dim_productos | sin cambios | — | — |
| `cobros_posteriores.csv` (nueva) | — | 61 | 61 |

- **Hacia atrás (ene-2020 → sep-2023):**
  - la historia previa de los anunciantes actuales dados de alta antes de oct-2023;
  - la historia de los **35 anunciantes de `dim_clientes` que no tenían campañas**, como anunciantes que abandonaron antes
    de oct-2023 (en los datos originales solo reciben propuestas de recuperación);
  - 95 anunciantes antiguos más (C0321 en adelante) que también abandonaron antes de oct-2023.
- **Hacia delante (sep-2026 → 27-nov-2026):** la continuación de los anunciantes que seguían activos y 5 altas nuevas.

## Reglas que cumple

- Mismos nombres de tablas y columnas, en el mismo orden. Todas las campañas se emiten el día 1 de mes.
- Coherencia entre tablas: cada campaña tiene su factura; cada propuesta ganada, su pedido del mismo cliente; las perdidas y
  las que se quedaron sin respuesta no tienen pedido. Todo anunciante tiene contacto y al menos una campaña.
- **La fecha de alta es igual o anterior a la primera campaña** de cada anunciante, también en la historia añadida a los
  anunciantes originales (si una campaña quedaba antes del alta, se retrasa al mes siguiente).
- Los anunciantes que abandonan antes de oct-2023 tienen su última campaña como muy tarde el 30-jun-2023. Así no entran en la
  población de los cortes de evaluación originales, que sigue siendo exactamente la misma (811 observaciones).
- Semilla fija (2020): dos ejecuciones dan archivos idénticos.

### Facturas pendientes

Las 61 facturas originales en estado «Pendiente» reflejan la situación a 30-sep-2026, la fecha de los datos originales, y
no se modifican. Su situación a 27-nov-2026 está en **`cobros_posteriores.csv`** (52 cobradas y 9 todavía pendientes), con
el retraso de cobro habitual. Ningún corte de entrenamiento la necesita: el último corte con 210 días observables es
dic-2025. Solo hace falta si se puntúa a 27-nov-2026.

## Método

Pensado para no introducir reglas nuevas que luego «descubra» el modelo:

1. **Campañas:** cada campaña nueva es una copia de una campaña real de un anunciante del mismo tamaño (productos,
   importes, duración, impresiones y clics), desplazada en el tiempo y con un ±5 % de ruido. Los anunciantes actuales
   siguen su propio ritmo anual y su estacionalidad, mezclada con la de su sector.
2. **Abandono:** el 70 % de las bajas va precedido de un descenso de la inversión (−40 %) y del CTR (−30 %) en los últimos
   6 meses; el 30 % desaparece de golpe. Algunos anunciantes actuales se dan de baja antes de 2023 y vuelven en el periodo
   original (reactivación, como en los datos reales).
3. **Propuestas:** las propuestas de ampliación no ganadas se envían **a cualquier anunciante con el mismo ritmo, siga
   comprando o no** (en los datos originales: 0,070 al mes a los activos y 0,066 a los que llevan más de un año sin comprar).
   Las ganadas salen de las campañas (84 %). En los meses previos a un episodio de abandono se añaden algunas propuestas
   que no prosperan, que es la relación que muestran los datos originales.
4. **Señales:** se calibran sobre los episodios de abandono de la **etiqueta E2 de producción**
   (`evaluacion/src/etiqueta_e2.py`), calculada sobre las campañas ya generadas:
   - **cambio de interlocutor** en los 60 días previos al 22 % de los episodios, más un 0,03 al año a cualquier anunciante;
   - **reclamación sin resolver** antes del 8 % de las pérdidas definitivas. Solo en anunciantes que no aparecen en los datos
     originales, porque la señal cuenta para siempre y alteraría los cortes originales. Las demás reclamaciones están
     resueltas;
   - **CTR un 25–55 % más bajo** en el año previo al 30 % de los episodios. Después se reajusta la parte añadida para que la
     mediana de CTR de cada producto (la referencia de la señal) sea la de los datos originales.
5. **Facturas e interacciones:** con las frecuencias y distribuciones medidas en los datos originales (condiciones de pago y
   retraso por cliente, ≈ 1,9 interacciones por cliente activo y mes).

Supuestos: anunciantes activos por ejercicio de 98 (EF2020, año de la pandemia, solo ene–sep), 110, 122 y 130; tarifas
de los productos iguales a las actuales.

## Comprobaciones

| Por ejercicio (oct–sep) | EF2020 | EF2021 | EF2022 | EF2023 | EF2024* | EF2025* | EF2026* |
|---|---|---|---|---|---|---|---|
| Anunciantes activos | 99 | 112 | 125 | 130 | 135 | 139 | 146 |
| Retenidos del año anterior | — | 46 %** | 71 % | 65 % | 61 % | 67 % | 63 % |
| Facturación (M€) | 0,52** | 0,83 | 1,06 | 1,01 | 0,97 | 1,19 | 1,11 |

\* Datos originales. \*\* EF2020 solo tiene nueve meses, lo que rebaja también la retención de EF2021.

**Relación de las señales con el abandono.** Abandono según la etiqueta E2 de producción (pérdida total o contracción).
Población de producción: anunciantes con como mucho 540 días sin campaña. Las señales se calculan como en
`evaluar_umbral_abandono.py`. Cada celda da el abandono con la señal frente a sin ella.

| | Originales (5 cortes E2) | Parte nueva (11 cortes, mar-21 → sep-23) |
|---|---|---|
| Observaciones · abandono medio | 811 · 55,5 % | 1.598 · 53,8 % |
| Cambio de interlocutor | 68,8 % vs 53,0 % (16 % de los casos) | 72,6 % vs 50,6 % (15 %) |
| Reclamación sin resolver | 95,0 % vs 54,5 % (2,5 %) | 92,6 % vs 53,2 % (1,7 %) |
| CTR bajo | 63,5 % vs 54,3 % | 60,8 % vs 52,3 % |
| Caída de inversión | 66,0 % vs 47,9 % | 63,8 % vs 46,8 % |
| Más de 90 días sin contacto | 97,4 % vs 45,8 % | 98,0 % vs 45,4 % |
| Con propuesta abierta: siguen · abandonan | 30,5 % · 17,8 % | 37,1 % · 19,5 % |
| Abandono con 0 · 1–2 · 3+ propuestas no ganadas en el último año | 51 % · 57 % · 69 % | 50 % · 56 % · 66 % |

En los cortes de evaluación originales, calculados con las tablas ampliadas, la población es la misma (811) y las
señales prácticamente no cambian. Por ejemplo, la reclamación sin resolver sigue en 95,0 % frente a 54,9 %. El abandono
medio pasa de 55,5 % a 55,9 %, porque la historia añadida da a algunos anunciantes el año previo que E2 necesita para
compararlos. El abandono por corte entre jun-2023 y dic-2023 es de 55 %, 51 % y 55 %, como en el resto (46–62 %).

## Qué cambia para el modelo

| Con la etiqueta E2 (cortes trimestrales con resultado a 210 días) | Solo originales | Ampliadas |
|---|---|---|
| Fechas de corte | 5 (dic-24 → dic-25) | 20 (mar-21 → dic-25) |
| Observaciones (anunciante × fecha de corte) | 811 | 3.030 |
| Abandonos | 450 | 1.664 |
| Anunciantes distintos | 196 | 326 |

**Recomendación de evaluación:** entrenar con los cortes antiguos y **evaluar solo con cortes de los datos originales**
(por ejemplo, sep-2025 y dic-2025), para que la cifra de acierto que se presenta esté medida sobre los datos del caso.
Conviene informar también del resultado entrenando solo con los originales, para que se vea qué aporta la ampliación.

## Regenerar

```
python tablas_ampliadas/generar_ampliacion.py
```
Las variables de entorno `CAL_*` solo sirven para recalibrar. Sin ellas se generan exactamente los CSV publicados.
