"""
Genera los flujos de n8n de Meridiano (JSON importables: Workflows → Import from file).
  W0_carga_semanal.json        · lunes a las 21:00: lee las tablas de la hoja de Google Sheets → valida → carga en Supabase
                                 (actualiza por identificador) → registro en ejecuciones → aviso si hay filas rechazadas o errores
  W1_ciclo_semanal.json        · martes a las 7:00: lanza el motor en GitHub Actions y espera su resultado → IA (Claude) → validador → Supabase → aviso a cada comercial
  W5_envio_al_aceptar.json     · webhook de base de datos al aceptar una propuesta en el panel → envía por Gmail el texto
                                 aprobado al contacto (modo demo: al buzón de pruebas) → registrar_envio en Supabase
  W2_alertas_cierre.json       · webhook de base de datos de Supabase al registrarse un evento → si es un cierre que lo requiere,
                                 alerta a dirección. (El panel escribe directamente en Supabase con accion_panel(), que deja la traza.)
  W3_recordatorio_semanal.json · lunes: tareas sin cerrar del plan vigente → recordatorio a cada comercial
  W7_auditor.json              · a mano: lee de GitHub el paquete y la rúbrica → modelo auditor (Claude, distinto y más capaz
                                 que el generador) → valida el JSON → guarda en Supabase (auditorias) → resumen por correo
  W8_baja.json                 · enlace de baja del pie de los correos: página de confirmación → registrar_baja en Supabase
                                 (lista de exclusión) → página de resultado. W5 no envía a contactos excluidos.
El código JavaScript de los nodos Code está en n8n/codigo/*.js (probado con node en tests/test_n8n.py).
Credenciales (se crean en n8n y se seleccionan en los nodos tras importar):
  · "GitHub account"            GitHub API   · Access Token = token de GitHub (solo meridiano-motor, Actions: lectura y escritura)
  · "Anthropic API"             Header Auth  · x-api-key: <clave de la API de Claude>
  · "Supabase account"          Supabase API · Host https://<proyecto>.supabase.co + Secret Key (service_role o secret)
  · "Webhook Supabase"          Header Auth  · x-webhook-token: <token compartido con el webhook de base de datos>
  · "Gmail account"             Gmail OAuth2 (Sign in with Google; los correos salen de esa cuenta)
  · "Google Sheets Meridiano"   Google Sheets OAuth2 (cuenta con acceso a la hoja; W0 solo LEE: una llamada GET a la API)
Los valores no secretos (URL del motor, de Supabase y del panel, correo de dirección, modelo) se editan en el nodo
"Configuración" de cada flujo: n8n 2.x bloquea $env en los nodos por defecto y n8n Cloud no admite variables propias.
"""
import json, os, uuid

AQUI = os.path.dirname(os.path.abspath(__file__))
COD = lambda n: open(os.path.join(AQUI, "codigo", n), encoding="utf-8").read()
CFG = "$('Configuración').first().json"
SB = "={{ " + CFG + ".supabase_url }}/rest/v1"
CRED = {"gh": {"githubApi": {"id": "github", "name": "GitHub account"}},
        "ia": {"httpHeaderAuth": {"id": "anthropic", "name": "Anthropic API"}},
        "sb": {"supabaseApi": {"id": "supabase", "name": "Supabase account"}},
        "wh": {"httpHeaderAuth": {"id": "webhook", "name": "Webhook Supabase"}},
        "gmail": {"gmailOAuth2": {"id": "gmail", "name": "Gmail account"}},
        "gs": {"googleSheetsOAuth2Api": {"id": "gsheets", "name": "Google Sheets Meridiano"}}}
SISTEMA_IA = ("Preparas materiales para un comercial de Meridiano, medio para el público senior que vive de anunciantes. "
              "Reglas: usa solo cifras del contexto, tal cual; nunca menciones que el cliente está en riesgo; "
              "no incluyas ninguna condición económica ni porcentaje; tono profesional y cercano, de usted; máximo 200 palabras. "
              "Devuelve solo el texto del material.")


def nodo(nombre, tipo, version, pos, params, cred=None, **extra):
    n = {"id": str(uuid.uuid5(uuid.NAMESPACE_DNS, nombre)), "name": nombre, "type": tipo, "typeVersion": version,
         "position": pos, "parameters": params}
    if cred: n["credentials"] = CRED[cred]
    n.update(extra); return n


