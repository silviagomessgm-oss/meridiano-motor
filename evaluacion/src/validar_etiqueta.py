"""
Meridiano · Validación de la etiqueta E2.

1. Calcula E2 en los cortes de config/etiqueta.json y la compara con la regla A.
2. Control secundario: reactivación posterior de las pérdidas totales y archivo de validación.
3. Genera la muestra ciega para los comerciales (una hoja por comercial) y su clave, que NO se les entrega.

Uso:
    python src/validar_etiqueta.py --datos data --config config/etiqueta.json --salida resultados
"""
import argparse, json, os
import numpy as np, pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.worksheet.datavalidation import DataValidation
from etiqueta_e2 import etiqueta_e2
from evaluar_umbral_abandono import inicios_de_campana

RESPUESTAS = ["Perdido", "Redujo mucho", "Activo", "Pausa: volvió después", "No sé"]


def calcular(fact, ini, cfg):
    filas = []
    for T in pd.to_datetime(cfg["cortes"]):
        vivos = fact[(fact.fe > T - pd.Timedelta(days=365)) & (fact.fe <= T)].id_cliente.unique()
        e = etiqueta_e2(fact, ini, T, cfg["horizonte_dias"], cfg["umbral_contraccion"], vivos)
        fin_W = T + pd.Timedelta(days=cfg["horizonte_dias"])
        camp_W = ini[(ini.fe > T) & (ini.fe <= fin_W)].groupby("id_cliente").size()
        e["regla_A_sin_campana_210d"] = (~e.id_cliente.isin(camp_W.index)).astype(int)
        vuelve = ini[ini.fe > fin_W].groupby("id_cliente").fe.min()
        e["reactiva_despues_de_W"] = e.id_cliente.map(vuelve).notna()
        e["dias_hasta_reactivacion"] = (e.id_cliente.map(vuelve) - fin_W).dt.days
        e["dias_observables_despues_de_W"] = (fact.fe.max() - fin_W).days
        filas.append(e)
    return pd.concat(filas, ignore_index=True)


def resumen(e, gt):
    r = pd.crosstab(e.corte, e.tipo_e2, margins=True)
    comp = pd.crosstab(e.tipo_e2, e.regla_A_sin_campana_210d.map({1: "A: abandono", 0: "A: activo"}))
    pt = e[e.tipo_e2 == "perdida_total"]
    reac = pt.groupby("corte").agg(perdidas_totales=("id_cliente", "size"), reactivan=("reactiva_despues_de_W", "sum"),
                                   dias_observables=("dias_observables_despues_de_W", "first"),
                                   mediana_dias_hasta_reactivar=("dias_hasta_reactivacion", "median"))
    reac["porcentaje_reactiva"] = reac.reactivan / reac.perdidas_totales
    if gt is not None:
        g = gt.set_index("id_cliente").fecha_baja_real
        e = e.assign(baja_real=e.id_cliente.map(g))
        e["baja_real_antes_fin_W"] = e.baja_real.notna() & (e.baja_real <= pd.to_datetime(e.corte) + pd.Timedelta(days=210))
        ctrl = e.groupby("tipo_e2").baja_real_antes_fin_W.mean().rename("porcentaje_con_baja_en_archivo_validacion")
    else:
        ctrl = pd.Series(dtype=float)
    return r, comp, reac, ctrl


def trimestres(fact, ini, inter, clientes, desde="2024-10-01", hasta="2026-09-30"):
    f = fact[(fact.fe >= desde) & (fact.fe <= hasta) & fact.id_cliente.isin(clientes)].copy()
    f["trim"] = f.fe.dt.to_period("Q").astype(str)
    fac = f.pivot_table(index="id_cliente", columns="trim", values="importe_eur", aggfunc="sum", fill_value=0)
    i = ini[(ini.fe >= desde) & (ini.fe <= hasta) & ini.id_cliente.isin(clientes)].copy()
    i["trim"] = i.fe.dt.to_period("Q").astype(str)
    cam = i.pivot_table(index="id_cliente", columns="trim", values="id_campana", aggfunc="count", fill_value=0)
    todos = pd.period_range(desde, hasta, freq="Q").astype(str)
    fac = fac.reindex(index=clientes, columns=todos, fill_value=0); cam = cam.reindex(index=clientes, columns=todos, fill_value=0)
    ult = fact[fact.id_cliente.isin(clientes)].groupby("id_cliente").fe.max().reindex(clientes)
    con = inter[inter.tipo.isin(["Llamada", "Email comercial", "Visita", "Videollamada"]) & inter.id_cliente.isin(clientes)]
    ultc = con.groupby("id_cliente").fe.max().reindex(clientes)
    return fac, cam, ult, ultc


