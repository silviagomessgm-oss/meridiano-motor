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
    cur.execute(open(os.path.join(RAIZ, "supabase", "auditorias.sql")).read())
    cur.execute(open(os.path.join(RAIZ, "supabase", "bajas.sql")).read())             # H2: baja y lista de exclusión
    cur.execute(open(os.path.join(RAIZ, "supabase", "envios.sql")).read())            # H1: envío idempotente
    cur.execute(open(os.path.join(RAIZ, "supabase", "controles.sql")).read())         # H7 y H8
    cur.execute(open(os.path.join(RAIZ, "supabase", "seguimiento.sql")).read())       # H5 y H6
    cur.execute(open(os.path.join(RAIZ, "supabase", "auditoria2.sql")).read())        # 2.ª auditoría
    # Esquema desplegado (volcado de producción): lunes, piloto, alta de leads, vistas del panel y webhooks
    cur.execute("create schema if not exists supabase_functions; create or replace function supabase_functions.http_request() "
                "returns trigger language plpgsql as $$ begin return null; end $$")
    cur.execute(open(os.path.join(RAIZ, "supabase", "esquema_desplegado.sql")).read())
    cur.execute(open(os.path.join(RAIZ, "supabase", "backlog2.sql")).read())          # 2.ª auditoría del backlog
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


# ------------------------------------------------------------------ H7 · carga de datos válida · H8 · interlocutor por llamada
def test_ultima_carga_apta_solo_si_w0_termino_bien_y_es_reciente(db):
    assert uno(db, "select ultima_carga()")[0] == {"apta": False, "motivo": "no hay ninguna carga de datos registrada"}
    db.execute("insert into ejecuciones (fecha, origen, estado, detalle) values (now() - interval '2 days', 'n8n', 'carga_ok', '{\"flujo\": \"W0\"}')")
    assert uno(db, "select ultima_carga() ->> 'apta'")[0] == "true"
    db.execute("insert into ejecuciones (origen, estado, detalle) values ('n8n', 'carga_detenida', '{\"flujo\": \"W0\"}')")
    r = uno(db, "select ultima_carga()")[0]
    assert r["apta"] is False and "carga_detenida" in r["motivo"]
    db.execute("insert into ejecuciones (origen, estado, detalle) values ('motor', 'ok', '{\"flujo\": \"W1\"}')")   # otros flujos no cuentan
    assert uno(db, "select ultima_carga() ->> 'estado'")[0] == "carga_detenida"
    db.execute("delete from ejecuciones; insert into ejecuciones (fecha, origen, estado, detalle) values (now() - interval '9 days', 'n8n', 'carga_con_avisos', '{\"flujo\": \"W0\"}')")
    r = uno(db, "select ultima_carga()")[0]
    assert r["apta"] is False and "8 días" in r["motivo"]


def test_cambio_de_interlocutor_va_por_llamada(db):
    db.execute("""insert into propuestas (fecha_corte, id_cliente, etiqueta, razon_social, comercial_asignado, accion_id, asunto_email)
                  values ('2026-09-01', 'CLI-2', 'riesgo', 'Viajes Oro', 'COM-02', 'reunion_nuevo_interlocutor', 'Reunión') returning canal""")
    assert db.fetchone()[0] == "llamada"


# ------------------------------------------------------------------ H5 · toques registrados · H6 · escalado de seguimientos
def _enviada_hace(db, cli, dias, grupo=None):
    accion(db, cli, "aprobar")
    if uno(db, "select canal from propuestas where id=%s", pid(db, cli))[0] == "email":
        accion(db, cli, "registrar_envio", "n8n", {"ok": True, "id_mensaje": "m"})
    db.execute("update propuestas set enviada_en = now() - make_interval(days => %s), grupo_piloto = %s where id=%s",
               (dias, grupo, pid(db, cli)))


def test_toque_registrado_y_llamada_cuenta_como_envio(db):
    accion(db, "CLI-2", "aprobar", "j@meridiano.com"); p = pid(db, "CLI-2")             # CLI-2 va por llamada
    assert uno(db, "select enviada_en from propuestas where id=%s", p)[0] is None
    _como(db, "m@meridiano.com")
    with pytest.raises(psycopg2.Error, match="no está en su cartera"):
        db.execute("select registrar_toque(%s, 'llamada', 'contactado')", (p,))
    db.execute("rollback"); _como(db, "j@meridiano.com")
    with pytest.raises(psycopg2.Error, match="Resultado no válido"):
        db.execute("select registrar_toque(%s, 'llamada', 'genial')", (p,))
    db.execute("rollback"); _como(db, "j@meridiano.com")
    assert uno(db, "select registrar_toque(%s, 'llamada', 'no_contesta', 'Volver a llamar el jueves')", p)[0]["ok"]
    db.execute("reset role")
    r = uno(db, "select enviada_en is not null, ultimo_toque_en is not null from propuestas where id=%s", p)
    assert r == (True, True)
    assert uno(db, "select datos ->> 'resultado' from eventos_propuesta where propuesta_id=%s and accion='toque'", p) == ("no_contesta",)


