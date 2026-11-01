"""
Meridiano · Validación continua de la etiqueta con las confirmaciones de los comerciales.

Cada mes, el comercial devuelve el plan (Plan_por_comercial) con el estado real del cliente, el motivo y si el
diagnóstico del automatismo era correcto. Este script acumula las confirmaciones y mide el acuerdo.

Uso:
    python src/confirmaciones.py --plan propuestas_retencion_devuelto.xlsx --historico resultados/confirmaciones_historico.csv
"""
import argparse, os
import pandas as pd

ESTADO_A_CLASE = {"Perdido": "abandono", "Redujo mucho": "abandono", "Activo": "activo", "Pausa: volvió después": "activo"}


def resumen(df):
    v = df[df.estado_confirmado_comercial.isin(ESTADO_A_CLASE)]
    pred = v.banda_riesgo.isin(["alta", "media"])          # todas las propuestas tienen riesgo: medimos si el comercial lo confirma
    conf = v.estado_confirmado_comercial.map(ESTADO_A_CLASE) == "abandono"
    diag = df[df.diagnostico_correcto.isin(["Sí", "No"])]
    mot = df[df.motivo_confirmado.notna()]
    return {"propuestas_confirmadas": int(len(v)),
            "riesgo_confirmado_por_el_comercial": float((pred & conf).sum() / max(len(v), 1)),
            "pausas_detectadas": int((v.estado_confirmado_comercial == "Pausa: volvió después").sum()),
            "diagnostico_correcto": float((diag.diagnostico_correcto == "Sí").mean()) if len(diag) else None,
            "motivo_coincide": float((mot.motivo_confirmado == mot.motivo_principal).mean()) if len(mot) else None}


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--plan", required=True)
    ap.add_argument("--historico", default="resultados/confirmaciones_historico.csv"); a = ap.parse_args()
    nuevo = pd.read_excel(a.plan, sheet_name="Plan_por_comercial")
    hist = pd.concat([pd.read_csv(a.historico), nuevo]) if os.path.exists(a.historico) else nuevo
    hist["fecha_corte"] = pd.to_datetime(hist.fecha_corte, format="mixed").dt.date.astype(str)   # un único formato de fecha
    hist = hist.drop_duplicates(["id_cliente", "fecha_corte"], keep="last")
    os.makedirs(os.path.dirname(a.historico) or ".", exist_ok=True); hist.to_csv(a.historico, index=False)
    for k, v in resumen(hist).items(): print(f"{k}: {round(v, 3) if isinstance(v, float) else v}")


if __name__ == "__main__":
    main()