def code(nombre, pos, archivo, modo="runOnceForAllItems"):
    return nodo(nombre, "n8n-nodes-base.code", 2, pos, {"mode": modo, "language": "javaScript", "jsCode": COD(archivo)})


def http(nombre, pos, metodo, url, cred, cuerpo=None, cabeceras=None, opciones=None, completa=False, **extra):
    """completa=True: devuelve {statusCode, body} sin fallar con 4xx/5xx (el nodo Code siguiente decide)."""
    p = {"method": metodo, "url": url, "options": opciones or {}}
    if cred == "sb":                     # credencial nativa «Supabase API» de n8n (Host + Secret Key): probada en n8n Cloud
        p.update({"authentication": "predefinedCredentialType", "nodeCredentialType": "supabaseApi"})
    elif cred == "gh":                   # credencial nativa «GitHub API» (Access Token): n8n pone la cabecera y la prueba
        p.update({"authentication": "predefinedCredentialType", "nodeCredentialType": "githubApi"})
    elif cred:
        p.update({"authentication": "genericCredentialType", "genericAuthType": list(CRED[cred])[0]})
    else:
        p["authentication"] = "none"
    if completa:
        p["options"]["response"] = {"response": {"fullResponse": True, "neverError": True}}
        extra.setdefault("onError", "continueRegularOutput"); extra.setdefault("alwaysOutputData", True)
    if cabeceras:
        p["sendHeaders"] = True; p["headerParameters"] = {"parameters": [{"name": k, "value": v} for k, v in cabeceras.items()]}
    if cuerpo:
        p["sendBody"] = True; p["specifyBody"] = "json"; p["jsonBody"] = cuerpo
    return nodo(nombre, "n8n-nodes-base.httpRequest", 4.2, pos, p, cred, **extra)


def leer_hoja(nombre, pos, pestanas):
    """Lee TODAS las pestañas con una llamada de solo lectura (GET values:batchGet): no puede crear ni modificar documentos."""
    rangos = "&".join(f"ranges={t}" for t in pestanas)
    return nodo(nombre, "n8n-nodes-base.httpRequest", 4.2, pos,
                {"method": "GET",
                 "url": "=https://sheets.googleapis.com/v4/spreadsheets/{{ " + CFG + ".hoja_datos_id }}/values:batchGet?" + rangos
                        + "&valueRenderOption=UNFORMATTED_VALUE&dateTimeRenderOption=FORMATTED_STRING",
                 "authentication": "predefinedCredentialType", "nodeCredentialType": "googleSheetsOAuth2Api",
                 "options": {"timeout": 120000}},
                "gs", retryOnFail=True, maxTries=3, waitBetweenTries=5000, onError="continueErrorOutput")


def responder(nombre, pos):
    return nodo(nombre, "n8n-nodes-base.respondToWebhook", 1.1, pos,
                {"respondWith": "json", "responseBody": "={{ JSON.stringify($json.respuesta) }}",
                 "options": {"responseCode": "={{ $json.status }}"}})


def _interior(expr):
    """'={{ x }}' -> 'x'; un texto fijo -> su literal JavaScript."""
    if expr.startswith("={{") and expr.endswith("}}") and expr.count("{{") == 1:
        return expr[3:-2].strip()
    return json.dumps(expr.lstrip("="), ensure_ascii=False)


def correo(nombre, pos, para, asunto, texto, html=False):
    """Todo correo pasa por el MODO DEMO: con modo_demo activo (por defecto) va al buzón de pruebas y el asunto indica
    a quién habría ido. Así ningún correo del caso ficticio sale a direcciones de terceros."""
    destino, tema = _interior(para), _interior(asunto)
    return nodo(nombre, "n8n-nodes-base.gmail", 2.1, pos,
                {"resource": "message", "operation": "send",
                 "sendTo": "={{ " + CFG + ".modo_demo ? " + CFG + ".buzon_demo : (" + destino + ") }}",
                 "subject": "={{ (" + CFG + ".modo_demo ? '[DEMO → ' + (" + destino + ") + '] ' : '') + (" + tema + ") }}",
                 "emailType": "html" if html else "text", "message": texto,
                 "options": {"appendAttribution": False, "senderName": "Meridiano · Plan comercial"}}, "gmail")


