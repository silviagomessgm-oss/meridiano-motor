"""Panel de dirección centrado en el equipo (supabase/panel_direccion.sql): embudo por comercial, carga actual y
recomendaciones de mejora, sin clientes."""
import os, sys
import pytest
sys.path.insert(0, os.path.dirname(__file__))
from test_supabase import db, uno, pid, accion, estado, _como, RAIZ, psycopg2, CIERRE_RIESGO  # noqa: F401

SQL = os.path.join(RAIZ, "supabase", "panel_direccion.sql")


@pytest.fixture
def dbd(db):
    for f in ["modelo_churn.sql", "resultado_riesgo.sql", "panel_direccion.sql"]:
        db.execute(open(os.path.join(RAIZ, "supabase", f)).read())
    yield db


def test_parche_idempotente_y_comprobacion(dbd):
    dbd.execute(open(SQL).read())
    assert dbd.fetchone() == (True, True, True)


def test_embudo_por_comercial_sin_clientes(dbd):
    accion(dbd, "CLI-2", "aprobar", "j@meridiano.com")                                        # llamada → seguimiento
    accion(dbd, "CLI-2", "cerrar", "j@meridiano.com", {**CIERRE_RIESGO, "estado_confirmado_comercial": "Activo", "desenlace": "ganada"})
    cols = [c.name for c in (dbd.execute("select * from equipo_semana limit 0") or dbd.description)]
    assert not any(c in cols for c in ("id_cliente", "razon_social", "id_lead"))
    r = uno(dbd, "select publicadas, aprobadas, cerradas, ganadas, pct_ganadas from equipo_semana where comercial_asignado='COM-02'")
    assert r == (1, 1, 1, 1, 100.0)
    r = uno(dbd, "select publicadas, aprobadas, pendientes from equipo_semana where comercial_asignado='COM-01'")
    assert r == (1, 0, 1)


def test_equipo_ahora_y_recomendaciones(dbd):
    dbd.execute("update propuestas set creado_en = now() - interval '5 days' where id_cliente = 'CLI-1'")
    a = uno(dbd, "select pendientes_aprobar, pendientes_mas_3_dias from equipo_ahora where comercial_asignado='COM-01'")
    assert a == (1, 1)
    dbd.execute("insert into kpis_ciclo (fecha_corte, indicador, valor) values ('2026-11-23', 'Aplazadas por capacidad', '49'), "
                "('2026-11-23', 'Grupo de control', '0')")
    recs = dbd.execute("select ambito, comercial, recomendacion from recomendaciones_direccion") or dbd.fetchall()
    ambitos = [r[0] for r in recs]
    assert "Capacidad" in ambitos and "Medición" in ambitos and "Ritmo" in ambitos
    assert any("49 cuentas" in r[2] for r in recs)
    cols = [c.name for c in (dbd.execute("select * from recomendaciones_direccion limit 0") or dbd.description)]
    assert cols == ["prioridad", "ambito", "comercial", "recomendacion", "dato"]


def test_comercial_solo_ve_lo_suyo(dbd):
    _como(dbd, "m@meridiano.com")
    assert [r[0] for r in (dbd.execute("select distinct comercial_asignado from equipo_semana") or dbd.fetchall())] == ["COM-01"]
    dbd.execute("reset role")


def test_parche_sentencia_a_sentencia(dbd):
    sqlparse = pytest.importorskip("sqlparse")
    texto = open(SQL).read()
    assert "$$" not in sqlparse.format(texto, strip_comments=True)
    for s in [s for s in sqlparse.split(texto) if sqlparse.format(s, strip_comments=True).strip()]:
        dbd.execute(s)
