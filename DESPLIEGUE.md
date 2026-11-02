# Meridiano · Puesta en marcha con n8n Cloud, Supabase y Lovable

## Cadencia

Decisión del equipo: el riesgo se calcula **cada martes por la mañana** para no saturar al equipo. Cada ciclo propone **4 cuentas nuevas por comercial** (12 por semana, unas 52 al mes). Una cuenta propuesta o en el grupo de control no vuelve a proponerse en 90 días, y el sorteo del grupo de control es estable durante el trimestre.

## Circuito

```
  Google Sheets (tablas) ──► n8n W0, lunes 21:00: valida y carga ──► Supabase
            martes 7:00                                     cada acción del comercial
  n8n Cloud ──► motor (GitHub Actions) ──► Supabase ◄──────────────────────────── Lovable (panel)
     │  W1: Claude redacta → validador ──────► Supabase ──── lectura (RLS) ──────────► Lovable
     │                                           │  accion_panel(): cambia la propuesta +
     │                                           │  evento + versión del material (una transacción)
     └──◄── W2: webhook de base de datos ◄───────┘  cada evento nuevo → alerta a dirección si es un cierre que lo requiere
        W3: lunes 8:00, recordatorio de tareas pendientes
```

| Pieza | Papel | Qué decide |
|---|---|---|
| **Google Sheets** | Fuente de las tablas: el equipo añade cada semana órdenes, facturas, interacciones y oportunidades | Nada: n8n la valida antes de cargarla |
| **Supabase** | Base de datos común y registro de trazabilidad | Quién ve qué (RLS por comercial; dirección todo). El panel solo escribe a través de `accion_panel()` |
| **Motor** (GitHub Actions) | El ciclo evaluado. n8n lo lanza cada martes con la API de GitHub y espera su aviso (nodo *Wait*). No guarda nada: lee y escribe en Supabase. Gratuito y sin servidor | Etiqueta vigente (E2 o A), puntuaciones L2, las 12 propuestas de la semana, KPIs |
| **n8n Cloud** | Orquestación y conexión con la IA | Cuándo se ejecuta cada cosa; redacción con Claude y descarte por el validador; avisos |
| **Claude (API)** | Redacta el material de apoyo de cada propuesta | Nada: su texto solo se usa si pasa el validador; si no, queda la plantilla del motor |
| **Lovable** | Panel del equipo comercial | Nada del modelo: muestra el plan, recoge las correcciones y el cierre |

## Trazabilidad

Toda escritura del panel pasa por **una sola función de Supabase, `accion_panel`**, que en la misma transacción:

1. saca el usuario **de la sesión** (no se puede suplantar) y comprueba que la propuesta es de su cartera (dirección: todas);
2. valida la acción (cierre con estado, motivo y diagnóstico; reapertura con motivo; material no vacío y con cambios);
3. cambia la propuesta;
4. registra el evento en `eventos_propuesta` (quién, cuándo, estado antes y después, datos) y, si es una corrección, una **versión nueva** del material en `material_versiones`.

Si cualquier paso falla, no se guarda nada. El panel no puede insertar, modificar ni borrar filas de ninguna tabla por otra vía. Las publicaciones del motor y los textos de la IA también quedan registrados por un disparador de la base de datos. Resultado: de cada propuesta se puede ver quién la publicó, qué redactó la IA, cada corrección del comercial (con el texto completo), cuándo se cerró, con qué diagnóstico, y cada reapertura con su motivo.

## Flujos de n8n (`n8n/*.json`)

| Flujo | Disparador | Pasos |
|---|---|---|
| **W0 · Carga semanal** | **Lunes, 21:00** (y manual) | Lee las 8 pestañas de la hoja (incluidos los contactos ficticios) con una sola llamada de solo lectura a la API de Google Sheets → valida columnas, tipos, fechas, identificadores repetidos y referencias (anunciante, producto, orden) → carga en Supabase por lotes de 1.000, actualizando por identificador → registro en `ejecuciones` → correo al responsable de datos si hay filas rechazadas o errores. Si falta una pestaña o columna, o más del 5 % de una tabla tiene errores, **no carga nada** y avisa |
| **W1 · Ciclo semanal** | **Martes, 7:00** (y manual) | Fecha de corte (lunes anterior) → motor `/ciclo` → una propuesta por item → **Claude** redacta el material (1 llamada cada 1,5 s, 3 reintentos) → **Validador** → `PATCH` en Supabase → un correo interno por comercial → registro en `ejecuciones`. Si el motor falla: correo a dirección y no se publica nada |
| **W2 · Alertas de cierre** | Webhook de base de datos de Supabase (cada fila nueva de `eventos_propuesta`) | Solo cierres → lee la propuesta → alerta a dirección si se pierde una cuenta clave, una cuenta marcada para dirección no se recupera o se pierde por reclamación |
| **W3 · Recordatorio** | Lunes, 8:00 (la víspera del nuevo lote) | Tareas sin cerrar de cualquier semana → un correo por comercial con las que vencen en 7 días o ya vencieron |

