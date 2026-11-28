"""Una baja de comunicaciones cierra las propuestas abiertas del contacto (supabase/baja_cierra.sql): pasan a «Cerradas o
rechazadas», queda el evento y no se crean propuestas nuevas para ese contacto."""
import os, sys
import pytest
sys.path.insert(0, os.path.dirname(__file__))
from test_supabase import db, uno, pid, accion, estado, _como, token, RAIZ, psycopg2  # noqa: F401

SQL = os.path.join(RAIZ, "supabase", "baja_cierra.sql")


@pytest.fixture
def dbb(db):
    for f in ["auditoria3.sql", "resultado_riesgo.sql", "importe_ganado.sql", "panel_direccion.sql", "baja_cierra.sql"]:
        db.execute(open(os.path.join(RAIZ, "supabase", f)).read())
    db.execute("update propuestas set etiqueta = 'riesgo', facturacion_en_riesgo = 5000 where id_cliente = 'CLI-2'")
    yield db


def test_parche_idempotente_y_comprobacion(dbb):
    dbb.execute(open(SQL).read())
    assert dbb.fetchone() == (True, True, True)


def test_baja_desde_el_panel_rechaza_la_pendiente(dbb):
    assert estado(dbb, "CLI-1") == "pendiente_aprobacion"
    _como(dbb, "m@meridiano.com")
    assert uno(dbb, "select baja_panel('CT-CLI-1-1', 'solicitud_contacto', 'Lo pidió por teléfono')")[0]["ok"]
    dbb.execute("reset role")
    assert uno(dbb, "select estado, motivo_rechazo from propuestas where id_cliente='CLI-1'") == \
        ("rechazada", "El contacto se ha dado de baja de las comunicaciones comerciales")
    assert uno(dbb, "select usuario, estado_antes, estado_despues from eventos_propuesta where accion='cerrada_por_baja'") == \
        ("m@meridiano.com", "pendiente_aprobacion", "rechazada")
    assert uno(dbb, "select estado from plan_vigente where id_cliente='CLI-1'")[0] == "rechazada"     # en «Cerradas o rechazadas»


def test_baja_por_enlace_cierra_la_de_seguimiento_sin_inventar_diagnostico(dbb):
    accion(dbb, "CLI-2", "aprobar", "j@meridiano.com")                                    # llamada → en seguimiento
    assert estado(dbb, "CLI-2") == "en_seguimiento"
    assert uno(dbb, "select registrar_baja(%s::uuid)", token(dbb, "CT-CLI-2-1"))[0]["ok"]
    r = uno(dbb, "select estado, desenlace, motivo_desenlace, diagnostico_correcto, importe_ganado_eur "
                 "from propuestas where id_cliente='CLI-2'")
    assert r == ("cerrada", "descartada", "Baja de comunicaciones comerciales", None, None)
    assert uno(dbb, "select cerradas, sin_decision from recuperacion_riesgo")[0:2] == (1, 1)


def test_no_se_crean_propuestas_nuevas_para_un_contacto_de_baja(dbb):
    dbb.execute("insert into exclusiones (email, motivo, origen, registrado_por) "
                "values ('laura.martin@ortopedia-sol.example', 'oposicion', 'panel', 'd@meridiano.com')")
    dbb.execute("insert into propuestas (fecha_corte, id_cliente, comercial_asignado, razon_social, accion_id, id_contacto, "
                "material_titulo, material_cuerpo, fuente_material) values ('2026-10-05', 'CLI-1', 'COM-01', 'Ortopedia Sol', "
                "'llamada_reactivacion', 'CT-CLI-1-1', 'Guion', 'GUION', 'plantilla')")
    assert uno(dbb, "select count(*) from propuestas where id_cliente='CLI-1' and fecha_corte='2026-10-05'")[0] == 0
    assert uno(dbb, "select count(*) from ejecuciones where estado='propuesta_descartada_baja'")[0] == 1


def test_bajas_anteriores_al_parche_se_aplican(db):
    for f in ["auditoria3.sql", "resultado_riesgo.sql", "importe_ganado.sql"]:
        db.execute(open(os.path.join(RAIZ, "supabase", f)).read())
    db.execute("insert into exclusiones (email, motivo, origen, registrado_por) "
               "values ('laura.martin@ortopedia-sol.example', 'oposicion', 'panel', 'd@meridiano.com')")
    assert estado(db, "CLI-1") == "pendiente_aprobacion"
    db.execute(open(SQL).read())
    assert db.fetchone() == (True, True, True) and estado(db, "CLI-1") == "rechazada"
