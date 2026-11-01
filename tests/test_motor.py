"""El motor HTTP en modo local (sin Supabase): lo que n8n llamará cada mes."""
import os, shutil, sys
import pytest
RAIZ = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, RAIZ)


@pytest.fixture
def cliente(monkeypatch):
    monkeypatch.delenv("SUPABASE_URL", raising=False); monkeypatch.delenv("SUPABASE_SERVICE_KEY", raising=False)
    monkeypatch.setenv("MOTOR_TOKEN", "secreto")
    from fastapi.testclient import TestClient
    from motor.app import app
    yield TestClient(app)
    shutil.rmtree(os.path.join(RAIZ, "salidas"), ignore_errors=True)
    ph = os.path.join(RAIZ, "historico", "propuestas_historico.csv")
    if os.path.exists(ph): os.remove(ph)


def test_salud(cliente):
    assert cliente.get("/salud").json() == {"estado": "ok", "modo": "local"}


def test_ciclo_exige_token(cliente):
    assert cliente.post("/ciclo", json={"fecha_corte": "2026-09-28"}).status_code == 401


def test_ciclo_devuelve_propuestas_para_n8n(cliente):
    r = cliente.post("/ciclo", json={"fecha_corte": "2026-09-28"}, headers={"X-Motor-Token": "secreto"})
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["propuestas"] == 12 and len(d["detalle_propuestas"]) == 12 and d["modo"] == "local"
    assert {"id_cliente", "material_cuerpo", "notas_internas", "comercial_asignado", "contexto_ia"} <= set(d["detalle_propuestas"][0])
    assert d["detalle_propuestas"][0]["contexto_ia"].startswith("Anunciante: ")


def test_limpieza_para_supabase():
    import math
    from motor import sync_supabase as s
    import pandas as pd, numpy as np
    r = s.limpiar([{"a": float("nan"), "b": np.int64(3), "c": pd.Timestamp("2026-09-28"), "d": "x"}])[0]
    assert r == {"a": None, "b": 3, "c": "2026-09-28", "d": "x"}


def test_ejecucion_desde_github_actions(tmp_path, monkeypatch):
    """motor/ejecutar_ciclo.py: sin secretos de Supabase no calcula y deja el motivo en el JSON; con --local calcula."""
    import subprocess, json
    monkeypatch.delenv("SUPABASE_URL", raising=False); monkeypatch.delenv("SUPABASE_SERVICE_KEY", raising=False)
    sal = tmp_path / "r.json"
    r = subprocess.run([sys.executable, "motor/ejecutar_ciclo.py", "--fecha_corte", "2026-09-28", "--salida", str(sal)],
                       cwd=RAIZ, capture_output=True, text=True)
    d = json.load(open(sal, encoding="utf-8"))
    assert r.returncode == 1 and not d["ok"] and "SUPABASE_URL" in d["error"]
    r = subprocess.run([sys.executable, "motor/ejecutar_ciclo.py", "--fecha_corte", "2026-09-28", "--local", "--salida", str(sal)],
                       cwd=RAIZ, capture_output=True, text=True)
    d = json.load(open(sal, encoding="utf-8"))
    assert r.returncode == 0 and d["ok"] and d["propuestas"] == 12 and len(d["detalle_propuestas"]) == 12
    shutil.rmtree(os.path.join(RAIZ, "salidas"), ignore_errors=True)
    ph = os.path.join(RAIZ, "historico", "propuestas_historico.csv")
    if os.path.exists(ph): os.remove(ph)


def test_lunes_anterior():
    from motor import servicio
    assert servicio.lunes_anterior("2026-09-29") == "2026-09-28" and servicio.lunes_anterior("2026-09-28") == "2026-09-21"