El código de los nodos *Code* está en `n8n/codigo/*.js` y se prueba con node (`tests/test_n8n.py`). Para regenerar los JSON tras cambiarlo: `python n8n/construir_flujos.py`.

## Puesta en marcha (una vez)

### 1. Supabase
1. Crear un proyecto en supabase.com (plan gratuito).
2. *SQL Editor* → pegar y ejecutar `supabase/schema.sql` (se puede ejecutar varias veces). Si el proyecto tenía una versión anterior del esquema, ejecutar antes `supabase/reset.sql` (borra los objetos del caso y sus datos).
   Comprobar con `supabase/comprobar.sql`: **no debe devolver ninguna fila**. Si lista «FALTAN permisos…» (proyectos creados sin permisos automáticos sobre tablas nuevas), ejecutar `supabase/permisos.sql`.
3. *Authentication → Users*: crear los usuarios del panel. Para cada uno, una fila en `perfiles` (correo, rol `comercial` o `direccion`, `id_comercial`). **En la demo**, todos son alias de tu cuenta de Gmail (`tu-cuenta+martina@gmail.com`, `+comercial2`, `+comercial3`, `+direccion`): hay un ejemplo comentado al final del esquema.

### 2. Hoja de datos en Google Sheets
1. `python despliegue/preparar_hoja_datos.py` genera `despliegue/Meridiano_Datos_Operativos.xlsx` (una pestaña por tabla y una pestaña LEEME).
2. Google Drive → Nuevo → Hoja de cálculo → *Archivo → Importar → Subir* ese archivo → **Sustituir hoja de cálculo**.
3. *Archivo → Configuración*: configuración regional **España**.
4. Copiar el identificador de la hoja (lo que va entre `/d/` y `/edit` en la URL) para el nodo *Configuración* de n8n.

### 3. Motor en GitHub Actions (gratuito, sin servidor)
1. github.com → **New repository** → nombre `meridiano-motor`, **Private**, sin README → *Create repository*.
2. Subir el código del paquete al repositorio (lo hace Claude con acceso al repositorio, o *Add file → Upload files* con el contenido del paquete, incluida la carpeta `.github`).
3. *Settings → Secrets and variables → Actions → New repository secret*: `SUPABASE_URL` y `SUPABASE_SERVICE_KEY` (la service_role).
4. Token para n8n: tu foto → *Settings → Developer settings → Personal access tokens → Fine-grained tokens → Generate new token*. *Repository access:* solo `meridiano-motor`. *Permissions → Repository → Actions:* **Read and write**. Copiar el token (`github_pat_…`).
5. Prueba: *Actions → Motor de churn → Run workflow* con fecha `2026-09-28`. Debe acabar en verde (2–3 minutos) y en Supabase aparecen 12 filas en `propuestas`. En la ejecución se guardan como *artifact* el plan y el cuadro de mando.

> n8n lanza la acción con la fecha de corte y la URL en la que espera (`$execution.resumeUrl`); al terminar, la acción le envía el resultado. Si falla o tarda más de 30 minutos, n8n avisa a dirección con el enlace a la ejecución.

