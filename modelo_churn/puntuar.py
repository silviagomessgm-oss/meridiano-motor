"""Puntuación de abandono de anunciantes (contrato con el resto del sistema).

Uso:
  python modelo_churn/puntuar.py --datos tablas --fecha AAAA-MM-DD --salida <carpeta>

Genera <carpeta>/scores_modelo.csv con exactamente las columnas id_cliente, prob_abandono: una fila por anunciante
activo en la fecha (alguna campaña en los 12 meses anteriores), con la probabilidad de que abandone en los 210 días
siguientes (etiqueta E2).

Pasos:
  1. La fecha no puede ser posterior al último dato registrado.
  2. Solo se usan los datos tal como estaban en la fecha (nada posterior).
  3. Se entrena la regresión logística elegida en el punto de control 2 con todas las fechas de corte cuyo resultado
     se conoce en la fecha (W termina antes del día 1 del último mes con campañas emitidas), sin anunciantes con menos
     de un año desde el alta. La regularización se elige con validación temporal dentro de esos cortes.
  4. Se puntúa a todos los anunciantes activos, también a los nuevos.

Opcional: --intervenciones <CSV id_cliente,fecha> (cuentas en las que el equipo actuó: propuesta aprobada o enviada).
  Se excluyen del entrenamiento las observaciones (fecha de corte T, cuenta) con una intervención entre 90 días antes de
  T y el final de su ventana W: su resultado ya no es el «natural» y el modelo aprendería que una cuenta salvada no
  estaba en riesgo. Solo cuentan las intervenciones registradas hasta la fecha de puntuación. No cambia la salida.
"""
import argparse
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from modelo_churn.datos import cargar_tablas, fin_de_datos, vista_en  # noqa: E402
from modelo_churn.etiqueta import HORIZONTE_DIAS  # noqa: E402
from modelo_churn.modelos import ajustar, elegir_hiperparametros  # noqa: E402
from modelo_churn.panel import construir_panel  # noqa: E402
from modelo_churn.variables import VARIABLES_MODELO, calcular_variables  # noqa: E402

MODELO = "c_logistica"            # decisión de la alumna en el punto de control 2
DESCRIPCION_MODELO = "E2 · regresión logística (modelo_churn)"   # se guarda con cada propuesta en Supabase
COLUMNAS = ["id_cliente", "prob_abandono"]
FICHERO = "scores_modelo.csv"
DECIMALES = 6
DIAS_INTERVENCION_PREVIA = 90      # la misma ventana que usaba el sistema anterior


def leer_intervenciones(ruta):
    if ruta is None or not Path(ruta).exists():
        return None
    df = pd.read_csv(ruta, dtype={"id_cliente": str})
    return pd.DataFrame({"id_cliente": df["id_cliente"], "fecha": pd.to_datetime(df["fecha"]).dt.tz_localize(None)})


def excluir_intervenidas(panel, intervenciones, F):
    """Quita del entrenamiento las observaciones cuyo resultado pudo cambiar por una acción del equipo."""
    if intervenciones is None or intervenciones.empty:
        return panel, 0
    iv = intervenciones[intervenciones["fecha"] <= pd.Timestamp(F)]
    m = panel[["fecha_corte", "id_cliente"]].reset_index().merge(iv, on="id_cliente")
    desde = m["fecha_corte"] - pd.Timedelta(days=DIAS_INTERVENCION_PREVIA)
    hasta = m["fecha_corte"] + pd.Timedelta(days=HORIZONTE_DIAS)
    afectadas = m.loc[(m["fecha"] > desde) & (m["fecha"] <= hasta), "index"].unique()
    return panel.drop(index=afectadas), len(afectadas)


