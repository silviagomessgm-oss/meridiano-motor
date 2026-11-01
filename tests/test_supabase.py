"""supabase/schema.sql en un Postgres local con una imitación mínima de Supabase.
Panel comercial unificado: publicación, corrección versionada, aprobar → envío (n8n) → seguimiento → cierre, rechazo,
leads (formulario web con consentimiento y puerta fría), permisos del panel y traza de cada paso."""
import os, uuid, json
import pytest
psycopg2 = pytest.importorskip("psycopg2")
RAIZ = os.path.join(os.path.dirname(__file__), "..")
DSN = os.environ.get("MERIDIANO_PG_TEST")          # p. ej. "host=/var/tmp/meridiano-pg port=5433 user=postgres"
pytestmark = pytest.mark.skipif(not DSN, reason="define MERIDIANO_PG_TEST con un Postgres local de pruebas")
CIERRE_RIESGO = {"estado_confirmado_comercial": "Perdido", "motivo_confirmado": "presupuesto_inversion", "diagnostico_correcto": "Sí"}


@pytest.fixture
def db():
    nombre = "t_" + uuid.uuid4().hex[:8]
    adm = psycopg2.connect(DSN + " dbname=postgres"); adm.autocommit = True
    adm.cursor().execute(f"create database {nombre}")
    c = psycopg2.connect(DSN + f" dbname={nombre}"); c.autocommit = True
    cur = c.cursor()
    cur.execute(open(os.path.join(RAIZ, "tests", "supabase_stub.sql")).read())
    cur.execute(open(os.path.join(RAIZ, "supabase", "schema.sql")).read())
    cur.execute("""
      insert into dim_comercial values ('COM-01','Martina','m@meridiano.com'), ('COM-02','Juan','j@meridiano.com');
      insert into perfiles values ('m@meridiano.com','comercial','COM-01'), ('j@meridiano.com','comercial','COM-02'),
                                  ('d@meridiano.com','direccion',null);
      insert into dim_clientes (id_cliente, razon_social, comercial_asignado) values ('CLI-1','Ortopedia Sol','COM-01'),
                                                                                    ('CLI-2','Viajes Oro','COM-02');
      insert into contactos (id_contacto, id_cliente, nombre, email) values ('CT-CLI-1-1','CLI-1','Laura Martín','laura.martin@ortopedia-sol.example'),
                                                                            ('CT-CLI-2-1','CLI-2','Pedro Gil','pedro.gil@viajes-oro.example');
      insert into propuestas (fecha_corte, id_cliente, comercial_asignado, razon_social, accion_id, material_titulo, material_cuerpo, fuente_material)
        values ('2026-09-28','CLI-1','COM-01','Ortopedia Sol','informe_resultados_y_optimizacion','Informe','PLANTILLA','plantilla'),
               ('2026-09-28','CLI-2','COM-02','Viajes Oro','llamada_reactivacion','Guion','GUION','plantilla');
    """)
    yield cur
    c.close(); adm.cursor().execute(f"drop database {nombre} with (force)"); adm.close()


def uno(cur, q, *a): cur.execute(q, a); return cur.fetchone()
def pid(cur, cli): return uno(cur, "select id from propuestas where coalesce(id_cliente, id_lead)=%s", cli)[0]
def accion(cur, cli, acc, usuario="m@meridiano.com", datos=None):
    return uno(cur, "select registrar_accion(%s, %s, %s, %s::jsonb)", pid(cur, cli), acc, usuario, json.dumps(datos or {}))[0]
def estado(cur, cli): return uno(cur, "select estado from propuestas where coalesce(id_cliente, id_lead)=%s", cli)[0]
def eventos(cur, cli):
    cur.execute("select accion, usuario, estado_antes, estado_despues from eventos_propuesta where propuesta_id=%s order by id", (pid(cur, cli),))
    return cur.fetchall()


def test_publicacion_completa_canal_y_contacto(db):
    r = uno(db, "select canal, id_contacto, estado from propuestas where id_cliente='CLI-1'")
    assert r == ("email", "CT-CLI-1-1", "pendiente_aprobacion")
    assert uno(db, "select canal from propuestas where id_cliente='CLI-2'")[0] == "llamada"        # reactivación = llamada
    assert eventos(db, "CLI-1") == [("publicada", "motor", None, "pendiente_aprobacion")]
    db.execute("update propuestas set material_cuerpo='TEXTO IA', fuente_material='llm' where id_cliente='CLI-1'")
    db.execute("select version, origen, autor from material_versiones where propuesta_id=%s order by version", (pid(db, "CLI-1"),))
    assert db.fetchall() == [(1, "plantilla", "motor"), (2, "llm", "n8n · Claude")]


