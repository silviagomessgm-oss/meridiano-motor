"""
Meridiano · Validación automática de la etiqueta E2 (decisión del equipo, 25-oct-2026).

Para cada propuesta confirmada por un comercial (confirmaciones_historico.csv del automatismo de propuestas)
cuya ventana de 210 días ya se ha cerrado, calcula E2 en su fecha de corte y la compara con el estado que
confirmó el comercial. Con al menos `min_casos` casos:
  acuerdo >= umbral -> etiqueta vigente E2
  acuerdo <  umbral -> etiqueta vigente A (respaldo) y aviso para revisar la definición
Escribe resultados/estado_etiqueta.json, que lee generar_scores.py.

Uso:
    python src/validacion_automatica.py --datos data --confirmaciones confirmaciones_historico.csv --salida resultados
"""
import argparse, json, os
from datetime import datetime
import pandas as pd
from etiqueta_e2 import etiqueta_e2
from evaluar_umbral_abandono import inicios_de_campana


def comparar(conf, fact, ini, cfg):
    va = cfg["validacion_automatica"]; H = cfg["horizonte_dias"]
    conf = conf[conf.estado_confirmado_comercial.isin(va["mapa_respuestas"])].copy()
    conf["fecha_corte"] = pd.to_datetime(conf.fecha_corte, format="mixed")
    hoy = fact.fe.max()
    cerradas = conf[conf.fecha_corte + pd.Timedelta(days=H) <= hoy]
    filas = []
    for T, d in cerradas.groupby("fecha_corte"):
        e = etiqueta_e2(fact, ini, T, H, cfg["umbral_contraccion"], d.id_cliente.unique()).set_index("id_cliente")
        d = d.assign(tipo_e2=d.id_cliente.map(e.tipo_e2))
        filas.append(d)
    if not filas:
        return pd.DataFrame(columns=["id_cliente", "fecha_corte", "tipo_e2", "clase_comercial"]), len(conf), 0
    r = pd.concat(filas)
    r["clase_comercial"] = r.estado_confirmado_comercial.map(va["mapa_respuestas"])
    return r, len(conf), len(r)


def veredicto(r, cfg):
    va = cfg["validacion_automatica"]
    n = len(r)
    acuerdo = float((r.tipo_e2 == r.clase_comercial).mean()) if n else None
    if n < va["min_casos"]:
        vigente, estado = "E2", f"E2 vigente por decisión del equipo; validación en curso ({n} de {va['min_casos']} casos necesarios)"
    elif acuerdo >= va["umbral_acuerdo"]:
        vigente, estado = "E2", f"E2 VALIDADA con datos: acuerdo {acuerdo:.1%} en {n} casos"
    else:
        vigente, estado = va["etiqueta_respaldo"], (f"E2 NO VALIDADA: acuerdo {acuerdo:.1%} en {n} casos (< {va['umbral_acuerdo']:.0%}). "
                                                    "Vuelta automática a la regla A. Revisar la definición con el equipo")
    return dict(etiqueta_vigente=vigente, estado=estado, casos=n, acuerdo=acuerdo, fecha=datetime.now().isoformat(timespec="seconds"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--datos", default="data"); ap.add_argument("--confirmaciones", required=True)
    ap.add_argument("--config", default="config/etiqueta.json"); ap.add_argument("--salida", default="resultados")
    a = ap.parse_args(); os.makedirs(a.salida, exist_ok=True)
    cfg = json.load(open(a.config, encoding="utf-8"))
    fact = pd.read_csv(os.path.join(a.datos, "fact_campanas.csv"), parse_dates=["fecha_emision"]); fact["fe"] = fact.fecha_emision
    r, total, cerradas = comparar(pd.read_csv(a.confirmaciones), fact, inicios_de_campana(fact), cfg)
    v = veredicto(r, cfg); v.update(confirmaciones_validas=total, con_ventana_cerrada=cerradas)
    json.dump(v, open(os.path.join(a.salida, "estado_etiqueta.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    if len(r):
        pd.crosstab(r.tipo_e2, r.clase_comercial).to_csv(os.path.join(a.salida, "validacion_automatica_matriz.csv"))
    print(json.dumps(v, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
