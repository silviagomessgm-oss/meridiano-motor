"""
Meridiano · SIMULACIÓN de las confirmaciones de los comerciales (solo para el TFG: los datos son ficticios y no hay comerciales).

Rellena las columnas de confirmación de un plan ya generado con lo que realmente ocurrió en las tablas
en los 210 días siguientes (etiqueta E2) y añade un porcentaje de error configurable, para imitar el criterio humano.
Sirve para demostrar el circuito completo: plan → confirmaciones → validación automática de E2.

Uso:
    python simular_confirmaciones.py --plan salidas/2025-12-31/propuestas_retencion.xlsx --acierto 0.8 --salida plan_simulado.xlsx
"""
import argparse, os, sys
import numpy as np, pandas as pd

RAIZ = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(RAIZ, "evaluacion", "src"))
from etiqueta_e2 import etiqueta_e2
from evaluar_umbral_abandono import inicios_de_campana

A_ESTADO = {"perdida_total": "Perdido", "contraccion": "Redujo mucho", "activo": "Activo"}
MOTIVOS = ["rendimiento_campanas", "relacion_interlocutor", "perdida_contacto", "servicio_reclamacion",
           "presupuesto_inversion", "cobro_financiero", "temporada", "otro"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", required=True); ap.add_argument("--acierto", type=float, default=0.8)
    ap.add_argument("--salida", default="plan_simulado.xlsx"); ap.add_argument("--semilla", type=int, default=2026)
    a = ap.parse_args(); g = np.random.default_rng(a.semilla)
    hojas = pd.read_excel(a.plan, sheet_name=None); plan = hojas["Plan_por_comercial"]
    T = pd.Timestamp(plan.fecha_corte.iloc[0])
    f = pd.read_csv(os.path.join(RAIZ, "tablas", "fact_campanas.csv"), parse_dates=["fecha_emision"]); f["fe"] = f.fecha_emision
    if T + pd.Timedelta(days=210) > f.fe.max():
        raise SystemExit("La ventana de 210 días de este plan aún no se ha cerrado en las tablas: no se puede simular lo que pasó.")
    ini = inicios_de_campana(f)
    e = etiqueta_e2(f, ini, T, 210, 0.5, plan.id_cliente.unique()).set_index("id_cliente")
    vuelve = ini[ini.fe > T + pd.Timedelta(days=210)].id_cliente.unique()
    estados = []
    for cid in plan.id_cliente:
        real = A_ESTADO[e.at[cid, "tipo_e2"]]
        if g.random() < a.acierto:
            est = real
        else:
            est = g.choice([x for x in A_ESTADO.values() if x != real])
        if est == "Perdido" and cid in vuelve and g.random() < 0.5:
            est = "Pausa: volvió después"
        estados.append(est)
    plan["estado_confirmado_comercial"] = estados
    plan["motivo_confirmado"] = [m if g.random() < a.acierto else g.choice(MOTIVOS) for m in plan.motivo_principal]
    plan["diagnostico_correcto"] = np.where(g.random(len(plan)) < a.acierto, "Sí", "No")
    plan["comentario_comercial"] = "SIMULADO para el TFG"
    hojas["Plan_por_comercial"] = plan
    with pd.ExcelWriter(a.salida) as xl:
        for n, d in hojas.items(): d.to_excel(xl, sheet_name=n, index=False)
    print(f"Plan simulado: {len(plan)} confirmaciones (acierto {a.acierto:.0%}) en {a.salida}. Estados: {pd.Series(estados).value_counts().to_dict()}")


if __name__ == "__main__":
    main()