def test_corregir_aprobar_enviar_seguir_y_cerrar(db):
    accion(db, "CLI-1", "guardar_material", datos={"material": "Corrección 1"})
    accion(db, "CLI-1", "guardar_material", datos={"material": "Corrección 2"})
    assert estado(db, "CLI-1") == "pendiente_aprobacion"
    r = accion(db, "CLI-1", "aprobar")
    assert r["estado"] == "enviando" and r["texto_aprobado"] == "Corrección 2" and r["version_aprobada"] == 3
    with pytest.raises(psycopg2.Error, match="ya está aprobada"):
        accion(db, "CLI-1", "guardar_material", datos={"material": "Cambio tardío"})
    assert uno(db, "select count(*) from envios_pendientes")[0] == 1
    r = accion(db, "CLI-1", "registrar_envio", "n8n", {"ok": True, "id_mensaje": "msg-123"})
    assert r["estado"] == "en_seguimiento" and r["id_mensaje"] == "msg-123"
    assert uno(db, "select count(*) from envios_pendientes")[0] == 0
    accion(db, "CLI-1", "registrar_respuesta", datos={"resumen": "Pide la propuesta para noviembre"})
    with pytest.raises(psycopg2.Error):
        accion(db, "CLI-1", "cerrar", datos={"estado_confirmado_comercial": "Perdido"})          # cierre incompleto
    accion(db, "CLI-1", "cerrar", datos=CIERRE_RIESGO)
    assert eventos(db, "CLI-1") == [
        ("publicada", "motor", None, "pendiente_aprobacion"),
        ("guardar_material", "m@meridiano.com", "pendiente_aprobacion", "pendiente_aprobacion"),
        ("guardar_material", "m@meridiano.com", "pendiente_aprobacion", "pendiente_aprobacion"),
        ("aprobar", "m@meridiano.com", "pendiente_aprobacion", "enviando"),
        ("registrar_envio", "n8n", "enviando", "en_seguimiento"),
        ("registrar_respuesta", "m@meridiano.com", "en_seguimiento", "en_seguimiento"),
        ("cerrar", "m@meridiano.com", "en_seguimiento", "cerrada")]


def test_error_de_envio_se_corrige_y_se_reintenta(db):
    accion(db, "CLI-1", "aprobar")
    r = accion(db, "CLI-1", "registrar_envio", "n8n", {"ok": False, "error": "Gmail: cuota superada"})
    assert r["estado"] == "error_envio" and "cuota" in r["error_envio"]
    accion(db, "CLI-1", "guardar_material", datos={"material": "Texto revisado"})
    assert accion(db, "CLI-1", "aprobar")["estado"] == "enviando"


def test_rechazo_con_motivo_y_reapertura(db):
    with pytest.raises(psycopg2.Error, match="por qué se rechaza"): accion(db, "CLI-1", "rechazar")
    r = accion(db, "CLI-1", "rechazar", datos={"motivo": "El cliente ya ha renovado por teléfono"})
    assert r["estado"] == "rechazada" and r["estado_tarea"] == "cerrada"
    with pytest.raises(psycopg2.Error): accion(db, "CLI-1", "aprobar")
    assert accion(db, "CLI-1", "reabrir", "d@meridiano.com", {"motivo": "Revisar"})["estado"] == "pendiente_aprobacion"


def test_llamada_se_aprueba_sin_envio(db):
    r = accion(db, "CLI-2", "aprobar", "j@meridiano.com")
    assert r["estado"] == "en_seguimiento" and r["estado_envio"] == "aprobada"
    assert uno(db, "select count(*) from envios_pendientes")[0] == 0


def _como(db, correo):
    db.execute("reset role; select set_config('request.jwt.claims', %s, false); set role authenticated",
               (json.dumps({"email": correo} if correo else {}),))


