"""Flujos de n8n: estructura importable y lógica de los nodos Code ejecutada con node."""
import json, os, subprocess, tempfile, shutil
import pytest
RAIZ = os.path.join(os.path.dirname(__file__), ".."); N8N = os.path.join(RAIZ, "n8n")
FLUJOS = ["W0_carga_semanal", "W1_ciclo_semanal", "W2_alertas_cierre", "W3_recordatorio_semanal", "W5_envio_al_aceptar"]
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
    ("Hemos detectado un riesgo en su cuenta.", "menciona el riesgo"),
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


def test_w5_correo_con_texto_aprobado_y_bloqueo_fuera_de_demo():
    r = correr("w5_preparar_correo.js", {"input": [PEND], "nodos": {"Configuración": [{"modo_demo": True}]}})[0]
    assert r["bloqueo"] is None and r["asunto"] == "Informe de resultados" and "Estimada Laura" in r["texto"]
    assert "Correo de demostración" in r["texto"] and "laura@ortopedia-sol.example" in r["texto"] and "Martina Rodriguez" in r["texto"]
    r = correr("w5_preparar_correo.js", {"input": [PEND], "nodos": {"Configuración": [{"modo_demo": False}]}})[0]
    assert r["bloqueo"] and "ficticio" in r["bloqueo"]


def test_w5_registra_envio_correcto_error_y_bloqueo():
    env = [dict(id=7), dict(id=8)]
    prep = [dict(id=7, bloqueo=None), dict(id=8, bloqueo=None), dict(id=9, bloqueo="Contacto ficticio: no se envía fuera del modo demo")]
    r = correr("w5_resultado_envio.js", {"input": [{"id": "msg-1", "threadId": "t1"}, {"error": {"message": "Quota exceeded"}}],
                                         "nodos": {"Solo enviables": env, "Preparar correo": prep}})
    assert r[0]["p_datos"] == {"ok": True, "id_mensaje": "msg-1"} and r[0]["p_accion"] == "registrar_envio" and r[0]["p_usuario"] == "n8n"
    assert r[1]["p_datos"]["ok"] is False and "Quota" in r[1]["p_datos"]["error"]
    assert r[2]["p_propuesta_id"] == 9 and "ficticio" in r[2]["p_datos"]["error"]
