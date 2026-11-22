"""Flujos de n8n: estructura importable y lógica de los nodos Code ejecutada con node."""
import json, os, subprocess, tempfile, shutil
import pytest
RAIZ = os.path.join(os.path.dirname(__file__), ".."); N8N = os.path.join(RAIZ, "n8n")
FLUJOS = ["W0_carga_semanal", "W1_ciclo_semanal", "W2_alertas_cierre", "W3_recordatorio_semanal", "W5_envio_al_aceptar", "W7_auditor", "W8_baja"]
pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="requiere node")


def correr(archivo, datos):
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f: json.dump(datos, f)
    r = subprocess.run(["node", os.path.join(RAIZ, "tests", "n8n_harness.js"), os.path.join(N8N, "codigo", archivo), f.name],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


@pytest.mark.parametrize("nombre", FLUJOS)
def test_flujo_importable(nombre):
    w = json.load(open(os.path.join(N8N, nombre + ".json"), encoding="utf-8"))
    nombres = {n["name"] for n in w["nodes"]}
    assert len(nombres) == len(w["nodes"])
    for n in w["nodes"]:
        assert n["type"].startswith("n8n-nodes-base.") and n["typeVersion"] and len(n["position"]) == 2
    for origen, c in w["connections"].items():
        assert origen in nombres
        for salida in c["main"]:
            for dest in salida: assert dest["node"] in nombres
    # Ningún secreto en el JSON: las claves van en credenciales de n8n
    texto = json.dumps(w, ensure_ascii=False)
    assert "sk-ant" not in texto and "service_role" not in texto.replace("Supabase Meridiano", "")
    # Todo correo pasa por el modo demo
    for n in w["nodes"]:
        assert n["type"] != "n8n-nodes-base.emailSend"                 # los correos salen por Gmail, no por SMTP
        if n["type"] == "n8n-nodes-base.gmail":
            assert ".modo_demo ?" in n["parameters"]["sendTo"] and ".buzon_demo" in n["parameters"]["sendTo"]
            assert "[DEMO → " in n["parameters"]["subject"] and n["parameters"]["operation"] == "send"
    # Sin $env: n8n 2.x lo bloquea por defecto y n8n Cloud no lo admite
    assert "$env" not in texto and "Configuración" in nombres
    # Los nombres usados con $('...') existen en el flujo
    import re
    for ref in re.findall(r"\$\('([^']+)'\)", texto): assert ref in nombres, ref


PROP = {"fecha_corte": "2026-09-30", "id_cliente": "CLI-1", "razon_social": "Ortopedia Sol", "comercial_asignado": "COM-01",
        "comercial_nombre": "Martina Rodriguez", "correo_comercial": "m@x.com", "material_cuerpo": "PLANTILLA",
        "contexto_ia": "Anunciante: Ortopedia Sol. Datos: 3 campañas; CTR 0,8; última campaña hace 145 días"}


def ia(texto): return {"content": [{"type": "text", "text": texto}]}


def test_validador_acepta_texto_trazable():
    r = correr("w1_validador.js", {"input": [ia("Estimado cliente: tras sus 3 campañas con un CTR de 0,8 le proponemos revisar resultados.")],
                                    "nodos": {"Separar propuestas": [PROP]}})[0]
    assert r["valido"] and r["fuente_material"] == "llm" and r["material_cuerpo"].startswith("Estimado")


@pytest.mark.parametrize("texto,motivo", [
    ("Tras sus 5 campañas le proponemos una reunión.", "cifras no trazables [5]"),
    ("Le ofrecemos un descuento especial en su próxima campaña.", "condición económica"),
    ("Hemos detectado un riesgo en su cuenta.", "insinúa el riesgo"),
    ("palabra " * 201, "201 palabras"),
])
def test_validador_descarta_y_conserva_plantilla(texto, motivo):
    r = correr("w1_validador.js", {"input": [ia(texto)], "nodos": {"Separar propuestas": [PROP]}})[0]
    assert not r["valido"] and r["material_cuerpo"] == "PLANTILLA" and motivo in r["fuente_material"]


def test_validador_sin_respuesta_de_ia():
    r = correr("w1_validador.js", {"input": [{"error": {"message": "timeout"}}], "nodos": {"Separar propuestas": [PROP]}})[0]
    assert not r["valido"] and "IA no disponible" in r["fuente_material"]


def test_resumen_un_correo_por_comercial():
    filas = [dict(PROP, id_cliente=f"C{i}", comercial_asignado=c, correo_comercial=c + "@x", valido=True)
             for i, c in enumerate(["COM-01", "COM-01", "COM-02"])]
    r = correr("w1_resumen_comercial.js", {"input": [], "nodos": {"Validador (sensor Govern)": filas, "Configuración": [{"panel_url": "https://panel"}]}})
    assert sorted(x["propuestas"] for x in r) == [1, 2] and "https://panel" in r[0]["texto"] and "2026-09" in r[0]["asunto"]


def test_w2_alerta_solo_en_cierres_que_lo_requieren():
    ev = lambda acc, pid: {"body": {"type": "INSERT", "table": "eventos_propuesta",
                                    "record": {"propuesta_id": pid, "accion": acc, "usuario": "m@x", "creado_en": "2026-09-29"}}}
    cierres = correr("w2_solo_cierres.js", {"nodos": {"Evento registrado en Supabase": [ev("cerrar", 7), ev("guardar_material", 7), ev("cerrar", 8)]}})
    assert [c["propuesta_id"] for c in cierres] == [7, 8]
    base = dict(PROP, estado_confirmado_comercial="Perdido", motivo_confirmado="presupuesto_inversion", diagnostico_correcto="Sí",
                requiere_direccion=False, facturacion_en_riesgo=9000)
    props = [{"statusCode": 200, "body": [dict(base, cuenta_clave=True)]}, {"statusCode": 200, "body": [dict(base, cuenta_clave=False)]}]
    al = correr("w2_alertas.js", {"input": props, "nodos": {"Solo cierres": cierres}})
    assert len(al) == 1 and "cuenta clave perdida" in al[0]["asunto"] and "m@x" in al[0]["texto"]


def test_w3_agrupa_pendientes():
    com = [{"id_comercial": "COM-01", "nombre": "Martina R", "correo": "m@x"}, {"id_comercial": "COM-02", "nombre": "Juan P", "correo": "j@x"}]
    tareas = [{"id_cliente": "C1", "razon_social": "A", "comercial_asignado": "COM-01", "fecha_limite": "2000-01-01"},
              {"id_cliente": "C2", "razon_social": "B", "comercial_asignado": "COM-01", "fecha_limite": "2999-01-01"}]
    r = correr("w3_agrupar.js", {"input": tareas, "nodos": {"Supabase: comerciales": com, "Configuración": [{"panel_url": "https://panel"}]}})
    assert len(r) == 1 and r[0]["pendientes"] == 2 and r[0]["urgentes"] == 1 and "(vencida)" in r[0]["texto"]


def test_contrato_motor_n8n():
    """Lo que devuelve el motor es lo que espera 'Separar propuestas'."""
    r = correr("w1_separar_propuestas.js", {"input": [{"ok": True, "fecha_corte": "2026-09-30", "etiqueta_vigente": "E2",
                                                       "detalle_propuestas": [PROP, dict(PROP, id_cliente="CLI-2")]}]})
    assert len(r) == 2 and r[0]["contexto_ia"] and r[0]["etiqueta_vigente"] == "E2"


def test_resultado_del_motor_de_github():
    """Lo que devuelve la acción de GitHub al webhook de espera de n8n, o nada si se agotó el tiempo."""
    bien = {"ok": True, "fecha_corte": "2026-09-28", "etiqueta_vigente": "E2", "detalle_propuestas": [PROP]}
    r = correr("w1_resultado_motor.js", {"input": [{"headers": {}, "body": bien}]})[0]
    assert r["ok"] and len(correr("w1_separar_propuestas.js", {"input": [r]})) == 1 and correr("w1_fallo_motor.js", {"input": [r]}) == []
    mal = correr("w1_resultado_motor.js", {"input": [{"body": {"ok": False, "error": "RuntimeError: x", "ejecucion_github": "https://github.com/a/b/actions/runs/1"}}]})[0]
    assert correr("w1_separar_propuestas.js", {"input": [mal]}) == []
    f = correr("w1_fallo_motor.js", {"input": [mal]})[0]
    assert f["error"] == "RuntimeError: x" and f["ejecucion_github"].endswith("/runs/1")
    nada = correr("w1_resultado_motor.js", {"input": [{}]})[0]                       # tiempo de espera agotado
    assert not nada["ok"] and "30 minutos" in nada["error"]


def test_w5_que_enviar_solo_la_aceptacion_del_evento():
    ev = lambda acc, pid: {"body": {"type": "INSERT", "table": "eventos_propuesta", "record": {"propuesta_id": pid, "accion": acc}}}
    r = correr("w5_que_enviar.js", {"nodos": {"Propuesta aceptada en el panel": [ev("aprobar", 7)]}})
    assert r == [{"filtro": "&id=eq.7"}]
    assert correr("w5_que_enviar.js", {"nodos": {"Propuesta aceptada en el panel": [ev("guardar_material", 7)]}}) == []
    assert correr("w5_que_enviar.js", {"nodos": {}}) == [{"filtro": ""}]                     # lanzamiento a mano: todas


PEND = {"id": 7, "razon_social": "Ortopedia Sol", "asunto_email": None, "material_titulo": "Informe de resultados",
        "texto_aprobado": "Estimada Laura: …", "contacto_nombre": "Laura Martín", "contacto_email": "laura@ortopedia-sol.example",
        "contacto_ficticio": True, "comercial_nombre": "Martina Rodriguez"}


TOKEN = "3f2b1c4d-5e6f-4a7b-8c9d-0e1f2a3b4c5d"
CFG_W5 = {"modo_demo": True, "baja_url": "http://localhost:5678/webhook/meridiano-baja"}


def test_w5_correo_con_texto_aprobado_y_bloqueo_fuera_de_demo():
    p = dict(PEND, token_baja=TOKEN, contacto_excluido=False)
    r = correr("w5_preparar_correo.js", {"input": [p], "nodos": {"Configuración": [CFG_W5]}})[0]
    assert r["bloqueo"] is None and r["asunto"] == "Informe de resultados" and "Estimada Laura" in r["texto"]
    assert "Correo de demostración" in r["texto"] and "laura@ortopedia-sol.example" in r["texto"] and "Martina Rodriguez" in r["texto"]
    r = correr("w5_preparar_correo.js", {"input": [p], "nodos": {"Configuración": [dict(CFG_W5, modo_demo=False)]}})[0]
    assert r["bloqueo"] and "ficticio" in r["bloqueo"]


def test_w5_correo_html_con_marca_y_enlace_de_baja():
    p = dict(PEND, token_baja=TOKEN, contacto_excluido=False, etiqueta="riesgo", comercial_correo="m@meridiano.com",
             texto_aprobado="Estimada Laura:\n\nLe resumo:\n\n- 3 campañas\n- CTR 0,8 <b>\n\nUn saludo")
    r = correr("w5_preparar_correo.js", {"input": [p], "nodos": {"Configuración": [CFG_W5]}})[0]
    h = r["html"]
    assert f"meridiano-baja?t={TOKEN}" in h and "darse de baja" in h and f"meridiano-baja?t={TOKEN}" in r["texto"]
    assert "#1B1712" in h and "#C0902F" in h and "Fraunces" in h and "MERID<em" in h     # identidad de marca
    assert "<li" in h and "&lt;b&gt;" in h and "<b>" not in h                              # listas y texto escapado
    assert "Correo de demostración" in h and "en riesgo" not in h.lower()


def test_w5_no_envia_a_excluidos_ni_sin_enlace_de_baja():
    p = dict(PEND, token_baja=TOKEN, contacto_excluido=True)
    r = correr("w5_preparar_correo.js", {"input": [p], "nodos": {"Configuración": [CFG_W5]}})[0]
    assert "baja" in r["bloqueo"]
    r = correr("w5_preparar_correo.js", {"input": [dict(p, contacto_excluido=False)], "nodos": {"Configuración": [{"modo_demo": True}]}})[0]
    assert "enlace de baja" in r["bloqueo"] and r["html"] is None


def test_w8_pagina_pide_confirmacion_y_muestra_resultado():
    r = correr("w8_pagina.js", {"nodos": {"Enlace de baja (abrir)": [{"query": {"t": TOKEN}}]}})[0]["html"]
    assert 'method="post"' in r and TOKEN in r and "Confirmar la baja" in r and "MERID<em>I</em>ANO" in r
    r = correr("w8_pagina.js", {"nodos": {"Enlace de baja (abrir)": [{"query": {"t": "<script>"}}]}})[0]["html"]
    assert "no válido" in r and "<script>" not in r
    ok = correr("w8_pagina.js", {"input": [{"statusCode": 200, "body": {"ok": True, "email": "la***@x.example"}}], "nodos": {}})[0]["html"]
    assert "Baja registrada" in ok and "la***@x.example" in ok
    ko = correr("w8_pagina.js", {"input": [{"statusCode": 200, "body": {"ok": False, "motivo": "enlace_no_valido"}}], "nodos": {}})[0]["html"]
    assert "No hemos podido" in ko


def test_w8_token_invalido_no_da_de_baja():
    assert correr("w8_token.js", {"nodos": {"Enlace de baja (confirmar)": [{"body": {"t": TOKEN}}]}}) == [{"p_token": TOKEN}]
    r = correr("w8_token.js", {"nodos": {"Enlace de baja (confirmar)": [{"body": {"t": "x' or 1=1"}}]}})
    assert r == [{"p_token": "00000000-0000-0000-0000-000000000000"}]


def test_w5_registra_envio_correcto_y_error():
    env = [dict(id=7), dict(id=8)]
    r = correr("w5_resultado_envio.js", {"input": [{"id": "msg-1", "threadId": "t1"}, {"error": {"message": "Quota exceeded"}}],
                                         "nodos": {"Solo reservados": env}})
    assert r[0]["p_datos"] == {"ok": True, "id_mensaje": "msg-1"} and r[0]["p_accion"] == "registrar_envio" and r[0]["p_usuario"] == "n8n"
    assert r[1]["p_datos"]["ok"] is False and "Quota" in r[1]["p_datos"]["error"] and len(r) == 2


def test_w5_bloqueados_en_rama_propia():
    prep = [dict(id=7, bloqueo=None), dict(id=9, bloqueo="Contacto ficticio: no se envía fuera del modo demo")]
    r = correr("w5_bloqueados.js", {"input": prep})
    assert r == [{"p_propuesta_id": 9, "p_accion": "registrar_envio", "p_usuario": "n8n",
                  "p_datos": {"ok": False, "error": "Contacto ficticio: no se envía fuera del modo demo"}}]
    assert correr("w5_bloqueados.js", {"input": [dict(id=7, bloqueo=None)]}) == []


def test_w5_solo_envia_lo_que_ha_reservado():
    prep = [dict(id=7, bloqueo=None), dict(id=8, bloqueo=None), dict(id=9, bloqueo="baja")]
    r = correr("w5_solo_reservados.js", {"input": [{"reservadas": [8, 9]}], "nodos": {"Preparar correo": prep}})
    assert [x["id"] for x in r] == [8]                     # 7 la reservó otra ejecución; 9 está bloqueada
    assert correr("w5_solo_reservados.js", {"input": [{"reservadas": []}], "nodos": {"Preparar correo": prep}}) == []


def test_w5_estructura_reserva_antes_de_gmail():
    w = json.load(open(os.path.join(RAIZ, "n8n", "W5_envio_al_aceptar.json")))
    sig = {k: [d["node"] for d in v["main"][0]] for k, v in w["connections"].items()}
    assert sig["Preparar correo"] == ["Supabase: reservar envíos", "Bloqueados"]
    assert sig["Supabase: reservar envíos"] == ["Solo reservados"] and sig["Solo reservados"] == ["Enviar al contacto"]
    n = {x["name"]: x for x in w["nodes"]}
    assert n["Supabase: reservar envíos"]["executeOnce"] is True and "reservar_envios" in n["Supabase: reservar envíos"]["parameters"]["url"]


# ------------------------------------------------------------------ W7 · auditor
import base64
def _gh(texto, sha="abc1234def"):
    return {"statusCode": 200, "body": {"content": base64.b64encode(texto.encode()).decode(), "sha": sha}}
RUBRICA = "# R\n\n## Mensaje de sistema\n\n" + "Eres un auditor. " * 20 + "\n\n## Uso manual\n\nNo enviar esto."
PAR = {"tipo": "prueba", "modelo": "claude-fable-5-1", "paquete": "auditoria/paquete_prueba.md", "rubrica": "auditoria/rubrica_diseno.md"}
PREP = {"tipo": "prueba", "modelo": "claude-fable-5-1", "paquete_ruta": "a.md", "paquete_sha": "s1", "rubrica_ruta": "r.md", "rubrica_sha": "s2"}
BUENO = {"veredicto": "rechazado", "resumen": "El envío no tiene aprobación humana.",
         "hallazgos": [{"id": "H1", "nodo": "N2", "criterio": "C5", "hallazgo": "Envía sin aprobación", "evidencia": "N2 · Dentro",
                        "severidad": "alta", "correccion_propuesta": "Añadir aprobación del comercial"},
                       {"id": "H2", "nodo": "N1", "criterio": "C3", "hallazgo": "Criterio no verificable", "evidencia": "N1 · Criterios",
                        "severidad": "media", "correccion_propuesta": "Definir criterios con sí o no"}],
         "puntos_fuertes": ["Proceso corto"]}


def test_w7_parametros_y_preparar():
    p = correr("w7_parametros.js", {"input": [{}], "nodos": {"Configuración": [{"github_repo": "u/meridiano-motor", "github_rama": "main"}]}})[0]
    assert p["paquete"] == "auditoria/paquete_prueba.md" and p["repo"] == "u/meridiano-motor" and p["modelo"] == "claude-fable-5-1"
    r = correr("w7_preparar.js", {"input": [{}], "nodos": {"Parámetros de la auditoría": [PAR],
                                  "GitHub: leer paquete": [_gh("# Paquete con ñ y acentos")], "GitHub: leer rúbrica": [_gh(RUBRICA, "r9")]}})[0]
    assert r["paquete"] == "# Paquete con ñ y acentos" and r["rubrica_sha"] == "r9"
    assert r["sistema"].startswith("Eres un auditor.") and "Uso manual" not in r["sistema"]


def test_w7_preparar_falla_si_github_no_encuentra_el_archivo():
    import tempfile as _t
    d = {"input": [{}], "nodos": {"Parámetros de la auditoría": [PAR],
         "GitHub: leer paquete": [{"statusCode": 404, "body": {"message": "Not Found"}}], "GitHub: leer rúbrica": [_gh(RUBRICA)]}}
    f = _t.NamedTemporaryFile("w", suffix=".json", delete=False); json.dump(d, f); f.close()
    r = subprocess.run(["node", os.path.join(RAIZ, "tests", "n8n_harness.js"), os.path.join(N8N, "codigo", "w7_preparar.js"), f.name],
                       capture_output=True, text=True)
    assert r.returncode != 0 and "auditoria/paquete_prueba.md" in r.stderr and "404" in r.stderr


def _validar(respuesta):
    return correr("w7_validar.js", {"input": [respuesta], "nodos": {"Preparar la petición": [PREP]}})[0]


def test_w7_validar_respuesta_correcta_con_vallas_de_codigo():
    texto = "```json\n" + json.dumps(BUENO, ensure_ascii=False) + "\n```"
    f = _validar({"statusCode": 200, "body": {"content": [{"type": "text", "text": texto}], "usage": {"input_tokens": 900, "output_tokens": 300}}})
    assert f["estado"] == "ok" and f["veredicto"] == "rechazado" and (f["n_altas"], f["n_medias"], f["n_bajas"]) == (1, 1, 0)
    assert f["tokens_entrada"] == 900 and f["avisos"] == [] and f["paquete_sha"] == "s1"


def test_w7_validar_formato_invalido_y_error():
    malo = dict(BUENO, veredicto="ok", hallazgos=[{"id": "H1", "severidad": "grave"}])
    f = _validar({"statusCode": 200, "body": {"content": [{"type": "text", "text": json.dumps(malo)}]}})
    assert f["estado"] == "formato_invalido" and "veredicto" in f["error"] and "faltan" in f["error"] and f["respuesta_bruta"]
    f = _validar({"statusCode": 200, "body": {"content": [{"type": "text", "text": "No puedo responder en JSON."}]}})
    assert f["estado"] == "formato_invalido" and "JSON" in f["error"]
    f = _validar({"statusCode": 404, "body": {"error": {"message": "model: claude-xyz not found"}}})
    assert f["estado"] == "error" and "not found" in f["error"] and f["veredicto"] is None


def test_w7_aviso_de_coherencia_y_correo():
    incoherente = dict(BUENO, veredicto="aprobado")
    f = _validar({"statusCode": 200, "body": {"content": [{"type": "text", "text": json.dumps(incoherente)}]}})
    assert f["estado"] == "ok" and f["avisos"]
    c = correr("w7_correo.js", {"input": [{}], "nodos": {"Validar respuesta del auditor": [f]}})[0]
    assert "aprobado (1 altas, 1 medias, 0 bajas)" in c["asunto"] and "[ALTA] H1" in c["texto"] and "AVISOS DE COHERENCIA" in c["texto"]
    e = _validar({"statusCode": 500, "body": {"error": {"message": "overloaded"}}})
    c = correr("w7_correo.js", {"input": [{}], "nodos": {"Validar respuesta del auditor": [e]}})[0]
    assert "no respondió" in c["asunto"] and "overloaded" in c["texto"]


def test_w7_respuesta_cortada_por_longitud():
    f = _validar({"statusCode": 200, "body": {"stop_reason": "max_tokens", "usage": {"output_tokens": 8000},
                  "content": [{"type": "thinking", "thinking": "..."}, {"type": "text", "text": "```json\n{\"veredicto\": \"apro"}]}})
    assert f["estado"] == "formato_invalido" and "cortada" in f["error"] and "8000" in f["error"]


# ------------------------------------------------------------------ H3 · validador · H7 · puerta de datos
def _validar_w1(texto):
    prop = {"fecha_corte": "2026-09-01", "id_cliente": "CLI-1", "contexto_ia": "3 campañas, CTR 0,8", "material_cuerpo": "plantilla"}
    return correr("w1_validador.js", {"input": [{"content": [{"type": "text", "text": texto}]}],
                                      "nodos": {"Separar propuestas": [prop]}})[0]


def test_validador_rechaza_insinuar_el_riesgo():
    assert _validar_w1("Estimada Laura: le resumo sus 3 campañas, con un CTR de 0,8. ¿Hablamos?")["valido"] is True
    for t in ["Hemos notado que ha reducido su actividad.", "No queremos perderle como cliente.",
              "Nos preocupa la caída de su inversión.", "Su cuenta está inactiva.", "Tiene facturas pendientes con nosotros."]:
        r = _validar_w1(t)
        assert r["valido"] is False and "insinúa el riesgo" in r["fuente_material"], t


def test_w1_puerta_de_datos():
    fc = {"Fecha de corte": [{"fecha_corte": "2026-09-01"}], "Configuración": [{"correo_direccion": "d@m.com", "correo_datos": "x@m.com"}]}
    ok = {"statusCode": 200, "body": {"apta": True, "estado": "carga_ok"}}
    ko = {"statusCode": 200, "body": {"apta": False, "estado": "carga_detenida", "motivo": "la última carga de datos terminó en carga_detenida",
                                      "fecha": "2026-11-16T21:00:00Z"}}
    assert correr("w_datos_al_dia.js", {"input": [ok], "nodos": fc}) == [{"fecha_corte": "2026-09-01"}]
    assert correr("w_datos_no_aptos.js", {"input": [ok], "nodos": fc}) == []
    assert correr("w_datos_al_dia.js", {"input": [ko], "nodos": fc}) == []
    r = correr("w_datos_no_aptos.js", {"input": [ko], "nodos": fc})[0]
    assert r["para"] == "d@m.com,x@m.com" and "carga_detenida" in r["texto"] and r["registro"]["estado"] == "detenido_por_datos"
    caida = {"statusCode": 503, "body": {"message": "down"}}                                   # Supabase caído: tampoco se sigue
    assert correr("w_datos_al_dia.js", {"input": [caida], "nodos": fc}) == []
    assert "503" in correr("w_datos_no_aptos.js", {"input": [caida], "nodos": fc})[0]["texto"]


def test_w1_lanza_el_motor_solo_tras_la_puerta():
    w = json.load(open(os.path.join(RAIZ, "n8n", "W1_ciclo_semanal.json")))
    sig = {k: [d["node"] for d in v["main"][0]] for k, v in w["connections"].items()}
    assert sig["Fecha de corte"] == ["Supabase: estado de la carga"] and sig["Datos al día"] == ["GitHub: lanzar motor"]


# ------------------------------------------------------------------ H6 · escalado en el resumen de dirección (W6)
def test_w6_escalado_a_direccion():
    base = {"asunto": "Meridiano · resumen comercial", "texto": "Resumen.\n\nPREVISIÓN\nx\n\nDetalle, alertas e indicadores en el panel:\nURL"}
    sin = {"statusCode": 200, "body": [
        {"comercial_nombre": "Martina", "razon_social": "Ortopedia Sol", "etiqueta": "ampliacion", "canal": "email", "toque_debido": 4,
         "dias_vencido": 8, "enviada_en": "2026-11-02T10:00:00Z", "ultima_actividad": None}]}
    kpi = {"statusCode": 200, "body": [{"grupo": "tratamiento", "con_toque_debido": 4, "al_dia": 3},
                                       {"grupo": "control", "con_toque_debido": 5, "al_dia": 2}]}
    r = correr("w6_escalado.js", {"input": [base], "nodos": {"Supabase: seguimientos sin atender": [sin], "Supabase: KPI de toques": [kpi]}})[0]
    assert r["asunto"].endswith("· 1 seguimiento sin atender") and r["seguimientos_sin_atender"] == 1
    t = r["texto"]
    assert t.index("ESCALADO") < t.index("Detalle, alertas") and "Ortopedia Sol" in t and "vencido hace 8 días" in t
    assert "tratamiento: 3 de 4 al día (75,0 %)" in t and "control: 2 de 5 al día (40,0 %)" in t
    caido = correr("w6_escalado.js", {"input": [base], "nodos": {"Supabase: seguimientos sin atender": [{"statusCode": 500, "body": {}}],
                                                                  "Supabase: KPI de toques": [{"statusCode": 500}]}})[0]
    assert "No se ha podido consultar" in caido["texto"] and caido["asunto"] == base["asunto"]
    vacio = correr("w6_escalado.js", {"input": [base], "nodos": {"Supabase: seguimientos sin atender": [{"statusCode": 200, "body": []}],
                                                                  "Supabase: KPI de toques": [{"statusCode": 200, "body": []}]}})[0]
    assert "Ninguno" in vacio["texto"]
