"""Filas borradas de la hoja (auditoría del diseño v5, H1): supabase/ausencias.sql.
Tras cada carga sin errores, W0 llama a marcar_presencia_carga() con los clientes y contactos de la hoja; los que faltan
quedan ausentes, sus propuestas abiertas se cierran y la base de datos impide aprobarles, reservarles o crearles nada."""
import os, sys, json
import pytest
sys.path.insert(0, os.path.dirname(__file__))
from test_supabase import db, uno, pid, accion, estado, _como, RAIZ, psycopg2  # noqa: F401  (db es el fixture)

SQL = os.path.join(RAIZ, "supabase", "ausencias.sql")
CLIENTES = ["CLI-1", "CLI-2"] + [f"CLI-{i}" for i in range(3, 11)]
CONTACTOS = ["CT-CLI-1-1", "CT-CLI-2-1"] + [f"CT-CLI-{i}-1" for i in range(3, 11)]


@pytest.fixture
def dba(db):
    db.execute(open(os.path.join(RAIZ, "supabase", "auditoria3.sql")).read())
    db.execute(open(SQL).read())
    for i in range(3, 11):                                       # 10 clientes y 10 contactos: la salvaguarda es del 20 %
        db.execute("insert into dim_clientes (id_cliente, razon_social, comercial_asignado) values (%s, %s, 'COM-01')", (f"CLI-{i}", f"Cliente {i}"))
        db.execute("insert into contactos (id_contacto, id_cliente, nombre, email) values (%s, %s, 'X', %s)",
                   (f"CT-CLI-{i}-1", f"CLI-{i}", f"x{i}@c{i}.example"))
    db.execute("update propuestas set id_contacto = 'CT-CLI-1-1', canal = 'email' where id_cliente = 'CLI-1'")
    db.execute("update propuestas set id_contacto = 'CT-CLI-2-1' where id_cliente = 'CLI-2'")
    yield db


def marcar(db, clientes, contactos):
    return uno(db, "select marcar_presencia_carga(%s::text[], %s::text[])", clientes, contactos)[0]


def test_parche_idempotente_y_comprobacion(dba):
    dba.execute(open(SQL).read())
    assert dba.fetchone() == (True, True, True, True)


def test_cliente_borrado_queda_ausente_y_se_cierran_sus_propuestas(dba):
    p = pid(dba, "CLI-2")
    r = marcar(dba, [c for c in CLIENTES if c != "CLI-2"], CONTACTOS)
    assert r["ok"] and r["clientes_nuevos_ausentes"] == 1 and r["contactos_nuevos_ausentes"] == 0 and r["propuestas_cerradas"] == 1
    assert uno(dba, "select presente_en_ultima_carga, ausente_desde is not null from dim_clientes where id_cliente='CLI-2'") == (False, True)
    assert estado(dba, "CLI-2") == "rechazada"
    assert uno(dba, "select motivo_rechazo from propuestas where id=%s", p)[0] == "No está en la última carga de datos"
    assert uno(dba, "select accion, usuario, estado_despues from eventos_propuesta where propuesta_id=%s order by id desc limit 1", p) == \
        ("descartada_por_carga", "W0", "rechazada")
    assert estado(dba, "CLI-1") == "pendiente_aprobacion"                                   # lo demás no cambia
    assert uno(dba, "select detalle->>'clientes_ausentes' from ejecuciones where detalle->>'flujo'='W0_ausencias' order by id desc limit 1")[0] == "1"
    r2 = marcar(dba, [c for c in CLIENTES if c != "CLI-2"], CONTACTOS)                       # repetir no duplica
    assert r2["clientes_nuevos_ausentes"] == 0 and r2["propuestas_cerradas"] == 0


