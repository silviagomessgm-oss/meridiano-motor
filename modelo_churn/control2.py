"""Punto de control 2: comparación de modelos en los cortes de prueba.

Uso:
  python -m modelo_churn.control2 --datos tablas --limite-fin-w 2026-09-01 \
      --inicio-originales 2024-09-30 --salida modelo_churn/punto_control_2.md
"""
import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import brier_score_loss, roc_auc_score
from sklearn.tree import export_text

from .datos import cargar_tablas
from .modelos import NOMBRES, SEMILLA, ajustar, elegir_hiperparametros, puntuacion
from .panel import construir_panel, separar_entrenamiento_prueba
from .variables import VARIABLES_MODELO

CAPACIDAD = 12
N_BOOT = 1000


def top_k(df, score, k):
    """Precisión entre las k cuentas de más riesgo (desempate estable por id_cliente)."""
    d = df.assign(_s=score).sort_values(["_s", "id_cliente"], ascending=[False, True], kind="stable")
    return d["abandono"].head(k).mean()


def remuestras(prueba, n=N_BOOT):
    """Índices de filas de cada remuestra por anunciante (el mismo anunciante aparece en las dos fechas)."""
    rng = np.random.default_rng(SEMILLA)
    ids = prueba["id_cliente"].to_numpy()
    unicos = np.unique(ids)
    filas = {k: np.flatnonzero(ids == k) for k in unicos}
    y = prueba["abandono"].to_numpy()
    for _ in range(n):
        idx = np.concatenate([filas[k] for k in rng.choice(unicos, len(unicos))])
        if 0 < y[idx].sum() < len(idx):
            yield idx


def ic(valores):
    lo, hi = np.percentile(valores, [2.5, 97.5])
    return f"[{lo:.3f}; {hi:.3f}]"


def evaluar(prueba, punt, prob, muestras):
    y = prueba["abandono"].to_numpy()
    cortes = sorted(prueba["fecha_corte"].unique())
    fila = {"AUC": roc_auc_score(y, punt),
            "IC 95 % AUC": ic([roc_auc_score(y[i], punt[i]) for i in muestras])}
    for T in cortes:
        m = (prueba["fecha_corte"] == T).to_numpy()
        fila[f"precisión top {CAPACIDAD} · {pd.Timestamp(T).date()}"] = top_k(prueba[m], punt[m], CAPACIDAD)
    fila[f"precisión top {CAPACIDAD} · media"] = np.mean([fila[k] for k in fila if k.startswith("precisión top")])
    n25 = int(round(0.25 * len(prueba) / len(cortes)))
    fila[f"precisión 25 % de más riesgo (top {n25})"] = np.mean(
        [top_k(prueba[(prueba["fecha_corte"] == T).to_numpy()], punt[(prueba["fecha_corte"] == T).to_numpy()], n25)
         for T in cortes])
    fila["Brier"] = brier_score_loss(y, prob)
    return fila


def deciles(prueba, prob):
    d = pd.DataFrame({"prob": prob, "y": prueba["abandono"].to_numpy()})
    d["decil"] = pd.qcut(d["prob"].rank(method="first"), 10, labels=range(1, 11))
    t = d.groupby("decil", observed=True).agg(obs=("y", "size"), prob_media=("prob", "mean"), abandono_real=("y", "mean"))
    t["prob_media"] = (100 * t["prob_media"]).round(1)
    t["abandono_real"] = (100 * t["abandono_real"]).round(1)
    return t


def nombres_columnas(pipe):
    imp = pipe[0]
    return list(VARIABLES_MODELO) + [f"sin_dato_{VARIABLES_MODELO[i]}" for i in imp.indicator_.features_]


def coeficientes(pipe):
    coef = pd.Series(pipe[-1].coef_[0], index=nombres_columnas(pipe))
    t = pd.DataFrame({"peso (por 1 desv. típica)": coef.round(3),
                      "× probabilidad relativa (odds) por 1 desv. típica": np.exp(coef).round(2)})
    sd = pd.Series(pipe[1].scale_, index=coef.index)
    t["1 desv. típica equivale a"] = sd.round(2)
    return t.reindex(coef.abs().sort_values(ascending=False).index)


