# Panel comercial de Meridiano · prompt para Lovable

> **Cómo usarlo.**
> 1. En Lovable, crea un proyecto y **conecta tu proyecto de Supabase existente**: integración *Supabase → Connect*, y elige el proyecto `vxvmgwlrtrhqjuacmdss`. **No** uses el backend integrado de Lovable (*Lovable Cloud*): los datos, las reglas y la trazabilidad ya están en tu Supabase.
> 2. Pega el bloque **Prompt** como primer mensaje.
> 3. Si Lovable propone crear tablas, funciones, políticas o migraciones, **recházalo**. El esquema ya existe y lo gobierna `supabase/schema.sql`.
> 4. El panel usa solo la clave pública (anon) y el inicio de sesión de cada persona. La clave secreta nunca va en el panel.
>
> Datos ficticios (caso de estudio). Los usuarios de la demo son alias de una cuenta de Gmail.

---

## Prompt

Construye una aplicación web interna en **español** llamada **«Meridiano · Panel comercial»** para el equipo comercial de un medio digital que vive de anunciantes. La base de datos es **Supabase, ya creada**: no crees tablas, columnas, funciones, políticas ni migraciones, y usa exactamente lo que se describe aquí. Lo que ve cada usuario lo decide la seguridad a nivel de fila (RLS) de Supabase. Filtrar en el cliente es solo comodidad, no seguridad.

### Qué hace

Cada semana se publican en Supabase **propuestas** para empresas. Cada una lleva una **etiqueta**:
- `riesgo`: cliente con riesgo de abandono (churn). Se publica los martes.
- `ampliacion`: cliente actual con oportunidad de crecer.
- `lead_nuevo`: empresa que aún no es cliente.
- `seguimiento`: propuesta ya enviada que hay que seguir.

La IA ha redactado un material para cada propuesta. El comercial la **revisa en el panel**: la **acepta** (si es un correo, el sistema lo envía; si es una llamada, queda aprobada), **corrige** el texto o la **rechaza** con un motivo. Después **registra la respuesta** del cliente y la **cierra**. Todo queda registrado con su autor y su fecha. La aplicación **no envía correos por sí misma**: el envío lo hace otro sistema (n8n) cuando la propuesta queda aceptada.

### Regla de escritura (muy importante)

La aplicación **nunca** hace `insert`, `update`, `upsert` ni `delete` sobre ninguna tabla. La base de datos lo rechaza. **Todas** las acciones se hacen con estas funciones:

```ts
// Acciones sobre una propuesta
const { data, error } = await supabase.rpc('accion_panel', {
  p_propuesta_id: propuesta.id,
  p_accion: 'guardar_material' | 'aprobar' | 'rechazar' | 'registrar_respuesta' | 'cerrar' | 'reabrir',
  p_datos: { ... }   // según la acción (tabla de abajo)
});
// data = la propuesta actualizada (JSON). Si hay error, mostrar error.message (viene en español) y no dar la acción por hecha.

// Alta de un lead de puerta fría
await supabase.rpc('alta_lead_panel', { p: { razon_social, categoria, provincia, nombre, cargo, email, telefono,
                                             consentimiento_comercial, consentimiento_medio, consentimiento_nota, mensaje } });

// Registrar que un lead ha aceptado recibir información comercial
await supabase.rpc('registrar_consentimiento', { p_id_lead, p_medio: 'telefono' | 'presencial' | 'email', p_nota });
```

| Acción | `p_datos` | Botón |
|---|---|---|
| `guardar_material` | `{ material: "<texto completo>" }` | «Guardar corrección» (crea una versión nueva) |
| `aprobar` | `{}` | «Aceptar y enviar» si `canal = 'email'`; «Aprobar llamada» si `canal = 'llamada'` |
| `rechazar` | `{ motivo }` | «Rechazar» (diálogo que pide el motivo) |
| `registrar_respuesta` | `{ resumen }` | «Registrar respuesta del cliente» |
| `cerrar` (etiqueta `riesgo`) | `{ estado_confirmado_comercial, motivo_confirmado, diagnostico_correcto, comentario_comercial }` | «Cerrar» |
| `cerrar` (resto de etiquetas) | `{ desenlace, motivo_desenlace, comentario_comercial }` | «Cerrar» |
| `reabrir` | `{ motivo }` | «Reabrir» (diálogo que pide el motivo) |

