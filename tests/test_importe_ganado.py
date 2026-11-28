"""Importe ganado al cerrar una propuesta (supabase/importe_ganado.sql): se rellena con el estimado de la propuesta, el
comercial puede cambiarlo al cerrar o después, y el panel de dirección lo suma. Todo pasa por accion_panel, como Lovable."""
import json, os, sys
import pytest
sys.path.insert(0, os.path.dirname(__file__))
from test_supabase import db, uno, pid, accion, estado, _como, RAIZ, psycopg2, CIERRE_RIESGO  # noqa: F401

SQL = os.path.join(RAIZ, "supabase", "importe_ganado.sql")


@pytest.fixture
def dbi(db):
    for f in ["resultado_riesgo.sql", "importe_ganado.sql", "panel_direccion.sql"]:
        db.execute(open(os.path.join(RAIZ, "supabase", f)).read())
    # CLI-1: ampliación con importe propuesto (correo). CLI-2: riesgo, llamada, con producto sugerido y facturación en riesgo
    db.execute("insert into dim_productos (id_producto, nombre, tarifa_base_eur) values ('P01', 'Display web ROS', 900) on conflict do nothing")
    db.execute("update propuestas set etiqueta = 'ampliacion', importe_propuesto_eur = 1400 where id_cliente = 'CLI-1'")
    db.execute("update propuestas set etiqueta = 'riesgo', producto_sugerido_nombre = 'Display web ROS', facturacion_en_riesgo = 5000 "
               "where id_cliente = 'CLI-2'")
    accion(db, "CLI-1", "aprobar", "m@meridiano.com")
    accion(db, "CLI-1", "registrar_envio", "n8n", {"ok": True, "id_mensaje": "m1"})
    accion(db, "CLI-2", "aprobar", "j@meridiano.com")
    yield db


def panel(db, correo, cli, acc, datos):
    db.execute("reset role"); id_ = pid(db, cli)
    _como(db, correo)
    try:
        return uno(db, "select accion_panel(%s, %s, %s::jsonb)", id_, acc, json.dumps(datos))[0]
    finally:
        db.execute("reset role")


def test_parche_idempotente_y_comprobacion(dbi):
    dbi.execute(open(SQL).read())
    assert dbi.fetchone() == (True, True, True)


def test_ganada_sin_importe_toma_el_estimado(dbi):
    r = panel(dbi, "m@meridiano.com", "CLI-1", "cerrar", {"desenlace": "ganada"})
    assert (r["estado"], r["importe_ganado_eur"], r["importe_ganado_origen"]) == ("cerrada", 1400, "propuesta")


def test_ganada_con_importe_del_comercial_y_correccion_posterior(dbi):
    r = panel(dbi, "m@meridiano.com", "CLI-1", "cerrar", {"desenlace": "ganada", "importe_ganado_eur": "1250,50"})
    assert (float(r["importe_ganado_eur"]), r["importe_ganado_origen"]) == (1250.5, "comercial")
    r = panel(dbi, "m@meridiano.com", "CLI-1", "corregir_importe", {"importe_ganado_eur": 2000})
    assert float(r["importe_ganado_eur"]) == 2000
    ev = uno(dbi, "select datos from eventos_propuesta where accion = 'corregir_importe'")[0]
    assert float(ev["importe_anterior"]) == 1250.5 and ev["importe_ganado_eur"] == 2000
    with pytest.raises(psycopg2.Error, match="número de euros"):
        panel(dbi, "m@meridiano.com", "CLI-1", "corregir_importe", {"importe_ganado_eur": "-5"})
    dbi.execute("reset role")
    with pytest.raises(psycopg2.Error, match="no está en tu cartera"):
        panel(dbi, "j@meridiano.com", "CLI-1", "corregir_importe", {"importe_ganado_eur": 10})


def test_riesgo_recuperada_llega_desde_el_panel_con_el_producto_sugerido(dbi):
    r = panel(dbi, "j@meridiano.com", "CLI-2", "cerrar",
              {**CIERRE_RIESGO, "estado_confirmado_comercial": "Activo", "desenlace": "ganada"})
    assert (r["desenlace"], r["importe_ganado_eur"], r["importe_ganado_origen"]) == ("ganada", 900, "propuesta")


def test_importe_solo_si_se_gana_y_perdida_sin_importe(dbi):
    with pytest.raises(psycopg2.Error, match="solo se indica si la propuesta se gana"):
        panel(dbi, "m@meridiano.com", "CLI-1", "cerrar", {"desenlace": "perdida", "motivo_desenlace": "Sin presupuesto",
                                                          "importe_ganado_eur": 100})
    dbi.execute("reset role")
    r = panel(dbi, "j@meridiano.com", "CLI-2", "cerrar", CIERRE_RIESGO)                       # «Perdido» → no recuperada
    assert (r["desenlace"], r["importe_ganado_eur"]) == ("perdida", None)
    with pytest.raises(psycopg2.Error, match="Solo se cambia el importe de una propuesta ganada"):
        panel(dbi, "j@meridiano.com", "CLI-2", "corregir_importe", {"importe_ganado_eur": 100})


def test_sin_estimado_hay_que_escribir_el_importe(dbi):
    dbi.execute("update propuestas set importe_propuesto_eur = null where id_cliente = 'CLI-1'")
    with pytest.raises(psycopg2.Error, match="Indica el importe ganado"):
        panel(dbi, "m@meridiano.com", "CLI-1", "cerrar", {"desenlace": "ganada"})
    dbi.execute("reset role")
    r = panel(dbi, "m@meridiano.com", "CLI-1", "cerrar", {"desenlace": "ganada", "importe_ganado_eur": 800})
    assert float(r["importe_ganado_eur"]) == 800


def test_panel_de_direccion_suma_aprobado_y_ganado(dbi):
    panel(dbi, "m@meridiano.com", "CLI-1", "cerrar", {"desenlace": "ganada", "importe_ganado_eur": 1600})
    panel(dbi, "j@meridiano.com", "CLI-2", "cerrar", {**CIERRE_RIESGO, "estado_confirmado_comercial": "Activo", "desenlace": "ganada"})
    r = uno(dbi, "select sum(importe_aprobado), sum(importe_ganado), sum(ganadas_importe_cambiado) from equipo_semana")
    assert tuple(float(x) for x in r) == (1400 + 900, 1600 + 900, 1)
