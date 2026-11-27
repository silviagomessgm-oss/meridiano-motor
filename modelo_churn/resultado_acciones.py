"""Resultado de las acciones de retención: qué cuentas salva el equipo comercial y cuáles no.

Para cada cuenta propuesta o en el grupo de control en un ciclo anterior (fecha de corte t), cuando su ventana
W = (t, t + 210 días] ya ha terminado en la fecha F:
  - grupo: «accion» (propuesta aprobada o enviada dentro de la ventana), «propuesta_sin_accion» (propuesta en la que no se
    llegó a actuar) o «control» (no recibió ninguna acción, elegida al azar);
  - resultado: etiqueta E2 en t (pérdida total, contracción o activo). Si la cuenta no estaba en la población del modelo
    (sin campaña en los 12 meses anteriores a t), el resultado es si volvió a comprar en W;
  - salvada: hubo acción y no abandonó.

El grupo de control se sortea solo entre las cuentas de banda de riesgo «media» (nunca alta ni cuentas clave), así que el
efecto de la acción se mide comparando acción y control DENTRO de la banda media (`efecto`); comparar todas las cuentas
con acción con el control mezclaría riesgos distintos. La tabla de aprendizaje
añade las variables del modelo de cada cuenta en t: es la base para entrenar, cuando haya casos suficientes, un modelo
de qué cuentas se pueden salvar.

Uso:
  python -m modelo_churn.resultado_acciones --datos tablas --historico historico --fecha AAAA-MM-DD --salida <carpeta>
"""
import argparse
from pathlib import Path

import pandas as pd

from .datos import cargar_tablas, vista_en
from .etiqueta import HORIZONTE_DIAS, en, etiquetar
from .variables import VARIABLES_MODELO, calcular_variables

GRUPOS = ["accion", "propuesta_sin_accion", "control"]
COLUMNAS = ["fecha_corte", "id_cliente", "grupo", "banda_riesgo", "resultado", "abandono", "salvada",
            "estado_confirmado_comercial", "fecha_resultado"]
BANDA_CONTROL = "media"      # banda en la que se sortea el grupo de control (propuestas/config/parametros.json)


def leer_historico(carpeta):
    carpeta = Path(carpeta)

    def leer(nombre, fechas):
        ruta = carpeta / nombre
        if not ruta.exists():
            return None
        df = pd.read_csv(ruta, dtype={"id_cliente": str})
        for c in fechas:
            df[c] = pd.to_datetime(df[c], utc=True, format="mixed").dt.tz_localize(None).dt.normalize()
        return df

    return {"asignaciones": leer("propuestas_historico.csv", ["fecha_corte"]),
            "intervenciones": leer("intervenciones.csv", ["fecha"]),
            "confirmaciones": leer("confirmaciones_historico.csv", ["fecha_corte"])}


def limite_resultados(t_vista, F):
    """Las ventanas tienen que terminar antes del día 1 del último mes con campañas emitidas (como en puntuar.py)."""
    emitidas = t_vista["campanas"].loc[t_vista["campanas"]["fecha_emision"] <= F, "fecha_emision"]
    return min(emitidas.max().to_period("M").to_timestamp(), F)