def muestra(e, cli, fact, ini, inter, cfg, salida):
    m = cfg["validacion"]["muestra"]; g = np.random.default_rng(m["semilla"])
    d = e[e.corte == pd.Timestamp(m["corte"]).date()].copy()
    fuera = d[(d.tipo_e2 == "activo") & d.motivo_e2.str.startswith("fuera de temporada")]
    resto_act = d[(d.tipo_e2 == "activo") & ~d.id_cliente.isin(fuera.id_cliente)]
    def toma(df, n): return df.iloc[g.permutation(len(df))[:min(n, len(df))]]
    partes = [toma(d[d.tipo_e2 == "perdida_total"], m["perdida_total"]), toma(d[d.tipo_e2 == "contraccion"], m["contraccion"])]
    n_fuera = max(m["de_los_activos_fuera_de_temporada_minimo"], 0)
    partes += [toma(fuera, n_fuera)]
    faltan = m["tamano"] - sum(len(p) for p in partes)
    partes += [toma(resto_act, faltan)]
    s = pd.concat(partes).sample(frac=1, random_state=m["semilla"]).reset_index(drop=True)
    s["id_caso"] = [f"V{i+1:03d}" for i in range(len(s))]
    comp_idx = s.groupby("tipo_e2", group_keys=False).apply(lambda x: x.sample(frac=m["compartidos_por_los_3_comerciales"] / len(s),
                                                                               random_state=m["semilla"])).index
    s["compartido"] = s.index.isin(comp_idx)
    s = s.merge(cli[["razon_social", "categoria", "comercial_asignado"]], left_on="id_cliente", right_index=True)
    s[["id_caso", "id_cliente", "razon_social", "comercial_asignado", "compartido", "tipo_e2", "motivo_e2"]].to_csv(
        os.path.join(salida, "clave_muestra_NO_ENTREGAR.csv"), index=False)
    fac, cam, ult, ultc = trimestres(fact, ini, inter, s.id_cliente.values)
    wb = Workbook(); ws0 = wb.active; ws0.title = "Instrucciones"
    for t in ["Validación de la etiqueta de abandono · Meridiano", "",
              cfg["validacion"]["pregunta_al_comercial"], "",
              "Responda en la columna 'respuesta' con una de las opciones: Perdido · Redujo mucho · Activo · Pausa: volvió después · No sé.",
              "'Pausa: volvió después' = dejó de comprar en esos meses pero ha vuelto a contratar más tarde: no lo da por perdido.",
              "'Redujo mucho' = sigue comprando, pero bastante menos que en la misma época del año anterior.",
              "Use su conocimiento de la cuenta. No hay respuestas correctas: se compara su criterio con el de la regla.",
              "Algunos anunciantes aparecen en las hojas de los tres comerciales: respóndalos sin consultar a los demás."]:
        ws0.append([t])
    ws0["A1"].font = Font(name="Arial", bold=True, size=13); ws0.column_dimensions["A"].width = 120
    cab = PatternFill("solid", fgColor="1F4E5F")
    for com in sorted(s.comercial_asignado.unique()):
        sub = s[(s.comercial_asignado == com) | s.compartido]
        ws = wb.create_sheet(com)
        trims = list(fac.columns)
        ws.append(["id_caso", "anunciante", "categoría"] + [f"fact. {t} (€)" for t in trims] + [f"campañas {t}" for t in trims] +
                  ["última campaña", "último contacto", "respuesta", "comentario"])
        for x in ws[1]: x.font = Font(name="Arial", bold=True, color="FFFFFF", size=10); x.fill = cab; x.alignment = Alignment(wrap_text=True)
        for r in sub.itertuples():
            ws.append([r.id_caso, r.razon_social, r.categoria] + [round(float(v)) for v in fac.loc[r.id_cliente]] +
                      [int(v) for v in cam.loc[r.id_cliente]] +
                      [ult[r.id_cliente].date() if pd.notna(ult[r.id_cliente]) else None,
                       ultc[r.id_cliente].date() if pd.notna(ultc[r.id_cliente]) else None, None, None])
        dv = DataValidation(type="list", formula1='"' + ",".join(RESPUESTAS) + '"', allow_blank=True)
        col = 3 + 2 * len(trims) + 3
        from openpyxl.utils import get_column_letter as L
        dv.add(f"{L(col)}2:{L(col)}{ws.max_row}"); ws.add_data_validation(dv)
        for c in range(1, ws.max_column + 1): ws.column_dimensions[L(c)].width = 13
        ws.column_dimensions["B"].width = 28; ws.column_dimensions[L(col + 1)].width = 40; ws.freeze_panes = "D2"
    wb.save(os.path.join(salida, "muestra_comerciales.xlsx"))
    return s


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--datos", default="data"); ap.add_argument("--config", default="config/etiqueta.json"); ap.add_argument("--salida", default="resultados")
    a = ap.parse_args(); os.makedirs(a.salida, exist_ok=True)
    cfg = json.load(open(a.config, encoding="utf-8"))
    fact = pd.read_csv(os.path.join(a.datos, "fact_campanas.csv"), parse_dates=["fecha_emision"]); fact["fe"] = fact.fecha_emision
    inter = pd.read_csv(os.path.join(a.datos, "fact_interacciones.csv"), parse_dates=["fecha"]); inter["fe"] = inter.fecha
    cli = pd.read_csv(os.path.join(a.datos, "dim_clientes.csv")).set_index("id_cliente")
    rgt = os.path.join(a.datos, "validacion", "aux_ground_truth.csv")
    gt = pd.read_csv(rgt, parse_dates=["fecha_baja_real"]) if os.path.exists(rgt) else None
    ini = inicios_de_campana(fact)
    e = calcular(fact, ini, cfg)
    r, comp, reac, ctrl = resumen(e, gt)
    e.to_csv(os.path.join(a.salida, "etiqueta_e2_por_corte.csv"), index=False)
    with pd.ExcelWriter(os.path.join(a.salida, "validacion_etiqueta_e2.xlsx")) as xl:
        r.to_excel(xl, sheet_name="Tipos por corte"); comp.to_excel(xl, sheet_name="E2 frente a regla A")
        reac.to_excel(xl, sheet_name="Reactivacion"); ctrl.to_frame().to_excel(xl, sheet_name="Archivo validacion")
    s = muestra(e, cli, fact, ini, inter, cfg, a.salida)
    print("Tipos E2 por corte:\n", r.to_string(), "\n\nE2 frente a regla A:\n", comp.to_string(),
          "\n\nReactivación de las pérdidas totales:\n", reac.round(3).to_string(),
          "\n\nMuestra para comerciales:", len(s), "casos;", int(s.compartido.sum()), "compartidos.",
          "Clave guardada aparte en clave_muestra_NO_ENTREGAR.csv")


if __name__ == "__main__":
    main()