Después de cada llamada correcta, sustituye la propuesta en pantalla por `data` y recarga su historial.

### Datos (solo lectura)

- `perfiles(correo, rol, id_comercial)`: rol `comercial` o `direccion`. Tras el login, lee el perfil por el correo del usuario.
- Vista **`plan_vigente`**: propuestas de la última semana y propuestas anteriores sin cerrar. Tiene las mismas columnas que `propuestas` y además `nueva_esta_semana` (booleano).
- **`propuestas`** (columnas principales):
  - Identificación y prioridad: `id`, `fecha_corte`, `etiqueta`, `id_cliente`, `id_lead`, `comercial_asignado`, `comercial_nombre`, `orden_comercial`, `razon_social`, `categoria`.
  - Diagnóstico: `tipo_riesgo` (`perdida_total` | `contraccion`), `banda_riesgo`, `facturacion_en_riesgo` (€), `valor_cuenta` (€), `cuenta_clave`, `requiere_direccion`, `motivo_principal`, `motivo_secundario`, `accion_id`, `producto_sugerido_nombre`, `fecha_limite`, `justificacion`, `ficha_cuenta`.
  - Material y canal: `canal` (`email` | `llamada`), `id_contacto`, `asunto_email`, `material_titulo`, `material_cuerpo`, `material_editado`, `notas_internas`, `fuente_material` (`llm` o texto que empieza por `plantilla`).
  - Seguimiento: **`estado`** (ver abajo), `texto_aprobado`, `version_aprobada`, `aprobada_por`, `aprobada_en`, `motivo_rechazo`, `enviada_en`, `error_envio`, `ultima_respuesta_en`, `estado_confirmado_comercial`, `motivo_confirmado`, `diagnostico_correcto`, `desenlace`, `motivo_desenlace`, `comentario_comercial`, `fecha_confirmacion`.
- **`estado`** (único estado que debe mostrar el panel):

  | Valor | Etiqueta visible | Color |
  |---|---|---|
  | `pendiente_aprobacion` | Pendiente de aprobar | ámbar |
  | `enviando` | Enviando… | azul |
  | `error_envio` | Error de envío | rojo |
  | `en_seguimiento` | En seguimiento | verde |
  | `rechazada` | Rechazada | gris |
  | `cerrada` | Cerrada | gris oscuro |

- `contactos(id_contacto, id_cliente, id_lead, nombre, cargo, email, telefono, principal, ficticio)`: muestra el contacto de cada propuesta (`id_contacto`). Si `ficticio` es verdadero, añade el distintivo «Contacto ficticio (demo)».
- `eventos_propuesta(id, propuesta_id, accion, usuario, estado_antes, estado_despues, datos, creado_en)`: historial de cada propuesta.
- `material_versiones(id, propuesta_id, version, origen, autor, texto, creado_en)`: `origen` puede ser `plantilla`, `llm` o `comercial`.
- `leads(id_lead, razon_social, categoria, provincia, origen, comercial_asignado, estado, consentimiento_comercial, consentimiento_fecha, consentimiento_medio, consentimiento_texto, creado_en)` y `eventos_lead`.
- Datos de cada cliente: `dim_clientes`, `fact_campanas` (`fecha_emision`, `familia`, `importe_eur`, `impresiones`, `clics`, `leads_entregados`), `fact_interacciones` (`fecha`, `tipo`, `canal`, `resultado`) y `fact_facturacion` (`fecha_emision`, `importe_eur`, `estado`, `dias_retraso`).
- Solo dirección: `kpis_ciclo(fecha_corte, indicador, valor)`, `estado_etiqueta(fecha_corte, etiqueta_vigente, estado, casos, acuerdo)` y `ejecuciones(fecha, origen, estado, detalle)`.

### Listas cerradas

