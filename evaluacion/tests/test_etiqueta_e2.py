import os, sys
import pandas as pd
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from etiqueta_e2 import etiqueta_e2
from evaluar_umbral_abandono import inicios_de_campana

T = "2025-06-30"


def _f(filas):
    f = pd.DataFrame(filas, columns=["id_cliente", "id_campana", "fecha_emision", "importe_eur"])
    f["fe"] = pd.to_datetime(f.fecha_emision); return f


def _e2(filas):
    f = _f(filas); return etiqueta_e2(f, inicios_de_campana(f), T).set_index("id_cliente")


def test_se_salta_su_temporada():
    e = _e2([("X", "K1", "2024-03-01", 1000), ("X", "K2", "2024-09-01", 1000), ("X", "K3", "2025-03-01", 1000)])
    assert e.loc["X", "tipo_e2"] == "perdida_total" and e.loc["X", "motivo_e2"] == "se salta su temporada"


def test_fuera_de_temporada_sigue_activo():
    # compra solo en marzo: ni en jul-ene del año anterior ni en el actual, pero sí este marzo
    e = _e2([("X", "K1", "2024-03-01", 1000), ("X", "K2", "2025-03-01", 1000)])
    assert e.loc["X", "tipo_e2"] == "activo" and "fuera de temporada" in e.loc["X", "motivo_e2"]


def test_un_anio_sin_comprar():
    e = _e2([("X", "K1", "2024-03-01", 1000), ("X", "K2", "2024-06-01", 1000)])
    assert e.loc["X", "tipo_e2"] == "perdida_total"


def test_contraccion_mas_del_50_por_ciento():
    base = [("X", "K1", "2024-01-01", 500), ("X", "K2", "2024-08-01", 4000), ("X", "K3", "2025-03-01", 500)]
    assert _e2(base + [("X", "K4", "2025-08-01", 1500)]).loc["X", "tipo_e2"] == "contraccion"   # 1.500 < 50 % de 4.000
    assert _e2(base + [("X", "K4", "2025-08-01", 2500)]).loc["X", "tipo_e2"] == "activo"        # 2.500 >= 2.000


def test_menos_de_un_anio_usa_regla_A():
    assert _e2([("N", "K1", "2025-01-01", 900)]).loc["N", "tipo_e2"] == "perdida_total"
    assert _e2([("N", "K1", "2025-01-01", 900), ("N", "K2", "2025-10-01", 900)]).loc["N", "tipo_e2"] == "activo"


def test_no_usa_datos_fuera_de_las_ventanas():
    base = [("X", "K1", "2024-03-01", 1000), ("X", "K2", "2024-09-01", 1000), ("X", "K3", "2025-03-01", 1000)]
    a = _e2(base); b = _e2(base + [("X", "K9", "2026-05-01", 9999)])     # compra posterior a W
    assert a.loc["X", "tipo_e2"] == b.loc["X", "tipo_e2"]


def test_evaluacion_de_la_muestra():
    import evaluar_muestra as em
    clave = pd.DataFrame({"id_caso": ["V1", "V2", "V3", "V4"], "id_cliente": list("abcd"), "comercial_asignado": ["C1", "C1", "C2", "C2"],
                          "compartido": [True, False, True, False], "tipo_e2": ["perdida_total", "activo", "contraccion", "activo"]})
    resp = pd.DataFrame({"comercial": ["C1", "C1", "C2", "C2", "C2", "C1"], "id_caso": ["V1", "V2", "V3", "V4", "V1", "V3"],
                         "respuesta": ["Perdido", "Activo", "Activo", "No sé", "Perdido", "Activo"]})
    r, _, _ = em.evaluar(resp, clave, 0.70)
    assert r["n_evaluados"] == 3 and abs(r["acuerdo_3_clases"] - 2 / 3) < 1e-9 and r["veredicto"] == "NO VALIDADA"
    assert r["respuestas_no_se"] == 1
    assert em.cohen_kappa(["a", "b", "a"], ["a", "b", "a"]) == 1.0


def test_validacion_automatica_y_vuelta_a_regla_A():
    import json as _j, validacion_automatica as va
    cfg = _j.load(open(os.path.join(os.path.dirname(__file__), "..", "config", "etiqueta.json"), encoding="utf-8"))
    def r(n, ok):
        return pd.DataFrame({"tipo_e2": ["activo"] * n, "clase_comercial": ["activo"] * ok + ["perdida_total"] * (n - ok)})
    assert va.veredicto(r(10, 2), cfg)["etiqueta_vigente"] == "E2"            # pocos casos: sigue E2 por decisión del equipo
    assert va.veredicto(r(40, 30), cfg)["etiqueta_vigente"] == "E2"           # 75 % >= 70 %
    v = va.veredicto(r(40, 20), cfg)
    assert v["etiqueta_vigente"] == "A" and "NO VALIDADA" in v["estado"]       # 50 %: vuelta automática


def test_validacion_solo_usa_ventanas_cerradas():
    import json as _j, validacion_automatica as va
    cfg = _j.load(open(os.path.join(os.path.dirname(__file__), "..", "config", "etiqueta.json"), encoding="utf-8"))
    f = _f([("X", "K1", "2024-03-01", 1000), ("X", "K2", "2024-09-01", 1000), ("X", "K3", "2025-03-01", 1000), ("Y", "K4", "2026-01-01", 500), ("Z", "K5", "2026-04-01", 100)])
    conf = pd.DataFrame({"id_cliente": ["X", "Y"], "fecha_corte": ["2025-06-30", "2025-12-31"], "estado_confirmado_comercial": ["Perdido", "Activo"]})
    r, total, cerradas = va.comparar(conf, f, inicios_de_campana(f), cfg)
    assert total == 2 and cerradas == 1 and r.iloc[0].tipo_e2 == "perdida_total"   # dic-2025 + 210 > última fecha
