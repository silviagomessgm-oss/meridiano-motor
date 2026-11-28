"""Simulacro de la presentación: el escenario supuesto solo cambia cuentas con acción que abandonaron, y queda rotulado."""
import os, sys
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "demo"))
from simulacro import RESULTADO_ESCENARIO, aplicar_escenario, escribir_sql  # noqa: E402


def _res():
    return pd.DataFrame({
        "fecha_corte": ["2026-01-05"] * 6, "id_cliente": [f"C{i}" for i in range(6)],
        "grupo": ["accion", "accion", "accion", "propuesta_sin_accion", "control", "control"],
        "banda_riesgo": ["media"] * 6, "resultado": ["perdida_total", "activo", "contraccion", "perdida_total", "perdida_total", "activo"],
        "abandono": [1, 0, 1, 1, 1, 0], "salvada": [False, True, False, False, False, False],
        "estado_confirmado_comercial": [None] * 6, "fecha_resultado": ["2026-08-03"] * 6})


def test_escenario_solo_toca_cuentas_con_accion_que_abandonaron():
    antes = _res()
    despues = aplicar_escenario(antes, 1.0, np.random.default_rng(0))          # efecto supuesto del 100 %
    cambiadas = despues.escenario_supuesto
    assert set(despues.loc[cambiadas, "id_cliente"]) == {"C0", "C2"}
    assert (despues.loc[cambiadas, "resultado"] == RESULTADO_ESCENARIO).all() and (despues.loc[cambiadas, "salvada"]).all()
    pd.testing.assert_frame_equal(despues.loc[~cambiadas, ["grupo", "abandono", "resultado"]],
                                  antes.loc[~cambiadas.to_numpy(), ["grupo", "abandono", "resultado"]])
    assert not aplicar_escenario(antes, 0.0, np.random.default_rng(0)).escenario_supuesto.any()


def test_sql_de_carga_y_borrado_cubren_las_mismas_filas(tmp_path):
    res = aplicar_escenario(_res(), 0.5, np.random.default_rng(1))
    escribir_sql(res, tmp_path, {"prueba": True})
    carga = (tmp_path / "cargar_simulacro.sql").read_text(encoding="utf-8")
    borra = (tmp_path / "borrar_simulacro.sql").read_text(encoding="utf-8")
    assert carga.count("('2026-01-05', 'C") == len(res) and borra.count("('2026-01-05'::date, 'C") == len(res)
    assert "on conflict (fecha_corte, id_cliente)" in carga and "SIMULACRO" in carga and "SIMULACRO" in borra