def flujo(nombre, nodos, conexiones):
    con = {}
    for origen, destino, *salida in conexiones:
        s = salida[0] if salida else 0
        main = con.setdefault(origen, {"main": []})["main"]
        while len(main) <= s: main.append([])
        main[s].append({"node": destino, "type": "main", "index": 0})
    return {"name": nombre, "nodes": nodos, "connections": con, "active": False,
            "settings": {"executionOrder": "v1", "timezone": "Europe/Madrid"}, "pinData": {},
            "meta": {"templateCredsSetupCompleted": False}, "tags": []}


# ------------------------------------------------------------------ W0 · carga semanal de las tablas (Google Sheets → Supabase)
TABLAS = ["dim_comercial", "dim_productos", "dim_clientes", "fact_campanas", "fact_facturacion", "fact_interacciones", "oportunidades",
          "contactos"]
w0_nodos = [nodo("Lunes 21:00", "n8n-nodes-base.scheduleTrigger", 1.2, [0, 0],
                 {"rule": {"interval": [{"field": "weeks", "weeksInterval": 1, "triggerAtDay": [1], "triggerAtHour": 21}]}}),
            nodo("Cargar ahora", "n8n-nodes-base.manualTrigger", 1, [0, 200], {}),
            code("Configuración", [180, 100], "configuracion.js")]
w0_nodos += [leer_hoja("Google Sheets: leer pestañas", [360, 100], TABLAS)]
X = 600
w0_nodos += [
    code("Preparar tablas", [X, 100], "w0_preparar_tablas.js"),
    code("Solo cargables", [X + 180, 0], "w0_solo_cargables.js"),
    http("Supabase: cargar lote", [X + 360, 0], "POST", SB + "/{{ $json.tabla }}?on_conflict={{ $json.pk }}", "sb",
         cabeceras={"Prefer": "resolution=merge-duplicates,return=minimal"}, cuerpo="={{ JSON.stringify($json.filas) }}",
         opciones={"timeout": 120000, "batching": {"batch": {"batchSize": 1, "batchInterval": 200}}}, completa=True),
    code("Resumen de la carga", [X + 540, 0], "w0_resumen.js"),
    http("Supabase: registrar carga", [X + 720, -100], "POST", SB + "/ejecuciones", "sb", cabeceras={"Prefer": "return=minimal"},
         cuerpo="={{ JSON.stringify($json.registro) }}"),
    code("Solo avisos", [X + 720, 100], "w0_solo_avisos.js"),
    correo("Aviso al responsable de datos", [X + 900, 100], "={{ " + CFG + ".correo_datos }}", "={{ $json.asunto }}", "={{ $json.texto }}"),
    code("Solo carga detenida", [X + 180, 250], "w0_solo_abortada.js"),
    code("Lectura fallida", [X, 400], "w0_lectura_fallida.js"),
    http("Supabase: registrar carga detenida", [X + 360, 250], "POST", SB + "/ejecuciones", "sb", cabeceras={"Prefer": "return=minimal"},
         cuerpo="={{ JSON.stringify($json.registro) }}"),
    correo("Aviso: carga detenida", [X + 360, 400], "={{ " + CFG + ".correo_datos }}", "={{ $json.asunto }}", "={{ $json.texto }}"),
]
w0_con = [("Lunes 21:00", "Configuración"), ("Cargar ahora", "Configuración"), ("Configuración", "Google Sheets: leer pestañas"),
          ("Google Sheets: leer pestañas", "Lectura fallida", 1)]
w0_con += [("Google Sheets: leer pestañas", "Preparar tablas"), ("Preparar tablas", "Solo cargables"), ("Preparar tablas", "Solo carga detenida"),
           ("Solo cargables", "Supabase: cargar lote"), ("Supabase: cargar lote", "Resumen de la carga"),
           ("Resumen de la carga", "Supabase: registrar carga"), ("Resumen de la carga", "Solo avisos"),
           ("Solo avisos", "Aviso al responsable de datos"),
           ("Solo carga detenida", "Supabase: registrar carga detenida"), ("Solo carga detenida", "Aviso: carga detenida"),
           ("Lectura fallida", "Supabase: registrar carga detenida"), ("Lectura fallida", "Aviso: carga detenida")]