def puntuar(tablas, fecha, intervenciones=None):
    """Devuelve (scores, info). `tablas` es lo que devuelve cargar_tablas; `intervenciones`, lo de leer_intervenciones."""
    F = pd.Timestamp(fecha)
    fin = fin_de_datos(tablas)
    if F > fin:
        raise ValueError(f"La fecha de puntuación {F.date()} es posterior al último dato ({fin.date()}): "
                         "todas las cuentas parecerían inactivas. Actualiza los datos o usa una fecha anterior.")
    t = vista_en(tablas, F)
    emitidas = t["campanas"].loc[t["campanas"]["fecha_emision"] <= F, "fecha_emision"]
    limite = emitidas.max().to_period("M").to_timestamp()
    panel = construir_panel(t, limite=limite)
    panel, n_excluidas = excluir_intervenidas(panel, intervenciones, F)
    if panel.empty or panel["abandono"].nunique() < 2:
        raise ValueError(f"No hay fechas de corte con resultado conocido antes de {F.date()}")
    hiper, _ = elegir_hiperparametros(MODELO, panel)
    modelo = ajustar(MODELO, panel, **hiper)

    X = calcular_variables(t, F)
    prob = modelo.predict_proba(X[VARIABLES_MODELO])[:, 1]
    scores = (pd.DataFrame({"id_cliente": X["id_cliente"].astype(str), "prob_abandono": prob.round(DECIMALES)})
              .sort_values("id_cliente").reset_index(drop=True))[COLUMNAS]
    info = {
        "fecha": F.date(), "fin_de_datos": fin.date(),
        "cortes_entrenamiento": f"{panel['fecha_corte'].min().date()} a {panel['fecha_corte'].max().date()} "
                                f"({panel['fecha_corte'].nunique()} cortes, {len(panel)} obs.)",
        "observaciones_excluidas_por_intervencion": n_excluidas,
        "hiperparametros": hiper, "anunciantes_puntuados": len(scores),
    }
    info["_modelo"], info["_variables"] = modelo, X
    return scores, info


def detalle(scores, info):
    """Pesos del modelo y resumen de la puntuación (solo por pantalla; no cambia la salida del contrato)."""
    modelo, X = info["_modelo"], info["_variables"]
    nombres = list(VARIABLES_MODELO) + [f"sin_dato_{VARIABLES_MODELO[i]}" for i in modelo[0].indicator_.features_]
    coef = pd.Series(modelo[-1].coef_[0], index=nombres)
    pesos = pd.DataFrame({"peso (1 desv. típica)": coef.round(3), "× odds": np.exp(coef).round(2),
                          "1 desv. típica =": pd.Series(modelo[1].scale_, index=nombres).round(2)})
    print("\nPesos del modelo (ordenados por importancia):")
    print(pesos.reindex(coef.abs().sort_values(ascending=False).index).to_string())
    nuevos = X.set_index("id_cliente")["antiguedad_meses"] < 12
    s = scores.set_index("id_cliente")["prob_abandono"]
    print("\nResumen de la puntuación:")
    print(f"  anunciantes: {len(s)} (nuevos, < 12 meses desde el alta: {int(nuevos.reindex(s.index).sum())})")
    print(f"  probabilidad media: {s.mean():.3f}; mediana: {s.median():.3f}")
    print(f"  con probabilidad >= 0,5: {(s >= 0.5).sum()}; >= 0,8: {(s >= 0.8).sum()}")
    top = s.sort_values(ascending=False, kind="stable").head(12)
    print(f"  probabilidad de la cuenta nº 12 por riesgo: {top.iloc[-1]:.3f}")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--datos", required=True, help="Carpeta con las tablas (CSV)")
    ap.add_argument("--fecha", required=True, help="Fecha de puntuación AAAA-MM-DD")
    ap.add_argument("--salida", required=True, help="Carpeta donde escribir scores_modelo.csv")
    ap.add_argument("--intervenciones", default=None,
                    help="CSV id_cliente,fecha de cuentas en las que se actuó (se excluyen del entrenamiento)")
    ap.add_argument("--detalle", action="store_true", help="Muestra los pesos del modelo y un resumen (no cambia la salida)")
    a = ap.parse_args(argv)

    scores, info = puntuar(cargar_tablas(a.datos), a.fecha, leer_intervenciones(a.intervenciones))
    salida = Path(a.salida)
    salida.mkdir(parents=True, exist_ok=True)
    scores.to_csv(salida / FICHERO, index=False, float_format=f"%.{DECIMALES}f")
    for k, v in info.items():
        if not k.startswith("_"):
            print(f"{k}: {v}")
    if a.detalle:
        detalle(scores, info)
    print(f"Escrito {salida / FICHERO}")


if __name__ == "__main__":
    main()
