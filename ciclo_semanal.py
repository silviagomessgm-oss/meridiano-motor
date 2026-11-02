"""
Meridiano · Ciclo SEMANAL del churn de anunciantes (los martes por la mañana; sin CRM).

Decisión del equipo: el riesgo se calcula cada martes para que las propuestas no lleguen todas a la vez.
La fecha de corte es el lunes anterior (datos cerrados). Cada semana:
  1. Comprueba las tablas (columnas, fechas e integridad).
  2. Validación automática de E2 con las confirmaciones acumuladas de los comerciales (historico/).
  3. Puntuaciones L2 con la etiqueta vigente (E2, o A si la validación automática no la confirma).
  4. Propuestas de retención: 12 acciones de mayor valor esperado (4 por comercial), sin repetir cuentas
     propuestas o en control en los últimos 90 días (historico/propuestas_historico.csv).
  5. Cuadro de mando en Excel.
Los resultados quedan en salidas/<fecha_corte>/.

Uso:
    python ciclo_semanal.py --fecha_corte 2026-09-28
    python ciclo_semanal.py --fecha_corte 2026-09-28 --plan_devuelto plan_rellenado.xlsx   # registra antes las confirmaciones
"""
import argparse, json, os, shutil, subprocess, sys
import numpy as np, pandas as pd

RAIZ = os.path.dirname(os.path.abspath(__file__))
TABLAS = os.path.join(RAIZ, "tablas"); HIST = os.path.join(RAIZ, "historico")
EV = os.path.join(RAIZ, "evaluacion"); PR = os.path.join(RAIZ, "propuestas")
COLUMNAS = {"dim_clientes": ["id_cliente", "categoria", "tamano", "fecha_alta", "comercial_asignado"],
            "dim_productos": ["id_producto", "familia", "es_producto_compromiso"],
            "dim_comercial": ["id_comercial", "nombre"],
            "fact_campanas": ["id_orden", "id_cliente", "id_producto", "familia", "fecha_emision", "importe_eur", "impresiones", "clics", "id_campana"],
            "fact_facturacion": ["id_factura", "id_cliente", "id_orden", "importe_eur", "fecha_emision", "fecha_vencimiento", "fecha_cobro", "estado"],
            "fact_interacciones": ["id_interaccion", "id_cliente", "fecha", "tipo", "resultado"],
            "oportunidades": ["id_oportunidad", "id_cliente", "id_lead", "fecha_envio", "fecha_cierre", "desenlace"]}


def paso(n, texto): print(f"\n=== {n}. {texto} ===", flush=True)


def ejecutar(cmd, cwd):
    r = subprocess.run([sys.executable] + cmd, cwd=cwd, capture_output=True, text=True)
    salida = "\n".join(l for l in (r.stdout + r.stderr).splitlines() if "Warning" not in l)
    print(salida[-3000:])
    if r.returncode != 0:
        raise SystemExit(f"Falló: {' '.join(cmd)}")


def comprobar_tablas(T):
    t = {n: pd.read_csv(os.path.join(TABLAS, n + ".csv")) for n in COLUMNAS}
    errores = [f"{n}: faltan {sorted(set(c) - set(t[n].columns))}" for n, c in COLUMNAS.items() if not set(c) <= set(t[n].columns)]
    f, fa = t["fact_campanas"], t["fact_facturacion"]
    if not set(f.id_cliente) <= set(t["dim_clientes"].id_cliente): errores.append("órdenes con cliente inexistente")
    if not set(fa.id_orden) <= set(f.id_orden): errores.append("facturas con orden inexistente")
    if abs(f.importe_eur.sum() - fa.importe_eur.sum()) > 0.01: errores.append("facturación de campañas ≠ facturas")
    if f.id_orden.duplicated().any(): errores.append("órdenes duplicadas")
    ultima = pd.to_datetime(f.fecha_emision).max()
    if errores:
        raise SystemExit("Tablas con errores: " + "; ".join(errores))
    print(f"Tablas correctas. Última emisión: {ultima.date()}. Anunciantes: {len(t['dim_clientes'])}. Órdenes: {len(f)}")
    if ultima > T:
        print(f"AVISO: hay datos posteriores a la fecha de corte ({ultima.date()}). Ejecución retrospectiva: "
              "cada paso usa solo los datos hasta la fecha de corte.")


def config_temporal(origen, destino, cambios):
    c = json.load(open(origen, encoding="utf-8")); c.update(cambios)
    json.dump(c, open(destino, "w", encoding="utf-8"), ensure_ascii=False, indent=1); return destino


