"""Prueba de extremo a extremo del ciclo semanal (martes; corte el lunes anterior) sobre las tablas."""
import json, os, shutil, subprocess, sys
import pandas as pd
RAIZ = os.path.join(os.path.dirname(__file__), "..")
HIST = os.path.join(RAIZ, "historico")
ARCHIVOS_HIST = ["confirmaciones_historico.csv", "propuestas_historico.csv"]


def _run(*args):
    r = subprocess.run([sys.executable, *args], cwd=RAIZ, capture_output=True, text=True)
    assert r.returncode == 0, r.stdout[-2000:] + r.stderr[-2000:]
    return r.stdout


def _plan(fecha):
    return pd.read_excel(os.path.join(RAIZ, "salidas", fecha, "propuestas_retencion.xlsx"), sheet_name=None)


def test_ciclos_semanales_enfriamiento_y_vuelta_automatica_a_regla_A(tmp_path):
    for a in ARCHIVOS_HIST:
        if os.path.exists(os.path.join(HIST, a)): shutil.move(os.path.join(HIST, a), tmp_path / a)
    try:
        semanas = ["2025-12-01", "2025-12-08", "2025-12-15"]          # lunes: corte del ciclo de cada martes
        devuelto, vistos = None, set()
        for i, fecha in enumerate(semanas):
            _run("ciclo_semanal.py", "--fecha_corte", fecha, *(["--plan_devuelto", devuelto] if devuelto else []))
            pl = _plan(fecha); p = pl["Plan_por_comercial"]
            assert len(p) == 12 and (p.groupby("comercial_asignado").size() == 4).all()
            assert {"estado_confirmado_comercial", "tipo_riesgo"} <= set(p.columns)
            semana = set(p.id_cliente) | set(pl["Grupo_control"].id_cliente)
            assert not (semana & vistos)                               # enfriamiento: ninguna cuenta se repite
            vistos |= semana
            devuelto = str(tmp_path / f"sim{i}.xlsx")
            _run("simular_confirmaciones.py", "--plan", os.path.join(RAIZ, "salidas", fecha, "propuestas_retencion.xlsx"),
                 "--acierto", "0.3", "--salida", devuelto)
        _run("ciclo_semanal.py", "--fecha_corte", "2026-09-28", "--plan_devuelto", devuelto)
        est = json.load(open(os.path.join(RAIZ, "salidas", "2026-09-28", "estado_etiqueta.json"), encoding="utf-8"))
        assert est["casos"] >= 30 and est["etiqueta_vigente"] == "A"    # acuerdo bajo con ≥ 30 casos: vuelve sola a A
        sc = pd.read_csv(os.path.join(RAIZ, "salidas", "2026-09-28", "scores_modelo.csv"))
        assert (sc.etiqueta_entrenamiento == "A").all()
        assert os.path.exists(os.path.join(RAIZ, "salidas", "2026-09-28", "cuadro_de_mando.xlsx"))
        # Repetir un ciclo no duplica el histórico
        h = pd.read_csv(os.path.join(HIST, "propuestas_historico.csv"))
        assert not h.duplicated(["fecha_corte", "id_cliente"]).any()
    finally:
        for a in ARCHIVOS_HIST:
            if os.path.exists(os.path.join(HIST, a)): os.remove(os.path.join(HIST, a))
            if os.path.exists(tmp_path / a): shutil.move(tmp_path / a, os.path.join(HIST, a))
        shutil.rmtree(os.path.join(RAIZ, "salidas"), ignore_errors=True)