- **Etiqueta:** `riesgo` → «Riesgo de abandono» (rojo) · `ampliacion` → «Ampliación» (azul) · `lead_nuevo` → «Lead nuevo» (violeta) · `seguimiento` → «Seguimiento» (gris).
- `estado_confirmado_comercial`: `Perdido`, `Redujo mucho`, `Activo`, `Pausa: volvió después`, `No sé`.
- `motivo_confirmado` (se muestra la etiqueta y se guarda el valor):

  | Valor | Etiqueta visible |
  |---|---|
  | `rendimiento_campanas` | Rendimiento de las campañas |
  | `relacion_interlocutor` | Cambio o relación con el interlocutor |
  | `perdida_contacto` | Pérdida de contacto |
  | `servicio_reclamacion` | Servicio o reclamación |
  | `presupuesto_inversion` | Presupuesto o inversión |
  | `cobro_financiero` | Cobro o situación financiera |
  | `temporada` | Temporada |
  | `otro` | Otro |
- `diagnostico_correcto`: `Sí`, `No`.
- `desenlace`: `ganada` → «Ganada», `perdida` → «Perdida», `descartada` → «Descartada». El motivo es obligatorio si no es «Ganada».
- `tipo_riesgo`: `perdida_total` → «Pérdida total», `contraccion` → «Contracción».
- `motivo_principal` y `accion_id`: sustituir `_` por espacios y poner la primera letra en mayúscula.

### Pantallas

1. **Inicio de sesión** con Supabase Auth (correo y contraseña). Sin registro abierto. Si el correo no tiene fila en `perfiles`, mostrar «Tu usuario no tiene acceso al panel» y cerrar la sesión.

2. **Mi panel** (pantalla principal).
   - **Datos:** lee `plan_vigente`.
   - **Cabecera:** «Semana del dd/mm/aaaa» (la `fecha_corte` más reciente) y cuatro contadores (pendientes de aprobar, en seguimiento, cerradas esta semana y errores de envío).
   - **Filtros:** etiqueta, estado y, solo para dirección, comercial.
   - **Agrupación:**
     - **Pendientes de aprobar**: incluye también las de error de envío.
     - **Enviando**
     - **En seguimiento**
     - **Cerradas o rechazadas esta semana**
   - **Orden:** dentro de cada grupo, por `fecha_limite` y después por `orden_comercial`.
   - **Tarjeta:** etiqueta de color, `razon_social`, `categoria`, tipo de riesgo si existe, `facturacion_en_riesgo` en €, acción sugerida, canal (icono de correo o de teléfono), `fecha_limite` (en rojo si ya pasó y no está cerrada), distintivos «Cuenta clave» y «Requiere dirección», estado y la marca «Nueva» si `nueva_esta_semana`.
   - **No** mostrar `prob_abandono` como porcentaje.
   - Si alguna propuesta está en «Enviando», refrescar la lista cada 10 segundos hasta que deje de estarlo.

3. **Detalle de la propuesta**, en cuatro bloques:
   - **Por qué está aquí:**
     - `justificacion` y `ficha_cuenta` (texto con saltos de línea), motivo y producto sugerido;
     - contacto: nombre, cargo, email y teléfono, con el distintivo de ficticio si corresponde;
     - pestañas de solo lectura con las últimas 10 campañas, las últimas 10 interacciones y las facturas pendientes del cliente.
   - **Material:**
     - `material_titulo` y un editor que empieza con `material_editado` o, si no hay, con `material_cuerpo`;
     - origen: «Redactado con IA y validado» si `fuente_material = 'llm'`; «Plantilla estándar» si empieza por `plantilla`;
     - botones «Copiar» y «Guardar corrección». El editor solo es editable en `pendiente_aprobacion` o `error_envio`; en los demás estados se muestra en solo lectura el **texto aprobado** (`texto_aprobado`);
     - enlace «Ver versiones»: lista de `material_versiones`, de la más reciente a la más antigua, con un botón «Recuperar esta versión» que copia el texto al editor. Al guardarlo se crea una versión nueva; nunca se borra ninguna;
     - `notas_internas` en un recuadro gris con el título «Solo para ti, no compartir con el cliente».
   - **Decisión y seguimiento** (los botones dependen del estado):
     - `pendiente_aprobacion` o `error_envio`: «Aceptar y enviar» (o «Aprobar llamada») y «Rechazar». En `error_envio`, mostrar `error_envio` y el texto «Corrige si hace falta y vuelve a aceptar».
     - `enviando`: aviso «Enviando… se actualizará en unos segundos».
     - `en_seguimiento`: «Registrar respuesta del cliente» y «Cerrar». El formulario de cierre depende de la etiqueta:
       - `riesgo`: los tres desplegables obligatorios y un comentario opcional;
       - resto: desenlace obligatorio, motivo obligatorio si no es «Ganada» y un comentario opcional.
     - `cerrada` o `rechazada`: resumen del cierre o del rechazo y botón «Reabrir», que pide el motivo.
     - Si un lead no tiene consentimiento, al aceptar el sistema devolverá un error explicativo. Muéstralo con un botón «Registrar consentimiento».
   - **Historial:** línea de tiempo con `eventos_propuesta`, de la más reciente a la más antigua. Muestra fecha y hora, quién y qué, en frases como:
     - «Publicada por el motor»
     - «Material redactado con IA»
     - «Material corregido (versión N)»
     - «Aceptada»
     - «Enviada por correo»
     - «Error de envío: …»
     - «Respuesta del cliente: …»
     - «Cerrada: …»
     - «Rechazada: …»
     - «Reabierta: …»

