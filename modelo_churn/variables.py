"""Variables candidatas, calculadas SOLO con datos con fecha <= T.

La primera operación de `calcular_variables` es `recortar_a(T)`: todo lo que
viene después trabaja con la vista de los datos tal como estaban en T.
"""
import numpy as np
import pandas as pd

from .etiqueta import UN_ANIO, en, poblacion

SEIS_MESES = pd.DateOffset(months=6)
DIAS_MES = 30.4375
TIPOS_CONTACTO_COMERCIAL = {"Llamada", "Email comercial", "Visita", "Videollamada"}
FAMILIA_DIGITAL = "Digital"

VARIABLES = [
    "recencia_dias", "frecuencia_12m", "antiguedad_meses", "valor_12m", "tendencia",
    "n_familias_12m", "ctr_relativo", "cambio_interlocutor_12m",
    "reclamacion_sin_resolver_12m", "dias_sin_contacto",
    "facturas_vencidas_impagadas", "retraso_medio_cobro_12m",
    "pedidos_firmados_pendientes", "propuestas_abiertas", "propuestas_perdidas_12m",
]
DESENLACES_PERDIDOS = {"Perdida", "Muerta en silencio"}


def recortar_a(tablas, T):
    """Vista de las tablas en la fecha T: nada con fecha posterior a T."""
    T = pd.Timestamp(T)
    f = tablas["facturas"]
    f = f[f["fecha_emision"] <= T].copy()
    # Un cobro posterior a T todavía no había ocurrido en T.
    f.loc[f["fecha_cobro"] > T, "fecha_cobro"] = pd.NaT
    # Propuestas enviadas hasta T; si se cerraron después de T, en T seguían abiertas.
    o = tablas["oportunidades"]
    o = o[o["fecha_envio"] <= T].copy()
    cerrada_despues = o["fecha_cierre"] > T
    o.loc[cerrada_despues, "fecha_cierre"] = pd.NaT
    o.loc[cerrada_despues, "desenlace"] = None
    # Pedidos firmados hasta T: los emitidos son campañas; el resto, cartera pendiente.
    c = tablas["campanas"]
    firmados = c[c["fecha_orden"] <= T]
    return {
        "clientes": tablas["clientes"][tablas["clientes"]["fecha_alta"] <= T],
        "campanas": firmados[firmados["fecha_emision"] <= T],
        "pedidos_pendientes": firmados[firmados["fecha_emision"] > T],
        "facturas": f,
        "interacciones": tablas["interacciones"][tablas["interacciones"]["fecha"] <= T],
        "oportunidades": o,
    }


def _por_cliente(serie, ids, relleno):
    return serie.reindex(ids).fillna(relleno)


def calcular_variables(tablas, T):
    T = pd.Timestamp(T)
    t = recortar_a(tablas, T)
    camp, fact, inter, cli = t["campanas"], t["facturas"], t["interacciones"], t["clientes"]
    ids = poblacion(camp, T)
    hace12, hace6 = T - UN_ANIO, T - SEIS_MESES
    c12 = en(camp, "fecha_emision", hace12, T)
    out = pd.DataFrame(index=ids)

    # Comportamiento de compra
    ultima = camp.groupby("id_cliente")["fecha_emision"].max()
    out["recencia_dias"] = (T - ultima.reindex(ids)).dt.days
    out["frecuencia_12m"] = _por_cliente(c12.groupby("id_cliente").size(), ids, 0)
    alta = cli.set_index("id_cliente")["fecha_alta"].reindex(ids)
    out["antiguedad_meses"] = ((T - alta).dt.days / DIAS_MES).round(1)
    out["valor_12m"] = _por_cliente(c12.groupby("id_cliente")["importe_eur"].sum(), ids, 0.0)
    ult6 = _por_cliente(en(camp, "fecha_emision", hace6, T).groupby("id_cliente")["importe_eur"].sum(), ids, 0.0)
    ant6 = _por_cliente(en(camp, "fecha_emision", hace12, hace6).groupby("id_cliente")["importe_eur"].sum(), ids, 0.0)
    out["tendencia"] = ((ult6 - ant6) / np.maximum(ant6, 1.0)).clip(-1, 1)
    out["n_familias_12m"] = _por_cliente(c12.groupby("id_cliente")["familia"].nunique(), ids, 0)

    # CTR relativo: clics reales / clics esperados con el CTR medio de cada producto
    # (CTR medio calculado con todas las campañas digitales del producto hasta T).
    dig = camp[(camp["familia"] == FAMILIA_DIGITAL) & (camp["impresiones"] > 0)]
    ctr_prod = dig.groupby("id_producto")["clics"].sum() / dig.groupby("id_producto")["impresiones"].sum()
    d12 = en(dig, "fecha_emision", hace12, T).copy()
    d12["clics_esperados"] = d12["impresiones"] * d12["id_producto"].map(ctr_prod)
    g = d12.groupby("id_cliente")[["clics", "clics_esperados"]].sum()
    out["ctr_relativo"] = (g["clics"] / g["clics_esperados"]).reindex(ids)  # NaN = sin campañas digitales

    # Relación comercial
    i12 = en(inter, "fecha", hace12, T)
    cambio = i12.loc[i12["tipo"] == "Cambio de interlocutor", "id_cliente"].unique()
    out["cambio_interlocutor_12m"] = ids.isin(cambio).astype(int)
    recl = i12.loc[(i12["tipo"] == "Reclamacion") & (i12["resultado"] == "Sin resolver"), "id_cliente"].unique()
    out["reclamacion_sin_resolver_12m"] = ids.isin(recl).astype(int)
    contacto = inter[inter["tipo"].isin(TIPOS_CONTACTO_COMERCIAL) & (inter["resultado"] != "Sin respuesta")]
    ultimo_contacto = contacto.groupby("id_cliente")["fecha"].max().reindex(ids)
    out["dias_sin_contacto"] = (T - ultimo_contacto).dt.days  # NaN = ningún contacto registrado

    # Cobros
    vencidas = fact[(fact["fecha_vencimiento"] <= T) & fact["fecha_cobro"].isna()]
    out["facturas_vencidas_impagadas"] = _por_cliente(vencidas.groupby("id_cliente").size(), ids, 0)
    cobradas = en(fact.dropna(subset=["fecha_cobro"]), "fecha_cobro", hace12, T)
    retraso = (cobradas["fecha_cobro"] - cobradas["fecha_vencimiento"]).dt.days.clip(lower=0)
    out["retraso_medio_cobro_12m"] = retraso.groupby(cobradas["id_cliente"]).mean().reindex(ids)  # NaN = sin cobros

    # Actividad de venta
    out["pedidos_firmados_pendientes"] = _por_cliente(t["pedidos_pendientes"].groupby("id_cliente").size(), ids, 0)
    opo = t["oportunidades"]
    out["propuestas_abiertas"] = _por_cliente(opo[opo["fecha_cierre"].isna()].groupby("id_cliente").size(), ids, 0)
    perdidas = en(opo[opo["desenlace"].isin(DESENLACES_PERDIDOS)], "fecha_cierre", hace12, T)
    out["propuestas_perdidas_12m"] = _por_cliente(perdidas.groupby("id_cliente").size(), ids, 0)

    out = out[VARIABLES]
    out.insert(0, "fecha_corte", T)
    return out.reset_index()
