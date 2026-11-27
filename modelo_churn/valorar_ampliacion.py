"""¿Los datos generados ayudan a predecir los datos originales?

Validación SOLO con cortes originales de entrenamiento (mar-25 y jun-25); los cortes de
prueba (sep-25 y dic-25) no se tocan. Para cada corte de validación V se entrena con los
cortes anteriores a V, en cuatro variantes, y se mide sobre los anunciantes de V:
  A. solo cortes originales      B. todos los cortes (ampliado)
  C. solo cortes generados       D. ampliado sin los cortes de la costura (mar-23 a jun-24)

Además: abandono por corte según el origen del anunciante (efecto costura), propuestas
abiertas según la etiqueta y pesos de la regresión logística con y sin datos generados.

Uso: python -m modelo_churn.valorar_ampliacion --panel modelo_churn/panel.csv \
        --tablas-originales tablas --salida modelo_churn/valoracion_utilidad.md
"""
import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier

from .datos import cargar_tablas
from .variables import VARIABLES_MODELO

SEMILLA = 42
INICIO_ORIGINALES = pd.Timestamp("2024-09-30")   # primer corte con 12 meses previos originales
COSTURA = (pd.Timestamp("2023-03-31"), pd.Timestamp("2024-06-30"))
VALIDACION = [pd.Timestamp("2025-03-31"), pd.Timestamp("2025-06-30")]
CAPACIDAD = 12


def modelos():
    imputar = lambda: SimpleImputer(strategy="median", add_indicator=True)
    return {
        "regresión logística": make_pipeline(imputar(), StandardScaler(),
                                             LogisticRegression(C=1.0, max_iter=2000, random_state=SEMILLA)),
        "árbol (3 niveles)": make_pipeline(imputar(), DecisionTreeClassifier(
            max_depth=3, min_samples_leaf=20, random_state=SEMILLA)),
    }


def variantes(panel, V):
    previos = panel[panel["fecha_corte"] < V]
    original = previos["fecha_corte"] >= INICIO_ORIGINALES
    costura = previos["fecha_corte"].between(*COSTURA)
    return {
        "A. solo originales": previos[original],
        "B. ampliado completo": previos,
        "C. solo generados": previos[~original],
        "D. ampliado sin costura": previos[~costura],
    }


def bootstrap_auc_dif(val, p1, p2, n=1000):
    """IC 95 % de AUC(p1) − AUC(p2), remuestreando anunciantes (no filas)."""
    rng = np.random.default_rng(SEMILLA)
    ids = val["id_cliente"].unique()
    filas = {k: np.flatnonzero(val["id_cliente"].to_numpy() == k) for k in ids}
    y = val["abandono"].to_numpy()
    difs = []
    for _ in range(n):
        idx = np.concatenate([filas[k] for k in rng.choice(ids, len(ids))])
        if y[idx].min() == y[idx].max():
            continue
        difs.append(roc_auc_score(y[idx], p1[idx]) - roc_auc_score(y[idx], p2[idx]))
    return np.percentile(difs, [2.5, 97.5])


