# Grabación para la evaluación de viabilidad · Meridiano, retención de anunciantes

Vídeo de 10–12 minutos para que el tribunal o el equipo decidan si el caso es viable. Cada escena indica qué se ve, qué
se dice y de dónde sale cada cifra. **Regla de la grabación:** separar siempre lo **medido** (modelo evaluado con datos
que no vio al entrenar) de lo **simulado** y de lo **supuesto**. Todos los datos son ficticios (caso de estudio).

Preparación: la misma que en `GUION_DEMO_EN_DIRECTO.md` (migración, simulacro cargado, W1 con fecha de corte
2026-11-23). Grabar la pantalla a 1080p, con el zoom del navegador al 110–125 % para que las tablas se lean.

| # | Escena (duración) | En pantalla | Narración (resumen) | Fuente de las cifras |
|---|---|---|---|---|
| 1 | El problema (1 min) | Portada o la web de Meridiano | Meridiano vive de la publicidad y cada anunciante que se va es facturación perdida. Objetivo: anticipar qué anunciantes van a abandonar en los próximos 210 días y decidir cada semana a cuáles dedicar el tiempo comercial. | — |
| 2 | Qué es abandonar (1 min) | `modelo_churn/informe.md`, apartado 3 | Abandonar = dejar de comprar (pérdida total) o comprar menos de la mitad que el año anterior en el mismo periodo (contracción). Los anunciantes de temporada que no compraban en esas fechas no cuentan como abandono. | Informe, apartado 3 |
| 3 | Los datos (1 min) | La hoja de Google y W0 terminando en `carga_ok` | Datos ficticios de ene-2020 a nov-2026: campañas, facturas, contactos comerciales y propuestas. Cada lunes se validan y se cargan solos. | Informe, apartado 2 |
| 4 | ¿Funciona el modelo? (2 min) | `modelo_churn/informe.md`, apartado 5 | Se entrenó con 2020 → jun-2025 y se probó con sep-2025 y dic-2025, que el modelo no había visto. AUC 0,883 (IC 95 %: 0,842–0,920), frente a 0,731 ordenando por días sin campaña y 0,518 por valor de la cuenta. Entre el 25 % de cuentas de más riesgo, el 92 % abandonó de verdad (74 % con la mejor regla sencilla). **Esto está medido.** | Informe, apartado 5 |
| 5 | Por qué se va un anunciante (1 min) | Informe, apartado 7 | Lo que más pesa: días sin contacto comercial, no tener pedidos firmados, la caída de la inversión y cuánto compró en el mismo periodo del año anterior (cuanto más compró, más fácil es que se quede por debajo de la mitad). Las dos primeras son palancas que un comercial puede tocar. | Informe, apartado 7 |
| 6 | El sistema en marcha (2 min) | W1 en n8n, registro de GitHub Actions y el panel | Cada martes el modelo puntúa a los anunciantes activos y elige las 12 cuentas de la semana, 4 por comercial: las de mayor valor esperado de actuar. Un 20 % de las cuentas de riesgo medio queda como grupo de control y no recibe acción. | Registro de la ejecución; `propuestas/config/parametros.json` |
| 7 | El trabajo del comercial (1,5 min) | Panel de Lovable, usuario comercial | Ve sus cuentas, el motivo y el material preparado. Corrige, aprueba (sale el correo) y al cerrar confirma qué pasó. Todo queda registrado. | — |
| 8 | Aprender de las acciones (1,5 min) | Panel de dirección, bloque «Resultado de las acciones», con el aviso de simulacro, y `demo/salida/simulacro.xlsx` | A los 210 días el sistema compara el abandono de las cuentas con acción con el del grupo de control (riesgo medio). **Lo que se ve es un simulacro:** decisiones de los comerciales simuladas y un **efecto supuesto** (la acción evita el 30 % de los abandonos): 20,0 % de abandono con acción frente a 46,2 % en el control. Sin el supuesto la diferencia es de 12,8 puntos y **no es un efecto**, sino azar con 13 cuentas en el control. El modelo, además, deja de aprender de las cuentas en las que se actuó. | `simulacro.xlsx`, hojas 5 y 6 |
| 9 | ¿Es viable? (1,5 min) | Diapositiva con los tres puntos de abajo | Ver «Cómo decidir la viabilidad». | Informe, apartados 8 y 9; `parametros.json` |
| 10 | Limitaciones (0,5 min) | Informe, apartado 8 | Datos ficticios, pocos anunciantes (142 en la prueba) y efecto de la acción todavía sin medir. | Informe, apartado 8 |

## Cómo decidir la viabilidad (escena 9)

1. **¿Sabe el sistema a quién llamar? Sí, medido.** Ordena el riesgo mucho mejor que las reglas sencillas (AUC 0,883
   frente a 0,731) y acierta en el 92 % del 25 % de más riesgo.
2. **¿Compensa actuar? Depende de un dato que aún no existe: cuántas cuentas en riesgo salva una acción.** Hoy el
   sistema decide con un supuesto: actúa si probabilidad de abandono × valor de la cuenta × 20 % de recuperación supera
   120 € de coste por acción (`propuestas/config/parametros.json`). Ese 20 % es un supuesto, no una medida.
3. **Cómo se mide:** con el grupo de control y la ventana de 210 días. Propuesta para la decisión:
   - piloto de 2 trimestres con el sistema tal como está;
   - medir el efecto en la banda media (acción frente a control) en el bloque «Resultado de las acciones»;
   - con la tasa de recuperación real, recalcular si el valor esperado compensa el coste comercial. Si no compensa,
     se ajustan el coste, la capacidad o las cuentas elegibles; si compensa, se amplía.

Mensaje final: «El modelo ya sabe dónde mirar. El piloto dirá si actuar compensa, y el sistema está preparado para
medirlo sin trabajo adicional».

## Lo que NO se debe decir en la grabación

- Que el sistema «salva» un porcentaje de cuentas: las cifras de cuentas salvadas son del simulacro con efecto supuesto.
- Que los 12,8 puntos sin supuesto demuestran algo: con acciones simuladas no hay efecto que medir.
- Cifras de facturación recuperada: todavía no hay ninguna medida.