def resultados(tablas, historico, fecha):
    """Tabla de resultados con las ventanas cerradas en `fecha`. Solo usa datos e historial hasta esa fecha."""
    F = pd.Timestamp(fecha)
    asig = historico.get("asignaciones")
    if asig is None or asig.empty:
        return pd.DataFrame(columns=COLUMNAS)
    t_vista = vista_en(tablas, F)
    limite = limite_resultados(t_vista, F)
    asig = asig[asig["fecha_corte"] + pd.Timedelta(days=HORIZONTE_DIAS) < limite].drop_duplicates(["fecha_corte", "id_cliente"])
    if asig.empty:
        return pd.DataFrame(columns=COLUMNAS)
    iv = historico.get("intervenciones")
    iv = iv[iv["fecha"] <= F] if iv is not None else pd.DataFrame(columns=["id_cliente", "fecha"])
    camp = t_vista["campanas"]
    filas = []
    for t, g in asig.groupby("fecha_corte"):
        e2 = etiquetar(camp, t_vista["clientes"], t).set_index("id_cliente")
        w0, w1 = t, t + pd.Timedelta(days=HORIZONTE_DIAS)
        compran_w = set(en(camp, "fecha_emision", w0, w1)["id_cliente"])
        con_accion = set(iv.loc[(iv["fecha"] >= w0) & (iv["fecha"] <= w1), "id_cliente"])
        for r in g.itertuples():
            if r.id_cliente in e2.index:
                resultado = e2.at[r.id_cliente, "tipo"]
                abandono = int(e2.at[r.id_cliente, "abandono"])
            else:
                vuelve = r.id_cliente in compran_w
                resultado = "fuera_de_poblacion_volvio" if vuelve else "fuera_de_poblacion_sin_compra"
                abandono = int(not vuelve)
            grupo = "control" if r.estado_plan == "control" else (
                "accion" if r.id_cliente in con_accion else "propuesta_sin_accion")
            banda = getattr(r, "banda_riesgo", None)
            filas.append({"fecha_corte": t.date(), "id_cliente": r.id_cliente, "grupo": grupo,
                          "banda_riesgo": banda if isinstance(banda, str) else None, "resultado": resultado,
                          "abandono": abandono, "salvada": grupo == "accion" and abandono == 0, "fecha_resultado": w1.date()})
    res = pd.DataFrame(filas)
    conf = historico.get("confirmaciones")
    if conf is not None and not conf.empty:
        c = conf.assign(fecha_corte=conf["fecha_corte"].dt.date).drop_duplicates(["fecha_corte", "id_cliente"], keep="last")
        res = res.merge(c[["fecha_corte", "id_cliente", "estado_confirmado_comercial"]], on=["fecha_corte", "id_cliente"],
                        how="left")
    else:
        res["estado_confirmado_comercial"] = None
    return res[COLUMNAS].sort_values(["fecha_corte", "id_cliente"]).reset_index(drop=True)


def resumen(res):
    """Cuentas, % de abandono y cuentas salvadas por grupo."""
    filas = []
    for g in GRUPOS:
        d = res[res["grupo"] == g]
        filas.append({"grupo": g, "cuentas": len(d), "abandonos": int(d["abandono"].sum()),
                      "pct_abandono": round(100 * d["abandono"].mean(), 1) if len(d) else None,
                      "salvadas": int(d["salvada"].sum())})
    return pd.DataFrame(filas)


def efecto(res, banda=BANDA_CONTROL):
    """Abandono con acción frente a control en la misma banda de riesgo (la única comparación justa)."""
    d = res[res["banda_riesgo"] == banda]
    a, c = d[d["grupo"] == "accion"], d[d["grupo"] == "control"]
    pa = 100 * a["abandono"].mean() if len(a) else None
    pc = 100 * c["abandono"].mean() if len(c) else None
    return {"banda": banda, "cuentas_accion": len(a), "pct_abandono_accion": None if pa is None else round(pa, 1),
            "cuentas_control": len(c), "pct_abandono_control": None if pc is None else round(pc, 1),
            "diferencia_puntos": None if pa is None or pc is None else round(pc - pa, 1)}


def tabla_aprendizaje(tablas, res):
    """Resultados + variables del modelo de cada cuenta en su fecha de corte (para un futuro modelo de qué se salva)."""
    if res.empty:
        return res.assign(**{v: pd.Series(dtype=float) for v in VARIABLES_MODELO})
    partes = []
    for t, g in res.groupby("fecha_corte"):
        X = calcular_variables(tablas, pd.Timestamp(t)).drop(columns="fecha_corte")
        partes.append(g.merge(X, on="id_cliente", how="left"))
    return pd.concat(partes, ignore_index=True)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--datos", required=True)
    ap.add_argument("--historico", required=True)
    ap.add_argument("--fecha", required=True)
    ap.add_argument("--salida", required=True)
    a = ap.parse_args(argv)
    tablas = cargar_tablas(a.datos)
    res = resultados(tablas, leer_historico(a.historico), a.fecha)
    salida = Path(a.salida)
    salida.mkdir(parents=True, exist_ok=True)
    res.to_csv(salida / "resultado_acciones.csv", index=False)
    tabla_aprendizaje(vista_en(tablas, a.fecha), res).to_csv(salida / "aprendizaje_acciones.csv", index=False)
    print(resumen(res).to_string(index=False))
    print(efecto(res))


if __name__ == "__main__":
    main()