4. **Leads:**
   - Lista de `leads` del usuario: origen («Formulario web» o «Puerta fría»), estado y consentimiento («Acepta información comercial» con fecha y medio, o «Sin consentimiento»).
   - Botón **«Nuevo lead (puerta fría)»**. Abre un formulario con empresa, categoría, provincia, persona de contacto, cargo, email, teléfono y notas, y una casilla «Ha aceptado recibir información comercial» que, si se marca, pide el medio (teléfono, presencial o email) y una nota. Llama a `alta_lead_panel`.
   - En cada lead sin consentimiento, botón **«Registrar consentimiento»**, que llama a `registrar_consentimiento`.

5. **Dirección** (solo rol `direccion`; ocultar el menú a los comerciales):
   - Selector de semana (`fecha_corte`) e indicadores de `kpis_ciclo` en tarjetas.
   - Estado de la etiqueta de abandono (`estado_etiqueta`). Si la vigente es `A`, avisar: «La validación automática no ha confirmado E2; el sistema mide con la regla A».
   - Tabla por comercial con:
     - propuestas, aceptadas, rechazadas, cerradas y errores de envío;
     - % de «diagnóstico correcto = Sí»;
     - facturación en riesgo total y recuperada (cerradas como `Activo` o `Pausa: volvió después`).
   - Lista de cuentas clave o que requieren dirección, con su estado.
   - Últimas 10 `ejecuciones` (fecha, origen y estado, con el detalle desplegable).
   - Dirección puede abrir y gestionar cualquier propuesta.

### Estilo

Herramienta de trabajo sobria:
- fondo claro, tipografía legible, acento azul oscuro;
- colores solo para etiquetas y estados;
- sin animaciones decorativas ni emojis;
- en móvil, las tarjetas pasan a una columna.

Formato español: `12.500 €` y fechas `dd/mm/aaaa`.

### Reglas

- No crear nada en Supabase. Ninguna escritura que no sea una de las tres funciones `rpc` descritas.
- No enviar correos ni integrar servicios externos desde la aplicación.
- No añadir datos de ejemplo inventados en el código.

---

## Comprobaciones tras la primera versión

| Comprobación | Resultado esperado |
|---|---|
| Entrar como COM-01 | Solo sus propuestas y sus leads. Las de otros comerciales no aparecen ni por URL |
| Corregir el material dos veces | Versiones nuevas en «Ver versiones», con su correo; la plantilla o la IA siguen como versiones anteriores |
| Aceptar una propuesta por correo | Pasa a «Enviando…». Cuando el flujo de envío de n8n (W5) esté activo, pasa a «En seguimiento» y llega el correo al buzón demo |
| Aceptar una llamada | Pasa directamente a «En seguimiento» |
| Rechazar sin motivo | El diálogo no deja confirmar |
| Cerrar una propuesta de riesgo sin los tres desplegables | El botón está desactivado |
| Cerrar una cuenta clave como «Perdido» | Llega la alerta a dirección (n8n W2) |
| Alta de un lead de puerta fría sin consentimiento y aceptar su propuesta por correo | Error explicativo y botón «Registrar consentimiento» |
| `update` directo desde la consola del navegador | Supabase lo rechaza |