def test_seguimiento_sin_atender_se_escala_salvo_control(db):
    _enviada_hace(db, "CLI-1", 10)                         # toque del día 4 vencido hace 6 días: aún no se escala
    assert uno(db, "select toque_pendiente, dias_vencido, sin_atender from seguimientos_estado") == (4, 6, False)
    db.execute("update propuestas set enviada_en = now() - interval '11 days'")
    assert uno(db, "select toque_pendiente, dias_vencido, sin_atender from seguimientos_estado") == (4, 7, True)
    db.execute("update propuestas set enviada_en = now() - interval '13 days'")    # llega el día 12: el del 4 sigue escalado
    assert uno(db, "select toque_debido, toque_pendiente, dias_vencido, sin_atender from seguimientos_estado") == (12, 4, 9, True)
    assert uno(db, "select count(*) from seguimientos_sin_atender")[0] == 1
    db.execute("update propuestas set grupo_piloto = 'control'")
    assert uno(db, "select count(*) from seguimientos_sin_atender")[0] == 0               # el control no se escala
    assert uno(db, "select grupo, con_toque_debido, al_dia from kpi_toques_por_grupo") == ("control", 1, 0)
    db.execute("update propuestas set grupo_piloto = 'tratamiento', ultimo_toque_en = now() - interval '6 days'")
    assert uno(db, "select sin_atender, toque_pendiente from seguimientos_estado") == (False, 12)   # atendido el del 4; el del 12 acaba de vencer
    assert uno(db, "select pct_al_dia from kpi_toques_por_grupo")[0] == 100


# ------------------------------------------------------------------ 2.ª auditoría · llamada sin iniciar y avisos del texto
def test_llamada_aprobada_sin_iniciar_se_escala(db):
    accion(db, "CLI-2", "aprobar", "j@meridiano.com"); p = pid(db, "CLI-2")
    db.execute("update propuestas set aprobada_en = now() - interval '11 days' where id=%s", (p,))
    assert uno(db, "select fase, toque_pendiente, dias_vencido, sin_atender from seguimientos_estado") == ("inicio", 4, 7, True)
    assert uno(db, "select count(*) from seguimientos_sin_atender")[0] == 1
    _como(db, "j@meridiano.com"); db.execute("select registrar_toque(%s, 'llamada', 'contactado')", (p,)); db.execute("reset role")
    assert uno(db, "select fase, sin_atender from seguimientos_estado") == ("seguimiento", False)


def test_avisos_del_texto_no_bloquean_y_quedan_registrados(db):
    assert uno(db, "select avisos_texto('Le resumo sus 3 campañas del último año')")[0] == []
    assert uno(db, "select avisos_texto('Hemos notado una caída; le hacemos un 10 %% de descuento')")[0] == ["insinúa el riesgo", "condición económica"]
    p = pid(db, "CLI-1")
    accion(db, "CLI-1", "guardar_material", datos={"material": "Estimada Laura: no queremos perderle. Le ofrecemos un descuento."})
    assert uno(db, "select avisos from material_versiones where propuesta_id=%s and origen='comercial'", p)[0] == ["insinúa el riesgo", "condición económica"]
    accion(db, "CLI-1", "aprobar")                                                     # aprueba igualmente (decide la persona)
    assert estado(db, "CLI-1") == "enviando"
    assert uno(db, "select datos -> 'avisos' from eventos_propuesta where propuesta_id=%s and accion='aprobada_con_aviso'", p)[0] == ["insinúa el riesgo", "condición económica"]


