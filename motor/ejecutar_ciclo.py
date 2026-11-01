"""
Meridiano · Ejecución del motor desde GitHub Actions (o a mano).
  python motor/ejecutar_ciclo.py --fecha_corte 2026-09-28 --salida resultado.json
Sin --fecha_corte usa el lunes anterior. Escribe siempre el JSON de salida, también si falla ({"ok": false, "error": ...}),
para que n8n reciba el motivo. Exige Supabase (SUPABASE_URL y SUPABASE_SERVICE_KEY) salvo con --local.
"""
import argparse, json, os, sys, traceback
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sync_supabase as sync
import servicio

ap = argparse.ArgumentParser()
ap.add_argument("--fecha_corte", default=""); ap.add_argument("--salida", default="resultado.json")
ap.add_argument("--local", action="store_true", help="usar tablas/*.csv sin Supabase (pruebas)")
a = ap.parse_args()
try:
    if sync.modo_local() and not a.local:
        raise RuntimeError("Faltan los secretos SUPABASE_URL y SUPABASE_SERVICE_KEY (Settings → Secrets and variables → Actions)")
    res = servicio.ejecutar(a.fecha_corte.strip() or None); codigo = 0
except Exception as e:
    traceback.print_exc()
    res = {"ok": False, "fecha_corte": a.fecha_corte or None, "error": f"{type(e).__name__}: {e}"[:1500]}; codigo = 1
json.dump(res, open(a.salida, "w", encoding="utf-8"), ensure_ascii=False)
print(json.dumps({k: v for k, v in res.items() if k != "detalle_propuestas"}, ensure_ascii=False))
sys.exit(codigo)
