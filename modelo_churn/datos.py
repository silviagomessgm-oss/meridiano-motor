"""Carga de las tablas del TFP.

Se eliminan al cargar las columnas que son una «foto» tomada al final del
periodo (y que, por tanto, contienen información posterior a cualquier fecha
de corte). Así es imposible usarlas por descuido.
"""
from pathlib import Path

import pandas as pd

# Columnas calculadas a fecha de extracción de los datos: fuga garantizada.
COLUMNAS_FOTO = {
    "clientes": ["antiguedad_meses"],          # se recalcula desde fecha_alta
    "facturas": ["estado", "dias_retraso"],    # se recalculan desde las fechas
}

_TABLAS = {
    "clientes": ("dim_clientes", ["fecha_alta"]),
    "campanas": ("fact_campanas", ["fecha_orden", "fecha_emision"]),
    "facturas": ("fact_facturacion", ["fecha_emision", "fecha_vencimiento", "fecha_cobro"]),
    "interacciones": ("fact_interacciones", ["fecha"]),
}


def cargar_tablas(carpeta) -> dict:
    carpeta = Path(carpeta)
    tablas = {}
    for clave, (fichero, fechas) in _TABLAS.items():
        df = pd.read_csv(carpeta / f"{fichero}.csv", parse_dates=fechas)
        tablas[clave] = df.drop(columns=COLUMNAS_FOTO.get(clave, []), errors="ignore")
    return tablas
