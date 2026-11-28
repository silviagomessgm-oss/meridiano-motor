"""Punto de control 1: descripción del panel antes de modelar.

Uso:
  python -m modelo_churn.control1 --datos tablas --limite-fin-w 2026-09-01 \
      --inicio-originales 2023-10-01 --salida modelo_churn/punto_control_1.md
"""
import argparse
from pathlib import Path

import pandas as pd

from .datos import cargar_tablas
from .etiqueta import UN_ANIO
from .panel import construir_panel, separar_entrenamiento_prueba
from .variables import VARIABLES

BINARIAS = ["cambio_interlocutor_12m", "reclamacion_sin_resolver_12m"]
TIPOS = ["perdida_total", "contraccion", "nuevo_sin_campana", "activo", "nuevo_activo"]
GENERADA, ORIGINAL = "con datos generados", "solo datos originales"


def md(df, **kw):
    return df.to_markdown(**kw)


def parte_de_los_datos(cortes, inicio_originales):
    """Un corte es «original» si sus 12 meses previos y su W están en los datos originales."""
    if inicio_originales is None:
        return pd.Series(ORIGINAL, index=cortes)
    ini = pd.Timestamp(inicio_originales) - pd.Timedelta(days=1)
    return pd.Series([ORIGINAL if T - UN_ANIO >= ini else GENERADA for T in cortes], index=cortes)


def tabla_cortes(panel, cortes_prueba, parte):
    g = panel.groupby("fecha_corte")
    t = pd.DataFrame({"observaciones": g.size(), "abandonos": g["abandono"].sum()})
    t["% abandono"] = (100 * t["abandonos"] / t["observaciones"]).round(1)
    tipos = pd.crosstab(panel["fecha_corte"], panel["tipo"])
    t = t.join(tipos[[c for c in TIPOS if c in tipos.columns]])
    t.insert(0, "datos", parte.reindex(t.index).values)
    t.index = [f"{T.date()}{' (prueba)' if T in cortes_prueba else ''}" for T in t.index]
    tot = t.drop(columns="datos").sum()
    tot["% abandono"] = round(100 * tot["abandonos"] / tot["observaciones"], 1)
    t.loc["TOTAL"] = tot
    t.loc["TOTAL", "datos"] = ""
    return t


def tabla_distribucion(panel):
    filas = {}
    for v in VARIABLES:
        s = panel[v]
        if v in BINARIAS:
            filas[v] = {"n": s.notna().sum(), "sin dato": s.isna().sum(), "nº con 1": int(s.sum()),
                        "clientes distintos con 1": panel.loc[s == 1, "id_cliente"].nunique()}
        else:
            d = s.describe(percentiles=[.1, .25, .5, .75, .9])
            filas[v] = {"n": int(d["count"]), "sin dato": int(s.isna().sum()), "media": d["mean"],
                        "mín": d["min"], "p10": d["10%"], "p25": d["25%"], "mediana": d["50%"],
                        "p75": d["75%"], "p90": d["90%"], "máx": d["max"]}
    return pd.DataFrame(filas).T


def _tramos(s, binaria):
    if binaria:
        return s.map({0: "no", 1: "sí"})
    con_dato = s.dropna()
    if (con_dato == con_dato.round()).all() and con_dato.max() <= 10:  # recuentos pequeños: por valor
        return s.clip(upper=3).map({0: "0", 1: "1", 2: "2", 3: "3 o más"})
    # Cuartiles por valor: un mismo valor cae siempre en el mismo tramo (puede haber menos de 4).
    q = pd.qcut(con_dato, 4, duplicates="drop")
    rangos = con_dato.groupby(q, observed=True).agg(["min", "max"])
    etiqueta = {k: f"T{i + 1} [{r['min']:.4g} a {r['max']:.4g}]" for i, (k, r) in enumerate(rangos.iterrows())}
    return q.map(etiqueta).astype(str).reindex(s.index).fillna("sin dato")


