"""Regla sin excepción: ninguna variable puede usar datos posteriores a T."""
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from modelo_churn.datos import cargar_tablas
from modelo_churn.etiqueta import fechas_corte
from modelo_churn.panel import LIMITE_FIN_W
from modelo_churn.variables import calcular_variables

TABLAS = Path(__file__).resolve().parents[2] / "tablas"
DATOS = cargar_tablas(TABLAS)
CORTES = fechas_corte(DATOS["campanas"], LIMITE_FIN_W)


def _solo_hasta(tablas, T):
    """Copia de las tablas tal como existirían si se extrajeran el día T."""
    f = tablas["facturas"][tablas["facturas"]["fecha_emision"] <= T].copy()
    f.loc[f["fecha_cobro"] > T, "fecha_cobro"] = pd.NaT
    return {
        "clientes": tablas["clientes"][tablas["clientes"]["fecha_alta"] <= T].copy(),
        "campanas": tablas["campanas"][tablas["campanas"]["fecha_emision"] <= T].copy(),
        "facturas": f,
        "interacciones": tablas["interacciones"][tablas["interacciones"]["fecha"] <= T].copy(),
    }


def _con_futuro(tablas, T, seed=0):
    """Añade datos inventados posteriores a T que cambiarían cualquier variable con fuga."""
    rng = np.random.default_rng(seed)
    t = {k: v.copy() for k, v in tablas.items()}
    ids = t["campanas"]["id_cliente"].unique()
    despues = lambda n: T + pd.to_timedelta(rng.integers(1, 400, n), unit="D")
    n = 300

    camp = t["campanas"].sample(n, replace=True, random_state=seed).copy()
    camp["id_cliente"] = rng.choice(ids, n)
    camp["fecha_emision"] = despues(n)
    camp["fecha_orden"] = camp["fecha_emision"] - pd.Timedelta(days=10)
    camp["importe_eur"] *= 5
    camp["clics"] = camp["impresiones"]  # CTR del 100 %
    camp["id_orden"] = [f"FUT{i}" for i in range(n)]
    t["campanas"] = pd.concat([t["campanas"], camp], ignore_index=True)

    fac = t["facturas"].sample(n, replace=True, random_state=seed).copy()
    fac["id_cliente"] = rng.choice(ids, n)
    fac["fecha_emision"] = despues(n)
    fac["fecha_vencimiento"] = fac["fecha_emision"] + pd.Timedelta(days=30)
    fac["fecha_cobro"] = pd.NaT
    t["facturas"] = pd.concat([t["facturas"], fac], ignore_index=True)

    inter = []
    for tipo, resultado in [("Cambio de interlocutor", "Nuevo responsable de marketing"),
                            ("Reclamacion", "Sin resolver"), ("Llamada", "Contacto efectivo"),
                            ("Visita", "Interesado")]:
        inter.append(pd.DataFrame({"id_interaccion": [f"FUT-{tipo}-{i}" for i in range(n)],
                                   "id_cliente": rng.choice(ids, n), "fecha": despues(n),
                                   "tipo": tipo, "canal": "Entrante", "resultado": resultado,
                                   "comercial": "COM-01", "previa_al_alta": "No"}))
    t["interacciones"] = pd.concat([t["interacciones"], *inter], ignore_index=True)

    nuevo = t["clientes"].iloc[[0]].copy()
    nuevo["id_cliente"], nuevo["fecha_alta"] = "CFUT", T + pd.Timedelta(days=5)
    t["clientes"] = pd.concat([t["clientes"], nuevo], ignore_index=True)

    # Facturas emitidas antes de T pero cobradas después: el cobro no debe verse en T.
    f = t["facturas"]
    pendientes_en_T = (f["fecha_emision"] <= T) & (f["fecha_vencimiento"] <= T)
    f.loc[pendientes_en_T & f["fecha_cobro"].isna(), "fecha_cobro"] = T + pd.Timedelta(days=3)
    return t


@pytest.mark.parametrize("T", CORTES, ids=lambda T: str(T.date()))
def test_variables_no_cambian_con_datos_posteriores(T):
    referencia = calcular_variables(_solo_hasta(DATOS, T), T)
    pd.testing.assert_frame_equal(calcular_variables(DATOS, T), referencia, check_dtype=False)
    pd.testing.assert_frame_equal(calcular_variables(_con_futuro(DATOS, T), T), referencia, check_dtype=False)


def test_el_test_detecta_una_fuga():
    """Control del propio test: una variable que mira al futuro debe hacerlo fallar."""
    T = CORTES[0]

    def con_fuga(tablas, T):
        X = calcular_variables(tablas, T)
        total = tablas["campanas"].groupby("id_cliente")["importe_eur"].sum()
        X["valor_12m"] = X["id_cliente"].map(total)
        return X

    with pytest.raises(AssertionError):
        pd.testing.assert_frame_equal(con_fuga(_con_futuro(DATOS, T), T), con_fuga(_solo_hasta(DATOS, T), T))
