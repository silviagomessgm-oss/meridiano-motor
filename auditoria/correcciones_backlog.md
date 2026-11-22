# Auditoría del backlog y de la solución desplegada (paso 08 FORGEN)

## Primera auditoría (22-nov-2026 · ejecución n8n 99 · paquete backlog-v2, sha `b0a1f05`)

Modelo auditor: `claude-fable-5-1` (W7, tipo `backlog`). Veredicto: **aprobado con cambios** · 3 altas, 6 medias, 3 bajas.

Resumen del auditor: «El backlog cubre los nueve nodos y el trabajo desplegado es amplio y bien trazado, pero tres hallazgos altos impiden darlo por terminado: parte del código desplegado (W4, W6 y el SQL de los lunes y del piloto) no está bajo control de versiones tras la pérdida del contenedor, la plataforma corre en un ordenador local del que dependen flujos programados y la página pública de baja, y no consta el encargo del tratamiento para los datos de clientes que viajan a la API de Claude y a GitHub Actions».

| Hallazgo | Gravedad | Resumen | Corrección propuesta por el auditor |
|---|---|---|---|
| H1 | Alta | W4, W6 y el SQL de lunes, seguimientos y piloto desplegados sin fuente versionada | Exportar W4 y W6, volcar el esquema de Supabase y versionarlo |
| H2 | Alta | n8n en un equipo local: flujos programados y página de baja caen si se apaga | n8n Cloud o servidor; enlace de baja en dominio estable |
| H3 | Alta | Encargados del tratamiento no constan en el backlog; datos de cuenta a Claude y GitHub Actions | Apartado de encargados, no retención, pseudonimizar lo que sale al motor |
| H4 | Media | Sin versión del modelo, probabilidad y variables por propuesta | Tres columnas escritas por W1 al publicar |
| H5 | Media | E2-H3 «desplegada» sin el aviso visual del panel | Estado «parcial» o aviso en Lovable |
| H6 | Media | Criterios del panel solo con prueba manual | Tests de RLS con dos comerciales y dirección; checklist manual fechada |
| H7 | Media | Sin flujo de errores ni tope de coste de IA | Error workflow en n8n; fallback si Claude falla; topes y límites |
| H8 | Media | Tests no trazados a criterios | Tabla criterio → test; test de concurrencia real de la reserva |
| H9 | Media | Envío real nunca ejercitado | Lista de paso a producción (remitente, SPF/DKIM, cuota, prueba externa) |
| H10 | Baja | Incoherencias en dependencias y nombres de grupos de control | Corregir orden y nombrar control_riesgo y control_avisos |
| H11 | Baja | Criterios no comprobables con sí/no | Reglas observables y checklist |
| H12 | Baja | Falta tabla regla transversal → historia | Añadirla y enlazar los plazos de conservación |

## Segunda auditoría (22-nov-2026 · ejecución n8n 100 · paquete backlog-v4, sha `c82c589`)

| | 1.ª (backlog-v2) | 2.ª (backlog-v4) |
|---|---|---|
| Veredicto | Aprobado con cambios | Aprobado con cambios |
| Altas | 3 | **2** (nuevas) |
| Medias | 6 | 7 |
| Bajas | 3 | 3 |

Las tres altas de la primera (reproducibilidad, despliegue en local, encargados) no reaparecen como altas: la reproducibilidad
y los encargados se dan por resueltos y el despliegue en local baja a media, como riesgo de operación (latido externo).
Resumen del auditor: «Quedan dos huecos altos con corrección clara: un elemento del diseño que puede provocar propuestas
duplicadas a un mismo cliente (leads que ya son cuentas) y varias historias declaradas desplegadas sin prueba trazable».

Hallazgos: lead que ya es cliente (alta) · historias desplegadas sin test en la tabla (alta) · «aprobada con aviso» no llega
a dirección (media) · caducidad de pendientes (media) · test del validador del comentario de W6 (media) · latido externo a
n8n (media) · resolver en el panel un envío sin confirmar (media) · exportar todos los flujos y retirar legado (media) ·
filas ausentes de la hoja (media) · coste mensual y rotación de credenciales (baja) · prioridades de dependencias (baja) ·
adjuntar política de conservación y regla del piloto (baja).
