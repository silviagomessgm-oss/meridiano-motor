# Valoración de los datos ampliados (`tablas_ampliadas/`) · versión 3

Fecha: 2026-11-27. Datos regenerados en `main` (commit a3525ce). Las cifras salen de `valoracion_utilidad.md`
(`python -m modelo_churn.valorar_ampliacion`) y de `punto_control_1.md`. Las versiones 1 y 2 de esta valoración quedan en
el historial de git (commits e06f69c y 590155b). La validación usa solo cortes originales de entrenamiento (mar-25 y
jun-25); los cortes de prueba (sep-25 y dic-25) no se han tocado.

## Veredicto: suman y la calibración ya es limpia. Propuesta: darlos por definitivos

| | Solo originales | Ampliados v3 |
|---|---|---|
| Regresión logística · AUC (validación) | 0,818 | 0,837 (dif. +0,019, IC 95 % [−0,009; +0,044]) |
| Regresión logística · Brier | 0,186 | 0,167 |
| Árbol de 3 niveles · AUC | 0,743 | 0,802 (dif. +0,059, IC 95 % [+0,003; +0,114]) |

## Calibración: comprobada en el código del generador

- Todo lo que el generador mide en los datos originales (plantillas, ritmos, frecuencias, interacciones) usa datos hasta
  el 30-jun-2025 (`REF = 2025-06-30` en `generar_ampliacion.py`).
- Los episodios de abandono con los que se calibran las señales salen de cortes de jun-20 a sep-24, cuya W termina como
  muy tarde en abr-25. `comprobar_senales.py` compara con los cortes originales de dic-24 a jun-25.
- Los cortes de prueba (sep-25 y dic-25) no intervienen.
- La población es la de este modelo (campaña en los 12 meses previos y al menos un año desde el alta). El generador cuenta
  365 días en lugar de meses de calendario; la diferencia es mínima.

## Evolución de los problemas

| Problema | Originales (cortes de entrenamiento) | v1 | v2 | v3 |
|---|---|---|---|---|
| Con propuesta abierta: siguen · abandonan | 27,7 % · 22,3 % | 40,5 % · 15,7 % | 35,7 % · 20,0 % | 38,9 % · 19,1 % |
| Peso de `propuestas_abiertas` | −0,10 | −0,40 | −0,21 | −0,31 |
| Peso de `propuestas_perdidas_12m` | +0,31 | −0,11 | +0,06 | +0,06 |
| Peso de `cambio_interlocutor_12m` | +0,37 | +0,13 | +0,20 | +0,27 |
| Abandono con cambio de interlocutor (en la parte generada de cada versión) | 68,5 % | 56,2 % | 62,8 % | 64,3 % |
| Abandono en jun-23 · sep-23 · dic-23 | 49–53 % en el resto | 38,8 · 37,0 · 38,3 % | 43,0 · 43,1 · 44,9 % | 50,9 · 51,7 · 43,2 % |
| Abandono en jun-24 | | 45,3 % | 36,4 % | 39,1 % |
| Abandono en dic-21 → sep-22 | | 45,8–53,4 % | 47,1–53,5 % | 38,8–41,0 % |
| Calibración con cortes de prueba | — | — | sí | **no** |

Los pesos de la tabla son de la regresión logística entrenada con los cortes anteriores a jun-25; el «original» de cada
versión cambia un poco porque la historia anterior a oct-23 también afecta a algunas variables de los cortes originales.

## Lo que queda (limitaciones para el informe)

1. **Propuestas abiertas, algo más fuertes que en los originales.** Con los datos ampliados pesan unas tres veces más en el
   modelo (−0,31 frente a −0,10). Al explicar el modelo en el Punto de Control 2 conviene comparar con el entrenado solo
   con originales.
2. **El abandono varía más entre cortes en la parte generada** (39–61 %) que en la original (49–53 %), con valores bajos en
   dic-21 → sep-22, dic-23 y jun-24. Quitar los cortes de la costura ya no cambia el acierto (AUC 0,833 frente a 0,837).
3. **Aportan volumen, no información nueva:** las señales se calibraron con los datos originales de entrenamiento, así
   que los datos generados repiten sus relaciones con más casos.
4. **Reproducibilidad:** `generar_ampliacion.py` y `comprobar_senales.py` importan código de `evaluacion/` (la etiqueta E2
   y otras funciones). Si se borra `evaluacion/`, los datos ampliados ya no se podrán regenerar. Habría que cambiar el
   generador para que use `modelo_churn/etiqueta.py` o incluya su propia copia de la etiqueta antes de borrar esa carpeta.

## Recomendación

- Dar estos datos por definitivos: la calibración ya es limpia y otra ronda de ajustes aportaría poco frente a lo que
  queda pendiente del proyecto.
- Entrenar con todos los cortes (sin quitar la costura) y, en el Punto de Control 2, comparar con el entrenamiento solo
  con originales sobre los mismos cortes de prueba.
- Antes de borrar `evaluacion/`, quitar del generador la dependencia de esa carpeta.

## Nota para el punto de control 2

La precisión entre las 12 cuentas de más riesgo es 1,00 en casi todas las variantes: con ≈ 120 anunciantes por corte y
un 50 % de abandono, las 12 primeras son fáciles de acertar. Esa métrica no servirá para distinguir modelos; el AUC y la
calibración serán las que decidan.