# ------------------------------------------------------------------ Auditoría del backlog · H8 concurrencia real · H6 permisos cruzados
def test_reserva_concurrente_con_dos_transacciones(db):
    """Dos ejecuciones de W5 a la vez (dos conexiones): la segunda espera al bloqueo de la fila y no recibe la propuesta."""
    import threading
    accion(db, "CLI-1", "aprobar"); p = pid(db, "CLI-1")
    db.connection.commit()                                    # la propuesta aprobada, visible para las dos conexiones
    a = psycopg2.connect(DSN, dbname=db.connection.info.dbname); b = psycopg2.connect(DSN, dbname=db.connection.info.dbname)
    try:
        ca, cb = a.cursor(), b.cursor()
        ca.execute("select reservar_envios(array[%s]::bigint[])", (p,)); ra = ca.fetchone()[0]   # A reserva y no confirma aún
        out = {}
        t = threading.Thread(target=lambda: (cb.execute("select reservar_envios(array[%s]::bigint[])", (p,)),
                                             out.setdefault("b", cb.fetchone()[0])))
        t.start(); t.join(1.0)
        assert t.is_alive()                                   # B está esperando el bloqueo de A
        a.commit(); t.join(5); b.commit()
        assert ra == {"reservadas": [p]} and out["b"] == {"reservadas": []}
    finally:
        a.close(); b.close()


def test_permisos_cruzados_entre_comerciales(db):
    """Un comercial no ve ni puede tocar la cartera de otro; dirección ve todo."""
    total = uno(db, "select count(*) from propuestas")[0]; ajena = pid(db, "CLI-2")
    _como(db, "m@meridiano.com"); de_m = uno(db, "select count(*) from propuestas")[0]
    assert 0 < de_m < total
    assert uno(db, "select count(*) from propuestas where comercial_asignado <> 'COM-01'")[0] == 0
    with pytest.raises(psycopg2.Error, match="cartera"):
        db.execute("select accion_panel(%s, 'aprobar', '{}')", (ajena,))
    db.execute("rollback"); _como(db, "j@meridiano.com")
    assert uno(db, "select count(*) from propuestas where comercial_asignado = 'COM-01'")[0] == 0
    db.execute("rollback"); _como(db, "d@meridiano.com")
    assert uno(db, "select count(*) from propuestas")[0] == total


# ------------------------------------------------------------------ Esquema desplegado (auditoría del backlog, H1)
def test_preparar_lunes_es_idempotente_y_respeta_una_etiqueta(db):
    lead = uno(db, """select alta_lead_web('{"razon_social": "Clínica Sol", "nombre": "Ana Ruiz", "email": "ana@clinica-sol.example",
                      "acepta_comercial": true, "texto_consentimiento": "Acepto recibir información comercial"}'::jsonb)""")[0]
    db.execute("select count(*) from preparar_lunes('2026-11-23')"); primera = db.fetchone()[0]
    n1 = uno(db, "select count(*) from propuestas where fecha_corte = '2026-11-23'")[0]
    db.execute("select count(*) from preparar_lunes('2026-11-23')")
    assert uno(db, "select count(*) from propuestas where fecha_corte = '2026-11-23'")[0] == n1           # idempotente
    assert uno(db, "select etiqueta, canal, grupo_piloto in ('tratamiento', 'control') from propuestas where id_lead=%s", lead) == \
        ("lead_nuevo", "email", True)                                                                      # consentimiento → correo; sorteo del piloto
    assert primera >= 1


def test_balance_lunes_una_fila_por_comercial(db):
    accion(db, "CLI-1", "aprobar")
    filas = [r[0] for r in (db.execute("select * from balance_lunes(current_date + 1)") or db.fetchall())]
    assert sorted(f["id_comercial"] for f in filas) == sorted(r[0] for r in (db.execute("select id_comercial from dim_comercial") or db.fetchall()))
    m = next(f for f in filas if f["id_comercial"] == "COM-01")
    assert m["semana_anterior"]["aceptadas"] == 1 and set(m) >= {"pendientes", "prevision", "seguimientos_debidos", "riesgo_abiertas"}


def test_sorteo_del_piloto_reproducible(db):
    r = [x[0] for x in (db.execute("select sorteo_piloto(i) from generate_series(1, 400) i") or db.fetchall())]
    assert r == [x[0] for x in (db.execute("select sorteo_piloto(i) from generate_series(1, 400) i") or db.fetchall())]
    assert 0.40 < r.count("tratamiento") / len(r) < 0.60                                                  # en torno al 50 %