### 4. n8n Cloud
1. *Credentials* → crear:

   | Nombre (exacto) | Tipo | Contenido |
   |---|---|---|
   | GitHub Meridiano | Header Auth | Name `Authorization`, Value `Bearer github_pat_…` (el token del paso 3.4) |
   | Anthropic API | Header Auth | `x-api-key` = clave de la API de Claude |
   | Supabase account | **Supabase API** | *Host* = `https://<proyecto>.supabase.co` (con https, sin barra final) · *Secret Key* = clave service_role/secret. Debe dar «Connection tested successfully» |
   | Webhook Supabase | Header Auth | `x-webhook-token` = otra cadena larga inventada |
   | Gmail account | **Gmail OAuth2 API** | *Sign in with Google* con tu cuenta. Todos los correos salen de esa cuenta |
   | Google Sheets Meridiano | Google Sheets OAuth2 API | *Sign in with Google* con la cuenta que tiene la hoja |

2. *Workflows → Import from file*: `W0_carga_semanal.json`, `W1_ciclo_semanal.json`, `W2_alertas_cierre.json`, `W3_recordatorio_semanal.json`. Abrir cada nodo con credencial y seleccionarla. **Ningún nodo debe quedar con datos fijados (morado con chincheta): no aceptar datos de prueba del n8n Assistant.**
3. En el nodo **Configuración** de cada flujo: repositorio del motor (`usuario/meridiano-motor`) y rama (`main`), URL de Supabase, identificador de la hoja de datos, URL del panel, correos de dirección y del responsable de datos, modelo y **modo demo** (`modo_demo: true`, `buzon_demo` = tu cuenta con alias `+demo`). Con el modo demo, **todos** los correos de los flujos llegan a tu buzón y el asunto indica a quién habrían ido. No se usan variables de entorno: n8n Cloud no las admite.
4. Ejecutar **W0 a mano** («Cargar ahora»): es la carga inicial. En Supabase, la tabla `ejecuciones` debe mostrar `carga_ok` con las 8 tablas completas (solo llega correo si hay filas rechazadas o errores).
5. Activar los cuatro flujos. Copiar la *Production URL* del webhook de W2.

### 5. Webhook de base de datos (Supabase → n8n W2)
Supabase → *Database → Webhooks → Create*: tabla **`eventos_propuesta`**, evento **Insert**, tipo HTTP Request, método `POST`, URL = la *Production URL* de W2, cabecera `x-webhook-token` = el valor de la credencial "Webhook Supabase".

### 6. Lovable
Seguir `lovable/PROMPT_LOVABLE.md`. Poner la URL publicada del panel en el nodo *Configuración* (`panel_url`) de W1 y W3.

### 7. Prueba de la demostración
0. Añadir en la hoja una orden nueva con un anunciante inexistente y lanzar W0 a mano: la fila se rechaza y llega el correo con la fila y el motivo; el resto se carga.
1. En W1, cambiar el nodo *Fecha de corte* por `return [{ json: { fecha_corte: '2026-09-28' } }];` y ejecutarlo a mano: 12 propuestas en el panel (4 por comercial), materiales con su origen, 3 correos y una fila en `ejecuciones`.
2. En el panel, como comercial: empezar una propuesta, corregir el material dos veces, cerrarla. En "Historial" y "Ver versiones" aparece cada paso con su correo.
3. Cerrar una cuenta clave como *Perdido*: llega la alerta a dirección.
4. Como dirección: reabrir una propuesta con su motivo y revisar los KPI.
5. Repetir W1 con `2026-10-05`: otras 12 cuentas, ninguna repetida.

## Problemas frecuentes al montar (vistos en la puesta en marcha)

| Síntoma | Causa | Solución |
|---|---|---|
| Nodos en morado con chincheta 📌 y aviso «data was made up by the n8n Assistant» | Datos de prueba fijados: el nodo no se ejecuta de verdad | Seleccionar el nodo y pulsar **P** (o clic derecho → *Unpin*). No aceptar datos de prueba del asistente |
| «Credentials not found» o el error nombra una credencial que no existe | Tras importar, el nodo guarda una referencia a otra credencial | En el nodo: *Authentication → None* y volver a elegir el tipo y la credencial; guardar |
| «Domain not allowed … Only the following domains are allowed: …» | En la credencial, el campo *Allowed HTTP Request Domains* tiene un valor erróneo, o la URL de Configuración no lleva `https://` | Credencial con *Allowed domains = All*; `supabase_url` con `https://` y sin barra final |
| «Invalid URL … must start with http» | `supabase_url` sin `https://` | Corregir el nodo Configuración |
| «Invalid API key» en Supabase | Clave mal copiada en una credencial Custom Auth | Usar la credencial nativa **Supabase API** (*Host* + *Secret Key*), la que da «Connection tested successfully» |
| «permission denied» / «Authorization failed» con la clave correcta | Proyecto creado sin permisos automáticos sobre tablas nuevas | Ejecutar `supabase/permisos.sql`; `comprobar.sql` sin filas |
| «The resource you are requesting could not be found» al leer la hoja | `hoja_datos_id` incompleto o de otra cuenta de Google | Copiar entero el identificador entre `/d/` y `/edit` |
| «Invalid or unexpected token» | Sintaxis rota al editar el nodo Configuración (comillas tipográficas, coma) | Pegar el bloque completo de Configuración de nuevo |
| Se crean hojas «Hoja de cálculo sin título» en Drive | Versión anterior de W0 con nodos de Google Sheets | Usar la versión con una sola llamada de lectura (`Google Sheets: leer pestañas`) |
| El correo no sale («refused the connection») | SMTP mal configurado | Los flujos usan **Gmail** (Sign in with Google), no SMTP |

