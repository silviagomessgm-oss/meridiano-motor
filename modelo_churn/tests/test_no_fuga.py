"""Regla sin excepción: ninguna variable puede usar datos posteriores a T."""
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from modelo_churn.datos import cargar_tablas
from modelo_churn.etiqueta import fechas_corte
from modelo_churn.panel import limite_fin_w
from modelo_churn.variables import calcular_variables

RAIZ = Path(__file__).resolve().parents[2]
# Se comprueba con los datos originales (tablas_originales/) y con los actuales (tablas/, ampliados), en todas las fechas de corte
# posibles con cada conjunto (incluidas las que caen en la parte generada).
CONJUNTOS = {nombre: cargar_tablas(RAIZ / nombre)
             for nombre in ("tablas_originales", "tablas") if (RAIZ / nombre).is_dir()}
CASOS = [(nombre, T) for nombre, t in CONJUNTOS.items()
         for T in fechas_corte(t["campanas"], limite_fin_w(t))]
DATOS = CONJUNTOS["tablas"]
CORTES = fechas_corte(DATOS["campanas"], limite_fin_w(DATOS))


def _solo_hasta(tablas, T):
    """Copia de las tablas tal como existirían si se extrajeran el día T."""
    f = tablas["facturas"][tablas["facturas"]["fecha_emision"] <= T].copy()
    f.loc[f["fecha_cobro"] > T, "fecha_cobro"] = pd.NaT
    o = tablas["oportunidades"][tablas["oportunidades"]["fecha_envio"] <= T].copy()
    abierta = o["fecha_cierre"] > T
    o.loc[abierta, ["fecha_cierre", "desenlace"]] = [pd.NaT, None]
    return {
        "clientes": tablas["clientes"][tablas["clientes"]["fecha_alta"] <= T].copy(),
        # Un pedido firmado en T existe en T aunque la campaña se emita después.
        "campanas": tablas["campanas"][tablas["campanas"]["fecha_orden"] <= T].copy(),
        "facturas": f,
        "interacciones": tablas["interacciones"][tablas["interacciones"]["fecha"] <= T].copy(),
        "oportunidades": o,
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
    camp["fecha_orden"] = despues(n)
    camp["fecha_emision"] = camp["fecha_orden"] + pd.Timedelta(days=10)
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

    opo = t["oportunidades"].sample(n, replace=True, random_state=seed).copy()
    opo["id_cliente"] = rng.choice(ids, n)
    opo["fecha_envio"] = despues(n)
    opo["fecha_cierre"] = opo["fecha_envio"] + pd.Timedelta(days=20)
    opo["desenlace"] = "Perdida"
    opo["id_oportunidad"] = [f"FUT{i}" for i in range(n)]
    o = t["oportunidades"]
    # Propuestas abiertas en T: su desenlace futuro no puede verse en T.
    o.loc[o["fecha_cierre"] > T, "desenlace"] = "Perdida"
    t["oportunidades"] = pd.concat([o, opo], ignore_index=True)

    nuevo = t["clientes"].iloc[[0]].copy()
    nuevo["id_cliente"], nuevo["fecha_alta"] = "CFUT", T + pd.Timedelta(days=5)
    t["clientes"] = pd.concat([t["clientes"], nuevo], ignore_index=True)

    # Facturas emitidas antes de T pero cobradas después: el cobro no debe verse en T.
    f = t["facturas"]
    pendientes_en_T = (f["fecha_emision"] <= T) & (f["fecha_vencimiento"] <= T)
    f.loc[pendientes_en_T & f["fecha_cobro"].isna(), "fecha_cobro"] = T + pd.Timedelta(days=3)
    return t


@pytest.mark.parametrize("conjunto,T", CASOS, ids=[f"{n}-{T.date()}" for n, T in CASOS])
def test_variables_no_cambian_con_datos_posteriores(conjunto, T):
    datos = CONJUNTOS[conjunto]
    referencia = calcular_variables(_solo_hasta(datos, T), T)
    pd.testing.assert_frame_equal(calcular_variables(datos, T), referencia, check_dtype=False)
    pd.testing.assert_frame_equal(calcular_variables(_con_futuro(datos, T), T), referencia, check_dtype=False)


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
