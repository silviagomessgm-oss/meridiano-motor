"""Panel de entrenamiento: una fila por (fecha de corte, anunciante)."""
import pandas as pd

from .etiqueta import etiquetar, fechas_corte
from .variables import calcular_variables

N_CORTES_PRUEBA = 2


def limite_fin_w(tablas):
    """W debe terminar antes del día 1 del último mes con campañas (con los datos
    del TFP: 1-sep-2026). Se calcula de los datos para que sirva si se amplían."""
    return tablas["campanas"]["fecha_emision"].max().to_period("M").to_timestamp()


def construir_panel(tablas, limite=None, regla_anio="W", excluir_nuevos=True):
    """excluir_nuevos: fuera los anunciantes con < 1 año desde el alta en T (decisión 21)."""
    filas = []
    for T in fechas_corte(tablas["campanas"], limite or limite_fin_w(tablas)):
        X = calcular_variables(tablas, T)
        y = etiquetar(tablas["campanas"], tablas["clientes"], T, regla_anio=regla_anio)
        filas.append(X.merge(y, on=["fecha_corte", "id_cliente"], how="inner", validate="1:1"))
    panel = pd.concat(filas, ignore_index=True)
    if excluir_nuevos:
        panel = panel[~panel["nuevo"]].reset_index(drop=True)
    return panel


def separar_entrenamiento_prueba(panel, n_prueba=N_CORTES_PRUEBA):
    cortes = sorted(panel["fecha_corte"].unique())
    prueba = set(cortes[-n_prueba:])
    es_prueba = panel["fecha_corte"].isin(prueba)
    return panel[~es_prueba].copy(), panel[es_prueba].copy()
