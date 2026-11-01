# Panel del equipo comercial de Meridiano · prompt para Lovable

> **Pendiente de actualizar (fase 3 del panel comercial unificado).** El esquema ya incluye leads, contactos, etiquetas y el ciclo aprobar → enviar → seguimiento → cierre (`accion_panel` con `aprobar`, `rechazar`, `registrar_respuesta`; `alta_lead_panel`; `registrar_consentimiento`). La acción `marcar_en_curso` de este prompt ya no existe: la sustituye «Aceptar» (`aprobar`). Este prompt se reescribe en la fase 3.

> **Cómo usarlo.** En Lovable: crear proyecto → conectar **Supabase** (integración nativa) con el proyecto donde se ejecutó `supabase/schema.sql` → pegar el bloque "Prompt" de abajo como primer mensaje. Si Lovable propone crear tablas, funciones o migraciones, **rechazarlo**: el esquema ya existe y lo gobierna el repositorio. El panel usa solo la clave pública (*anon*) y el inicio de sesión de cada persona; la clave de servicio nunca va en el panel.
>
> **Trazabilidad.** El panel escribe directamente en Supabase, pero solo llamando a la función `accion_panel`. Cada acción queda registrada con su autor (sacado de la sesión, no se puede suplantar) en `eventos_propuesta`, y cada corrección del material es una versión nueva en `material_versiones`. Nada se sobrescribe ni se pierde.
>
> Después, dar de alta a los usuarios en Supabase → Authentication y su fila en `perfiles` (correo, rol, id_comercial).

---

## Prompt

Construye una aplicación web interna en **español** llamada **"Meridiano · Plan de retención"** para el equipo comercial de un medio digital que vive de anunciantes. La base de datos es **Supabase, ya creada**: no crees tablas, columnas, migraciones ni funciones; usa exactamente las que se describen. Los permisos los resuelve la seguridad a nivel de fila (RLS) de Supabase: no filtres por comercial en el cliente como medida de seguridad, solo como comodidad.

**Regla principal de escritura:** la aplicación **nunca** hace `insert`, `update`, `upsert` ni `delete` sobre ninguna tabla (la base de datos lo rechaza). **Toda** acción del usuario se guarda con una única llamada:

```ts
const { data, error } = await supabase.rpc('accion_panel', {
  p_propuesta_id: propuesta.id,
  p_accion: 'marcar_en_curso' | 'guardar_material' | 'cerrar' | 'reabrir',
  p_datos: { ... }   // según la acción, ver abajo
});
// data = la propuesta actualizada (JSON). error.message = motivo legible, en español, para mostrar al usuario.
```

| Acción | `p_datos` | Cuándo |
|---|---|---|
| `marcar_en_curso` | `{}` | Botón "Empezar" en una propuesta pendiente |
| `guardar_material` | `{ material: "<texto completo>" }` | Botón "Guardar corrección" del material (crea una versión nueva; si estaba pendiente, pasa a en curso) |
| `cerrar` | `{ estado_confirmado_comercial, motivo_confirmado, diagnostico_correcto, comentario_comercial }` | Botón "Cerrar propuesta" |
| `reabrir` | `{ motivo: "<por qué>" }` | Botón "Reabrir" en una propuesta cerrada (pide el motivo en un diálogo) |

Tras cada llamada correcta, sustituir la propuesta en pantalla por `data` y recargar su historial. Si hay `error`, mostrar `error.message` en un aviso y no dar la acción por hecha.

**Qué hace la aplicación.** Cada **martes por la mañana** un proceso automático publica en la tabla `propuestas` 12 cuentas nuevas de anunciantes con probabilidad de abandono, repartidas entre 3 comerciales (4 cada uno), para que el trabajo no llegue todo a la vez. Cada comercial ve sus propuestas, ejecuta la acción sugerida fuera de la aplicación (llamada, reunión, correo propio) y vuelve para **cerrar** la propuesta con lo que pasó. La aplicación **no envía nada a los anunciantes**.

### Datos (Supabase)

- `perfiles(correo, rol, id_comercial)`: `rol` es `comercial` o `direccion`. Tras el login, leer el perfil del usuario por su correo para saber su rol.
- Vista `plan_vigente`: las propuestas nuevas de la última semana y las de semanas anteriores que siguen sin cerrar (mismas columnas que `propuestas`, más `nueva_esta_semana` booleano).
- `propuestas`: `id`, `fecha_corte`, `id_cliente`, `comercial_asignado`, `comercial_nombre`, `orden_comercial`, `razon_social`, `categoria`, `tipo_riesgo` (`perdida_total` | `contraccion`), `banda_riesgo`, `prob_abandono` (0–1), `valor_esperado_accion` (€), `facturacion_en_riesgo` (€), `valor_cuenta` (€), `cuenta_clave` (bool), `requiere_direccion` (bool), `motivo_principal`, `motivo_secundario`, `accion_id`, `producto_sugerido_nombre`, `fecha_limite`, `justificacion` (texto), `ficha_cuenta` (texto), `material_titulo`, `material_cuerpo`, `notas_internas`, `fuente_material` (`llm` o empieza por `plantilla`).
  Seguimiento (solo lectura; cambia con `accion_panel`): `estado_tarea` (`pendiente` | `en_curso` | `cerrada`), `estado_confirmado_comercial`, `motivo_confirmado`, `diagnostico_correcto`, `comentario_comercial`, `material_editado` (última corrección del comercial), `fecha_confirmacion`.
