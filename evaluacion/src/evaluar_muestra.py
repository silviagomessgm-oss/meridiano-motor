"""
Meridiano · Evalúa la muestra ciega rellenada por los comerciales frente a la etiqueta E2.

Uso:
    python src/evaluar_muestra.py --muestra muestra_comerciales_rellena.xlsx --clave resultados/clave_muestra_NO_ENTREGAR.csv \
        --config config/etiqueta.json --salida resultados
"""
import argparse, json, os, itertools
import numpy as np, pandas as pd

MAPA = {"Perdido": "perdida_total", "Redujo mucho": "contraccion", "Activo": "activo", "Pausa: volvió después": "activo"}


def cohen_kappa(a, b):
    cats = sorted(set(a) | set(b)); n = len(a)
    if n == 0: return np.nan
    po = np.mean(np.asarray(a) == np.asarray(b))
    pe = sum((np.sum(np.asarray(a) == c) / n) * (np.sum(np.asarray(b) == c) / n) for c in cats)
    return (po - pe) / (1 - pe) if pe < 1 else np.nan


def leer(ruta):
    hojas = pd.read_excel(ruta, sheet_name=None)
    filas = []
    for com, df in hojas.items():
        if com == "Instrucciones": continue
        for r in df.itertuples():
            filas.append(dict(comercial=com, id_caso=r.id_caso, respuesta=getattr(r, "respuesta", None)))
    return pd.DataFrame(filas)


def evaluar(resp, clave, umbral):
    d = resp.merge(clave, on="id_caso")
    d["clase_comercial"] = d.respuesta.map(MAPA)
    validas = d[d.clase_comercial.notna()]
    propios = validas[validas.comercial == validas.comercial_asignado]          # cada caso, juzgado por su comercial
    acuerdo = float((propios.clase_comercial == propios.tipo_e2).mean()) if len(propios) else np.nan
    binario = float(((propios.clase_comercial != "activo") == (propios.tipo_e2 != "activo")).mean()) if len(propios) else np.nan
    por_tipo = propios.assign(ok=propios.clase_comercial == propios.tipo_e2).groupby("tipo_e2").ok.mean().rename("acuerdo")
    matriz = pd.crosstab(propios.tipo_e2, propios.clase_comercial, rownames=["E2"], colnames=["comercial"])
    comp = validas[validas.compartido].pivot_table(index="id_caso", columns="comercial", values="clase_comercial", aggfunc="first")
    kappas = [cohen_kappa(comp[a].dropna().loc[comp[[a, b]].dropna().index], comp[b].loc[comp[[a, b]].dropna().index])
              for a, b in itertools.combinations(comp.columns, 2)] if comp.shape[1] >= 2 else []
    kappa = float(np.nanmean(kappas)) if kappas else np.nan
    no_se = int((d.respuesta == "No sé").sum()); sin_resp = int(d.respuesta.isna().sum())
    pausas_en_perdidas = int(((propios.tipo_e2 == "perdida_total") & (propios.respuesta == "Pausa: volvió después")).sum())
    veredicto = ("VALIDADA" if acuerdo >= umbral else "NO VALIDADA") if not np.isnan(acuerdo) else "SIN DATOS"
    return dict(acuerdo_3_clases=acuerdo, acuerdo_abandono_si_no=binario, kappa_entre_comerciales=kappa,
                respuestas_no_se=no_se, sin_responder=sin_resp, perdidas_E2_que_el_comercial_ve_como_pausa=pausas_en_perdidas, n_evaluados=len(propios), veredicto=veredicto), por_tipo, matriz


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--muestra", required=True); ap.add_argument("--clave", default="resultados/clave_muestra_NO_ENTREGAR.csv")
    ap.add_argument("--config", default="config/etiqueta.json"); ap.add_argument("--salida", default="resultados")
    a = ap.parse_args(); cfg = json.load(open(a.config, encoding="utf-8"))
    res, por_tipo, matriz = evaluar(leer(a.muestra), pd.read_csv(a.clave), 0.70)
    with open(os.path.join(a.salida, "validacion_muestra.md"), "w", encoding="utf-8") as fh:
        fh.write("# Validación de la etiqueta E2 con la muestra de comerciales\n\n")
        fh.write(f"- Criterio registrado: {cfg['validacion']['criterio_aceptacion']}\n")
        for k, v in res.items(): fh.write(f"- {k}: {round(v, 3) if isinstance(v, float) else v}\n")
        fh.write("\n## Acuerdo por tipo\n\n" + por_tipo.round(3).to_frame().to_markdown() + "\n\n## Matriz E2 × comercial\n\n" + matriz.to_markdown() + "\n")
    print(open(os.path.join(a.salida, "validacion_muestra.md"), encoding="utf-8").read())


if __name__ == "__main__":
    main()
