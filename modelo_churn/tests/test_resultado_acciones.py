"""Aprendizaje de las acciones: exclusión de cuentas intervenidas al entrenar y registro de cuentas salvadas."""
from pathlib import Path

import pandas as pd
import pytest

from modelo_churn.datos import cargar_tablas, vista_en
from modelo_churn.etiqueta import HORIZONTE_DIAS, etiquetar, poblacion
from modelo_churn.panel import construir_panel
from modelo_churn.puntuar import DIAS_INTERVENCION_PREVIA, excluir_intervenidas, puntuar
from modelo_churn.resultado_acciones import GRUPOS, efecto, resultados, resumen, tabla_aprendizaje
from test_no_fuga import _con_futuro

RAIZ = Path(__file__).resolve().parents[2]
DATOS = cargar_tablas(RAIZ / "tablas")
F = pd.Timestamp("2026-09-28")
CICLOS = [pd.Timestamp(d) for d in ("2025-12-01", "2025-12-08", "2026-03-02")]   # el último aún no ha cerrado su ventana


def _historico():
    """Cada ciclo: 6 cuentas propuestas y 4 en control; acción en las 3 primeras propuestas (y una acción posterior a F)."""
    asig, iv = [], []
    for k, t in enumerate(CICLOS):
        ids = list(poblacion(DATOS["campanas"][DATOS["campanas"]["fecha_emision"] <= t], t))[10 * k: 10 * k + 10]
        # propuestas 0-2 en banda alta y 3-5 en media; el control (6-9) siempre en media, como en propuestas.py
        asig += [{"id_cliente": c, "estado_plan": "propuesto" if i < 6 else "control", "fecha_corte": t,
                  "banda_riesgo": "alta" if i < 3 else "media"} for i, c in enumerate(ids)]
        iv += [{"id_cliente": ids[3], "fecha": t + pd.Timedelta(days=7)}]                  # una acción en banda media
        iv += [{"id_cliente": c, "fecha": t + pd.Timedelta(days=7)} for c in ids[:3]]
    iv.append({"id_cliente": asig[3]["id_cliente"], "fecha": F + pd.Timedelta(days=5)})   # futura: no debe contar
    return {"asignaciones": pd.DataFrame(asig), "intervenciones": pd.DataFrame(iv), "confirmaciones": None}


HIST = _historico()


def test_solo_ventanas_cerradas_y_grupos():
    res = resultados(DATOS, HIST, F)
    assert set(pd.to_datetime(res["fecha_corte"])) == set(CICLOS[:2])          # mar-26 aún no ha cerrado su ventana
    assert set(res["grupo"]) <= set(GRUPOS)
    por_ciclo = res.groupby(["fecha_corte", "grupo"]).size().unstack(fill_value=0)
    assert (por_ciclo["accion"] == 4).all() and (por_ciclo["propuesta_sin_accion"] == 2).all() and (por_ciclo["control"] == 4).all()
    assert (res["salvada"] == ((res["grupo"] == "accion") & (res["abandono"] == 0))).all()
    r = resumen(res)
    assert r["cuentas"].sum() == len(res) and r.loc[r["grupo"] == "accion", "salvadas"].item() == res["salvada"].sum()


def test_resultado_coincide_con_la_etiqueta_E2():
    res = resultados(DATOS, HIST, F)
    for t, g in res.groupby("fecha_corte"):
        e2 = etiquetar(DATOS["campanas"], DATOS["clientes"], pd.Timestamp(t)).set_index("id_cliente")
        dentro = g[g["id_cliente"].isin(e2.index)]
        assert (dentro["abandono"].to_numpy() == e2.loc[dentro["id_cliente"], "abandono"].to_numpy()).all()
        assert (pd.to_datetime(g["fecha_resultado"]) == pd.Timestamp(t) + pd.Timedelta(days=HORIZONTE_DIAS)).all()


def test_resultados_sin_datos_posteriores_a_la_fecha():
    referencia = resultados(vista_en(DATOS, F), HIST, F)
    pd.testing.assert_frame_equal(resultados(DATOS, HIST, F), referencia)
    pd.testing.assert_frame_equal(resultados(_con_futuro(DATOS, F), HIST, F), referencia)


def test_tabla_de_aprendizaje_tiene_las_variables_en_la_fecha_de_corte():
    res = resultados(DATOS, HIST, F)
    ap = tabla_aprendizaje(vista_en(DATOS, F), res)
    assert len(ap) == len(res) and {"dias_sin_contacto", "tendencia"} <= set(ap.columns)


def test_exclusion_de_observaciones_intervenidas():
    limite = pd.Timestamp("2026-09-01")
    panel = construir_panel(vista_en(DATOS, F), limite=limite)
    iv = HIST["intervenciones"]
    filtrado, n = excluir_intervenidas(panel, iv, F)
    # cálculo independiente: intervención entre 90 días antes del corte y el final de su ventana, registrada hasta F
    esperadas = 0
    for r in panel.itertuples():
        f = iv[(iv["id_cliente"] == r.id_cliente) & (iv["fecha"] <= F)]["fecha"]
        esperadas += bool(((f > r.fecha_corte - pd.Timedelta(days=DIAS_INTERVENCION_PREVIA)) &
                           (f <= r.fecha_corte + pd.Timedelta(days=HORIZONTE_DIAS))).any())
    assert n == esperadas > 0 and len(filtrado) == len(panel) - n


@pytest.mark.parametrize("cuando", ["antes", "despues"])
def test_puntuar_con_intervenciones(cuando):
    sin, info_sin = puntuar(DATOS, F)
    if cuando == "despues":     # intervenciones posteriores a la fecha: no cambian nada
        iv = HIST["intervenciones"].assign(fecha=F + pd.Timedelta(days=1))
        con, info = puntuar(DATOS, F, iv)
        assert info["observaciones_excluidas_por_intervencion"] == 0
        pd.testing.assert_frame_equal(con, sin)
    else:
        con, info = puntuar(DATOS, F, HIST["intervenciones"])
        assert info["observaciones_excluidas_por_intervencion"] > 0
        assert list(con.columns) == list(sin.columns) and set(con["id_cliente"]) == set(sin["id_cliente"])


def test_efecto_solo_compara_la_misma_banda():
    res = resultados(DATOS, HIST, F)
    e = efecto(res)
    media = res[res["banda_riesgo"] == "media"]
    assert e["cuentas_accion"] == (media["grupo"] == "accion").sum() == 2          # una por ciclo cerrado
    assert e["cuentas_control"] == (media["grupo"] == "control").sum() == 8
    esperado = 100 * media.loc[media.grupo == "control", "abandono"].mean() - 100 * media.loc[media.grupo == "accion", "abandono"].mean()
    assert e["diferencia_puntos"] == round(esperado, 1)