def test_leads_formulario_con_consentimiento_y_puerta_fria_sin_el(db):
    db.execute("set role anon")
    with pytest.raises(psycopg2.Error, match="aceptar recibir"):
        db.execute("select alta_lead_web(%s::jsonb)", (json.dumps({"razon_social": "Clínica Norte", "nombre": "Ana", "email": "ana@norte.example"}),))
    db.execute("rollback")
    web = uno(db, "select alta_lead_web(%s::jsonb)", json.dumps({
        "razon_social": "Clínica Norte", "nombre": "Ana Ruiz", "email": "Ana@Norte.example", "acepta_comercial": True,
        "texto_consentimiento": "Acepto recibir información comercial de Meridiano"}))[0]
    db.execute("reset role")
    assert uno(db, "select origen, consentimiento_comercial, consentimiento_medio from leads where id_lead=%s", web) == \
        ("formulario_web", True, "formulario_web")
    assert uno(db, "select email from contactos where id_lead=%s", web)[0] == "ana@norte.example"
    _como(db, "j@meridiano.com")
    fria = uno(db, "select alta_lead_panel(%s::jsonb)", json.dumps({"razon_social": "Gimnasio Senior", "nombre": "Luis",
                                                                    "email": "luis@gimnasio.example"}))[0]
    assert fria["origen"] == "puerta_fria" and fria["comercial_asignado"] == "COM-02" and not fria["consentimiento_comercial"]
    db.execute("reset role")
    assert uno(db, "select count(*) from leads_sin_propuesta")[0] == 2
    db.execute("""insert into propuestas (fecha_corte, etiqueta, id_lead, comercial_asignado, razon_social, material_cuerpo, fuente_material)
                  values ('2026-10-05','lead_nuevo',%s,'COM-02','Gimnasio Senior','Propuesta inicial','llm')""", (fria["id_lead"],))
    with pytest.raises(psycopg2.Error, match="consentimiento"): accion(db, fria["id_lead"], "aprobar", "j@meridiano.com")
    _como(db, "j@meridiano.com")
    with pytest.raises(psycopg2.Error, match="en qué términos"):
        db.execute("select registrar_consentimiento(%s, 'telefono', '')", (fria["id_lead"],))
    db.execute("rollback"); _como(db, "j@meridiano.com")
    db.execute("select registrar_consentimiento(%s, 'telefono', 'Acepta por teléfono recibir la propuesta')", (fria["id_lead"],))
    db.execute("reset role")
    assert accion(db, fria["id_lead"], "aprobar", "j@meridiano.com")["estado"] == "enviando"
    accion(db, fria["id_lead"], "registrar_envio", "n8n", {"ok": True, "id_mensaje": "m1"})
    with pytest.raises(psycopg2.Error):
        accion(db, fria["id_lead"], "cerrar", "j@meridiano.com", {"desenlace": "perdida"})            # perdida sin motivo
    accion(db, fria["id_lead"], "cerrar", "j@meridiano.com", {"desenlace": "ganada"})
    assert uno(db, "select estado from leads where id_lead=%s", fria["id_lead"])[0] == "convertido"
    db.execute("select accion from eventos_lead where id_lead=%s order by id", (fria["id_lead"],))
    assert [r[0] for r in db.fetchall()] == ["alta_puerta_fria", "consentimiento_registrado"]


def test_panel_solo_lee_y_actua_con_accion_panel(db):
    p1, p2 = pid(db, "CLI-1"), pid(db, "CLI-2")
    _como(db, "m@meridiano.com")
    db.execute("select id_cliente from propuestas"); assert db.fetchall() == [("CLI-1",)]
    for q in ["update propuestas set estado_envio='enviada'", "insert into leads (razon_social, origen, comercial_asignado, creado_por) values ('x','puerta_fria','COM-01','x')",
              "delete from material_versiones", f"select registrar_accion({p1}, 'aprobar', 'd@meridiano.com', '{{}}')",
              f"select accion_panel({p1}, 'registrar_envio', '{{\"ok\": true}}')", f"select accion_panel({p2}, 'aprobar', '{{}}')"]:
        with pytest.raises(psycopg2.Error): db.execute(q)
        db.execute("rollback"); _como(db, "m@meridiano.com")
    r = uno(db, "select accion_panel(%s, 'guardar_material', %s::jsonb)", p1, json.dumps({"material": "Mi versión", "estado_envio": "enviada"}))[0]
    assert r["material_editado"] == "Mi versión" and r["estado"] == "pendiente_aprobacion"           # no se cuela otro campo
    assert uno(db, "select accion_panel(%s, 'aprobar', '{}')", p1)[0]["aprobada_por"] == "m@meridiano.com"
    db.execute("reset role; set role anon")
    with pytest.raises(psycopg2.Error): db.execute(f"select accion_panel({p1}, 'rechazar', '{{}}')")
