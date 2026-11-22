# Comunicaciones comerciales por correo: baja, exclusión y conservación

Corrección del hallazgo **H2 (alta)** de la auditoría del diseño (W7, ejecución 95): «los correos no tienen mecanismo de baja, no hay lista de exclusión ni plazo de conservación».

> Caso de estudio ficticio. Los plazos son supuestos de diseño razonables, no asesoramiento jurídico; en un despliegue real los validaría el responsable de protección de datos.

## 1. Baja en cada correo

- Todo correo que envía W5 lleva un pie con la base del envío (relación comercial o consentimiento del lead), el canal para ejercer derechos (`correo_privacidad`) y un enlace **«darse de baja aquí»**.
- El enlace lleva un token aleatorio por contacto (`contactos.token_baja`, UUID); no contiene el correo ni se puede adivinar.
- La baja es en **dos pasos** (W8): abrir el enlace muestra una página de confirmación y la baja se registra solo al pulsar «Confirmar la baja». Así, los filtros de seguridad de los proveedores de correo, que abren los enlaces automáticamente, no dan de baja a nadie.
- **W5 no envía ningún correo sin enlace de baja**: si falta `baja_url` o el token, el envío queda en `error_envio` con el motivo.
- La baja también se puede registrar desde el panel (`baja_panel`), cuando el contacto la pide por teléfono, por correo o en persona. Solo sobre la propia cartera; dirección, sobre todas.

## 2. Lista de exclusión

- Tabla `exclusiones`: solo el correo normalizado, el motivo (`enlace_baja`, `solicitud_contacto`, `oposicion`, `rebote_permanente`), el origen, quién la registró y cuándo.
- El bloqueo está **en la base de datos** (trigger `propuestas_bloquear_excluidos`): da igual quién lo intente (panel, n8n o consola), una propuesta por correo a un contacto excluido no se puede aprobar ni marcar como enviada. Por llamada sí se puede, porque la baja es del canal correo.
- Además, W5 lee `contacto_excluido` en `envios_pendientes` y no llega a llamar a Gmail.
- Ni el panel ni n8n pueden modificar ni borrar una baja. La reactivación solo la hace dirección desde el editor SQL, con un consentimiento nuevo registrado.

## 3. Plazo de conservación (supuesto de diseño)

| Datos | Plazo | Cómo se controla |
|---|---|---|
| Leads no convertidos | 24 meses desde su última actividad | Vista `conservacion_vencida`; dirección revisa y borra |
| Contactos de cuentas que dejaron de ser clientes | 36 meses desde la última factura | Revisión anual de dirección |
| Facturación | El que fije la normativa fiscal y mercantil | Fuera del alcance del sistema |
| Lista de exclusión | Mientras exista el contacto, para garantizar que no se le vuelve a escribir | Solo el correo y el motivo |
| Propuestas, eventos y auditorías | Mientras dure el caso; son la evidencia del proceso | Tablas inmutables o con traza |

El borrado no se automatiza: una reclamación abierta necesita la evidencia. La vista solo señala lo vencido.

## 4. Pruebas

- `tests/test_supabase.py`: baja por enlace (con bloqueo al aprobar y al enviar, y con posibilidad de rechazar), token desconocido, mayúsculas y espacios en el correo, canal llamada no afectado, baja desde el panel solo en la propia cartera, y sin permiso de borrado.
- `tests/test_n8n.py`: correo HTML con la marca y el enlace de baja, texto escapado, bloqueo de excluidos y de correos sin enlace, página de baja en dos pasos y token inválido.
