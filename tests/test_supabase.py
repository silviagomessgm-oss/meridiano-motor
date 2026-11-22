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
    cur.execute(open(os.path.join(RAIZ, "supabase", "bajas.sql")).read())             # H2: baja y lista de exclusión
    cur.execute(open(os.path.join(RAIZ, "supabase", "envios.sql")).read())            # H1: envío idempotente
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
    if acc == "registrar_envio" and (datos or {}).get("ok"):                       # como W5: reservar antes de enviar
        cur.execute("select reservar_envios(array[%s]::bigint[])", (pid(cur, cli),))
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


# ------------------------------------------------------------------ H2 · baja de comunicaciones y lista de exclusión
def token(cur, ct): return str(uno(cur, "select token_baja from contactos where id_contacto=%s", ct)[0])


def test_baja_por_enlace_bloquea_aprobar_y_enviar(db):
    accion(db, "CLI-1", "aprobar")                                            # aprobada antes de la baja
    assert uno(db, "select contacto_excluido, token_baja is not null from envios_pendientes") == (False, True)
    r = uno(db, "select registrar_baja(%s::uuid)", token(db, "CT-CLI-1-1"))[0]
    assert r == {"ok": True, "email": "la***@ortopedia-sol.example"}
    assert uno(db, "select registrar_baja(%s::uuid)", token(db, "CT-CLI-1-1"))[0]["ok"]          # repetir no falla
    assert uno(db, "select count(*) from exclusiones")[0] == 1
    assert uno(db, "select contacto_excluido from envios_pendientes")[0] is True                  # W5 la bloquea
    with pytest.raises(psycopg2.Error, match="dado de baja"):                                    # y la base también
        accion(db, "CLI-1", "registrar_envio", "n8n", {"ok": True, "id_mensaje": "m"})
    r = accion(db, "CLI-1", "registrar_envio", "n8n", {"ok": False, "error": "El contacto se ha dado de baja"})
    assert r["estado"] == "error_envio"
    with pytest.raises(psycopg2.Error, match="dado de baja"):                                    # no se puede volver a aprobar
        accion(db, "CLI-1", "aprobar")
    accion(db, "CLI-1", "rechazar", datos={"motivo": "Se dio de baja"})                          # pero sí rechazar
    assert estado(db, "CLI-1") == "rechazada"


def test_baja_con_token_desconocido_no_hace_nada(db):
    r = uno(db, "select registrar_baja('00000000-0000-0000-0000-000000000000'::uuid)")[0]
    assert r == {"ok": False, "motivo": "enlace_no_valido"} and uno(db, "select count(*) from exclusiones")[0] == 0


def test_baja_mayusculas_y_llamada_no_afectada(db):
    db.execute("update contactos set email='Pedro.Gil@Viajes-Oro.example ' where id_contacto='CT-CLI-2-1'")
    db.execute("insert into exclusiones (email, motivo, origen, registrado_por) values ('pedro.gil@viajes-oro.example','oposicion','panel','x')")
    assert uno(db, "select esta_excluido('PEDRO.GIL@viajes-oro.example')")[0] is True
    accion(db, "CLI-2", "aprobar", "j@meridiano.com")                                            # canal llamada: no se bloquea
    assert estado(db, "CLI-2") == "en_seguimiento"