**Nunca** pegar tokens o claves en el nodo Configuración: solo en credenciales.

## Seguridad y datos

- Las claves privadas solo están en los secretos del repositorio de GitHub y en las credenciales cifradas de n8n; ningún JSON de flujo ni el panel contienen secretos (lo comprueba un test).
- El panel usa la clave pública: lo que ve cada usuario lo decide la RLS, y lo que puede cambiar, `accion_panel()`.
- A la API de Claude se envían solo la razón social, la categoría, el motivo, el producto sugerido y las evidencias numéricas de la cuenta; nunca datos personales de contactos.
- Nada sale hacia los anunciantes: los correos son internos y el material lo usa el comercial.
- **Todos los datos son ficticios** (caso de estudio).

## Alternativa sin GitHub

`motor/app.py` expone el mismo ciclo como servicio HTTP (`POST /ciclo`) para un servidor propio; habría que cambiar en W1 el lanzamiento por una llamada a ese servicio.

## Qué se ha probado y qué no

| Probado | Cómo |
|---|---|
| Esquema de Supabase en Postgres 16: traza de publicaciones, versiones de la IA y del comercial, cierre incompleto sin efectos, cerrar → reabrir → cerrar, el panel no puede escribir en tablas ni llamar a `registrar_accion`, `accion_panel` impide suplantar al autor y actuar fuera de la cartera | `tests/test_supabase.py` (Postgres local con una imitación mínima de Supabase Auth) |
| Motor: ciclo semanal completo, ejecución tal como la lanza GitHub Actions (sin secretos no calcula y deja el motivo), y W1 lanzando el motor, esperando su aviso y recibiendo las 12 propuestas | `tests/test_motor.py`; W1 ejecutado en n8n 2.44.6 contra una imitación de la API de GitHub |
| Carga semanal: las 7 tablas reales pasan completas; formatos españoles (DD/MM/AAAA, 1.234,50); rechazo de fechas imposibles, identificadores repetidos y referencias inexistentes (y de las facturas que dependen de ellas); carga detenida si falta una pestaña o columna o hay demasiados errores; los lotes entran en el esquema y una corrección en la hoja actualiza la fila | `tests/test_carga.py` (con Postgres 16) y W0 ejecutado en n8n 2.44.6 con la hoja simulada: 7 tablas, 14.842 filas en 20 lotes |
| Ciclos semanales consecutivos sin repetir cuentas; validación automática de E2 y vuelta a la regla A | `tests/test_ciclo.py` |
| Estructura de los flujos, ausencia de secretos y de `$env`, y la lógica de todos los nodos Code | `tests/test_n8n.py` |
| Importación de W0, W1, W2 y W3 en n8n 2.44.6, y ejecución de los nodos Code de W1 dentro de n8n | `n8n import:workflow` y `n8n execute` en una instancia local |

| Pendiente de probar en el despliegue real | Por qué |
|---|---|
| Llamadas reales a Google Sheets, Claude, al servidor de correo y a GitHub Actions | Requieren las cuentas y claves |
| RLS y `accion_panel` en Supabase real (con su Auth) | Probado con una imitación de `auth.jwt()`; la tabla de comprobaciones de `lovable/PROMPT_LOVABLE.md` lo cubre |
| El panel de Lovable | Lo genera Lovable a partir del prompt |