- `eventos_propuesta(id, propuesta_id, accion, usuario, estado_antes, estado_despues, datos jsonb, creado_en)`: historial de cada propuesta. Valores de `accion`: `publicada`, `material_plantilla`, `material_ia`, `marcar_en_curso`, `guardar_material`, `cerrar`, `reabrir`.
- `material_versiones(id, propuesta_id, version, origen, autor, texto, creado_en)`: todas las versiones del material; `origen` es `plantilla` (motor), `llm` (redactado por Claude y validado) o `comercial` (corrección).
- Datos de la cuenta, de solo lectura: `dim_clientes` (por `id_cliente`), `fact_campanas` (`fecha_emision`, `familia`, `importe_eur`, `impresiones`, `clics`, `leads_entregados`), `fact_interacciones` (`fecha`, `tipo`, `canal`, `resultado`), `fact_facturacion` (`fecha_emision`, `importe_eur`, `estado`, `dias_retraso`).
- Solo dirección: `kpis_ciclo(fecha_corte, indicador, valor)` (uno por ciclo semanal), `estado_etiqueta(fecha_corte, etiqueta_vigente, estado, casos, acuerdo)`, `ejecuciones(fecha, origen, estado, detalle jsonb)`.

### Listas cerradas (usar exactamente estos valores en los desplegables)

- `estado_confirmado_comercial`: `Perdido`, `Redujo mucho`, `Activo`, `Pausa: volvió después`, `No sé`.
- `motivo_confirmado` (mostrar la etiqueta, guardar el valor): `rendimiento_campanas` → "Rendimiento de las campañas", `relacion_interlocutor` → "Cambio o relación con el interlocutor", `perdida_contacto` → "Pérdida de contacto", `servicio_reclamacion` → "Servicio o reclamación", `presupuesto_inversion` → "Presupuesto o inversión", `cobro_financiero` → "Cobro o situación financiera", `temporada` → "Temporada", `otro` → "Otro".
- `diagnostico_correcto`: `Sí`, `No`.
- Mostrar `tipo_riesgo` como "Pérdida total" / "Contracción" y `motivo_principal` y `accion_id` sustituyendo `_` por espacios con la primera letra en mayúscula.

### Pantallas

1. **Inicio de sesión** con Supabase Auth (correo y contraseña, o enlace mágico). Sin registro abierto: si el correo no tiene fila en `perfiles`, mostrar "Tu usuario no tiene acceso al panel; contacta con dirección" y cerrar sesión.

2. **Mi plan** (pantalla principal del rol `comercial`). Lee `plan_vigente`, ordenado primero por `fecha_limite` y después por `orden_comercial`. Cabecera con "Semana del dd/mm/aaaa" (la `fecha_corte` más reciente), contador "X de N cerradas" y barra de progreso. Dos secciones: **"Nuevas esta semana"** (`nueva_esta_semana` verdadero) y **"Pendientes de semanas anteriores"**. Una tarjeta por propuesta con: número de orden, `razon_social`, `categoria`, etiqueta de tipo de riesgo (contracción en ámbar, pérdida total en rojo), `facturacion_en_riesgo` en €, acción sugerida, `fecha_limite` (en rojo si ya pasó y no está cerrada), distintivos "Cuenta clave" y "Requiere dirección" cuando sean verdaderos, y el estado de la tarea. Filtros: estado de la tarea y tipo de riesgo. **No mostrar `prob_abandono` como porcentaje al comercial**; basta con `banda_riesgo`.