def registrar_propuestas(T, sal, ruta):
    """Histórico de cuentas propuestas y en control por ciclo (para el enfriamiento). Repetir un ciclo lo sustituye."""
    plan = pd.read_excel(os.path.join(sal, "propuestas_retencion.xlsx"), sheet_name=None)
    nuevo = pd.concat([plan["Plan_por_comercial"].assign(estado_plan="propuesto"), plan["Grupo_control"].assign(estado_plan="control")])
    nuevo = nuevo[["id_cliente", "estado_plan"]].assign(fecha_corte=T.date())
    if os.path.exists(ruta):
        viejo = pd.read_csv(ruta, dtype={"id_cliente": str}); viejo = viejo[viejo.fecha_corte != str(T.date())]
        nuevo = pd.concat([viejo, nuevo])
    nuevo.to_csv(ruta, index=False)


def cuadro_de_mando(T, sal, estado):
    sys.path.insert(0, os.path.join(EV, "src"))
    from etiqueta_e2 import etiqueta_e2
    from evaluar_umbral_abandono import inicios_de_campana
    f = pd.read_csv(os.path.join(TABLAS, "fact_campanas.csv"), parse_dates=["fecha_emision"]); f["fe"] = f.fecha_emision
    ini = inicios_de_campana(f)
    Tm = T - pd.Timedelta(days=210)                          # último corte con ventana de 210 días cerrada
    vivos = f[(f.fe > Tm - pd.Timedelta(days=365)) & (f.fe <= Tm)].id_cliente.unique()
    e = etiqueta_e2(f, ini, Tm, 210, 0.5, vivos)
    n = len(e); pt = (e.tipo_e2 == "perdida_total").sum(); ct = (e.tipo_e2 == "contraccion").sum()
    fact_perdida = e.loc[e.tipo_e2 != "activo", "fact_W_anio_anterior"].sum() - e.loc[e.tipo_e2 == "contraccion", "fact_W"].sum()
    plan = pd.read_excel(os.path.join(sal, "propuestas_retencion.xlsx"), sheet_name=None)
    prop = plan["Plan_por_comercial"]; apl = plan["Aplazados"]; ctl = plan["Grupo_control"]
    hist = os.path.join(HIST, "confirmaciones_historico.csv")
    n_conf = int(pd.read_csv(hist).estado_confirmado_comercial.notna().sum()) if os.path.exists(hist) else 0
    kpis = [("Fecha de corte", str(T.date())),
            ("Etiqueta de abandono vigente", estado.get("etiqueta_vigente", "E2")),
            ("Estado de la validación automática", estado.get("estado", "Sin confirmaciones todavía: E2 vigente por decisión del equipo")),
            ("Confirmaciones de comerciales acumuladas", n_conf),
            (f"Churn E2 · corte {Tm.date()} (ventana cerrada) · anunciantes vivos", n),
            ("   Pérdida total", f"{pt} ({pt / n:.1%})"), ("   Contracción", f"{ct} ({ct / n:.1%})"),
            ("   Churn E2 total", f"{(pt + ct) / n:.1%}"),
            ("   Facturación perdida en la ventana frente al año anterior (€)", round(float(fact_perdida))),
            ("Propuestas de la semana", len(prop)), ("Aplazadas por capacidad", len(apl)), ("Grupo de control", len(ctl)),
            ("Facturación en riesgo de las propuestas (€)", round(float(prop.facturacion_en_riesgo.sum())))]
    por_com = prop.groupby("comercial_nombre").agg(propuestas=("id_cliente", "size"), facturacion_en_riesgo=("facturacion_en_riesgo", "sum"))
    por_tipo = pd.crosstab(prop.accion_id, prop.tipo_riesgo, margins=True)
    with pd.ExcelWriter(os.path.join(sal, "cuadro_de_mando.xlsx")) as xl:
        pd.DataFrame(kpis, columns=["Indicador", "Valor"]).to_excel(xl, sheet_name="Resumen", index=False)
        por_com.to_excel(xl, sheet_name="Por comercial"); por_tipo.to_excel(xl, sheet_name="Acciones y tipo de riesgo")
        e.groupby(["tipo_e2", "motivo_e2"]).size().rename("anunciantes").to_frame().to_excel(xl, sheet_name="Churn E2 por motivo")
    print("\n".join(f"{k}: {v}" for k, v in kpis))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fecha_corte", required=True); ap.add_argument("--plan_devuelto", default=None)
    a = ap.parse_args(); T = pd.Timestamp(a.fecha_corte)
    sal = os.path.join(RAIZ, "salidas", str(T.date())); os.makedirs(sal, exist_ok=True); os.makedirs(HIST, exist_ok=True)
    hist = os.path.join(HIST, "confirmaciones_historico.csv")

    paso(1, "Comprobación de las tablas"); comprobar_tablas(T)
    if a.plan_devuelto:
        paso("1b", "Registro de las confirmaciones del plan devuelto")
        ejecutar(["src/confirmaciones.py", "--plan", os.path.abspath(a.plan_devuelto), "--historico", hist], PR)
    paso(2, "Validación automática de la etiqueta E2")
    estado_ruta = os.path.join(sal, "estado_etiqueta.json")
    if os.path.exists(hist):
        ejecutar(["src/validacion_automatica.py", "--datos", TABLAS, "--confirmaciones", hist, "--salida", sal], EV)
    else:
        json.dump({"etiqueta_vigente": "E2", "estado": "Sin confirmaciones todavía: E2 vigente por decisión del equipo", "casos": 0},
                  open(estado_ruta, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print("Sin confirmaciones todavía: E2 vigente por decisión del equipo")
    estado = json.load(open(estado_ruta, encoding="utf-8"))
    paso(3, f"Puntuaciones L2 (etiqueta vigente: {estado['etiqueta_vigente']})")
    prod = config_temporal(os.path.join(EV, "config", "produccion.json"), os.path.join(sal, "produccion_usada.json"), {"fecha_puntuacion": str(T.date())})
    ejecutar(["src/generar_scores.py", "--datos", TABLAS, "--produccion", prod, "--estado_etiqueta", estado_ruta, "--salida", sal], EV)
    paso(4, "Propuestas de retención")
    datos_pr = os.path.join(sal, "tablas_con_scores"); shutil.rmtree(datos_pr, ignore_errors=True); shutil.copytree(TABLAS, datos_pr)
    shutil.copy(os.path.join(sal, "scores_modelo.csv"), os.path.join(datos_pr, "scores_modelo.csv"))
    cfg = config_temporal(os.path.join(PR, "config", "parametros.json"), os.path.join(sal, "parametros_usados.json"), {"fecha_corte": str(T.date())})
    ph = os.path.join(HIST, "propuestas_historico.csv")
    dias = json.load(open(cfg, encoding="utf-8")).get("dias_enfriamiento", 90)
    po = os.path.join(HIST, "otras_etiquetas.csv")     # ampliación y seguimiento del panel (etiqueta única por empresa)
    partes = []
    if os.path.exists(ph):
        h = pd.read_csv(ph, parse_dates=["fecha_corte"], dtype={"id_cliente": str})
        partes.append(h[(h.fecha_corte < T) & (h.fecha_corte >= T - pd.Timedelta(days=dias))][["id_cliente"]])
    if os.path.exists(po):
        # incluye la misma semana: lo que el lunes ya propuso como ampliación no entra el martes en el plan de churn
        o = pd.read_csv(po, parse_dates=["fecha_corte"], dtype={"id_cliente": str})
        o = o[(o.fecha_corte <= T) & ((o.fecha_corte >= T - pd.Timedelta(days=dias)) | o.abierta.astype(bool))][["id_cliente"]]
        print(f"Con otra propuesta del panel (ampliación o seguimiento): {o.id_cliente.nunique()} anunciantes")
        partes.append(o)
    if partes:
        rec = pd.concat(partes).drop_duplicates()
        rec.to_csv(os.path.join(datos_pr, "propuestas_recientes.csv"), index=False)
        print(f"En enfriamiento ({dias} días): {rec.id_cliente.nunique()} anunciantes propuestos o en control")
    ejecutar(["src/propuestas.py", "--datos", datos_pr, "--config", cfg, "--salida", sal], PR)
    shutil.rmtree(datos_pr, ignore_errors=True)
    registrar_propuestas(T, sal, ph)
    paso(5, "Cuadro de mando"); cuadro_de_mando(T, sal, estado)
    print(f"\nCiclo completado. Resultados en salidas/{T.date()}/: propuestas_retencion.xlsx (plan por comercial), "
          "crm_tareas.csv, scores_modelo.csv, estado_etiqueta.json, cuadro_de_mando.xlsx")


if __name__ == "__main__":
    main()
