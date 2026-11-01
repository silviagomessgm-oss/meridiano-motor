"""
Meridiano · Etiqueta de abandono E2 (definición del equipo, config/etiqueta.json).

Para cada anunciante y fecha de corte T, con W = (T, T+210] y W' = (T−365, T−365+210]:
  pérdida total  · compró en W' y no inicia campaña en W (se salta su temporada), o
                   ninguna campaña en los 365 días que terminan al final de W (un año sin comprar)
  contracción    · compra en W y en W', pero factura en W menos del 50 % que en W'
  activo         · el resto (si no compró en W' ni en W está fuera de temporada: activo hasta ella)
  < 1 año de historial: regla A (pérdida total si no inicia campaña en W).
"""
import numpy as np
import pandas as pd


def etiqueta_e2(fact, inicios, T, H=210, umbral=0.5, poblacion=None):
    T = pd.Timestamp(T); fin_W = T + pd.Timedelta(days=H)
    Tp = T - pd.Timedelta(days=365); fin_Wp = Tp + pd.Timedelta(days=H)
    pasado = fact[fact.fe <= T]
    clientes = pasado.id_cliente.unique() if poblacion is None else np.asarray(poblacion)
    primera = inicios[inicios.fe <= T].groupby("id_cliente").fe.min().reindex(clientes)
    en = lambda df, a, b: df[(df.fe > a) & (df.fe <= b)]
    fac_W = en(fact, T, fin_W).groupby("id_cliente").importe_eur.sum().reindex(clientes).fillna(0)
    fac_Wp = en(fact, Tp, fin_Wp).groupby("id_cliente").importe_eur.sum().reindex(clientes).fillna(0)
    camp_W = en(inicios, T, fin_W).groupby("id_cliente").size().reindex(clientes).fillna(0)
    compra_Wp = en(fact, Tp, fin_Wp).groupby("id_cliente").size().reindex(clientes).fillna(0) > 0
    ult_anio = en(fact, fin_W - pd.Timedelta(days=365), fin_W).groupby("id_cliente").size().reindex(clientes).fillna(0) > 0
    con_historia = primera <= Tp
    activo_W = (fac_W > 0) | (camp_W > 0)
    tipo = pd.Series("activo", index=clientes, dtype=object); motivo = pd.Series("", index=clientes, dtype=object)
    # anunciantes con < 1 año: regla A
    nuevos = ~con_historia & (camp_W == 0)
    tipo[nuevos] = "perdida_total"; motivo[nuevos] = "menos de 1 año: sin campaña en 210 días"
    h = con_historia
    salta = h & compra_Wp & (camp_W == 0)
    anio = h & ~ult_anio
    tipo[salta | anio] = "perdida_total"
    motivo[salta] = "se salta su temporada"; motivo[anio & ~salta] = "un año sin comprar"
    contr = h & ~(salta | anio) & compra_Wp & activo_W & (fac_W < umbral * fac_Wp)
    tipo[contr] = "contraccion"; motivo[contr] = "factura < 50 % del mismo periodo del año anterior"
    fuera = h & ~(salta | anio | contr) & ~compra_Wp & ~activo_W
    motivo[fuera] = "fuera de temporada (activo hasta su temporada)"
    return pd.DataFrame({"id_cliente": clientes, "corte": T.date(), "tipo_e2": tipo.values, "motivo_e2": motivo.values,
                         "fact_W": fac_W.values, "fact_W_anio_anterior": fac_Wp.values, "campanas_W": camp_W.values,
                         "con_historia_1_anio": con_historia.values})
