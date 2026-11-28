"""Corrección de los dos hallazgos altos de la auditoría del diseño v4 (W7, ejecución 108): supabase/auditoria3.sql.
H1 · un envío sin confirmar que sí salió se registra con confirmar_envio_manual() y ya no se puede liberar.
H2 · la lista de exclusión se conserva por correo aunque se borre el contacto y no se puede modificar ni borrar."""
import os, sys
import pytest
sys.path.insert(0, os.path.dirname(__file__))
from test_supabase import db, uno, pid, accion, estado, _como, RAIZ, psycopg2  # noqa: F401  (db es el fixture)

SQL = os.path.join(RAIZ, "supabase", "auditoria3.sql")


@pytest.fixture
def db3(db):
    db.execute(open(SQL).read())
    yield db


def _sin_confirmar(db):
    accion(db, "CLI-1", "aprobar"); p = pid(db, "CLI-1")
    uno(db, "select reservar_envios(array[%s]::bigint[])", p)
    db.execute("update propuestas set envio_reservado_en = now() - interval '2 hours' where id=%s", (p,))
    assert uno(db, "select id from envios_sin_confirmar") == (p,)
    return p


def test_parche_idempotente_y_comprobacion(db3):
    db3.execute(open(SQL).read())                                                     # dos veces seguidas
    assert db3.fetchone() == (True, True, True)


def test_confirmar_envio_manual_solo_direccion_y_arranca_el_seguimiento(db3):
    p = _sin_confirmar(db3)
    hace_1h = uno(db3, "select now() - interval '1 hour'")[0]
    _como(db3, "m@meridiano.com")                                                      # un comercial no puede
    assert uno(db3, "select confirmar_envio_manual(%s, 'msg-1', %s)", p, hace_1h)[0] == {"ok": False}
    _como(db3, "d@meridiano.com")
    assert uno(db3, "select confirmar_envio_manual(%s, '  ', %s)", p, hace_1h)[0] == {"ok": False}   # exige el id del mensaje
    assert uno(db3, "select confirmar_envio_manual(%s, 'msg-1', now() + interval '1 day')", p)[0] == {"ok": False}  # fecha futura
    assert uno(db3, "select confirmar_envio_manual(%s, 'msg-1', now() - interval '3 days')", p)[0] == {"ok": False}  # antes de la reserva
    assert uno(db3, "select confirmar_envio_manual(%s, 'msg-1', %s)", p, hace_1h)[0] == {"ok": True}
    db3.execute("reset role")
    r = uno(db3, "select estado, estado_envio, id_mensaje, enviada_en = %s from propuestas where id=%s", hace_1h, p)
    assert r == ("en_seguimiento", "enviada", "msg-1", True)                           # los toques cuentan desde la fecha real
    assert uno(db3, "select count(*) from envios_sin_confirmar")[0] == 0
    ev = uno(db3, "select accion, usuario, estado_antes, estado_despues, datos->>'id_mensaje' from eventos_propuesta "
                  "where propuesta_id=%s order by id desc limit 1", p)
    assert ev == ("confirmar_envio_manual", "d@meridiano.com", "enviando", "en_seguimiento", "msg-1")


def test_confirmado_ya_no_se_libera_ni_se_reenvia(db3):
    p = _sin_confirmar(db3)
    _como(db3, "d@meridiano.com")
    assert uno(db3, "select confirmar_envio_manual(%s, 'msg-2', now() - interval '1 hour')", p)[0] == {"ok": True}
    assert uno(db3, "select liberar_envio(%s)", p)[0] == {"ok": False}                 # no se puede volver a enviar
    assert uno(db3, "select confirmar_envio_manual(%s, 'msg-3', now() - interval '1 hour')", p)[0] == {"ok": False}
    db3.execute("reset role")
    assert uno(db3, "select reservar_envios(array[%s]::bigint[])", p)[0] == {"reservadas": []}
    assert uno(db3, "select count(*) from envios_pendientes")[0] == 0