def test_baja_desde_el_panel_solo_en_la_propia_cartera(db):
    _como(db, "m@meridiano.com")
    with pytest.raises(psycopg2.Error, match="no está en su cartera"):
        db.execute("select baja_panel('CT-CLI-2-1')")
    db.execute("rollback"); _como(db, "m@meridiano.com")
    with pytest.raises(psycopg2.Error): db.execute("select registrar_baja(gen_random_uuid())")    # solo n8n
    db.execute("rollback"); _como(db, "m@meridiano.com")
    with pytest.raises(psycopg2.Error): db.execute("insert into exclusiones values ('a@b.c','oposicion','panel','x',null,null,now())")
    db.execute("rollback"); _como(db, "m@meridiano.com")
    assert uno(db, "select baja_panel('CT-CLI-1-1', 'solicitud_contacto', 'Lo pidió por teléfono')")[0]["ok"]
    assert uno(db, "select dado_de_baja, motivo_baja from contactos_estado where id_contacto='CT-CLI-1-1'") == (True, "solicitud_contacto")
    db.execute("select count(*) from exclusiones"); assert db.fetchone()[0] == 1                 # ve la de su cartera
    db.execute("reset role")
    assert uno(db, "select registrado_por, origen from exclusiones") == ("m@meridiano.com", "panel")
    with pytest.raises(psycopg2.Error): db.execute("set role service_role; delete from exclusiones")   # no se borra por error


# ------------------------------------------------------------------ H1 · envío idempotente
def test_reserva_atomica_solo_una_ejecucion_envia(db):
    accion(db, "CLI-1", "aprobar"); p = pid(db, "CLI-1")
    assert uno(db, "select count(*) from envios_pendientes")[0] == 1
    assert uno(db, "select reservar_envios(array[%s]::bigint[])", p)[0] == {"reservadas": [p]}
    assert uno(db, "select reservar_envios(array[%s]::bigint[])", p)[0] == {"reservadas": []}       # la otra ejecución no la recibe
    assert uno(db, "select count(*) from envios_pendientes")[0] == 0                                  # ni la vuelve a leer
    assert estado(db, "CLI-1") == "enviando"
    db.execute("select registrar_accion(%s, 'registrar_envio', 'n8n', '{\"ok\": true, \"id_mensaje\": \"m\"}')", (p,))
    assert estado(db, "CLI-1") == "en_seguimiento"
    with pytest.raises(psycopg2.Error):                                                              # ya no se puede registrar otra vez
        db.execute("select registrar_accion(%s, 'registrar_envio', 'n8n', '{\"ok\": true}')", (p,))


def test_sin_reserva_no_se_marca_enviada(db):
    accion(db, "CLI-1", "aprobar")
    with pytest.raises(psycopg2.Error, match="sin reserva"):
        db.execute("select registrar_accion(%s, 'registrar_envio', 'n8n', '{\"ok\": true}')", (pid(db, "CLI-1"),))


def test_reaprobar_tras_error_limpia_la_reserva(db):
    accion(db, "CLI-1", "aprobar"); p = pid(db, "CLI-1")
    uno(db, "select reservar_envios(array[%s]::bigint[])", p)
    accion(db, "CLI-1", "registrar_envio", "n8n", {"ok": False, "error": "Gmail: cuota"})
    accion(db, "CLI-1", "aprobar")
    assert uno(db, "select envio_reservado_en is null from propuestas where id=%s", p)[0] is True
    assert uno(db, "select reservar_envios(array[%s]::bigint[])", p)[0] == {"reservadas": [p]}


def test_reserva_sin_confirmar_solo_la_libera_direccion(db):
    accion(db, "CLI-1", "aprobar"); p = pid(db, "CLI-1")
    uno(db, "select reservar_envios(array[%s]::bigint[])", p)
    db.execute("update propuestas set envio_reservado_en = now() - interval '1 hour' where id=%s", (p,))
    assert uno(db, "select id from envios_sin_confirmar") == (p,)
    assert uno(db, "select reservar_envios(array[%s]::bigint[])", p)[0] == {"reservadas": []}       # no se reenvía sola
    _como(db, "m@meridiano.com")
    assert uno(db, "select liberar_envio(%s)", p)[0] == {"ok": False}                               # un comercial no puede
    _como(db, "d@meridiano.com")
    assert uno(db, "select liberar_envio(%s)", p)[0] == {"ok": True}
    db.execute("reset role")
    assert uno(db, "select count(*) from envios_pendientes")[0] == 1
    assert uno(db, "select accion from eventos_propuesta where propuesta_id=%s order by id desc limit 1", p) == ("liberar_envio",)
