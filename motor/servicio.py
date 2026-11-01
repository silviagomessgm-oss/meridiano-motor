"""
Meridiano · Un ciclo del motor: bajar de Supabase → ciclo semanal → subir a Supabase → resumen para n8n.
Lo usan la acción de GitHub (motor/ejecutar_ciclo.py) y, como alternativa, el servicio HTTP (motor/app.py).
"""
import json, os, subprocess, sys
import pandas as pd

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "motor"))
import sync_supabase as sync

CAMPOS = ["id_cliente", "comercial_asignado", "comercial_nombre", "razon_social", "categoria", "tipo_riesgo", "accion_id",
          "motivo_principal", "producto_sugerido_nombre", "notas_internas", "material_titulo", "material_cuerpo"]


def lunes_anterior(hoy=None):
    hoy = pd.Timestamp(hoy or pd.Timestamp.now(tz="Europe/Madrid").date())
    atras = (hoy.weekday() % 7) or 7                     # lunes anterior (un lunes, el de la semana pasada)
    return str((hoy - pd.Timedelta(days=atras)).date())


def ejecutar(fecha_corte=None):
    fecha = str(pd.Timestamp(fecha_corte).date()) if fecha_corte else lunes_anterior()
    sync.bajar()
    r = subprocess.run([sys.executable, "ciclo_semanal.py", "--fecha_corte", fecha], cwd=RAIZ, capture_output=True, text=True)
    print(r.stdout[-6000:]); print(r.stderr[-3000:], file=sys.stderr)
    if r.returncode != 0:
        raise RuntimeError("El ciclo semanal ha fallado: " + (r.stdout + r.stderr)[-1500:])
    subido = sync.subir(fecha)
    sal = os.path.join(RAIZ, "salidas", fecha)
    estado = json.load(open(os.path.join(sal, "estado_etiqueta.json"), encoding="utf-8"))
    plan = pd.read_excel(os.path.join(sal, "propuestas_retencion.xlsx"), sheet_name="Plan_por_comercial")
    propuestas = json.loads(plan[CAMPOS].to_json(orient="records", force_ascii=False))
    # Contexto para la IA con el mismo formato que N06 (propuestas.material_llm): n8n lo envía tal cual
    # y el validador comprueba que cada cifra del borrador está en este texto.
    correos = pd.read_csv(os.path.join(RAIZ, "tablas", "dim_comercial.csv")).set_index("id_comercial").correo.to_dict()
    for d, (_, r) in zip(propuestas, plan.iterrows()):
        d["fecha_corte"] = fecha; d["correo_comercial"] = correos.get(r.comercial_asignado)
        d["contexto_ia"] = (f"Anunciante: {r.razon_social} ({r.categoria}). Acción: {r.accion_id}. Motivo: {r.motivo_principal}. "
                            f"Producto sugerido: {r.producto_sugerido_nombre}. Próxima temporada: {r.get('proxima_ventana_mes', '')}. "
                            f"Datos: {r.get('evidencias', '')}")
    return {"ok": True, "fecha_corte": fecha, "etiqueta_vigente": estado.get("etiqueta_vigente"),
            "estado_etiqueta": estado.get("estado"), "propuestas": len(plan), "subido": subido,
            "modo": "local" if sync.modo_local() else "supabase", "detalle_propuestas": propuestas}