def test_solo_reservas_de_correo_aprobadas(db3):
    _como(db3, "d@meridiano.com")                                                      # aprobada sin reserva: no
    db3.execute("reset role"); accion(db3, "CLI-1", "aprobar"); p = pid(db3, "CLI-1"); _como(db3, "d@meridiano.com")
    assert uno(db3, "select confirmar_envio_manual(%s, 'msg-4', now())", p)[0] == {"ok": False}
    db3.execute("reset role")
    assert estado(db3, "CLI-1") == "enviando"


def test_baja_sobrevive_al_borrado_del_contacto_y_bloquea_si_reaparece(db3):
    db3.execute("insert into exclusiones (email, motivo, origen, registrado_por, id_contacto) "
                "values ('laura.martin@ortopedia-sol.example', 'enlace_baja', 'correo', 'W8', 'CT-CLI-1-1')")
    db3.execute("update propuestas set id_contacto = null where id_contacto = 'CT-CLI-1-1'")
    db3.execute("delete from contactos where id_contacto = 'CT-CLI-1-1'")                # plazo de conservación cumplido
    assert uno(db3, "select count(*) from exclusiones where email = 'laura.martin@ortopedia-sol.example'")[0] == 1
    # El mismo correo vuelve a entrar con otra ficha (mayúsculas y espacios incluidos) en otro cliente
    db3.execute("insert into contactos (id_contacto, id_cliente, nombre, email) "
                "values ('CT-CLI-2-9', 'CLI-2', 'Laura Martín', '  Laura.Martin@Ortopedia-Sol.example ')")
    db3.execute("update propuestas set id_contacto = 'CT-CLI-2-9', canal = 'email' where id = %s", (pid(db3, "CLI-2"),))
    with pytest.raises(psycopg2.Error, match="dado de baja"):
        accion(db3, "CLI-2", "aprobar", "j@meridiano.com")


def test_exclusiones_no_se_modifican_ni_borran_salvo_las_de_la_demo(db3):
    db3.execute("insert into exclusiones (email, motivo, origen, registrado_por) values "
                "('ana@empresa-real.es', 'solicitud_contacto', 'panel', 'd@meridiano.com'), "
                "('demo@ficticio.example', 'enlace_baja', 'correo', 'W8')")
    with pytest.raises(psycopg2.Error, match="no se modifica ni se borra"):
        db3.execute("delete from exclusiones where email = 'ana@empresa-real.es'")
    with pytest.raises(psycopg2.Error, match="no se modifica ni se borra"):
        db3.execute("update exclusiones set motivo = 'oposicion' where email = 'ana@empresa-real.es'")
    db3.execute("delete from exclusiones where email like '%.example'")                  # restaurar_demo.sql sigue funcionando
    assert uno(db3, "select count(*) from exclusiones")[0] == 1
    # Reactivación expresa de dirección (consentimiento nuevo): solo el correo indicado
    db3.execute("insert into exclusiones (email, motivo, origen, registrado_por) values ('luis@otra-real.es', 'oposicion', 'panel', 'd')")
    db3.execute("select set_config('meridiano.reactivar', 'ana@empresa-real.es', false)")
    with pytest.raises(psycopg2.Error, match="no se modifica ni se borra"):
        db3.execute("delete from exclusiones where email = 'luis@otra-real.es'")
    db3.execute("delete from exclusiones where email = 'ana@empresa-real.es'")
    assert uno(db3, "select array_agg(email) from exclusiones")[0] == ["luis@otra-real.es"]


def test_parche_sentencia_a_sentencia(db3):
    """Como el editor SQL de Supabase: cada sentencia por separado."""
    sqlparse = pytest.importorskip("sqlparse")
    texto = open(SQL).read()
    assert "$$" not in sqlparse.format(texto, strip_comments=True)
    for s in [s for s in sqlparse.split(texto) if sqlparse.format(s, strip_comments=True).strip()]:
        db3.execute(s)
