# Demostración en directo · Meridiano, retención de anunciantes

Duración: 15–20 minutos. Todo es real salvo lo marcado como **[simulacro]**: los datos son ficticios (caso de estudio).

## Antes de la demostración (una vez)

1. Supabase, SQL Editor: ejecutar `supabase/modelo_churn.sql` (si aún no se ha hecho) y después
   `demo/salida/cargar_simulacro.sql` **[simulacro]**. El último `select` debe devolver tres grupos y una fila de efecto.
2. Pull request fusionada en `main` (el motor de GitHub Actions usa `main`) y cambios de `lovable/CAMBIO_MODELO_ABANDONO.md`
   aplicados en Lovable.
3. n8n, flujo **W1**: en el nodo *Fecha de corte*, fijar `return [{ json: { fecha_corte: '2026-11-23' } }];` (los datos
   llegan al 27-nov-2026; con una fecha fija la demo no depende del día real).
4. Si ya se ensayó: `supabase/restaurar_demo.sql` para dejar las propuestas de la semana como recién publicadas.
5. Abrir en pestañas: la hoja de Google, n8n (W0, W1 y W5), GitHub Actions del repositorio, el panel de Lovable con un
   usuario **comercial** y otro de **dirección**, y el buzón demo de Gmail.
6. Tener a mano `demo/salida/simulacro.xlsx` **[simulacro]**.

## 1. Los datos entran solos (W0) · 2 min

- Enseñar la hoja de Google: 8 pestañas, datos de ene-2020 al 27-nov-2026.
- En n8n, **W0 → Cargar ahora**. Termina en `carga_ok`: valida tipos, claves y referencias y carga en Supabase.
- Opcional: añadir en la hoja una orden con un anunciante que no existe y volver a cargar. Esa fila se rechaza, llega un
  correo con el motivo y el resto se carga.

> «Cada lunes por la noche la hoja de datos se valida y se carga sola. Si algo está mal, avisa y no carga basura».

## 2. El modelo elige las cuentas de la semana (W1 + motor) · 4 min

- En n8n, ejecutar **W1** a mano. Lanza el motor en GitHub Actions; enseñar el registro de la ejecución:
  - *Paso 3 · Puntuaciones del modelo de abandono*: el modelo se reentrena con todas las semanas con resultado conocido y
    puntúa a cada anunciante activo con su probabilidad de abandonar en 210 días.
  - *Paso 4 · Propuestas*: cómo se eligen las cuentas.
- **Cómo se seleccionan las cuentas** (explicarlo con el cuadro de mando o con la hoja «3 Plan semana demo» del simulacro):
  1. Probabilidad de abandono del modelo × valor de la cuenta → valor esperado de actuar.
  2. Solo se actúa si ese valor supera el coste de la acción.
  3. Las 12 de más valor, 4 por comercial.
  4. Un 20 % de las cuentas de riesgo medio va al **grupo de control**: no reciben acción y sirven para medir si actuar
     funciona.
  5. Una cuenta propuesta o en control no se repite en 90 días.
- Llegan los correos de la semana al buzón demo.

> «El modelo no sustituye al comercial: le dice a qué 4 cuentas dedicar la semana y por qué».

## 3. Lo que ve el comercial (Lovable) · 5 min

Con el usuario **comercial**:

- Sus 4 propuestas nuevas: empresa, tipo de riesgo, facturación en riesgo, acción sugerida y fecha límite. En el detalle,
  «Modelo: E2 · regresión logística (modelo_churn)». Las propuestas de semanas anteriores llevan «Modelo anterior».
- Abrir una propuesta: ficha de la cuenta, motivo, material preparado. Corregir el texto y **aprobar** → W5 envía el correo
  (en modo demo llega al buzón de pruebas indicando el destinatario real).
- Cerrar otra propuesta con los tres desplegables (estado, motivo, diagnóstico). Enseñar el historial.

> «Cada aprobación queda registrada: el sistema sabe en qué cuentas se ha actuado».

## 4. Lo que ve dirección y cómo aprende el sistema · 5 min

Con el usuario de **dirección**:

- Indicadores de la semana. Entre ellos, «Modelo de abandono» y la validación de la etiqueta E2 como indicador.
- Bloque **«Resultado de las acciones (210 días)»** **[simulacro]**, con el aviso ámbar de simulacro:
  - Tres grupos: con acción del comercial, propuestas sin acción y grupo de control.
  - Cuentas **salvadas**: hubo acción y no abandonaron.
  - **Efecto de la acción** en la banda de riesgo media, la única que tiene grupo de control.
- Explicar el simulacro con `demo/salida/simulacro.xlsx`:
  - Hoja «2 Acciones comerciales»: 8 semanas pasadas, 71 propuestas aprobadas y 20 rechazadas (decisiones simuladas).
  - Hoja «6 Efecto (banda media)»: en el **escenario supuesto** (la acción evita el 30 % de los abandonos), 20,0 % de
    abandono con acción frente a 46,2 % en el control (13 cuentas): 26,2 puntos.
  - Sin el supuesto también sale una diferencia (33,3 % frente a 46,2 %: 12,8 puntos), y **no es un efecto**: las acciones son simuladas y no
    cambian los datos. Es azar con solo 13 cuentas en el control. Por eso el panel avisa de que con pocas cuentas la
    diferencia puede deberse al azar.
- **Cómo aprende el modelo**: al reentrenar deja fuera las cuentas en las que se actuó (en el simulacro, 207
  observaciones), para no aprender que una cuenta salvada no estaba en riesgo. Y cada semana guarda los resultados con
  los datos de cada cuenta: con casos suficientes, se podrá entrenar un modelo de qué cuentas se pueden salvar.

> «A los 210 días sabremos si actuar sirve, comparando con cuentas iguales que no recibieron acción».

## Al terminar

1. Supabase: `demo/salida/borrar_simulacro.sql` **[simulacro]** (el último `select` debe devolver 0).
2. Supabase: `supabase/restaurar_demo.sql` si se quiere repetir la demo.
3. n8n, W1: devolver el nodo *Fecha de corte* a su código original (calcula el lunes anterior).

## Si algo falla

| Síntoma | Qué hacer |
|---|---|
| W1 termina en error en GitHub Actions | Revisar que `supabase/modelo_churn.sql` está ejecutado (el motor sube columnas nuevas) |
| El bloque de resultados sale vacío | Ejecutar `demo/salida/cargar_simulacro.sql` con un usuario de dirección |
| No aparece «Modelo: …» en las propuestas nuevas | Comprobar que la pull request está fusionada y que W1 ha corrido después |
| La fecha de corte da error «posterior al último dato» | Usar una fecha de corte ≤ 27-nov-2026 o cargar datos más recientes |
