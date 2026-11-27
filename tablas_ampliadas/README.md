# Tablas ampliadas (ene-2020 → 27-nov-2026)

Ampliación de los datos sintéticos del TFP para entrenar el modelo de abandono con más historia. **Las tablas originales
(`tablas/`, oct-2023 → sep-2026) no se modifican**: en cada archivo de esta carpeta, las filas originales están copiadas
byte a byte al principio (salvo los cobros de 54 facturas, ver «Facturas pendientes») y las filas nuevas se añaden al final, con identificadores que continúan la numeración.

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
| fact_interacciones | 9.620 | 10.215 | 19.835 |
| oportunidades | 2.076 | 3.057 | 5.133 |
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

Las 61 facturas originales en estado «Pendiente» reflejan la situación a 30-sep-2026. En `tablas_ampliadas/fact_facturacion.csv`
**se actualiza su situación a 27-nov-2026**: 54 pasan a «Cobrada», con fecha de cobro y días de retraso, y 7 siguen
pendientes. Son las únicas filas originales que cambian en esta carpeta; `tablas/` no se toca. `cobros_posteriores.csv`
deja constancia de esas 61 facturas. Ningún corte con resultado depende de estos cobros.

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
4. **Señales:** se calibran sobre los episodios de abandono de **la etiqueta del modelo**, `modelo_churn/etiqueta.py`
   (copia literal en `etiqueta_modelo_churn.py`): población con campaña en los 12 meses de calendario anteriores al corte,
   E2 con W de 210 días y regla de año «W». Se excluyen los anunciantes con menos de un año desde el alta.
   - **Cambio de interlocutor:** en los 60 días previos al 22 % de los episodios, más 0,015 al año a cualquier anunciante.
   - **Reclamación sin resolver:** antes del 20 % de las pérdidas definitivas, más un 15 % de las reclamaciones ordinarias.
     Ambas solo en anunciantes que no aparecen en los datos originales, porque la señal cuenta para siempre y alteraría
     los cortes originales. Las demás reclamaciones están resueltas.
   - **CTR un 25–55 % más bajo:** en el año previo al 35 % de los episodios. Después se reajusta la parte añadida para que
     la mediana de CTR de cada producto (la referencia de la señal) sea la de los datos originales hasta jun-2025.
   - **Propuestas ganadas:** se cierran entre 2 días antes y 48 días después de la orden, con la misma distribución que en
     los originales.
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

**Abandono por corte** (etiqueta del modelo, sin anunciantes con menos de un año desde el alta):

| Corte | dic-20 | mar-21 | jun-21 | sep-21 | dic-21 | mar-22 | jun-22 | sep-22 | dic-22 | mar-23 | jun-23 | sep-23 | dic-23 | mar-24 | jun-24 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Abandono | 61 % | 54 % | 59 % | 55 % | 41 % | 39 % | 41 % | 39 % | 50 % | 52 % | 51 % | 52 % | 43 % | 50 % | 39 % |

Cortes de entrenamiento originales (sep-24 → jun-25): 50,7 % de media.

**Relación de las señales con el abandono** (misma etiqueta y población; señales calculadas como en
`evaluar_umbral_abandono.py`; con la señal frente a sin ella):

| | Originales, cortes de entrenamiento (sep-24 → jun-25) | Parte añadida (dic-20 → jun-24) |
|---|---|---|
| Observaciones · abandono medio | 477 · 50,7 % | 1.515 · 48,1 % |
| Cambio de interlocutor | 67,6 % vs 47,8 % (15 % de los casos) | 70,1 % vs 44,4 % (15 %) |
| Reclamación sin resolver | 75,0 % vs 50,1 % (2,5 %, n = 12) | 96,3 % vs 46,3 % (3,6 %) |
| CTR bajo | 63,9 % vs 48,4 % (15 %) | 60,5 % vs 45,1 % (19 %) |
| Caída de inversión | 68,9 % vs 30,0 % | 66,1 % vs 29,4 % |
| Más de 90 días sin contacto | 94,0 % vs 43,7 % | 91,5 % vs 43,2 % |
| Con propuesta abierta: siguen · abandonan | 27,7 % · 22,3 % | 37,3 % · 18,9 % |
| Abandono con 0 · 1–2 · 3+ propuestas no ganadas en el último año | 46 % · 54 % · 67 % | 40 % · 53 % · 64 % |

Diferencias que quedan:
- **Propuesta abierta entre los que siguen** (37 % frente a 28 %): son sobre todo propuestas ganadas abiertas en la fecha
  de corte (25 % frente a 16 %). No baja al reducir las propuestas no ganadas ni las ganadas por campaña, así que lo dejo
  señalado.
- **Reclamación sin resolver** algo más fuerte (96 % frente a 75 %). En los originales son 12 casos, 9 frente a 3. Para
  acercarla habría que poner reclamaciones sin resolver a anunciantes actuales que siguen, y eso cambiaría las señales de
  los cortes originales.
- **Abandono bajo en dic-21 → sep-22 (≈ 40 %) y en jun-24 (39 %).**

`comprobar_senales.py` reproduce estas tablas.

## Qué cambia para el modelo

Fechas de corte de `fechas_corte(campanas, "2026-09-01")`, sin anunciantes con menos de un año desde el alta:

| | Solo originales | Ampliadas |
|---|---|---|
| Cortes de entrenamiento | 4 (sep-24 → jun-25) | 19 (dic-20 → jun-25) |
| Observaciones de entrenamiento | 477 | 1.992 |
| Abandonos | 242 | 971 |
| Anunciantes distintos | 156 | 260 |
| Prueba (sep-25 y dic-25) | 251 observaciones · 130 abandonos | igual |

## Regenerar

```
python tablas_ampliadas/generar_ampliacion.py
```
Las variables de entorno `CAL_*` solo sirven para recalibrar. Sin ellas se generan exactamente los CSV publicados.
