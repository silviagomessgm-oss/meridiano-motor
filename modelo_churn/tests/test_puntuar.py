"""Tests del contrato de salida de puntuar.py."""
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

from modelo_churn.datos import cargar_tablas
from modelo_churn.etiqueta import poblacion
from modelo_churn.puntuar import COLUMNAS, FICHERO, puntuar
from test_no_fuga import _con_futuro, _solo_hasta

RAIZ = Path(__file__).resolve().parents[2]
SCRIPT = RAIZ / "modelo_churn" / "puntuar.py"
ORIGINALES = cargar_tablas(RAIZ / "tablas")
AMPLIADAS = RAIZ / "tablas_ampliadas"
DATOS_CLI = AMPLIADAS if AMPLIADAS.is_dir() else RAIZ / "tablas"
FECHA_CLI = "2026-09-30"


@pytest.fixture(scope="module")
def resultado():
    scores, _ = puntuar(cargar_tablas(DATOS_CLI), FECHA_CLI)
    return scores


@pytest.mark.parametrize("fecha", ["2025-12-31", "2026-03-15"])
def test_no_fuga_en_la_puntuacion(fecha):
    """Añadir datos posteriores a la fecha de puntuación no cambia nada (ni el entrenamiento ni las variables)."""
    F = pd.Timestamp(fecha)
    referencia, _ = puntuar(_solo_hasta(ORIGINALES, F), F)
    pd.testing.assert_frame_equal(puntuar(ORIGINALES, F)[0], referencia)
    pd.testing.assert_frame_equal(puntuar(_con_futuro(ORIGINALES, F), F)[0], referencia)


def test_probabilidades_entre_0_y_1(resultado):
    assert resultado["prob_abandono"].notna().all()
    assert resultado["prob_abandono"].between(0, 1).all()


def test_sin_clientes_duplicados(resultado):
    assert resultado["id_cliente"].is_unique


def test_columnas_exactas(resultado):
    assert list(resultado.columns) == COLUMNAS


def test_una_fila_por_anunciante_activo(resultado):
    t = cargar_tablas(DATOS_CLI)
    campanas = t["campanas"][t["campanas"]["fecha_emision"] <= pd.Timestamp(FECHA_CLI)]
    assert set(resultado["id_cliente"]) == set(poblacion(campanas, FECHA_CLI))


def test_identico_al_ejecutarlo_dos_veces(tmp_path):
    ficheros = []
    for i in (1, 2):
        salida = tmp_path / f"ejecucion_{i}"
        subprocess.run([sys.executable, str(SCRIPT), "--datos", str(DATOS_CLI), "--fecha", FECHA_CLI,
                        "--salida", str(salida)], check=True, capture_output=True, cwd=tmp_path)
        ficheros.append((salida / FICHERO).read_bytes())
    assert ficheros[0] == ficheros[1]
    assert ficheros[0].splitlines()[0] == b"id_cliente,prob_abandono"


def test_fecha_posterior_al_ultimo_dato_falla():
    with pytest.raises(ValueError, match="posterior al último dato"):
        puntuar(ORIGINALES, "2027-01-01")