def fidelidad(orig, ampl):
    """Comparación de distribuciones: filas originales (al principio de cada tabla) frente a filas añadidas."""
    def partes(clave):
        df = ampl[clave].copy()
        df["parte"] = "añadida"
        df.iloc[:len(orig[clave]), df.columns.get_loc("parte")] = "original"
        return df
    c, f, o = partes("campanas"), partes("facturas"), partes("oportunidades")
    f["retraso"] = (f["fecha_cobro"] - f["fecha_vencimiento"]).dt.days
    amp = o[o["origen"] == "Ampliacion de cartera"]
    t = pd.DataFrame({
        "campañas": c.groupby("parte").size(),
        "importe mediano (€)": c.groupby("parte")["importe_eur"].median().round(0),
        "descuento medio (%)": (100 * c.groupby("parte")["descuento_pct"].mean()).round(1),
        "% Digital": (100 * c.groupby("parte")["familia"].apply(lambda x: (x == "Digital").mean())).round(1),
        "retraso medio de cobro (días)": f.groupby("parte")["retraso"].mean().round(1),
        "% ampliaciones ganadas": (100 * amp.groupby("parte")["desenlace"].apply(lambda x: (x == "Ganada").mean())).round(1),
    })
    sin_campanas = set(orig["clientes"]["id_cliente"]) - set(orig["campanas"]["id_cliente"])
    prim = ampl["campanas"].groupby("id_cliente")["fecha_emision"].min()
    alta = ampl["clientes"].set_index("id_cliente")["fecha_alta"].reindex(prim.index)
    fo = f[f["parte"] == "original"]
    pend = fo[fo["fecha_cobro"].isna()]
    hechos = pd.Series({
        "anunciantes de dim_clientes sin campañas en los datos originales": len(sin_campanas),
        "… de ellos con alguna campaña en la ampliación": ampl["campanas"]["id_cliente"].isin(sin_campanas).groupby(
            ampl["campanas"]["id_cliente"]).any().sum(),
        "anunciantes con primera campaña anterior al alta": int((prim < alta).sum()),
        "facturas originales sin cobrar al final de la ampliación": len(pend),
        "… vencidas antes del 1-oct-2026": int((pend["fecha_vencimiento"] < "2026-10-01").sum()),
    }, name="valor")
    return t, hechos


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--panel", default="modelo_churn/panel.csv")
    ap.add_argument("--tablas-originales", default="tablas")
    ap.add_argument("--tablas-ampliadas", default="tablas_ampliadas")
    ap.add_argument("--salida", default="modelo_churn/valoracion_utilidad.md")
    a = ap.parse_args()
    panel = pd.read_csv(a.panel, parse_dates=["fecha_corte"])

    filas, preds = [], {}
    for nombre_m, _ in modelos().items():
        for V in VALIDACION:
            val = panel[panel["fecha_corte"] == V]
            for nombre_v, ent in variantes(panel, V).items():
                m = modelos()[nombre_m].fit(ent[VARIABLES_MODELO], ent["abandono"])
                preds[(nombre_m, nombre_v, V)] = m.predict_proba(val[VARIABLES_MODELO])[:, 1]
                filas.append({"modelo": nombre_m, "entrenamiento": nombre_v, "validación": V.date(),
                              "obs. entrenamiento": len(ent)})

    val = panel[panel["fecha_corte"].isin(VALIDACION)].reset_index(drop=True)
    resumen = []
    for nombre_m in modelos():
        for nombre_v in variantes(panel, VALIDACION[0]):
            p = np.concatenate([preds[(nombre_m, nombre_v, V)] for V in VALIDACION])
            top = np.mean([val.loc[val["fecha_corte"] == V, "abandono"].to_numpy()[
                np.argsort(-preds[(nombre_m, nombre_v, V)], kind="stable")[:CAPACIDAD]].mean() for V in VALIDACION])
            resumen.append({"modelo": nombre_m, "entrenamiento": nombre_v,
                            "AUC": roc_auc_score(val["abandono"], p),
                            f"precisión top {CAPACIDAD}": top,
                            "Brier": brier_score_loss(val["abandono"], p)})
    resumen = pd.DataFrame(resumen)

    difs = []
    for nombre_m in modelos():
        pA = np.concatenate([preds[(nombre_m, "A. solo originales", V)] for V in VALIDACION])
        for nombre_v in ["B. ampliado completo", "C. solo generados", "D. ampliado sin costura"]:
            pX = np.concatenate([preds[(nombre_m, nombre_v, V)] for V in VALIDACION])
            lo, hi = bootstrap_auc_dif(val, pX, pA)
            difs.append({"modelo": nombre_m, "comparación": f"{nombre_v[:2]} − A",
                         "dif. AUC": roc_auc_score(val["abandono"], pX) - roc_auc_score(val["abandono"], pA),
                         "IC 95 % (bootstrap por anunciante)": f"[{lo:+.3f}, {hi:+.3f}]"})
    difs = pd.DataFrame(difs)

    tam = pd.DataFrame(filas).pivot_table(index=["entrenamiento"], columns="validación",
                                         values="obs. entrenamiento", aggfunc="first")
    # Diagnósticos
    fid, hechos = fidelidad(cargar_tablas(a.tablas_originales), cargar_tablas(a.tablas_ampliadas))
    ids_orig = set(pd.read_csv(Path(a.tablas_originales) / "dim_clientes.csv")["id_cliente"])
    grupo = panel["id_cliente"].isin(ids_orig).map({True: "anunciante original", False: "anunciante nuevo (C0321+)"})
    costura = panel.pivot_table(index="fecha_corte", columns=grupo, values="abandono",
                                aggfunc=["size", "mean"]).round(2)
    costura.columns = [f"{'obs.' if f == 'size' else '% abandono'} {g}" for f, g in costura.columns]
    for c in [c for c in costura.columns if c.startswith("%")]:
        costura[c] = (100 * costura[c]).round(0)
    costura["% abandono total"] = (100 * panel.groupby("fecha_corte")["abandono"].mean()).round(1)
    costura.index = costura.index.date
    ent = panel[panel["fecha_corte"] < VALIDACION[-1] + pd.Timedelta(days=1)]
    parte = np.where(ent["fecha_corte"] >= INICIO_ORIGINALES, "cortes originales", "cortes generados")
    abiertas = (ent.assign(parte=parte).groupby(["parte", "abandono"])["propuestas_abiertas"]
                .apply(lambda x: 100 * (x > 0).mean()).unstack().round(1))
    abiertas.columns = ["% con propuesta abierta · sigue", "% con propuesta abierta · abandona"]
    pesos = {}
    for nombre_v, d in variantes(panel, VALIDACION[-1]).items():
        if nombre_v[0] not in "AB":
            continue
        m = modelos()["regresión logística"].fit(d[VARIABLES_MODELO], d["abandono"])
        nombres = list(VARIABLES_MODELO) + [f"sin dato: {VARIABLES_MODELO[i]}" for i in m[0].indicator_.features_]
        pesos[nombre_v] = pd.Series(m[-1].coef_[0], index=nombres)
    pesos = pd.DataFrame(pesos).round(2).sort_values("A. solo originales")

    base = val["abandono"].mean()
    texto = [
        "# Valoración de los datos ampliados · utilidad para predecir los datos originales (generado automáticamente)\n",
        f"Validación: cortes originales {', '.join(str(V.date()) for V in VALIDACION)} "
        f"({len(val)} obs., {val['id_cliente'].nunique()} anunciantes, {100 * base:.1f} % de abandono). "
        "Cortes de prueba (sep-25, dic-25) sin tocar. Variables: las del modelo. Semilla 42.\n",
        "## Observaciones de entrenamiento por variante\n", tam.to_markdown(), "",
        "## Resultados\n", resumen.to_markdown(index=False, floatfmt=".3f"), "",
        "## Diferencia de AUC frente a entrenar solo con originales\n", difs.to_markdown(index=False, floatfmt="+.3f"), "",
        "## Diagnóstico 0 · Fidelidad de las distribuciones (filas originales frente a añadidas)\n",
        fid.to_markdown(), "", hechos.to_frame().to_markdown(), "",
        "## Diagnóstico 1 · Abandono por corte según el origen del anunciante (efecto costura)\n",
        costura.to_markdown(), "",
        "## Diagnóstico 2 · Propuestas abiertas según la etiqueta (cortes hasta jun-25)\n", abiertas.to_markdown(), "",
        f"## Diagnóstico 3 · Pesos de la regresión logística (variables estandarizadas; entrenada con cortes anteriores a {VALIDACION[-1].date()})\n",
        pesos.to_markdown(), "",
    ]
    Path(a.salida).write_text("\n".join(texto), encoding="utf-8")
    print("\n".join(texto))


if __name__ == "__main__":
    main()
