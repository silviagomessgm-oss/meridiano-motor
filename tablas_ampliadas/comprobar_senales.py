"""Relación de las señales y las propuestas con el abandono (etiqueta E2) con la población de modelo_churn: campaña en los
12 meses anteriores al corte y al menos un año desde el alta. Compara los cortes de entrenamiento originales (dic-24 → jun-25)
con la parte añadida. Los cortes de prueba (sep-25, dic-25) no se usan."""
import os, sys, json, warnings; warnings.filterwarnings("ignore")
import pandas as pd, numpy as np
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "evaluacion", "src"))
from generar_scores import poblacion_observable
from etiqueta_e2 import etiqueta_e2
from evaluar_umbral_abandono import inicios_de_campana, foto_a_fecha, SENALES
cfg = json.load(open(os.path.join(RAIZ, "evaluacion", "config", "criterio.json")))
def panel(d, cortes):
    fact = pd.read_csv(f"{d}/fact_campanas.csv", parse_dates=["fecha_emision","fecha_orden"]); fact["fe"] = fact.fecha_emision
    inter = pd.read_csv(f"{d}/fact_interacciones.csv", parse_dates=["fecha"]); inter["fe"] = inter.fecha
    ffac = pd.read_csv(f"{d}/fact_facturacion.csv", parse_dates=["fecha_emision","fecha_vencimiento","fecha_cobro"])
    opo = pd.read_csv(f"{d}/oportunidades.csv", parse_dates=["fecha_envio","fecha_cierre"])
    ini = inicios_de_campana(fact); out = []
    for T in pd.to_datetime(cortes):
        alta = pd.read_csv(f"{d}/dim_clientes.csv", parse_dates=["fecha_alta"]).set_index("id_cliente").fecha_alta
        pob = fact[(fact.fe > T - pd.Timedelta(days=365)) & (fact.fe <= T)].id_cliente.unique()
        pob = [c for c in pob if alta[c] <= T - pd.Timedelta(days=365)]
        v = pd.DataFrame({"fecha_baja_real": pd.NaT, "ultima_orden_total": pd.NaT}, index=pob)
        s = foto_a_fecha(fact, ini, v, T, 365, 210, inter, ffac, cfg["senales"])
        e = etiqueta_e2(fact, ini, T, 210, 0.5, s.id_cliente.values).set_index("id_cliente")
        s["y"] = s.id_cliente.map(e.tipo_e2).isin(["perdida_total","contraccion"]).astype(int)
        o = opo[opo.id_cliente.notna()]
        s["abierta"] = s.id_cliente.isin(o[(o.fecha_envio <= T) & (o.fecha_cierre > T)].id_cliente)
        perd = o[(o.desenlace != "Ganada") & (o.fecha_cierre <= T) & (o.fecha_cierre > T - pd.Timedelta(days=365))]
        s["perdidas"] = s.id_cliente.map(perd.groupby("id_cliente").size()).fillna(0)
        perd2 = o[(o.desenlace == "Perdida") & (o.fecha_cierre <= T) & (o.fecha_cierre > T - pd.Timedelta(days=365))]
        s["perdidas_P"] = s.id_cliente.map(perd2.groupby("id_cliente").size()).fillna(0)
        s["corte"] = T; out.append(s)
    return pd.concat(out, ignore_index=True)
def informe(p, nombre):
    r = lambda m: f"{p[m].y.mean()*100:.1f}% (n={m.sum()})"
    print(f"--- {nombre}: obs {len(p)}, abandono {p.y.mean()*100:.1f}%")
    for sg in SENALES:
        if sg in p: print(f"  {sg:28s} con {r(p[sg]==1)} · sin {r(p[sg]!=1)}")
    print(f"  propuesta abierta: siguen {p[p.y==0].abierta.mean()*100:.1f}% · abandonan {p[p.y==1].abierta.mean()*100:.1f}%")
    for col in ["perdidas","perdidas_P"]:
        print(f"  {col}: 0 → {r(p[col]==0)} · 1-2 → {r(p[col].between(1,2))} · 3+ → {r(p[col]>=3)}")
if __name__ == "__main__":
    R = RAIZ
    informe(panel(f"{R}/tablas", ["2024-12-31","2025-03-31","2025-06-30"]), "ORIGINAL cortes de entrenamiento dic-24 → jun-25")
    pa = panel(f"{R}/tablas_ampliadas", pd.date_range("2021-03-31","2024-09-30",freq="QE"))
    informe(pa, "AMPLIADA parte nueva + mixtos (mar-21 → sep-24)")
