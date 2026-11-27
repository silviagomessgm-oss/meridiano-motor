# Valoración de los datos ampliados (`tablas_ampliadas/`) · versión 2

Fecha: 2026-11-27. Datos regenerados en `main` (commit 1ba91f4). Las cifras salen de `valoracion_utilidad.md`
(`python -m modelo_churn.valorar_ampliacion`) y de `punto_control_1.md`. La versión 1 de esta valoración queda en el
historial de git (commit e06f69c). La validación usa solo cortes originales de entrenamiento (mar-25 y jun-25); los
cortes de prueba (sep-25 y dic-25) no se han tocado.

## Veredicto: siguen sumando. Conservarlos, con una corrección pendiente y una precaución al entrenar

| | Solo originales | Ampliados v2 |
|---|---|---|
| Regresión logística · AUC (validación) | 0,813 | 0,831 (dif. +0,018, IC 95 % [−0,007; +0,044]) |
| Regresión logística · Brier | 0,190 | 0,169 |
| Árbol de 3 niveles · AUC | 0,716 | 0,799 (dif. +0,083, IC 95 % [+0,025; +0,142]) |

## Estado de los cuatro cambios pedidos

| Problema | Originales (cortes de entrenamiento) | Versión 1 | Versión 2 | Estado |
|---|---|---|---|---|
| Con propuesta abierta: siguen · abandonan | 27,7 % · 22,3 % | 40,5 % · 15,7 % | 35,7 % · 20,0 % | Mejorado; sigue algo más fuerte |
| Peso de `propuestas_abiertas` en el modelo | −0,10 | −0,40 | −0,21 | Mejorado |
| Peso de `propuestas_perdidas_12m` | +0,28 | −0,11 (signo cambiado) | +0,06 | Corregido el signo; más débil |
| Cambio de interlocutor: abandono con · sin | 68,5 % · 47,5 % | 56,2 % · 46,1 % | 62,8 % · 45,6 % | Resuelto en lo esencial |
| Peso de `cambio_interlocutor_12m` | +0,36 | +0,13 | +0,20 | Mejorado |
| 35 anunciantes de `dim_clientes` sin historia | — | 0 de 35 con campañas | 35 de 35 | Resuelto |
| Primera campaña anterior al alta | 0 | 16 | 0 | Resuelto |
| Facturas originales pendientes | — | 61 (9 vencidas antes de oct-26) | 9 (ninguna vencida antes de oct-26) | Resuelto (`cobros_posteriores.csv`, ya integrado en la carga) |
| Abandono en los cortes jun-23, sep-23, dic-23 | 49–53 % en el resto | 38,8 % · 37,0 % · 38,3 % | 43,0 % · 43,1 % · 44,9 % | Mejorado, no resuelto |
| Abandono en jun-24 | | 45,3 % | 36,4 % | Empeora (ver abajo) |

## Lo que queda

1. **La calibración usó los cortes de prueba (corrección necesaria).** Según el README, las señales generadas se
   calibraron con «5 cortes E2 originales, dic-24 → dic-25», que incluyen los de prueba (sep-25 y dic-25). No se han
   copiado filas, pero sí proporciones de la prueba, de modo que la cifra de acierto en la prueba podría salir algo
   optimista. Además, la calibración usa la etiqueta E2 de `evaluacion/` (población con hasta 540 días sin campaña), no la
   de este modelo (`modelo_churn/etiqueta.py`: campaña en los 12 meses previos, sin anunciantes nuevos).
2. **Sigue el bache de la costura.** En los cortes de jun-23 a jun-24 los anunciantes originales abandonan un 30–38 %,
   frente al 49–54 % antes y después. Causa: el generador da historia previa sobre todo a quien después sigue comprando.
   De los 89 anunciantes antiguos (alta antes de oct-22) que compran entre oct-23 y abr-24, 72 (81 %) tienen campañas
   generadas entre oct-22 y sep-23; de los 31 que no vuelven a comprar hasta después de abr-24, solo 5 (16 %). En jun-24
   el bache se ve más porque ya no quedan anunciantes nuevos (C0321+), que antes lo compensaban con un 100 % de abandono.
3. **Lo que aportan es volumen, no información nueva.** Como las señales se calibraron con los datos originales, los
   datos generados repiten las relaciones de los originales con más casos. Por eso el modelo es más estable, pero el
   informe debe decirlo así: no descubren patrones que no estuvieran ya en los datos del caso.

## Recomendación

- **Pedir una corrección al generador:** recalibrar las señales solo con los cortes de entrenamiento (hasta jun-25) y con
  la etiqueta de `modelo_churn/etiqueta.py`. Así ninguna información del periodo de prueba entra en el entrenamiento.
- **El bache de la costura se resuelve al entrenar, sin regenerar:** quitar del entrenamiento los cortes de mar-23 a jun-24
  da el mismo acierto (regresión logística: AUC 0,829 frente a 0,831; árbol: 0,815 frente a 0,799). Si el generador
  quiere corregirlo: dar compras entre oct-22 y sep-23 a más de los 31 anunciantes antiguos que vuelven tras abr-24
  (como pausas o bajas con reactivación), hasta que el abandono de esos cortes ronde el 50 %.
- **En el Punto de Control 2:** comparar el entrenamiento con solo originales y con los ampliados (sin la costura) sobre
  los mismos cortes de prueba, y explicar los pesos comerciales con los dos modelos.

## Nota para el punto de control 2

La precisión entre las 12 cuentas de más riesgo es 1,00 en casi todas las variantes: con ≈ 120 anunciantes por corte y
un 50 % de abandono, las 12 primeras son fáciles de acertar. Esa métrica no servirá para distinguir modelos; el AUC y la
calibración serán las que decidan.
