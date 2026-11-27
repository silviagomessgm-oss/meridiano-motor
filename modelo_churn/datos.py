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
    "oportunidades": ("oportunidades", ["fecha_envio", "fecha_cierre"]),
}


def cargar_tablas(carpeta) -> dict:
    carpeta = Path(carpeta)
    tablas = {}
    for clave, (fichero, fechas) in _TABLAS.items():
        df = pd.read_csv(carpeta / f"{fichero}.csv", parse_dates=fechas)
        tablas[clave] = df.drop(columns=COLUMNAS_FOTO.get(clave, []), errors="ignore")
    # Datos ampliados: las facturas originales pendientes se cobran en un fichero aparte,
    # porque las filas originales se conservan byte a byte.
    posteriores = carpeta / "cobros_posteriores.csv"
    if posteriores.exists():
        cobros = pd.read_csv(posteriores, parse_dates=["fecha_cobro"]).set_index("id_factura")["fecha_cobro"]
        f = tablas["facturas"]
        hueco = f["fecha_cobro"].isna()
        f.loc[hueco, "fecha_cobro"] = f.loc[hueco, "id_factura"].map(cobros)
    return tablas


def fin_de_datos(tablas):
    """Última fecha con algún hecho registrado (no se puede puntuar después)."""
    return max(tablas["campanas"]["fecha_orden"].max(), tablas["facturas"]["fecha_emision"].max(),
               tablas["interacciones"]["fecha"].max(), tablas["oportunidades"]["fecha_envio"].max())


def vista_en(tablas, F):
    """Las tablas tal como existirían si se extrajeran el día F: nada registrado después de F.
    Un pedido firmado hasta F se conserva aunque su campaña se emita después; un cobro o el cierre de una
    propuesta posteriores a F todavía no habían ocurrido."""
    F = pd.Timestamp(F)
    f = tablas["facturas"][tablas["facturas"]["fecha_emision"] <= F].copy()
    f.loc[f["fecha_cobro"] > F, "fecha_cobro"] = pd.NaT
    o = tablas["oportunidades"][tablas["oportunidades"]["fecha_envio"] <= F].copy()
    abierta = o["fecha_cierre"] > F
    o.loc[abierta, "fecha_cierre"] = pd.NaT
    o.loc[abierta, "desenlace"] = None
    return {
        "clientes": tablas["clientes"][tablas["clientes"]["fecha_alta"] <= F].copy(),
        "campanas": tablas["campanas"][tablas["campanas"]["fecha_orden"] <= F].copy(),
        "facturas": f,
        "interacciones": tablas["interacciones"][tablas["interacciones"]["fecha"] <= F].copy(),
        "oportunidades": o,
    }