w0 = flujo("Meridiano · W0 Carga semanal de datos (Google Sheets → Supabase)", w0_nodos, w0_con)

# ------------------------------------------------------------------ W1 · ciclo semanal (martes)
w1 = flujo("Meridiano · W1 Ciclo semanal de retención (martes)", [
    nodo("Martes 7:00", "n8n-nodes-base.scheduleTrigger", 1.2, [0, 0],
         {"rule": {"interval": [{"field": "weeks", "weeksInterval": 1, "triggerAtDay": [2], "triggerAtHour": 7}]}}),
    nodo("Ejecutar a mano", "n8n-nodes-base.manualTrigger", 1, [0, 200], {}),
    code("Configuración", [180, 100], "configuracion.js"),
    code("Fecha de corte", [360, 100], "w1_fecha_corte.js"),
    http("GitHub: lanzar motor", [540, 100], "POST",
         "=https://api.github.com/repos/{{ " + CFG + ".github_repo }}/actions/workflows/motor.yml/dispatches", "gh",
         cabeceras={"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"},
         cuerpo="={{ JSON.stringify({ ref: " + CFG + ".github_rama, inputs: { fecha_corte: $json.fecha_corte, resume_url: $execution.resumeUrl } }) }}",
         opciones={"timeout": 60000}, onError="continueErrorOutput", retryOnFail=True, maxTries=3, waitBetweenTries=10000),
    nodo("Esperar al motor", "n8n-nodes-base.wait", 1.1, [720, 100],
         {"resume": "webhook", "httpMethod": "POST", "responseMode": "onReceived", "limitWaitTime": True,
          "limitType": "afterTimeInterval", "resumeAmount": 30, "resumeUnit": "minutes", "options": {}},
         webhookId=str(uuid.uuid5(uuid.NAMESPACE_DNS, "w1-esperar-motor"))),
    code("Resultado del motor", [900, 100], "w1_resultado_motor.js"),
    code("Solo si falla el motor", [1080, 250], "w1_fallo_motor.js"),
    code("Separar propuestas", [1080, 0], "w1_separar_propuestas.js"),
    http("Claude: redactar material", [880, 0], "POST", "https://api.anthropic.com/v1/messages", "ia",
         cabeceras={"anthropic-version": "2023-06-01"},
         cuerpo="={{ JSON.stringify({ model: " + CFG + ".modelo_ia, max_tokens: 600, system: "
                + json.dumps(SISTEMA_IA, ensure_ascii=False) + ", messages: [{ role: 'user', content: $json.contexto_ia }] }) }}",
         opciones={"timeout": 60000, "batching": {"batch": {"batchSize": 1, "batchInterval": 1500}}},
         retryOnFail=True, maxTries=3, waitBetweenTries=5000, onError="continueRegularOutput"),
    code("Validador (sensor Govern)", [1100, 0], "w1_validador.js"),
    http("Supabase: guardar material", [1320, -100], "PATCH",
         SB + "/propuestas?fecha_corte=eq.{{ $json.fecha_corte }}&id_cliente=eq.{{ $json.id_cliente }}", "sb",
         cabeceras={"Prefer": "return=minimal"},
         cuerpo="={{ JSON.stringify({ material_cuerpo: $json.material_cuerpo, fuente_material: $json.fuente_material }) }}"),
    code("Resumen por comercial", [1540, -100], "w1_resumen_comercial.js"),
    correo("Aviso al comercial", [1760, -100], "={{ $json.correo }}", "={{ $json.asunto }}", "={{ $json.texto }}"),
    code("Resumen de la ejecución", [1320, 100], "w1_resumen_ejecucion.js"),
    http("Supabase: registrar ejecución", [1540, 100], "POST", SB + "/ejecuciones", "sb",
         cabeceras={"Prefer": "return=minimal"}, cuerpo="={{ JSON.stringify($json) }}"),
    correo("Aviso a dirección: fallo del motor", [1260, 250], "={{ " + CFG + ".correo_direccion }}",
           "Meridiano · el ciclo semanal de retención ha fallado",
           "=El motor no ha completado el ciclo con fecha de corte {{ $('Fecha de corte').first().json.fecha_corte }}.\n\n"
           "Detalle: {{ String($json.error || '').slice(0, 1500) }}\n{{ $json.ejecucion_github ? 'Ejecución en GitHub: ' + $json.ejecucion_github : '' }}\n\nNo se ha publicado ningún plan nuevo en el panel."),
], [("Martes 7:00", "Configuración"), ("Ejecutar a mano", "Configuración"), ("Configuración", "Fecha de corte"),
    ("Fecha de corte", "GitHub: lanzar motor"),
    ("GitHub: lanzar motor", "Esperar al motor", 0), ("GitHub: lanzar motor", "Solo si falla el motor", 1),
    ("Esperar al motor", "Resultado del motor"),
    ("Resultado del motor", "Separar propuestas"), ("Resultado del motor", "Solo si falla el motor"),
    ("Solo si falla el motor", "Aviso a dirección: fallo del motor"),
    ("Separar propuestas", "Claude: redactar material"), ("Claude: redactar material", "Validador (sensor Govern)"),
    ("Validador (sensor Govern)", "Supabase: guardar material"), ("Validador (sensor Govern)", "Resumen de la ejecución"),
    ("Supabase: guardar material", "Resumen por comercial"), ("Resumen por comercial", "Aviso al comercial"),
    ("Resumen de la ejecución", "Supabase: registrar ejecución")])

