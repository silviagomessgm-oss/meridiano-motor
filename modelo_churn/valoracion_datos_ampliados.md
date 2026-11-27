# Valoración de los datos ampliados (`tablas_ampliadas/`)

Fecha: 2026-11-27. Las cifras salen de `valoracion_utilidad.md` (generado con
`python -m modelo_churn.valorar_ampliacion`) y de `punto_control_1.md`. La validación usa solo
cortes originales de entrenamiento (mar-25 y jun-25); los cortes de prueba (sep-25 y dic-25) no se han tocado.

## Veredicto: suman. Conservarlos, pidiendo cuatro correcciones al generador

| Pregunta | Respuesta |
|---|---|
| ¿Se parecen a los originales? | Sí, en todo lo agregado: importes (mediana 1.098 € frente a 1.158 €), descuento medio (8 % en ambas), mezcla de familias, CTR por producto y año, tipos de interacción, tasas de éxito de propuestas (ampliaciones 54,6 % frente a 53,6 %) y retraso de cobro (10,5 frente a 9,6 días). |
| ¿Ayudan a predecir los datos originales? | Sí. Regresión logística: AUC 0,816 → 0,835 y Brier 0,187 → 0,167 (mejor calibrada); la mejora de AUC tiene un IC 95 % de [−0,011; +0,049]. Árbol de 3 niveles: AUC 0,727 → 0,792, IC [+0,010; +0,122]. |
| ¿Son fieles en lo que importa al modelo? | En casi todo: un modelo entrenado solo con datos generados predice los originales tan bien como uno entrenado con los originales (AUC 0,831 frente a 0,816 en logística). |
| ¿Qué restan? | Cambian la explicación comercial del modelo en tres variables (propuestas abiertas, propuestas perdidas y cambio de interlocutor) y tienen un bache en la costura de 2023. Ver abajo. |

## Problemas encontrados

1. **Propuestas comerciales ligadas al abandono futuro.** El generador casi deja de enviar propuestas a quien va a
   abandonar. Anunciantes con alguna propuesta abierta: en los cortes originales, 27,7 % entre los que siguen y 22,3 %
   entre los que abandonan; en los generados, 40,5 % frente a 15,7 %. Además, en los originales el abandono sube con las
   propuestas perdidas (45 % con 0 a 67 % con 3 o más) y en los generados no. Consecuencia en el modelo: el peso de
   `propuestas_abiertas` se multiplica por 4 (−0,10 → −0,40) y `propuestas_perdidas_12m` cambia de signo (+0,27 → −0,11).
2. **Bache en la costura de 2023.** El abandono total cae al 38,8 %, 37,0 % y 38,3 % en los cortes de jun-23, sep-23 y
   dic-23, frente al 45–54 % del resto. Los anunciantes originales abandonan solo un 22–28 % en esos cortes (36–52 % en
   los demás). Pista: 35 anunciantes de `dim_clientes` (altas de 2016 a 2022) no tienen ninguna campaña ni en los datos
   originales ni en la ampliación; por su perfil son anunciantes que se fueron antes de oct-23, pero no tienen historia.
3. **Señales de relación más débiles de lo que deberían.** Con cambio de interlocutor el abandono es 68,5 % frente a
   47,5 % sin él en los cortes originales, y 56,2 % frente a 46,1 % en los generados. El generador se calibró «sin
   superar» a los originales, pero ha quedado claramente por debajo: su peso en el modelo baja de 0,36 a 0,13.
4. **Detalles de coherencia (sin efecto en el modelo):** 16 anunciantes tienen la primera campaña entre 1 y 21 días antes
   de su fecha de alta (en los originales no ocurre nunca); y las 61 facturas originales pendientes a sep-26 siguen
   pendientes a 27-nov-26, aunque 9 vencieron antes de oct-26.

## Cambios que proponer al generador

1. Que el envío de propuestas y su desenlace no dependan de si el anunciante va a abandonar, o que se calibren con los
   originales: % con propuesta abierta 27,7 % (sigue) frente a 22,3 % (abandona), y abandono creciente con las propuestas
   perdidas (45 % → 67 %).
2. Generar la historia anterior a oct-23 de los 35 anunciantes de `dim_clientes` sin campañas, como anunciantes que
   abandonan antes de oct-23, y comprobar que el abandono de los cortes jun-23 a dic-23 queda en la línea del resto
   (≈ 50 %).
3. Calibrar el cambio de interlocutor y las reclamaciones para que su relación con el abandono sea igual a la original,
   no más débil.
4. Fecha de alta igual o anterior a la primera campaña, y decidir qué pasa con las facturas originales pendientes en
   los meses añadidos.

Después, volver a ejecutar `python -m modelo_churn.control1 --datos tablas_ampliadas --limite-fin-w 2026-09-01
--inicio-originales 2023-10-01` y `python -m modelo_churn.valorar_ampliacion` para comprobar que los problemas 1 a 3 han
desaparecido.

## Si no se regeneran

- Entrenar sin los cortes de la costura (mar-23 a jun-24) da el mismo acierto (logística: AUC 0,832; árbol: 0,810) y
  evita el problema 2.
- Los problemas 1 y 3 seguirían: la explicación comercial de los pesos tendría que hacerse con el modelo entrenado solo
  con datos originales, o advertir de que esas tres variables están distorsionadas.

## Nota para el punto de control 2

La precisión entre las 12 cuentas de más riesgo es 1,00 en casi todas las variantes: con ≈ 120 anunciantes por corte y
un 50 % de abandono, las 12 primeras son fáciles de acertar. Esa métrica no servirá para distinguir modelos; el AUC y la
calibración serán las que decidan.
