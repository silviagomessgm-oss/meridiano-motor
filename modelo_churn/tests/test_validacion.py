"""Tests de la validación de E2 con las confirmaciones de los comerciales (etiqueta de modelo_churn)."""
import pandas as pd

from modelo_churn.etiqueta import etiquetar, poblacion
from modelo_churn.validacion import CLASE_DE_TIPO, PARAMETROS, clase_e2, comparar, veredicto
from test_puntuar import DATOS

T = pd.Timestamp("2025-06-30")


def test_clase_e2_coincide_con_la_etiqueta_del_modelo():
    e = etiquetar(DATOS["campanas"], DATOS["clientes"], T).set_index("id_cliente")
    c = clase_e2(DATOS, e.index, T)
    assert (c == e.tipo.map(CLASE_DE_TIPO)).all()
    assert set(c) <= {"perdida_total", "contraccion", "activo"}


def test_fuera_de_poblacion_es_activo_si_vuelve_a_comprar():
    fuera = sorted(set(DATOS["clientes"].id_cliente) - set(poblacion(DATOS["campanas"], T)))
    camp = DATOS["campanas"]
    compran = set(camp[(camp.fecha_emision > T) & (camp.fecha_emision <= T + pd.Timedelta(days=210))].id_cliente)
    c = clase_e2(DATOS, fuera, T)
    for cid in fuera:
        assert c[cid] == ("activo" if cid in compran else "perdida_total")


def test_comparar_solo_ventanas_cerradas():
    e = etiquetar(DATOS["campanas"], DATOS["clientes"], T)
    conf = pd.DataFrame({"id_cliente": list(e.id_cliente[:3]) * 2,
                         "fecha_corte": [str(T.date())] * 3 + ["2026-10-31"] * 3,
                         "estado_confirmado_comercial": ["Perdido", "Activo", "No sé"] * 2})
    r, validas = comparar(conf, DATOS, "2026-11-23")
    assert validas == 4 and len(r) == 2                 # «No sé» no cuenta; la ventana de oct-2026 sigue abierta
    assert set(r.clase_comercial) == {"perdida_total", "activo"}


def _r(n, aciertos, comercial=None):
    return pd.DataFrame({"clase_e2": ["activo"] * n, "clase_comercial": ["activo"] * aciertos + ["perdida_total"] * (n - aciertos),
                         **({"comercial_asignado": comercial} if comercial is not None else {})})


def test_veredicto():
    assert veredicto(_r(10, 10))["validada"] is None
    assert veredicto(_r(PARAMETROS["min_casos"], PARAMETROS["min_casos"]))["validada"] is True
    v = veredicto(_r(40, 20))
    assert v["validada"] is False and v["etiqueta_vigente"] == "E2"      # el modelo sigue con E2: solo avisa
    com = ["A"] * 10 + ["B"] * 30
    r = pd.DataFrame({"clase_e2": ["activo"] * 40, "clase_comercial": ["perdida_total"] * 10 + ["activo"] * 30,
                      "comercial_asignado": com})
    assert "de A (0%)" in veredicto(r)["aviso_comercial"]
