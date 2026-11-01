"""
Meridiano · Sincronización entre Supabase (base de datos común de n8n y Lovable) y las tablas del motor.

  cargar          · carga desde los CSV (alternativa manual; lo normal es n8n W0 desde Google Sheets)
  bajar           · descarga las tablas de Supabase a tablas/ y las confirmaciones a historico/
  subir FECHA     · sube los resultados del ciclo (propuestas, estado de la etiqueta, KPIs) de salidas/FECHA/

Variables de entorno: SUPABASE_URL y SUPABASE_SERVICE_KEY (clave de servicio: solo en el servidor, nunca en el panel).
Sin esas variables funciona en MODO LOCAL: no hace nada y el ciclo usa las tablas locales.
"""
import json, math, os, sys
import pandas as pd

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TABLAS = os.path.join(RAIZ, "tablas"); HIST = os.path.join(RAIZ, "historico")
ORDEN_CARGA = ["dim_comercial", "dim_productos", "dim_clientes", "fact_campanas", "fact_facturacion",
               "fact_interacciones", "oportunidades", "contactos"]
COLS_PROPUESTA = ["fecha_corte", "id_cliente", "comercial_asignado", "comercial_nombre", "orden_comercial", "razon_social",
                  "categoria", "tipo_riesgo", "banda_riesgo", "prob_abandono", "valor_esperado_accion", "facturacion_en_riesgo",
                  "valor_cuenta", "cuenta_clave", "requiere_direccion", "motivo_principal", "motivo_secundario", "accion_id",
                  "producto_sugerido_nombre", "fecha_limite", "justificacion", "ficha_cuenta", "material_titulo",
                  "material_cuerpo", "notas_internas", "fuente_material"]
COLS_CONFIRMACION = ["id_cliente", "fecha_corte", "banda_riesgo", "motivo_principal", "estado_confirmado_comercial",
                     "motivo_confirmado", "diagnostico_correcto", "comentario_comercial"]


def modo_local():
    return not (os.environ.get("SUPABASE_URL") and os.environ.get("SUPABASE_SERVICE_KEY"))


def _cab(extra=None):
    k = os.environ["SUPABASE_SERVICE_KEY"]
    h = {"apikey": k, "Authorization": f"Bearer {k}", "Content-Type": "application/json"}
    h.update(extra or {}); return h


def _url(tabla): return f"{os.environ['SUPABASE_URL'].rstrip('/')}/rest/v1/{tabla}"


def limpiar(registros):
    """NaN -> null, numpy -> tipos nativos, fechas -> ISO."""
    out = []
    for r in registros:
        d = {}
        for k, v in r.items():
            if v is None or (isinstance(v, float) and math.isnan(v)): d[k] = None
            elif hasattr(v, "isoformat"): d[k] = v.isoformat()[:10] if "Timestamp" in type(v).__name__ or "date" in type(v).__name__ else v.isoformat()
            elif hasattr(v, "item"): d[k] = v.item()
            else: d[k] = v
        out.append(d)
    return out


def leer_tabla(tabla, filtro=""):
    import requests
    filas, desde, paso = [], 0, 1000
    while True:
        r = requests.get(f"{_url(tabla)}?select=*{filtro}", headers=_cab({"Range": f"{desde}-{desde + paso - 1}"}), timeout=60)
        r.raise_for_status(); lote = r.json(); filas += lote
        if len(lote) < paso: return pd.DataFrame(filas)
        desde += paso


def upsert(tabla, registros, conflicto=None, lote=500):
    import requests
    pref = "resolution=merge-duplicates,return=minimal"
    url = _url(tabla) + (f"?on_conflict={conflicto}" if conflicto else "")
    for i in range(0, len(registros), lote):
        r = requests.post(url, headers=_cab({"Prefer": pref}), data=json.dumps(limpiar(registros[i:i + lote])), timeout=120)
        if r.status_code >= 300:
            raise RuntimeError(f"Supabase {tabla}: {r.status_code} {r.text[:300]}")


