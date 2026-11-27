"""Copia literal de modelo_churn/etiqueta.py (proyecto del modelo de la alumna), para que el generador calibre las señales
con la misma población y la misma etiqueta. Si cambia el original, hay que actualizar esta copia y regenerar.

Población, fechas de corte y etiqueta E2.

Convenciones (ver registro_decisiones.md):
- «Un año» y «12 meses» se cuentan en meses de calendario (DateOffset), no en
  365 días: todas las campañas tienen fecha_emision el día 1 de mes y, con el
  29-feb-2024, contar 365 días deja fuera un mes entero en algunos cortes.
- W = (T, T + 210 días]; W' = (T - 1 año, T - 1 año + 210 días].
- «Compra» y «factura» = campañas por fecha_emision e importe_eur.
"""
import pandas as pd

HORIZONTE_DIAS = 210
UN_ANIO = pd.DateOffset(years=1)


def ventana(T):
    T = pd.Timestamp(T)
    return T, T + pd.Timedelta(days=HORIZONTE_DIAS)


def ventana_anio_anterior(T):
    inicio = pd.Timestamp(T) - UN_ANIO
    return inicio, inicio + pd.Timedelta(days=HORIZONTE_DIAS)


def en(df, col, desde, hasta):
    """Filas con desde < df[col] <= hasta."""
    return df[(df[col] > desde) & (df[col] <= hasta)]


def poblacion(campanas, T):
    """Anunciantes con alguna campaña en los 12 meses anteriores a T (incluido T)."""
    T = pd.Timestamp(T)
    return pd.Index(sorted(en(campanas, "fecha_emision", T - UN_ANIO, T)["id_cliente"].unique()),
                    name="id_cliente")


def fechas_corte(campanas, limite_fin_w):
    """Fin de trimestre (mar, jun, sep, dic) con 12 meses de historia previa y
    con W terminando estrictamente antes de `limite_fin_w`."""
    inicio_datos = campanas["fecha_emision"].min()
    limite_fin_w = pd.Timestamp(limite_fin_w)
    candidatas = pd.date_range(inicio_datos, limite_fin_w, freq="QE-DEC")
    return [T for T in candidatas
            if T - UN_ANIO >= inicio_datos - pd.Timedelta(days=1)
            and ventana(T)[1] < limite_fin_w]


def etiquetar(campanas, clientes, T, regla_anio="W", fin_datos=None):
    """Etiqueta E2 para la población en T.

    regla_anio:
      "W"   -> «pasa un año entero sin comprar» se evalúa solo hasta el final de W.
      "365" -> además es pérdida total si no hay campaña en (T, T + 365 días];
               requiere fin_datos >= T + 365 días.
    """
    T = pd.Timestamp(T)
    ids = poblacion(campanas, T)
    c = campanas[campanas["id_cliente"].isin(ids)]
    w0, w1 = ventana(T)
    p0, p1 = ventana_anio_anterior(T)
    imp_w = en(c, "fecha_emision", w0, w1).groupby("id_cliente")["importe_eur"].agg(["size", "sum"])
    imp_p = en(c, "fecha_emision", p0, p1).groupby("id_cliente")["importe_eur"].agg(["size", "sum"])

    df = pd.DataFrame(index=ids)
    df["n_w"] = imp_w["size"].reindex(ids).fillna(0).astype(int)
    df["eur_w"] = imp_w["sum"].reindex(ids).fillna(0.0)
    df["n_wp"] = imp_p["size"].reindex(ids).fillna(0).astype(int)
    df["eur_wp"] = imp_p["sum"].reindex(ids).fillna(0.0)
    alta = clientes.set_index("id_cliente")["fecha_alta"].reindex(ids)
    df["nuevo"] = alta > T - UN_ANIO

    sin_anio = pd.Series(False, index=ids)
    if regla_anio == "365":
        fin = T + pd.Timedelta(days=365)
        if fin_datos is None or pd.Timestamp(fin_datos) < fin:
            raise ValueError(f"No hay datos hasta {fin.date()} para evaluar la regla de 365 días")
        compran = en(c, "fecha_emision", T, fin)["id_cliente"].unique()
        sin_anio = ~ids.isin(compran)
        sin_anio = pd.Series(sin_anio, index=ids)

    perdida = ((df.n_wp > 0) & (df.n_w == 0)) | sin_anio
    contraccion = (df.n_wp > 0) & (df.n_w > 0) & (df.eur_w < 0.5 * df.eur_wp)
    tipo = pd.Series("activo", index=ids)
    tipo[contraccion] = "contraccion"
    tipo[perdida] = "perdida_total"
    tipo[df.nuevo] = "nuevo_activo"
    tipo[df.nuevo & (df.n_w == 0)] = "nuevo_sin_campana"
    df["tipo"] = tipo
    df["abandono"] = tipo.isin(["perdida_total", "contraccion", "nuevo_sin_campana"]).astype(int)
    df.insert(0, "fecha_corte", T)
    return df.reset_index()