def test_no_se_aprueba_ni_reserva_ni_crea_nada_para_un_ausente(dba):
    marcar(dba, CLIENTES, [c for c in CONTACTOS if c != "CT-CLI-1-1"])                       # se borra el contacto de CLI-1
    assert estado(dba, "CLI-1") == "rechazada"
    # Aunque alguien la reabra o la apruebe a mano, la base de datos no deja aprobarla ni enviarla
    dba.execute("update propuestas set estado_envio = 'pendiente_aprobacion', estado_tarea = 'pendiente' where id_cliente = 'CLI-1'")
    with pytest.raises(psycopg2.Error, match="no está en la última carga"):
        accion(dba, "CLI-1", "aprobar")
    # Reserva de W5: una aprobada de un ausente no se reserva
    dba.execute("alter table propuestas disable trigger propuestas_bloquear_ausentes")
    dba.execute("update propuestas set estado_envio = 'aprobada', texto_aprobado = 'Texto', aprobada_por = 'm@meridiano.com' where id_cliente = 'CLI-1'")
    dba.execute("alter table propuestas enable trigger propuestas_bloquear_ausentes")
    assert uno(dba, "select reservar_envios(array[%s]::bigint[])", pid(dba, "CLI-1"))[0] == {"reservadas": []}
    # W4 o el motor no crean propuestas nuevas para el ausente: se descartan y quedan registradas
    dba.execute("insert into propuestas (fecha_corte, id_cliente, id_contacto, comercial_asignado, razon_social, accion_id, material_titulo, "
                "material_cuerpo, fuente_material) values ('2026-11-30','CLI-1','CT-CLI-1-1','COM-01','Ortopedia Sol','x','T','C','plantilla'), "
                "('2026-11-30','CLI-3','CT-CLI-3-1','COM-01','Cliente 3','x','T','C','plantilla')")
    assert uno(dba, "select count(*) from propuestas where fecha_corte='2026-11-30'")[0] == 1      # solo la de CLI-3
    assert uno(dba, "select detalle->>'id_cliente' from ejecuciones where estado='propuesta_descartada_ausente'")[0] == "CLI-1"


def test_si_vuelve_a_la_hoja_se_reactiva(dba):
    marcar(dba, [c for c in CLIENTES if c != "CLI-2"], [c for c in CONTACTOS if c != "CT-CLI-2-1"])
    r = marcar(dba, CLIENTES, CONTACTOS)
    assert r["ok"] and r["clientes_que_vuelven"] == 1 and r["contactos_que_vuelven"] == 1 and r["clientes_ausentes"] == 0
    assert uno(dba, "select presente_en_ultima_carga, ausente_desde from dim_clientes where id_cliente='CLI-2'") == (True, None)
    assert uno(dba, "select ausente_de_la_carga('CLI-2', 'CT-CLI-2-1')")[0] is False


def test_salvaguarda_hoja_recortada_o_vacia(dba):
    r = marcar(dba, CLIENTES[:7], CONTACTOS)                                                 # faltan 3 de 10 (30 %)
    assert r["ok"] is False and r["clientes_ausentes"] == 3 and "20 %" in r["motivo"]
    assert uno(dba, "select count(*) from dim_clientes where not presente_en_ultima_carga")[0] == 0
    assert estado(dba, "CLI-2") == "pendiente_aprobacion"
    assert marcar(dba, [], [])["ok"] is False                                                   # lista vacía: nada
    assert uno(dba, "select estado from ejecuciones where detalle->>'flujo'='W0_ausencias' order by id desc limit 1")[0] == "ausencias_no_marcadas"


def test_contactos_de_leads_no_cuentan_y_la_puerta_de_datos_no_cambia(dba):
    dba.execute("insert into leads (id_lead, razon_social, comercial_asignado, origen, creado_por) values ('L-1', 'Lead SA', 'COM-01', 'puerta_fria', 'm@meridiano.com')")
    dba.execute("insert into contactos (id_contacto, id_lead, nombre, email) values ('CT-L-1', 'L-1', 'Lead', 'l@l.example')")
    dba.execute("insert into ejecuciones (origen, estado, detalle) values ('n8n', 'carga_ok', '{\"flujo\": \"W0\"}')")
    r = marcar(dba, CLIENTES, CONTACTOS)
    assert r["contactos_ausentes"] == 0 and uno(dba, "select presente_en_ultima_carga from contactos where id_contacto='CT-L-1'")[0] is True
    assert uno(dba, "select ultima_carga()->>'apta'")[0] == "true"                         # el registro de ausencias no es la carga


def test_permisos(dba):
    _como(dba, "d@meridiano.com")
    with pytest.raises(psycopg2.Error):
        marcar(dba, CLIENTES, CONTACTOS)                                                    # solo n8n (clave de servicio)
    dba.execute("reset role; set role service_role")
    assert marcar(dba, CLIENTES, CONTACTOS)["ok"] is True
    dba.execute("reset role")


def test_parche_sentencia_a_sentencia(dba):
    sqlparse = pytest.importorskip("sqlparse")
    texto = open(SQL).read()
    assert "$$" not in sqlparse.format(texto, strip_comments=True)
    for s in [s for s in sqlparse.split(texto) if sqlparse.format(s, strip_comments=True).strip()]:
        dba.execute(s)
