"""Tests de la explicación de la puntuación (motivo y pruebas de cada cuenta salen del modelo)."""
import numpy as np
import pandas as pd
import pytest

from modelo_churn.datos import cargar_tablas
from modelo_churn.explicar import MOTIVO_DE_VARIABLE, N_FACTORES, contribuciones, factores, texto_evidencia
from modelo_churn.puntuar import puntuar
from modelo_churn.variables import VARIABLES_MODELO
from test_puntuar import DATOS, FECHA_CLI


@pytest.fixture(scope="module")
def modelo():
    scores, info = puntuar(DATOS, FECHA_CLI)
    return scores, info["_modelo"], info["_variables"]


def test_todas_las_variables_tienen_motivo():
    assert set(MOTIVO_DE_VARIABLE) == set(VARIABLES_MODELO)


def test_contribuciones_explican_exactamente_la_puntuacion(modelo):
    """Contribuciones (variables + indicadores de dato que falta) + término independiente = log-odds del modelo."""
    _, m, X = modelo
    imputar, escalar, log = m[0], m[1], m[-1]
    Z = escalar.transform(imputar.transform(X[VARIABLES_MODELO]))
    total = (Z * log.coef_[0]).sum(axis=1) + log.intercept_[0]
    np.testing.assert_allclose(total, m.decision_function(X[VARIABLES_MODELO]), rtol=1e-9, atol=1e-9)
    c = contribuciones(m, X)
    assert list(c.columns) == list(VARIABLES_MODELO) and len(c) == len(X)


def test_factores_una_fila_por_cuenta_puntuada(modelo):
    scores, m, X = modelo
    f = factores(m, X)
    assert sorted(f.id_cliente) == sorted(scores.id_cliente.astype(str)) and f.id_cliente.is_unique


def test_motivo_es_el_de_la_variable_que_mas_sube_el_riesgo(modelo):
    _, m, X = modelo
    f = factores(m, X).set_index("id_cliente")
    c = contribuciones(m, X)
    for cid, r in f.iterrows():
        if isinstance(r.factor_1, str):
            assert r.factor_1 == c.loc[cid].idxmax() and c.loc[cid].max() > 0
            assert r.motivo_modelo == MOTIVO_DE_VARIABLE[r.factor_1]
        else:
            assert r.motivo_modelo == "desconocido" and (c.loc[cid] <= 0).all()
        valores = [r[f"contribucion_{k}"] for k in range(1, N_FACTORES + 1) if pd.notna(r[f"contribucion_{k}"])]
        assert all(v > 0 for v in valores) and valores == sorted(valores, reverse=True)
        assert r.motivo_modelo_secundario != r.motivo_modelo


def test_pruebas_con_datos_comprobables():
    assert texto_evidencia("dias_sin_contacto", 120) == "120 días sin contacto comercial con respuesta"
    assert "sin ningún contacto" in texto_evidencia("dias_sin_contacto", np.nan)
    assert texto_evidencia("pedidos_firmados_pendientes", 0) == "sin ningún pedido firmado pendiente de emitir"
    assert texto_evidencia("tendencia", -0.45) == "inversión de los últimos 6 meses un 45 % por debajo del semestre anterior"
    assert texto_evidencia("valor_mismo_periodo_anio_anterior", 12500) == "compró 12.500 € en el mismo periodo del año pasado"
    assert texto_evidencia("cambio_interlocutor_12m", 0) is None
    for v in VARIABLES_MODELO:
        assert texto_evidencia(v, 1.0) is None or isinstance(texto_evidencia(v, 1.0), str)


def test_puntuar_escribe_la_explicacion(tmp_path):
    import subprocess, sys
    from test_puntuar import DATOS_CLI, SCRIPT
    subprocess.run([sys.executable, str(SCRIPT), "--datos", str(DATOS_CLI), "--fecha", FECHA_CLI, "--salida", str(tmp_path)],
                   check=True, capture_output=True)
    s = pd.read_csv(tmp_path / "scores_modelo.csv"); e = pd.read_csv(tmp_path / "explicacion_modelo.csv")
    assert list(s.columns) == ["id_cliente", "prob_abandono"]          # el contrato no cambia
    assert sorted(e.id_cliente.astype(str)) == sorted(s.id_cliente.astype(str))
    assert {"motivo_modelo", "factor_1", "var_dias_sin_contacto"} <= set(e.columns)
