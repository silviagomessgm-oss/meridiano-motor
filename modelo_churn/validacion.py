"""Validación de la etiqueta E2 con lo que confirman los comerciales, y etiqueta E2 de cualquier cuenta en una fecha.

Sustituye a evaluacion/src/validacion_automatica.py (decisión 78): la comparación usa la misma etiqueta con la que se
entrena el modelo (modelo_churn/etiqueta.py), no la de la evaluación antigua.

Para cada propuesta confirmada por un comercial (historico/confirmaciones_historico.csv) cuya ventana de 210 días ya ha
terminado, calcula la clase E2 en su fecha de corte y la compara con el estado que confirmó el comercial
(«Perdido» → pérdida total, «Redujo mucho» → contracción, «Activo» y «Pausa: volvió después» → activo). Con al menos
`min_casos` casos y un acuerdo menor que `umbral_acuerdo`, avisa para revisar la definición con el equipo. Es un
indicador del cuadro de mando: el modelo se entrena siempre con E2 (decisión de la alumna, 27-nov-2026), por eso ya no
hay vuelta automática a otra etiqueta.

Uso:
    python -m modelo_churn.validacion --datos tablas --confirmaciones historico/confirmaciones_historico.csv --salida <carpeta>
"""
import argparse
import json
from datetime import datetime
from pathlib import Path

import pandas as pd

from .datos import cargar_tablas, vista_en
from .etiqueta import HORIZONTE_DIAS, en, etiquetar
from .resultado_acciones import limite_resultados

PARAMETROS = {"min_casos": 30, "umbral_acuerdo": 0.7, "desviacion_comercial": 0.2, "min_casos_comercial": 5}
MAPA_RESPUESTAS = {"Perdido": "perdida_total", "Redujo mucho": "contraccion", "Activo": "activo",
                   "Pausa: volvió después": "activo"}       # «No sé» no cuenta
CLASE_DE_TIPO = {"perdida_total": "perdida_total", "contraccion": "contraccion", "activo": "activo",
                 "nuevo_activo": "activo", "nuevo_sin_campana": "perdida_total"}


def clase_e2(tablas, ids, T):
    """Clase E2 (perdida_total, contraccion, activo) de las cuentas `ids` en la fecha T, con las tablas dadas.
    Una cuenta fuera de la población del modelo (sin campaña en los 12 meses anteriores) es «activo» si compra en
    W = (T, T + 210 días] y «perdida_total» si no (mismo criterio que resultado_acciones.py)."""
    T = pd.Timestamp(T)
    e = etiquetar(tablas["campanas"], tablas["clientes"], T).set_index("id_cliente")
    compran = set(en(tablas["campanas"], "fecha_emision", T, T + pd.Timedelta(days=HORIZONTE_DIAS))["id_cliente"])
    return pd.Series({cid: CLASE_DE_TIPO[e.at[cid, "tipo"]] if cid in e.index else
                      ("activo" if cid in compran else "perdida_total") for cid in ids}, dtype=object)


def comparar(confirmaciones, tablas, fecha):
    """Confirmaciones válidas con su clase E2 (solo las de ventana cerrada en `fecha`)."""
    conf = confirmaciones[confirmaciones.estado_confirmado_comercial.isin(MAPA_RESPUESTAS)].copy()
    conf["fecha_corte"] = pd.to_datetime(conf.fecha_corte, format="mixed")
    conf["id_cliente"] = conf.id_cliente.astype(str)
    F = pd.Timestamp(fecha)
    t = vista_en(tablas, F)
    cerradas = conf[conf.fecha_corte + pd.Timedelta(days=HORIZONTE_DIAS) < limite_resultados(t, F)]
    filas = [d.assign(clase_e2=d.id_cliente.map(clase_e2(t, d.id_cliente.unique(), T)))
             for T, d in cerradas.groupby("fecha_corte")]
    if not filas:
        return pd.DataFrame(columns=["id_cliente", "fecha_corte", "clase_e2", "clase_comercial"]), len(conf)
    r = pd.concat(filas)
    r["clase_comercial"] = r.estado_confirmado_comercial.map(MAPA_RESPUESTAS)
    return r, len(conf)


def veredicto(r, p=PARAMETROS):
    n = len(r)
    acuerdo = float((r.clase_e2 == r.clase_comercial).mean()) if n else None
    if n < p["min_casos"]:
        validada, estado = None, f"Validación en curso ({n} de {p['min_casos']} casos necesarios)"
    elif acuerdo >= p["umbral_acuerdo"]:
        validada, estado = True, f"E2 VALIDADA con datos: acuerdo {acuerdo:.1%} en {n} casos"
    else:
        validada, estado = False, (f"E2 NO VALIDADA: acuerdo {acuerdo:.1%} en {n} casos (< {p['umbral_acuerdo']:.0%}). "
                                   "El modelo sigue con E2: revisar la definición con el equipo")
    # H4 (auditoría): acuerdo por comercial y aviso si alguno se aparta más de 20 puntos del resto
    por_comercial, aviso = {}, None
    if n and "comercial_asignado" in r.columns:
        ok = r.assign(ok=r.clase_e2 == r.clase_comercial)
        g = ok.groupby("comercial_asignado").ok.agg(["mean", "size"])
        por_comercial = {c: {"acuerdo": round(float(v["mean"]), 3), "casos": int(v["size"])} for c, v in g.iterrows()}
        avisos = []
        for c, v in g[g["size"] >= p["min_casos_comercial"]].iterrows():
            resto = ok[ok.comercial_asignado != c]
            if len(resto) and abs(v["mean"] - float(resto.ok.mean())) > p["desviacion_comercial"]:
                avisos.append(f"el acuerdo de {c} ({v['mean']:.0%}) se aparta más de 20 puntos del resto")
        aviso = ("; ".join(avisos) + ": revisar cómo confirman") if avisos else None
        aviso = aviso[0].upper() + aviso[1:] if aviso else None
    return dict(etiqueta_vigente="E2", validada=validada, estado=estado, casos=n, acuerdo=acuerdo,
                acuerdo_por_comercial=por_comercial, aviso_comercial=aviso,
                fecha=datetime.now().isoformat(timespec="seconds"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--datos", required=True); ap.add_argument("--confirmaciones", required=True)
    ap.add_argument("--fecha", required=True); ap.add_argument("--salida", required=True)
    a = ap.parse_args()
    salida = Path(a.salida); salida.mkdir(parents=True, exist_ok=True)
    r, validas = comparar(pd.read_csv(a.confirmaciones, dtype={"id_cliente": str}), cargar_tablas(a.datos), a.fecha)
    v = veredicto(r); v.update(confirmaciones_validas=validas, con_ventana_cerrada=len(r))
    json.dump(v, open(salida / "estado_etiqueta.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    if len(r):
        pd.crosstab(r.clase_e2, r.clase_comercial).to_csv(salida / "validacion_automatica_matriz.csv")
    print(json.dumps(v, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
