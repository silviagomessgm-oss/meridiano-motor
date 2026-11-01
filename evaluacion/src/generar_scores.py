"""
Meridiano · Puntuaciones de producción con el modelo L2 (decisión: medir con A, actuar con L2 × valor).

Entrena L2 (logística R+F+T + señales) con todos los cortes cuyo resultado observable ya se conoce
(sin campaña en los 210 días siguientes) y puntúa a todos los anunciantes en la fecha de puntuación.
No usa el archivo de validación: la población se filtra solo con datos observables.

Salida: resultados/scores_modelo.csv (id_cliente, prob_abandono, ...) para el automatismo de propuestas.

Uso:
    python src/generar_scores.py --datos data --config config/criterio.json --produccion config/produccion.json --salida resultados
"""
import argparse, json, os
import numpy as np, pandas as pd
import p_activo
from etiqueta_e2 import etiqueta_e2
from evaluar_umbral_abandono import (inicios_de_campana, foto_a_fecha, variables_logit, variables_extra, SENALES,
                                     VARIABLES_L3_SIN_CONTACTO, VARIABLES_CONTACTO)


def poblacion_observable(fact, T, max_dias):
    """Sustituto sin verdad de referencia: anunciantes con orden <= T y <= max_dias sin actividad."""
    ult = fact[fact.fe <= T].groupby("id_cliente").fe.max()
    ok = ult[(T - ult).dt.days <= max_dias].index
    return pd.DataFrame({"fecha_baja_real": pd.NaT, "ultima_orden_total": pd.NaT}, index=ok)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--datos", default="data"); ap.add_argument("--config", default="config/criterio.json")
    ap.add_argument("--produccion", default="config/produccion.json"); ap.add_argument("--salida", default="resultados")
    ap.add_argument("--etiqueta_config", default="config/etiqueta.json"); ap.add_argument("--estado_etiqueta", default="resultados/estado_etiqueta.json")
    a = ap.parse_args(); os.makedirs(a.salida, exist_ok=True)
    cfg = json.load(open(a.config, encoding="utf-8")); prod = json.load(open(a.produccion, encoding="utf-8"))
    H = prod["horizonte_objetivo_dias"]; Tp = pd.Timestamp(prod["fecha_puntuacion"])
    fact = pd.read_csv(os.path.join(a.datos, "fact_campanas.csv"), parse_dates=["fecha_emision"]); fact["fe"] = fact.fecha_emision
    inter = pd.read_csv(os.path.join(a.datos, "fact_interacciones.csv"), parse_dates=["fecha"]); inter["fe"] = inter.fecha
    ffac = pd.read_csv(os.path.join(a.datos, "fact_facturacion.csv"), parse_dates=["fecha_emision", "fecha_vencimiento", "fecha_cobro"])
    ini = inicios_de_campana(fact)
    ecfg = json.load(open(a.etiqueta_config, encoding="utf-8"))
    etiqueta = prod.get("etiqueta", "A")
    if os.path.exists(a.estado_etiqueta):
        estado = json.load(open(a.estado_etiqueta, encoding="utf-8"))
        if estado.get("etiqueta_vigente") == "A" and etiqueta == "E2":
            print("Validación automática: E2 no validada -> se entrena con la regla A. " + estado.get("estado", ""))
            etiqueta = "A"
    cortes = pd.to_datetime(ecfg["cortes"] if etiqueta == "E2" else prod["cortes_entrenamiento"])
    cortes = cortes[cortes + pd.Timedelta(days=H) <= Tp]          # solo cortes cuyo resultado se conocía en la fecha de puntuación
    assert len(cortes) > 0, "No hay cortes de entrenamiento con resultado conocido antes de la fecha de puntuación"

    def foto(T):
        v = poblacion_observable(fact, T, prod["poblacion_max_dias_sin_actividad"])
        s = foto_a_fecha(fact, ini, v, T, 365, H, inter, ffac, cfg["senales"])
        return s
    def con_etiqueta(T):
        s = foto(T)
        if etiqueta == "E2":
            e = etiqueta_e2(fact, ini, T, H, ecfg["umbral_contraccion"], s.id_cliente.values).set_index("id_cliente")
            s["y"] = s.id_cliente.map(e.tipo_e2).isin(["perdida_total", "contraccion"]).astype(int)
        else:
            s["y"] = s.V3_sin_campana_210d
        return s
    entr = pd.concat([con_etiqueta(T) for T in cortes], ignore_index=True)
    cli = pd.read_csv(os.path.join(a.datos, "dim_clientes.csv")).set_index("id_cliente")
    entr = variables_extra(entr, ini, cli)
    mod = p_activo.Logistica(cfg["p_activo"].get("regularizacion_L2", 1.0)).fit(variables_logit(entr, prod["modelo"]), entr.y)
    hoy = variables_extra(foto(Tp), ini, cli)
    hoy["prob_abandono"] = mod.predict_proba(variables_logit(hoy, prod["modelo"]))
    out = hoy[["id_cliente", "prob_abandono", "recencia", "n_campanas", "valor_cuenta", "n_senales"] + SENALES].copy()
    out["modelo"] = prod["modelo"]; out["etiqueta_entrenamiento"] = etiqueta; out["fecha_corte"] = Tp.date(); out["cortes_entrenamiento"] = ",".join(c.strftime("%Y-%m-%d") for c in cortes)
    out.sort_values("prob_abandono", ascending=False).to_csv(os.path.join(a.salida, "scores_modelo.csv"), index=False)
    nombres = ["intercepto", "log(1+recencia)", "log(1+nº campañas)", "log(1+antigüedad)"] + {
        "L1": [], "L2": SENALES, "L3b": VARIABLES_L3_SIN_CONTACTO, "L3a": VARIABLES_L3_SIN_CONTACTO + VARIABLES_CONTACTO}[prod["modelo"]]
    pd.DataFrame({"variable": nombres, "coeficiente_estandarizado": mod.w}).to_csv(os.path.join(a.salida, "coeficientes_modelo.csv"), index=False)
    print(f"Modelo {prod['modelo']} entrenado con {len(entr)} observaciones de {len(cortes)} cortes; "
          f"puntuados {len(out)} anunciantes a {Tp.date()}. Etiqueta: {etiqueta}. Tasa de abandono en entrenamiento: {entr.y.mean():.3f}")


if __name__ == "__main__":
    main()
