# Cambio en el panel: dirección ve el equipo, no los clientes (28-nov-2026)

Pegar en Lovable **después** de ejecutar `supabase/panel_direccion.sql` en el SQL Editor de Supabase. No crea tablas ni
migraciones: solo lee vistas que ya existen.

---

Rehaz la página **Dirección** (solo rol `direccion`) para que muestre cómo trabaja el equipo, cómo va la venta y qué
conviene mejorar. **En esta página no aparece ningún nombre de cliente ni de lead**: ni en tarjetas, ni en tablas, ni en
listas. Dirección sigue pudiendo abrir cualquier propuesta desde la página de propuestas, como hasta ahora. Mantén el
estilo actual (Fraunces para cifras y títulos, IBM Plex Mono para rótulos, tarjetas `--paper-2` con filetes de 1 px, sin
sombras).

Arriba, un selector **«Periodo»**: «Esta semana» (la `fecha_corte` más reciente), «Últimas 4 semanas» (por defecto) y
«Últimas 12 semanas». Todos los bloques que dependen de semanas usan ese periodo.

**1. Resumen del equipo** (fila de 6 tarjetas, de `equipo_semana` sumando comerciales y tipos en el periodo):
- «Propuestas publicadas» (`publicadas`);
- «Aprobadas» (`aprobadas`, con «N % de las publicadas» debajo);
- «Días hasta decidir» (media de `dias_hasta_aprobar`, con un decimal);
- «Cerradas» (`cerradas`);
- «Ganadas» (`ganadas`, con «N % de las cerradas» debajo);
- «Facturación recuperada» (`facturacion_recuperada` en euros, con «de X € en riesgo» = `facturacion_en_riesgo` de las
  propuestas de etiqueta `riesgo`).

**2. Qué mejorar** (de `recomendaciones_direccion(prioridad, ambito, comercial, recomendacion, dato)`, ya ordenada):
lista de avisos, cada uno con su `ambito` como etiqueta (Capacidad, Medición, Ritmo, Seguimiento, Aprobación,
Conversión, Modelo, Textos de la IA, Verificación), el texto de `recomendacion` y, si hay `comercial`, su nombre. Prioridad
1 en borde rojo, 2 en ámbar, 3–5 en gris. Si no hay filas: «Sin incidencias: el equipo va al día». Nota fija debajo: «Reglas
fijas sobre las cuatro últimas semanas; los umbrales están en supabase/panel_direccion.sql».

**3. Embudo del equipo** (de `equipo_semana` en el periodo): barras horizontales Publicadas → Aprobadas → En marcha (`en_marcha`)
→ Con respuesta (`con_respuesta`) → Cerradas → Ganadas, con el número y el % sobre publicadas. Pestañas para filtrar por tipo:
«Todas», «Riesgo de abandono» (`riesgo`), «Ampliación» (`ampliacion`), «Lead nuevo» (`lead_nuevo`).

**4. Por comercial** (tabla, una fila por comercial; de `equipo_semana` en el periodo y de `equipo_ahora` para lo actual):
- del periodo: publicadas, % aprobadas, días hasta decidir, % ganadas, facturación recuperada, % textos de la IA corregidos
  (`aprobadas_editadas` / `aprobadas`), % diagnóstico correcto (`diagnostico_si` / `diagnostico_respondido`);
- ahora: pendientes de aprobar (`pendientes_aprobar`, y en ámbar `pendientes_mas_3_dias` si es mayor que 0), en
  seguimiento, toques pendientes, sin atender más de 7 días (en rojo si es mayor que 0) y errores de envío.
Fila final «Equipo» con los totales. Celda en ámbar cuando el valor del comercial se aparta más de 15 puntos de la media del
equipo en % aprobadas o % ganadas. Sin columnas de clientes.

**5. Evolución** (de `equipo_semana`, últimas 12 semanas, siempre): gráfico de líneas por semana con «% aprobadas» y «%
ganadas» del equipo, y barras de «publicadas». Debajo, el mismo gráfico por comercial en pestañas.

**6. Motor y medición** (sin clientes):
- tarjetas de `kpis_ciclo` de la última semana: «Propuestas de la semana», «Aplazadas por capacidad», «Grupo de control»,
  «Facturación en riesgo de las propuestas (€)». No muestres en esta página los indicadores de churn total ni de pérdida en
  la ventana: pasan a un desplegable «Más indicadores del motor», cerrado por defecto;
- validación de la etiqueta (`estado_etiqueta`), como ahora;
- «Resultado de las acciones (210 días)», de `resumen_resultado_acciones` y `efecto_accion`, como ahora pero **sin la tabla
  de `resultado_acciones` con empresas**;
- «Recuperación de cuentas en riesgo», de `recuperacion_riesgo`, como ahora (es agregada, sin clientes);
- «Piloto del seguimiento», como ahora.

**7. Escalados a dirección**: sustituye la lista de tarjetas «Cuentas clave o escaladas a dirección» (que muestra empresas)
por un único contador «Cuentas clave escaladas esta semana: N» (propuestas de `plan_vigente` de la última semana con
`requiere_direccion` o `cuenta_clave`) y el texto «El detalle llega por correo a dirección y está en la página de
propuestas».

**8. Sistema** (desplegable cerrado por defecto): últimas 10 `ejecuciones`, como ahora.

Elimina de la página de Dirección todo lo que muestre `razon_social`, `id_cliente`, `id_lead` o datos de contacto.

Comprobación: con el usuario de dirección no aparece ningún nombre de empresa en la página Dirección; los totales de
«Resumen del equipo» coinciden con la suma de la tabla «Por comercial»; con un comercial, el menú Dirección no aparece.