# ------------------------------------------------------------------ W2 · alertas de cierre (Supabase → n8n)
w2 = flujo("Meridiano · W2 Alertas de cierre", [
    nodo("Evento registrado en Supabase", "n8n-nodes-base.webhook", 2, [0, 0],
         {"httpMethod": "POST", "path": "meridiano-evento", "authentication": "headerAuth", "responseMode": "onReceived",
          "options": {}}, "wh", webhookId=str(uuid.uuid5(uuid.NAMESPACE_DNS, "w2-evento-supabase"))),
    code("Configuración", [180, 0], "configuracion.js"),
    code("Solo cierres", [360, 0], "w2_solo_cierres.js"),
    http("Supabase: propuesta cerrada", [540, 0], "GET",
         SB + "/propuestas?id=eq.{{ $json.propuesta_id }}&select=id,id_cliente,razon_social,fecha_corte,cuenta_clave,requiere_direccion,"
              "estado_confirmado_comercial,motivo_confirmado,diagnostico_correcto,comentario_comercial,facturacion_en_riesgo",
         "sb", completa=True),
    code("Alertas de cierre", [720, 0], "w2_alertas.js"),
    correo("Alerta a dirección", [900, 0], "={{ " + CFG + ".correo_direccion }}", "={{ $json.asunto }}", "={{ $json.texto }}"),
], [("Evento registrado en Supabase", "Configuración"), ("Configuración", "Solo cierres"), ("Solo cierres", "Supabase: propuesta cerrada"),
    ("Supabase: propuesta cerrada", "Alertas de cierre"), ("Alertas de cierre", "Alerta a dirección")])

