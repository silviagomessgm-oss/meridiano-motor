"""Resultado de la acción al cerrar una propuesta de riesgo (supabase/resultado_riesgo.sql): ganada / perdida / sin
decisión, coherente con el estado confirmado, y medición con los pedidos reales del cliente (vista recuperacion_riesgo)."""
import os, sys
import pytest
sys.path.insert(0, os.path.dirname(__file__))
from test_supabase import db, uno, pid, accion, estado, RAIZ, psycopg2, CIERRE_RIESGO  # noqa: F401

SQL = os.path.join(RAIZ, "supabase", "resultado_riesgo.sql")


@pytest.fixture
def dbr(db):
    db.execute(open(os.path.join(RAIZ, "supabase", "modelo_churn.sql")).read())
    db.execute(open(SQL).read())
    db.execute("update propuestas set etiqueta = 'riesgo', facturacion_en_riesgo = 5000 where id_cliente = 'CLI-2'")
    accion(db, "CLI-2", "aprobar", "j@meridiano.com")                     # llamada: pasa a seguimiento al aprobar
    assert estado(db, "CLI-2") == "en_seguimiento"
    yield db


def test_parche_idempotente_y_comprobacion(dbr):
    dbr.execute(open(SQL).read())
    assert dbr.fetchone() == (True, True)


def test_cierre_de_riesgo_exige_resultado_coherente(dbr):
    with pytest.raises(psycopg2.Error, match="Indica el resultado de la acción"):
        accion(dbr, "CLI-2", "cerrar", "j@meridiano.com", CIERRE_RIESGO)                    # sin desenlace
    with pytest.raises(psycopg2.Error, match="no puede cerrarse como recuperada"):
        accion(dbr, "CLI-2", "cerrar", "j@meridiano.com", {**CIERRE_RIESGO, "desenlace": "ganada"})   # «Perdido» + ganada
    datos = {**CIERRE_RIESGO, "estado_confirmado_comercial": "Activo", "desenlace": "ganada"}
    accion(dbr, "CLI-2", "cerrar", "j@meridiano.com", datos)
    assert uno(dbr, "select estado, desenlace from propuestas where id_cliente='CLI-2'") == ("cerrada", "ganada")


def test_no_recuperada_y_sin_decision_se_aceptan(dbr):
    accion(dbr, "CLI-2", "cerrar", "j@meridiano.com", {**CIERRE_RIESGO, "desenlace": "perdida"})
    assert uno(dbr, "select desenlace from propuestas where id_cliente='CLI-2'")[0] == "perdida"


def test_recuperacion_riesgo_cruza_lo_declarado_con_los_pedidos(dbr):
    accion(dbr, "CLI-2", "cerrar", "j@meridiano.com", {**CIERRE_RIESGO, "estado_confirmado_comercial": "Activo", "desenlace": "ganada"})
    r = uno(dbr, "select cerradas, recuperadas, pct_recuperadas, con_pedido_60_dias, recuperadas_sin_pedido_aun, importe_pedidos_60_dias "
                 "from recuperacion_riesgo where comercial_asignado='COM-02'")
    assert r == (1, 1, 100.0, 0, 1, 0)                                                     # declarada, aún sin pedido
    dbr.execute("insert into fact_campanas (id_orden, id_cliente, fecha_orden, fecha_emision, importe_eur) values "
                "('O-1', 'CLI-2', current_date + 5, current_date + 30, 1200), ('O-2', 'CLI-2', current_date + 90, current_date + 120, 999)")
    r = uno(dbr, "select con_pedido_60_dias, recuperadas_sin_pedido_aun, importe_pedidos_60_dias from recuperacion_riesgo")
    assert r == (1, 0, 1200)                                                               # solo cuenta el pedido de los 60 días


def test_cierres_anteriores_y_otras_etiquetas_no_cambian(dbr):
    accion(dbr, "CLI-1", "aprobar"); accion(dbr, "CLI-1", "registrar_envio", "n8n", {"ok": True, "id_mensaje": "m"})
    dbr.execute("update propuestas set etiqueta = 'ampliacion' where id_cliente = 'CLI-1'")
    accion(dbr, "CLI-1", "cerrar", datos={"desenlace": "perdida", "motivo_desenlace": "Sin presupuesto"})
    assert estado(dbr, "CLI-1") == "cerrada"


def test_parche_sentencia_a_sentencia(dbr):
    sqlparse = pytest.importorskip("sqlparse")
    texto = open(SQL).read()
    assert "$$" not in sqlparse.format(texto, strip_comments=True)
    for s in [s for s in sqlparse.split(texto) if sqlparse.format(s, strip_comments=True).strip()]:
        dbr.execute(s)