3. **Detalle de la propuesta** (al pulsar una tarjeta), con tres bloques:
   - *Por qué está en el plan*: `justificacion` y `ficha_cuenta` (texto con saltos de línea), `motivo_principal` y `motivo_secundario`, producto sugerido. Debajo, pestañas de solo lectura con las últimas 10 campañas, las últimas 10 interacciones y las facturas pendientes o con retraso de ese `id_cliente`.
   - *Material de apoyo*: `material_titulo` y un área de texto editable que se inicia con `material_editado` si existe o, si no, con `material_cuerpo`. Botones "Copiar" (al portapapeles) y "Guardar corrección" (`accion_panel` con `guardar_material`; desactivado si el texto no ha cambiado o la propuesta está cerrada). Indicar "Versión N · autor · fecha" de la versión vigente. Enlace "Ver versiones" que abre la lista de `material_versiones` de la propuesta (de la más reciente a la más antigua), con el texto de cada una y un botón "Recuperar esta versión" que copia ese texto al editor (al guardarlo se crea una versión nueva; nunca se borra ninguna). Aviso fijo: "Material interno de apoyo. Revísalo antes de usarlo; la aplicación no lo envía al cliente". Si `fuente_material` es `llm`, mostrar "Redactado con IA y validado"; si empieza por `plantilla`, "Plantilla estándar". `notas_internas` en un recuadro gris marcado "Solo para ti, no compartir con el cliente".
   - *Cierre*: botón "Empezar" si está pendiente (`marcar_en_curso`). Formulario con los tres desplegables obligatorios (estado confirmado, motivo confirmado, ¿el diagnóstico del sistema era correcto?) y un comentario opcional. El botón "Cerrar propuesta" solo se activa con los tres desplegables rellenos y llama a `accion_panel` con `cerrar`. Una propuesta cerrada se muestra en modo lectura con un botón "Reabrir", que pide el motivo y llama a `reabrir`.
   - *Historial*: línea de tiempo con los `eventos_propuesta` de la propuesta, del más reciente al más antiguo: fecha y hora, quién (`usuario`), qué (texto legible de `accion`: "Publicada por el motor", "Material redactado con IA", "Empezada", "Material corregido (versión N)", "Cerrada: <estado> · <motivo>", "Reabierta: <motivo>") y el cambio de estado.

4. **Histórico** (comercial): propuestas cerradas de `propuestas`, agrupadas por semana (`fecha_corte`), con su estado confirmado y motivo. Solo lectura.

5. **Dirección** (solo rol `direccion`; ocultar la entrada en el menú para comerciales):
   - Selector de semana (`fecha_corte` disponibles en `propuestas`, la más reciente por defecto) y un resumen de las últimas 4 semanas.
   - Indicadores de `kpis_ciclo` de esa semana en tarjetas (mostrar `indicador` y `valor` tal cual).
   - Estado de la etiqueta de abandono de `estado_etiqueta`: etiqueta vigente (E2 o A), estado, casos y acuerdo como porcentaje. Si la etiqueta vigente es `A`, mostrar un aviso: "La validación automática no ha confirmado E2; el sistema mide con la regla A (210 días sin campaña)".
   - Tabla por comercial: propuestas, cerradas, % cerradas, % "diagnóstico correcto = Sí" sobre cerradas, facturación en riesgo total y recuperada (suma de `facturacion_en_riesgo` de las cerradas con estado `Activo` o `Pausa: volvió después`).
   - Lista de cuentas con `requiere_direccion` o `cuenta_clave` y su estado.
   - Últimas 10 `ejecuciones` (fecha, origen, estado, y `detalle` desplegable).
   Dirección puede abrir el detalle de cualquier propuesta.

### Estilo

Herramienta de trabajo sobria: fondo claro, tipografía legible de tamaño generoso, un color de acento azul oscuro, sin animaciones decorativas ni emojis. Pensada para portátil y que funcione en móvil (las tarjetas pasan a una columna). Formato español: euros con separador de miles con punto y sin decimales (`12.500 €`), fechas `dd/mm/aaaa`.

### Reglas

- No crear tablas, columnas, funciones ni políticas en Supabase.
- Ninguna escritura que no sea `supabase.rpc('accion_panel', …)`.
- No añadir envío de correos ni integraciones externas: los avisos los hace n8n a partir de los eventos que registra Supabase.
- Todos los datos son ficticios (caso de estudio); no añadir datos de ejemplo inventados en el código.

---

## Comprobaciones tras la primera versión (pedírselas a Lovable si fallan)

| Comprobación | Resultado esperado |
|---|---|
| Entrar como COM-01 | Solo ve sus 4 propuestas de la semana y sus pendientes; las cuentas de otros comerciales no aparecen ni por URL |
| Cerrar sin los tres desplegables | El botón está desactivado |
| Cerrar con los tres | `estado_tarea = cerrada`, `fecha_confirmacion` rellena y un evento "Cerrada" con tu correo en el historial |
| Corregir el material dos veces | Versiones 2 y 3 en "Ver versiones", con tu correo; la plantilla original sigue como versión 1 |
| Cerrar una cuenta clave como Perdido | Llega la alerta a dirección (n8n W2) |
| Intentar un `update` directo desde la consola del navegador | Supabase lo rechaza (permiso denegado) |
| Llamar a `accion_panel` sobre una propuesta de otro comercial | Error "Esta propuesta no está en tu cartera" |
| Entrar como dirección | Ve el menú Dirección, los KPI y las 12 propuestas de la semana |