# ------------------------------------------------------------------ W5 · envío al aceptar (Lovable → Supabase → n8n → Gmail → Supabase)
w5 = flujo("Meridiano · W5 Envío al aceptar", [
    nodo("Propuesta aceptada en el panel", "n8n-nodes-base.webhook", 2, [0, 0],
         {"httpMethod": "POST", "path": "meridiano-envio", "authentication": "headerAuth", "responseMode": "onReceived",
          "options": {}}, "wh", webhookId=str(uuid.uuid5(uuid.NAMESPACE_DNS, "w5-envio"))),
    nodo("Reintentar envíos pendientes", "n8n-nodes-base.manualTrigger", 1, [0, 220], {}),
    code("Configuración", [200, 110], "configuracion.js"),
    code("Qué enviar", [400, 110], "w5_que_enviar.js"),
    http("Supabase: envíos pendientes", [600, 110], "GET", SB + "/envios_pendientes?select=*{{ $json.filtro }}", "sb"),
    code("Preparar correo", [800, 110], "w5_preparar_correo.js"),
    http("Supabase: reservar envíos", [1000, 40], "POST", SB + "/rpc/reservar_envios", "sb",
         cuerpo="={{ JSON.stringify({ p_ids: $('Preparar correo').all().filter(i => !i.json.bloqueo).map(i => i.json.id) }) }}",
         executeOnce=True),
    code("Solo reservados", [1200, 40], "w5_solo_reservados.js"),
    dict(correo("Enviar al contacto", [1400, 40], "={{ $json.para }}", "={{ $json.asunto }}", "={{ $json.html }}", html=True),
         onError="continueRegularOutput"),
    code("Resultado del envío", [1600, 40], "w5_resultado_envio.js"),
    http("Supabase: registrar envío", [1800, 40], "POST", SB + "/rpc/registrar_accion", "sb",
         cuerpo="={{ JSON.stringify($json) }}", completa=True),
    code("Bloqueados", [1000, 220], "w5_bloqueados.js"),
    http("Supabase: registrar bloqueo", [1200, 220], "POST", SB + "/rpc/registrar_accion", "sb",
         cuerpo="={{ JSON.stringify($json) }}", completa=True),
], [("Propuesta aceptada en el panel", "Configuración"), ("Reintentar envíos pendientes", "Configuración"),
    ("Configuración", "Qué enviar"), ("Qué enviar", "Supabase: envíos pendientes"),
    ("Supabase: envíos pendientes", "Preparar correo"), ("Preparar correo", "Supabase: reservar envíos"),
    ("Supabase: reservar envíos", "Solo reservados"), ("Solo reservados", "Enviar al contacto"),
    ("Enviar al contacto", "Resultado del envío"), ("Resultado del envío", "Supabase: registrar envío"),
    ("Preparar correo", "Bloqueados"), ("Bloqueados", "Supabase: registrar bloqueo")])

# ------------------------------------------------------------------ W3 · recordatorio semanal
w3 = flujo("Meridiano · W3 Recordatorio semanal", [
    nodo("Lunes 8:00", "n8n-nodes-base.scheduleTrigger", 1.2, [0, 0],
         {"rule": {"interval": [{"field": "weeks", "weeksInterval": 1, "triggerAtDay": [1], "triggerAtHour": 8}]}}),
    code("Configuración", [180, 0], "configuracion.js"),
    http("Supabase: comerciales", [360, 0], "GET", SB + "/dim_comercial?select=id_comercial,nombre,correo", "sb"),
    http("Supabase: tareas sin cerrar", [440, 0], "GET",
         SB + "/plan_vigente?estado_tarea=neq.cerrada&select=id_cliente,razon_social,comercial_asignado,accion_id,fecha_limite,estado_tarea&order=fecha_limite",
         "sb", executeOnce=True, alwaysOutputData=True),
    code("Agrupar por comercial", [660, 0], "w3_agrupar.js"),
    correo("Recordatorio al comercial", [880, 0], "={{ $json.correo }}", "={{ $json.asunto }}", "={{ $json.texto }}"),
], [("Lunes 8:00", "Configuración"), ("Configuración", "Supabase: comerciales"), ("Supabase: comerciales", "Supabase: tareas sin cerrar"),
    ("Supabase: tareas sin cerrar", "Agrupar por comercial"), ("Agrupar por comercial", "Recordatorio al comercial")])

# ------------------------------------------------------------------ W7 · auditor (pasos 05 y 08 de FORGEN)
GH_CONTENIDO = ("=https://api.github.com/repos/{{ $('Parámetros de la auditoría').first().json.repo }}/contents/"
                "{{ $('Parámetros de la auditoría').first().json.%s }}?ref={{ $('Parámetros de la auditoría').first().json.rama }}")
