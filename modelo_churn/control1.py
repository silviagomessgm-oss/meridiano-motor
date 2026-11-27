"""Punto de control 1: descripción del panel antes de modelar.

Uso: python -m modelo_churn.control1 --datos tablas --salida modelo_churn/punto_control_1.md
"""
import argparse
from pathlib import Path

import pandas as pd

from .datos import cargar_tablas
from .etiqueta import UN_ANIO, en, etiquetar, fechas_corte
from .panel import LIMITE_FIN_W, construir_panel, separar_entrenamiento_prueba
from .variables import VARIABLES

BINARIAS = ["cambio_interlocutor_12m", "reclamacion_sin_resolver_12m"]
TIPOS = ["perdida_total", "contraccion", "nuevo_sin_campana", "activo", "nuevo_activo"]


def md(df, **kw):
    return df.to_markdown(**kw)


def tabla_cortes(panel, cortes_prueba):
    g = panel.groupby("fecha_corte")
    t = pd.DataFrame({
        "observaciones": g.size(),
        "abandonos": g["abandono"].sum(),
    })
    t["% abandono"] = (100 * t["abandonos"] / t["observaciones"]).round(1)
    tipos = pd.crosstab(panel["fecha_corte"], panel["tipo"]).reindex(columns=TIPOS, fill_value=0)
    t = t.join(tipos)
    t.index = [f"{T.date()}{' (prueba)' if T in cortes_prueba else ''}" for T in t.index]
    tot = t.sum(numeric_only=True)
    tot["% abandono"] = round(100 * tot["abandonos"] / tot["observaciones"], 1)
    t.loc["TOTAL"] = tot
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


def tabla_por_tramos(entreno):
    """% de abandono por cuartil de cada variable (solo cortes de entrenamiento)."""
    bloques = []
    for v in VARIABLES:
        s = entreno[v]
        if v in BINARIAS:
            tramo = s.map({0: "no", 1: "sí"})
        elif s.nunique() <= 6:  # recuentos con muchos ceros: agrupar por valor
            tramo = s.clip(upper=2).map({0: "0", 1: "1", 2: "2 o más"})
        else:
            con_dato = s.dropna()
            q = pd.qcut(con_dato.rank(method="first"), 4, labels=["Q1 (bajo)", "Q2", "Q3", "Q4 (alto)"]).astype(str)
            rangos = con_dato.groupby(q).agg(["min", "max"])
            q = q.map(lambda k: f"{k} [{rangos.loc[k, 'min']:.4g} a {rangos.loc[k, 'max']:.4g}]")
            tramo = q.reindex(s.index).fillna("sin dato")
        g = entreno.groupby(tramo, observed=True)["abandono"].agg(["size", "mean"])
        for k, r in g.iterrows():
            bloques.append({"variable": v, "tramo": k, "obs": int(r["size"]), "% abandono": round(100 * r["mean"], 1)})
    return pd.DataFrame(bloques)


def sensibilidades(tablas, cortes, fin_datos):
    camp, cli = tablas["campanas"], tablas["clientes"]
    filas = []
    for T in cortes:
        base = etiquetar(camp, cli, T).set_index("id_cliente")
        fila = {"fecha_corte": T.date(), "obs": len(base), "abandonos E2 (regla W)": int(base["abandono"].sum())}
        # Duda 1: «un año sin comprar» mirando 365 días después de T.
        if T + pd.Timedelta(days=365) <= fin_datos:
            alt = etiquetar(camp, cli, T, regla_anio="365", fin_datos=fin_datos).set_index("id_cliente")
            fila["abandonos con regla 365 d"] = int(alt["abandono"].sum())
            fila["cambian 0→1"] = int(((base["abandono"] == 0) & (alt["abandono"] == 1)).sum())
        else:
            fila["abandonos con regla 365 d"] = "no observable"
            fila["cambian 0→1"] = "—"
        # Duda 4: «historia» por fecha de alta o por primera campaña.
        primera = camp.groupby("id_cliente")["fecha_emision"].min().reindex(base.index)
        nuevo_alta = base["nuevo"]
        nuevo_camp = primera > T - UN_ANIO
        fila["nuevos (por alta)"] = int(nuevo_alta.sum())
        fila["nuevos (por 1ª campaña)"] = int(nuevo_camp.sum())
        # Duda 5: población con 365 días frente a 12 meses de calendario.
        pob365 = en(camp, "fecha_emision", T - pd.Timedelta(days=365), T)["id_cliente"].nunique()
        fila["población 365 días"] = pob365
        fila["población 12 meses"] = len(base)
        filas.append(fila)
    return pd.DataFrame(filas).set_index("fecha_corte")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--datos", default="tablas")
    ap.add_argument("--salida", default="modelo_churn/punto_control_1.md")
    a = ap.parse_args()

    tablas = cargar_tablas(a.datos)
    panel = construir_panel(tablas)
    entreno, prueba = separar_entrenamiento_prueba(panel)
    cortes = sorted(panel["fecha_corte"].unique())
    cortes_prueba = set(prueba["fecha_corte"].unique())
    fin_datos = tablas["campanas"]["fecha_emision"].max() + pd.offsets.MonthEnd(0)

    rep = panel.groupby("id_cliente").size().value_counts().sort_index()
    rep.index.name, rep.name = "nº de fechas de corte en que aparece", "anunciantes"
    distintos = pd.Series({
        "Total panel": panel["id_cliente"].nunique(),
        "Entrenamiento (4 cortes)": entreno["id_cliente"].nunique(),
        "Prueba (2 cortes)": prueba["id_cliente"].nunique(),
        "En prueba y también en entrenamiento": len(set(prueba["id_cliente"]) & set(entreno["id_cliente"])),
    }, name="anunciantes distintos")

    partes = [
        "# Punto de control 1 · Descripción del panel (generado automáticamente)\n",
        f"Fechas de corte: {', '.join(str(T.date()) for T in cortes)}. "
        f"Prueba: {', '.join(str(T.date()) for T in sorted(cortes_prueba))}. "
        f"Fin de datos de campañas: {fin_datos.date()}.\n",
        "## 1. Observaciones y abandonos por fecha de corte\n", md(tabla_cortes(panel, cortes_prueba)), "",
        "## 2. Anunciantes distintos\n", md(distintos.to_frame()), "", md(rep.to_frame()), "",
        "## 3. Distribución de cada variable (todas las fechas de corte)\n",
        md(tabla_distribucion(panel), floatfmt=".4g"), "",
        "## 4. % de abandono por tramos de cada variable (solo entrenamiento)\n",
        md(tabla_por_tramos(entreno), index=False), "",
        "## 5. Sensibilidad de la etiqueta y la población\n", md(sensibilidades(tablas, cortes, fin_datos)), "",
    ]
    Path(a.salida).write_text("\n".join(partes), encoding="utf-8")
    panel.to_csv(Path(a.salida).with_name("panel.csv"), index=False)
    print(f"Escrito {a.salida}")


if __name__ == "__main__":
    main()