def hojas_arbol(pipe, entreno, prueba):
    nombres = nombres_columnas(pipe)
    arbol = pipe[-1]
    Xe = pipe[0].transform(entreno[VARIABLES_MODELO])
    Xp = pipe[0].transform(prueba[VARIABLES_MODELO])
    he, hp = arbol.apply(Xe), arbol.apply(Xp)
    t = arbol.tree_

    def camino(hoja):
        padres = {}
        for n in range(t.node_count):
            for h, lado in ((t.children_left[n], "≤"), (t.children_right[n], ">")):
                if h != -1:
                    padres[h] = (n, lado)
        reglas, n = [], hoja
        while n in padres:
            p, lado = padres[n]
            reglas.append(f"{nombres[t.feature[p]]} {lado} {t.threshold[p]:.4g}")
            n = p
        return " y ".join(reversed(reglas))

    filas = []
    for h in np.unique(he):
        filas.append({"regla": camino(h),
                      "obs. entrenamiento": int((he == h).sum()),
                      "% abandono entrenamiento": round(100 * entreno["abandono"].to_numpy()[he == h].mean(), 1),
                      "obs. prueba": int((hp == h).sum()),
                      "% abandono prueba": round(100 * prueba["abandono"].to_numpy()[hp == h].mean(), 1)
                      if (hp == h).any() else None})
    return pd.DataFrame(filas).sort_values("% abandono entrenamiento", ascending=False), export_text(
        arbol, feature_names=nombres, decimals=3)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--datos", default="tablas")
    ap.add_argument("--limite-fin-w", default="2026-09-01")
    ap.add_argument("--inicio-originales", default="2024-09-30",
                    help="Primer corte con solo datos originales (para el entrenamiento de comparación)")
    ap.add_argument("--salida", default="modelo_churn/punto_control_2.md")
    a = ap.parse_args()

    panel = construir_panel(cargar_tablas(a.datos), limite=a.limite_fin_w)
    entreno, prueba = separar_entrenamiento_prueba(panel)
    prueba = prueba.reset_index(drop=True)
    variantes = {"ampliado": entreno,
                 "solo originales": entreno[entreno["fecha_corte"] >= pd.Timestamp(a.inicio_originales)]}
    muestras = list(remuestras(prueba))

    resultados, punt, ajustes, modelos = [], {}, {}, {}
    for var, ent in variantes.items():
        for nombre in NOMBRES:
            hiper, tabla = elegir_hiperparametros(nombre, ent)
            m = ajustar(nombre, ent, **hiper)
            p = m.predict_proba(prueba if nombre in ("a_valor", "b_recencia") else prueba[VARIABLES_MODELO])[:, 1]
            s = puntuacion(nombre, m, prueba)
            punt[(var, nombre)], modelos[(var, nombre)] = (s, p), m
            if tabla is not None:
                ajustes[(var, nombre)] = (hiper, tabla)
            resultados.append({"entrenamiento": var, "modelo": NOMBRES[nombre],
                               "hiperparámetro": ", ".join(f"{k} = {v}" for k, v in hiper.items()) or "—",
                               **evaluar(prueba, s, p, muestras)})
    res = pd.DataFrame(resultados)

    # Diferencias de AUC emparejadas (mismas remuestras) frente a la mejor referencia y entre variantes
    y = prueba["abandono"].to_numpy()
    difs = []
    pares = [(("ampliado", "c_logistica"), ("ampliado", "b_recencia")),
             (("ampliado", "d_arbol"), ("ampliado", "b_recencia")),
             (("ampliado", "c_logistica"), ("ampliado", "d_arbol")),
             (("ampliado", "c_logistica"), ("solo originales", "c_logistica")),
             (("ampliado", "d_arbol"), ("solo originales", "d_arbol"))]
    for x, z in pares:
        sx, sz = punt[x][0], punt[z][0]
        d = [roc_auc_score(y[i], sx[i]) - roc_auc_score(y[i], sz[i]) for i in muestras]
        difs.append({"comparación": f"{NOMBRES[x[1]]} [{x[0]}] − {NOMBRES[z[1]]} [{z[0]}]",
                     "dif. AUC": roc_auc_score(y, sx) - roc_auc_score(y, sz), "IC 95 %": ic(d)})
    difs = pd.DataFrame(difs)

    # Sin los casos «fuera de temporada» (sin compra en el mismo periodo del año anterior): por definición de la
    # etiqueta no pueden ser abandono, así que todos los modelos los aciertan. Aquí se ve qué aporta cada uno en el resto.
    con_wp = (prueba["valor_mismo_periodo_anio_anterior"] > 0).to_numpy()
    sub = prueba[con_wp].reset_index(drop=True)
    muestras_sub = list(remuestras(sub))
    ys = sub["abandono"].to_numpy()
    filas_sub = []
    for nombre in NOMBRES:
        s = punt[("ampliado", nombre)][0][con_wp]
        filas_sub.append({"modelo": NOMBRES[nombre], "AUC": roc_auc_score(ys, s),
                          "IC 95 % AUC": ic([roc_auc_score(ys[i], s[i]) for i in muestras_sub])})
    tabla_sub = pd.DataFrame(filas_sub)
    resumen_sub = (f"Casos fuera de temporada en prueba: {int((~con_wp).sum())} de {len(prueba)} "
                   f"({100 * prueba['abandono'].to_numpy()[~con_wp].mean():.1f} % de abandono). Resto: {len(sub)} obs., "
                   f"{100 * ys.mean():.1f} % de abandono.\n")

    base = entreno["abandono"].mean()
    hojas, texto_arbol = hojas_arbol(modelos[("ampliado", "d_arbol")], entreno, prueba)
    coef_amp = coeficientes(modelos[("ampliado", "c_logistica")])
    coef_ori = coeficientes(modelos[("solo originales", "c_logistica")])
    coef = coef_amp.join(coef_ori[["peso (por 1 desv. típica)"]].rename(
        columns={"peso (por 1 desv. típica)": "peso · solo originales"}))

    partes = [
        "# Punto de control 2 · Comparación de modelos (generado automáticamente)\n",
        f"Datos: `{a.datos}`. Entrenamiento: {entreno['fecha_corte'].nunique()} cortes "
        f"({entreno['fecha_corte'].min().date()} a {entreno['fecha_corte'].max().date()}, {len(entreno)} obs.); "
        f"comparación «solo originales»: {variantes['solo originales']['fecha_corte'].nunique()} cortes "
        f"({len(variantes['solo originales'])} obs.). Prueba: "
        f"{', '.join(str(pd.Timestamp(T).date()) for T in sorted(prueba['fecha_corte'].unique()))} "
        f"({len(prueba)} obs., {prueba['id_cliente'].nunique()} anunciantes, {100 * prueba['abandono'].mean():.1f} % de "
        f"abandono). IC 95 %: bootstrap por anunciante ({len(muestras)} remuestras, semilla {SEMILLA}).\n",
        f"Brier de referencia sin modelo (predecir siempre el {100 * base:.1f} % de entrenamiento): "
        f"{brier_score_loss(y, np.full(len(y), base)):.3f}.\n",
        "## 1. Tabla comparativa (periodo de prueba)\n", res.to_markdown(index=False, floatfmt=".3f"), "",
        "## 2. Diferencias de AUC emparejadas\n", difs.to_markdown(index=False, floatfmt="+.3f"), "",
        "## 2 bis. AUC sin los casos fuera de temporada (entrenamiento ampliado)\n", resumen_sub,
        tabla_sub.to_markdown(index=False, floatfmt=".3f"), "",
        "## 3. Calibración por deciles (prueba, entrenamiento ampliado)\n",
    ]
    for nombre in NOMBRES:
        partes += [f"### {NOMBRES[nombre]}\n", deciles(prueba, punt[("ampliado", nombre)][1]).to_markdown(), ""]
    partes += [
        "## 4. Regresión logística: pesos (entrenamiento ampliado; última columna, solo originales)\n",
        "Variables estandarizadas: el peso indica cuánto sube (+) o baja (−) el riesgo cuando la variable aumenta una "
        "desviación típica, con el resto igual. La columna «× odds» es el factor por el que se multiplica la razón "
        "abandono/permanencia.\n", coef.to_markdown(), "",
        "## 5. Árbol de decisión: reglas (entrenamiento ampliado)\n", hojas.to_markdown(index=False), "",
        "```\n" + texto_arbol + "```\n",
        "## 6. Elección de hiperparámetros (validación temporal dentro de entrenamiento)\n",
    ]
    for (var, nombre), (hiper, tabla) in ajustes.items():
        partes += [f"### {NOMBRES[nombre]} · {var} · elegido {hiper}\n", tabla.to_markdown(index=False, floatfmt=".3f"), ""]
    Path(a.salida).write_text("\n".join(partes), encoding="utf-8")
    pd.DataFrame({"fecha_corte": prueba["fecha_corte"], "id_cliente": prueba["id_cliente"], "abandono": y,
                  **{f"{v}|{n}": punt[(v, n)][1] for v, n in punt}}).to_csv(
        Path(a.salida).with_name("predicciones_prueba.csv"), index=False)
    print(f"Escrito {a.salida}")


if __name__ == "__main__":
    main()