w7 = flujo("Meridiano · W7 Auditor (pasos 05 y 08 FORGEN)", [
    nodo("Lanzar auditoría", "n8n-nodes-base.manualTrigger", 1, [0, 100], {}),
    code("Configuración", [180, 100], "configuracion.js"),
    code("Parámetros de la auditoría", [360, 100], "w7_parametros.js"),
    http("GitHub: leer paquete", [540, 100], "GET", GH_CONTENIDO % "paquete", "gh", completa=True),
    http("GitHub: leer rúbrica", [720, 100], "GET", GH_CONTENIDO % "rubrica", "gh", completa=True),
    code("Preparar la petición", [900, 100], "w7_preparar.js"),
    http("Claude: modelo auditor", [1080, 100], "POST", "https://api.anthropic.com/v1/messages", "ia",
         cabeceras={"anthropic-version": "2023-06-01"},
         cuerpo="={{ JSON.stringify({ model: $json.modelo, max_tokens: 32000, system: $json.sistema, "
                "messages: [{ role: 'user', content: $json.paquete }] }) }}",
         opciones={"timeout": 600000}, completa=True, retryOnFail=True, maxTries=2, waitBetweenTries=10000),
    code("Validar respuesta del auditor", [1260, 100], "w7_validar.js"),
    http("Supabase: guardar auditoría", [1440, 0], "POST", SB + "/auditorias", "sb",
         cabeceras={"Prefer": "return=minimal"}, cuerpo="={{ JSON.stringify($json) }}"),
    code("Redactar resumen", [1440, 200], "w7_correo.js"),
    correo("Resumen de la auditoría", [1620, 200], "={{ " + CFG + ".correo_direccion }}", "={{ $json.asunto }}", "={{ $json.texto }}"),
], [("Lanzar auditoría", "Configuración"), ("Configuración", "Parámetros de la auditoría"),
    ("Parámetros de la auditoría", "GitHub: leer paquete"), ("GitHub: leer paquete", "GitHub: leer rúbrica"),
    ("GitHub: leer rúbrica", "Preparar la petición"), ("Preparar la petición", "Claude: modelo auditor"),
    ("Claude: modelo auditor", "Validar respuesta del auditor"),
    ("Validar respuesta del auditor", "Supabase: guardar auditoría"), ("Validar respuesta del auditor", "Redactar resumen"),
    ("Redactar resumen", "Resumen de la auditoría")])


# ------------------------------------------------------------------ W8 · baja de comunicaciones comerciales (H2)
def pagina_html(nombre, pos):
    return nodo(nombre, "n8n-nodes-base.respondToWebhook", 1.1, pos,
                {"respondWith": "text", "responseBody": "={{ $json.html }}",
                 "options": {"responseHeaders": {"entries": [{"name": "Content-Type", "value": "text/html; charset=utf-8"},
                                                             {"name": "Cache-Control", "value": "no-store"}]}}})


w8 = flujo("Meridiano · W8 Baja de comunicaciones", [
    nodo("Enlace de baja (abrir)", "n8n-nodes-base.webhook", 2, [0, 0],
         {"httpMethod": "GET", "path": "meridiano-baja", "responseMode": "responseNode", "options": {}},
         webhookId=str(uuid.uuid5(uuid.NAMESPACE_DNS, "w8-baja-get"))),
    code("Página de confirmación", [240, 0], "w8_pagina.js"),
    pagina_html("Mostrar confirmación", [480, 0]),
    nodo("Enlace de baja (confirmar)", "n8n-nodes-base.webhook", 2, [0, 240],
         {"httpMethod": "POST", "path": "meridiano-baja", "responseMode": "responseNode", "options": {}},
         webhookId=str(uuid.uuid5(uuid.NAMESPACE_DNS, "w8-baja-post"))),
    code("Configuración", [200, 240], "configuracion.js"),
    code("Token de la baja", [400, 240], "w8_token.js"),
    http("Supabase: registrar baja", [600, 240], "POST", SB + "/rpc/registrar_baja", "sb",
         cuerpo="={{ JSON.stringify($json) }}", completa=True),
    code("Página de resultado", [800, 240], "w8_pagina.js"),
    pagina_html("Mostrar resultado", [1000, 240]),
], [("Enlace de baja (abrir)", "Página de confirmación"), ("Página de confirmación", "Mostrar confirmación"),
    ("Enlace de baja (confirmar)", "Configuración"), ("Configuración", "Token de la baja"),
    ("Token de la baja", "Supabase: registrar baja"), ("Supabase: registrar baja", "Página de resultado"),
    ("Página de resultado", "Mostrar resultado")])

if __name__ == "__main__":
    for nombre, w in [("W0_carga_semanal", w0), ("W1_ciclo_semanal", w1), ("W2_alertas_cierre", w2), ("W5_envio_al_aceptar", w5), ("W3_recordatorio_semanal", w3), ("W7_auditor", w7), ("W8_baja", w8)]:
        json.dump(w, open(os.path.join(AQUI, nombre + ".json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        print(nombre, len(w["nodes"]), "nodos")