def tabla_por_tramos(entreno, parte):
    """% de abandono por tramo de cada variable (solo entrenamiento), total y por parte de los datos.
    Los tramos se calculan con todo el entrenamiento para que las columnas sean comparables."""
    p = entreno["fecha_corte"].map(parte)
    bloques = []
    for v in VARIABLES:
        tramo = _tramos(entreno[v], v in BINARIAS)
        for k, idx in entreno.groupby(tramo, observed=True).groups.items():
            fila = {"variable": v, "tramo": k, "obs": len(idx),
                    "% abandono": round(100 * entreno.loc[idx, "abandono"].mean(), 1)}
            for nombre in (GENERADA, ORIGINAL):
                sub = entreno.loc[idx][p.loc[idx] == nombre]
                fila[f"% {nombre} (obs)"] = f"{100 * sub['abandono'].mean():.1f} ({len(sub)})" if len(sub) else "—"
            bloques.append(fila)
    return pd.DataFrame(bloques)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--datos", default="tablas")
    ap.add_argument("--salida", default="modelo_churn/punto_control_1.md")
    ap.add_argument("--limite-fin-w", default=None,
                    help="W debe terminar antes de esta fecha (por defecto: día 1 del último mes con campañas)")
    ap.add_argument("--inicio-originales", default=None,
                    help="Primer día de los datos originales, para separar cortes con datos generados")
    a = ap.parse_args()

    tablas = cargar_tablas(a.datos)
    panel = construir_panel(tablas, limite=a.limite_fin_w)
    entreno, prueba = separar_entrenamiento_prueba(panel)
    cortes = sorted(panel["fecha_corte"].unique())
    cortes_prueba = set(prueba["fecha_corte"].unique())
    parte = parte_de_los_datos(cortes, a.inicio_originales)
    c = tablas["campanas"]["fecha_emision"]

    rep = panel.groupby("id_cliente").size().value_counts().sort_index()
    rep.index.name, rep.name = "nº de fechas de corte en que aparece", "anunciantes"
    n_ent = entreno["fecha_corte"].nunique()
    distintos = pd.Series({
        "Total panel": panel["id_cliente"].nunique(),
        f"Entrenamiento ({n_ent} cortes)": entreno["id_cliente"].nunique(),
        f"Prueba ({len(cortes_prueba)} cortes)": prueba["id_cliente"].nunique(),
        "En prueba y también en entrenamiento": len(set(prueba["id_cliente"]) & set(entreno["id_cliente"])),
    }, name="anunciantes distintos")
    resumen_partes = entreno.groupby(entreno["fecha_corte"].map(parte)).agg(
        cortes=("fecha_corte", "nunique"), observaciones=("abandono", "size"),
        anunciantes=("id_cliente", "nunique"), abandonos=("abandono", "sum"))
    resumen_partes["% abandono"] = (100 * resumen_partes["abandonos"] / resumen_partes["observaciones"]).round(1)

    partes = [
        "# Punto de control 1 · Descripción del panel (generado automáticamente)\n",
        f"Datos: `{a.datos}` (campañas de {c.min().date()} a {c.max().date()}). "
        f"Límite de W: {a.limite_fin_w or 'día 1 del último mes con campañas'}.\n",
        f"Fechas de corte ({len(cortes)}): {', '.join(str(T.date()) for T in cortes)}.\n",
        f"Prueba: {', '.join(str(T.date()) for T in sorted(cortes_prueba))} "
        f"({', '.join(sorted(set(parte.reindex(sorted(cortes_prueba)))))}).\n",
        "## 1. Observaciones y abandonos por fecha de corte\n", md(tabla_cortes(panel, cortes_prueba, parte)), "",
        "## 2. Anunciantes distintos\n", md(distintos.to_frame()), "", md(rep.to_frame()), "",
        "## 3. Entrenamiento: cortes con datos generados frente a cortes con solo datos originales\n",
        md(resumen_partes), "",
        "## 4. Distribución de cada variable (todas las fechas de corte)\n",
        md(tabla_distribucion(panel), floatfmt=".4g"), "",
        "## 5. % de abandono por tramos de cada variable (solo entrenamiento)\n",
        md(tabla_por_tramos(entreno, parte), index=False), "",
    ]
    Path(a.salida).write_text("\n".join(partes), encoding="utf-8")
    panel.to_csv(Path(a.salida).with_name(Path(a.salida).stem.replace("punto_control_1", "panel") + ".csv"), index=False)
    print(f"Escrito {a.salida}")


if __name__ == "__main__":
    main()
