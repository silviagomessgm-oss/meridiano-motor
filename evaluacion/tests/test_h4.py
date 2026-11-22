"""H4 (auditoría del diseño): el reentrenamiento excluye cuentas intervenidas y la validación informa por comercial."""
import json, os, sys
import pandas as pd
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from generar_scores import excluir_intervenidas
from validacion_automatica import veredicto

CFG = {"validacion_automatica": {"min_casos": 5, "umbral_acuerdo": 0.7, "etiqueta_respaldo": "A"}}


def test_excluye_solo_observaciones_con_intervencion_en_su_ventana(tmp_path):
    entr = pd.DataFrame({"id_cliente": ["C1", "C1", "C2", "C3"],
                         "corte": pd.to_datetime(["2025-01-01", "2026-06-01", "2026-06-01", "2026-06-01"]), "y": [0, 1, 0, 1]})
    ruta = tmp_path / "interv.csv"
    pd.DataFrame({"id_cliente": ["C1", "C3"], "fecha": ["2026-07-15", "2025-01-01"]}).to_csv(ruta, index=False)
    out, n = excluir_intervenidas(entr, str(ruta), H=210, dias_previos=90)
    assert n == 1 and list(zip(out.id_cliente, out.corte.dt.year)) == [("C1", 2025), ("C2", 2026), ("C3", 2026)]
    assert excluir_intervenidas(entr, None, 210)[1] == 0


def test_acuerdo_por_comercial_y_aviso():
    filas = [("COM-01", "perdida_total", "perdida_total")] * 6 + [("COM-02", "perdida_total", "activo")] * 5 + \
            [("COM-02", "activo", "activo")] * 1
    r = pd.DataFrame(filas, columns=["comercial_asignado", "tipo_e2", "clase_comercial"])
    v = veredicto(r, CFG)
    assert v["acuerdo_por_comercial"]["COM-01"] == {"acuerdo": 1.0, "casos": 6}
    assert v["aviso_comercial"] and "COM-02" in v["aviso_comercial"]
    sin = veredicto(r.drop(columns="comercial_asignado"), CFG)
    assert sin["acuerdo_por_comercial"] == {} and sin["aviso_comercial"] is None
