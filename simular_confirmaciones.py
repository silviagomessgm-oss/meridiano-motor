"""
Meridiano · SIMULACIÓN de las confirmaciones de los comerciales (solo para el TFG: los datos son ficticios y no hay comerciales).

Rellena las columnas de confirmación de un plan ya generado con lo que realmente ocurrió en las tablas
en los 210 días siguientes (etiqueta E2 de modelo_churn/etiqueta.py, la misma con la que se entrena el modelo) y añade un porcentaje de error configurable, para imitar el criterio humano.
Sirve para demostrar el circuito completo: plan → confirmaciones → validación automática de E2.

Uso:
    python simular_confirmaciones.py --plan salidas/2025-12-31/propuestas_retencion.xlsx --acierto 0.8 --salida plan_simulado.xlsx
"""
import argparse, os, sys
import numpy as np, pandas as pd

RAIZ = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, RAIZ)
from modelo_churn.datos import cargar_tablas
from modelo_churn.etiqueta import HORIZONTE_DIAS
from modelo_churn.validacion import clase_e2
sys.path.insert(0, os.path.join(RAIZ, "propuestas", "src"))
from propuestas import MOTIVO_CONFIRMABLE

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
    tablas = cargar_tablas(os.path.join(RAIZ, "tablas")); f = tablas["campanas"]
    fin_w = T + pd.Timedelta(days=HORIZONTE_DIAS)
    if fin_w > f.fecha_emision.max():
        raise SystemExit("La ventana de 210 días de este plan aún no se ha cerrado en las tablas: no se puede simular lo que pasó.")
    plan["id_cliente"] = plan.id_cliente.astype(str)
    clase = clase_e2(tablas, plan.id_cliente.unique(), T)
    vuelve = f[f.fecha_emision > fin_w].id_cliente.unique()
    estados = []
    for cid in plan.id_cliente:
        real = A_ESTADO[clase[cid]]
        if g.random() < a.acierto:
            est = real
        else:
            est = g.choice([x for x in A_ESTADO.values() if x != real])
        if est == "Perdido" and cid in vuelve and g.random() < 0.5:
            est = "Pausa: volvió después"
        estados.append(est)
    plan["estado_confirmado_comercial"] = estados
    plan["motivo_confirmado"] = [MOTIVO_CONFIRMABLE.get(m, "otro") if g.random() < a.acierto else g.choice(MOTIVOS)
                               for m in plan.motivo_principal]
    plan["diagnostico_correcto"] = np.where(g.random(len(plan)) < a.acierto, "Sí", "No")
    plan["comentario_comercial"] = "SIMULADO para el TFG"
    hojas["Plan_por_comercial"] = plan
    with pd.ExcelWriter(a.salida) as xl:
        for n, d in hojas.items(): d.to_excel(xl, sheet_name=n, index=False)
    print(f"Plan simulado: {len(plan)} confirmaciones (acierto {a.acierto:.0%}) en {a.salida}. Estados: {pd.Series(estados).value_counts().to_dict()}")


if __name__ == "__main__":
    main()