# ------------------------------------------------------------------ 2.ª auditoría del backlog
def test_lead_que_ya_es_cliente_no_recibe_propuesta_de_lead(db):
    dominio = uno(db, "select split_part(email, '@', 2) from contactos where id_cliente = 'CLI-1' limit 1")[0]
    ya = uno(db, f"""select alta_lead_web('{{"razon_social": "Otra marca", "nombre": "Eva", "email": "eva@{dominio}",
                     "acepta_comercial": true, "texto_consentimiento": "Acepto"}}'::jsonb)""")[0]
    nuevo = uno(db, """select alta_lead_web('{"razon_social": "Clínica Nueva", "nombre": "Ana", "email": "ana@gmail.com",
                       "acepta_comercial": true, "texto_consentimiento": "Acepto"}'::jsonb)""")[0]
    razon = uno(db, "select razon_social from dim_clientes where id_cliente = 'CLI-2'")[0]
    igual = uno(db, f"""select alta_lead_web('{{"razon_social": "{razon.upper()}, S.L.", "nombre": "Luis", "email": "luis@otro.example",
                       "acepta_comercial": true, "texto_consentimiento": "Acepto"}}'::jsonb)""")[0]
    db.execute("select count(*) from preparar_lunes('2026-11-23')")
    assert uno(db, "select count(*) from propuestas where id_lead in (%s, %s)", ya, igual)[0] == 0          # no reciben propuesta de lead
    assert uno(db, "select estado, id_cliente_convertido from leads where id_lead = %s", ya) == ("descartado", "CLI-1")
    assert uno(db, "select id_cliente_convertido from leads where id_lead = %s", igual) == ("CLI-2",)
    assert uno(db, "select datos ->> 'id_cliente' from eventos_lead where id_lead = %s and accion = 'ya_es_cliente'", ya) == ("CLI-1",)
    assert uno(db, "select count(*) from propuestas where id_lead = %s", nuevo)[0] == 1                      # gmail no cuenta como dominio


def test_avisos_de_toque_a_los_4_12_y_25_dias(db):
    accion(db, "CLI-1", "aprobar"); accion(db, "CLI-1", "registrar_envio", "n8n", {"ok": True, "id_mensaje": "m"}); p = pid(db, "CLI-1")
    def toque(dias):
        db.execute("update propuestas set enviada_en = now() - make_interval(days => %s) where id=%s", (dias, p))
        r = uno(db, "select toque from seguimientos_debidos where id=%s", p); return r[0] if r else None
    assert [toque(d) for d in (3, 4, 13, 26)] == [None, "primer toque", "segundo toque", "último toque o cierre"]
    db.execute("update propuestas set ultima_respuesta_en = now() where id=%s", (p,))
    assert toque(13) is None                                                     # con respuesta del cliente, no hay aviso
    db.execute("update propuestas set ultima_respuesta_en = null, grupo_piloto = 'control' where id=%s", (p,))
    assert toque(13) is None                                                     # el grupo control_avisos no recibe avisos


def test_aprobadas_con_aviso_llegan_a_direccion(db):
    accion(db, "CLI-1", "guardar_material", datos={"material": "Estimada Laura: no queremos perderle."})
    accion(db, "CLI-1", "aprobar")
    assert uno(db, "select razon_social, avisos from aprobadas_con_aviso")[1] == ["insinúa el riesgo"]


# ------------------------------------------------------------------ Restaurar la demo
def test_restaurar_demo_deja_la_semana_como_recien_publicada(db):
    accion(db, "CLI-1", "guardar_material", datos={"material": "Estimada Laura: texto corregido."})
    accion(db, "CLI-1", "aprobar"); accion(db, "CLI-1", "registrar_envio", "n8n", {"ok": True, "id_mensaje": "m"})
    p = pid(db, "CLI-1")
    _como(db, "m@meridiano.com"); db.execute("select registrar_toque(%s, 'llamada', 'contactado')", (p,)); db.execute("reset role")
    uno(db, "select registrar_baja(token_baja) from contactos where id_contacto = 'CT-CLI-1-1'")
    accion(db, "CLI-2", "aprobar", "j@meridiano.com")
    db.execute(open(os.path.join(RAIZ, "supabase", "restaurar_demo.sql")).read())
    total, no_pend, reservas, toques, bajas = db.fetchone()
    assert total >= 2 and (no_pend, reservas, toques, bajas) == (0, 0, 0, 0)
    assert uno(db, "select material_editado, texto_aprobado, enviada_en from propuestas where id=%s", p) == (None, None, None)
    assert uno(db, "select count(*) from eventos_propuesta where propuesta_id=%s and accion not in ('publicada','material_ia','material_plantilla')", p)[0] == 0
    assert uno(db, "select count(*) from eventos_propuesta where propuesta_id=%s and accion = 'publicada'", p)[0] == 1
    accion(db, "CLI-1", "aprobar")                                               # la demo se puede repetir
    assert estado(db, "CLI-1") == "enviando"
