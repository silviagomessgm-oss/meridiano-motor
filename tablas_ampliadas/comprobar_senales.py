"""Relación de las señales y las propuestas con el abandono, con la etiqueta y la población de modelo_churn/etiqueta.py
(copia en etiqueta_modelo_churn.py), excluidos los anunciantes con menos de un año desde el alta. Compara los cortes de
entrenamiento originales (sep-24 → jun-25) con la parte añadida. Los cortes de prueba (sep-25, dic-25) no se usan."""
import os, sys, json, warnings; warnings.filterwarnings("ignore")
import pandas as pd, numpy as np
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "evaluacion", "src"))
from generar_scores import poblacion_observable
from etiqueta_e2 import etiqueta_e2
from evaluar_umbral_abandono import inicios_de_campana, foto_a_fecha, SENALES
cfg = json.load(open(os.path.join(RAIZ, "evaluacion", "config", "criterio.json")))
sys.path.insert(0, os.path.join(RAIZ, "tablas_ampliadas"))
from etiqueta_modelo_churn import etiquetar, fechas_corte
def panel(d, cortes):
    fact = pd.read_csv(f"{d}/fact_campanas.csv", parse_dates=["fecha_emision","fecha_orden"]); fact["fe"] = fact.fecha_emision
    inter = pd.read_csv(f"{d}/fact_interacciones.csv", parse_dates=["fecha"]); inter["fe"] = inter.fecha
    ffac = pd.read_csv(f"{d}/fact_facturacion.csv", parse_dates=["fecha_emision","fecha_vencimiento","fecha_cobro"])
    opo = pd.read_csv(f"{d}/oportunidades.csv", parse_dates=["fecha_envio","fecha_cierre"])
    cli = pd.read_csv(f"{d}/dim_clientes.csv", parse_dates=["fecha_alta"])
    ini = inicios_de_campana(fact); out = []
    for T in pd.to_datetime(cortes):
        e = etiquetar(fact, cli, T); e = e[~e.nuevo].set_index("id_cliente")
        v = pd.DataFrame({"fecha_baja_real": pd.NaT, "ultima_orden_total": pd.NaT}, index=e.index)
        s = foto_a_fecha(fact, ini, v, T, 365, 210, inter, ffac, cfg["senales"])
        s["y"] = s.id_cliente.map(e.abandono)
        o = opo[opo.id_cliente.notna()]
        s["abierta"] = s.id_cliente.isin(o[(o.fecha_envio <= T) & (o.fecha_cierre > T)].id_cliente)
        perd = o[(o.desenlace != "Ganada") & (o.fecha_cierre <= T) & (o.fecha_cierre > T - pd.Timedelta(days=365))]
        s["perdidas"] = s.id_cliente.map(perd.groupby("id_cliente").size()).fillna(0)
        s["perdidas_P"] = 0
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
    informe(panel(f"{R}/tablas", ["2024-09-30","2024-12-31","2025-03-31","2025-06-30"]), "ORIGINAL entrenamiento sep-24 → jun-25")
    pa = panel(f"{R}/tablas_ampliadas", pd.date_range("2020-12-31","2024-06-30",freq="QE-DEC"))
    informe(pa, "AMPLIADA parte añadida dic-20 → jun-24")
    print(" ".join(f"{str(k)[2:7]}:{g.y.mean()*100:.0f}" for k, g in pa.groupby("corte")))