def cargar():
    for t in ORDEN_CARGA:
        df = pd.read_csv(os.path.join(TABLAS, t + ".csv"))
        upsert(t, df.to_dict("records")); print(f"{t}: {len(df)} filas")


def bajar():
    if modo_local():
        print("Modo local: se usan las tablas de tablas/"); return
    for t in ORDEN_CARGA:
        df = leer_tabla(t); df.to_csv(os.path.join(TABLAS, t + ".csv"), index=False); print(f"{t}: {len(df)} filas")
    # El motor no guarda nada entre ejecuciones: el histórico se reconstruye cada vez desde Supabase
    asig = leer_tabla("asignaciones_ciclo")
    os.makedirs(HIST, exist_ok=True)
    if len(asig):
        asig[["id_cliente", "estado_plan", "fecha_corte"]].to_csv(os.path.join(HIST, "propuestas_historico.csv"), index=False)
    print(f"asignaciones de ciclos anteriores: {len(asig)}")
    conf = leer_tabla("propuestas", "&estado_tarea=eq.cerrada&etiqueta=eq.riesgo&estado_confirmado_comercial=not.is.null")
    os.makedirs(HIST, exist_ok=True)
    if len(conf):
        conf[COLS_CONFIRMACION].to_csv(os.path.join(HIST, "confirmaciones_historico.csv"), index=False)
    print(f"confirmaciones: {len(conf)}")


def subir(fecha):
    sal = os.path.join(RAIZ, "salidas", fecha)
    plan = pd.read_excel(os.path.join(sal, "propuestas_retencion.xlsx"), sheet_name="Plan_por_comercial")
    plan["fecha_corte"] = pd.to_datetime(plan.fecha_corte).dt.date
    plan["fecha_limite"] = pd.to_datetime(plan.fecha_limite).dt.date
    regs = plan[[c for c in COLS_PROPUESTA if c in plan.columns]].to_dict("records")   # sin columnas de confirmación
    est = json.load(open(os.path.join(sal, "estado_etiqueta.json"), encoding="utf-8"))
    kpis = pd.read_excel(os.path.join(sal, "cuadro_de_mando.xlsx"), sheet_name="Resumen")
    kregs = [{"fecha_corte": fecha, "indicador": str(r.Indicador).strip(), "valor": str(r.Valor)} for r in kpis.itertuples()]
    eregs = [{"fecha_corte": fecha, "etiqueta_vigente": est.get("etiqueta_vigente"), "estado": est.get("estado"),
              "casos": est.get("casos"), "acuerdo": est.get("acuerdo")}]
    asig = pd.concat([plan.assign(estado_plan="propuesto"),
                      pd.read_excel(os.path.join(sal, "propuestas_retencion.xlsx"), sheet_name="Grupo_control").assign(estado_plan="control")])
    aregs = asig[["id_cliente", "estado_plan"]].assign(fecha_corte=fecha).to_dict("records")
    if modo_local():
        print(f"Modo local: {len(regs)} propuestas, estado y {len(kregs)} KPIs listos para subir (no se sube nada)")
        return dict(propuestas=len(regs), kpis=len(kregs))
    upsert("propuestas", regs, "fecha_corte,id_cliente")
    upsert("asignaciones_ciclo", aregs, "fecha_corte,id_cliente")
    upsert("estado_etiqueta", eregs, "fecha_corte"); upsert("kpis_ciclo", kregs, "fecha_corte,indicador")
    upsert("ejecuciones", [{"origen": "motor", "estado": "ok", "detalle": {"fecha_corte": fecha, "propuestas": len(regs),
                                                                          "etiqueta": est.get("etiqueta_vigente")}}])
    print(f"Subidas {len(regs)} propuestas, estado de la etiqueta y {len(kregs)} KPIs")
    return dict(propuestas=len(regs), kpis=len(kregs))


if __name__ == "__main__":
    accion = sys.argv[1] if len(sys.argv) > 1 else ""
    if accion == "cargar": cargar()
    elif accion == "bajar": bajar()
    elif accion == "subir": subir(sys.argv[2])
    else: print(__doc__)
