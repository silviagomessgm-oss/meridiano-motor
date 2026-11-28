"""Explicación de la puntuación de cada anunciante: qué variables de la regresión logística suben su riesgo.

La contribución de una variable a la puntuación de una cuenta es peso × valor estandarizado (con la misma imputación y
escala que usa el modelo). Es positiva cuando esa variable empuja la probabilidad por encima de la de una cuenta media y
negativa cuando la protege. Como el modelo es lineal en ese espacio, las contribuciones suman la puntuación (log-odds)
menos la de una cuenta media: son una explicación exacta, no una aproximación.

Las columnas «sin_dato_*» (indicadores de valor que falta) no se usan para el motivo: su lectura comercial es ambigua
(«sin cobros en 12 meses» suele ser un anunciante de temporada). Su efecto queda dentro de la probabilidad.

Con la contribución más alta de cada cuenta se decide el motivo comercial (MOTIVO_DE_VARIABLE), y con los valores de las
variables se escriben las pruebas que ve el comercial (texto_evidencia). Las reclamaciones sin resolver y las facturas
vencidas no entran en el modelo (decisiones 22 y 23), pero el plan las trata como reglas de negocio que mandan sobre el
motivo del modelo (propuestas/src/propuestas.py).
"""
import numpy as np
import pandas as pd

from .variables import VARIABLES_MODELO

# Motivo comercial de cada variable del modelo (cuando es la que más sube el riesgo de la cuenta).
MOTIVO_DE_VARIABLE = {
    "dias_sin_contacto": "perdida_contacto",
    "cambio_interlocutor_12m": "relacion_interlocutor",
    "pedidos_firmados_pendientes": "sin_pedido_firmado",
    "propuestas_abiertas": "sin_pedido_firmado",
    "valor_mismo_periodo_anio_anterior": "temporada",
    "tendencia": "presupuesto_inversion",
    "valor_12m": "presupuesto_inversion",
    "frecuencia_12m": "patron_compra",
    "n_familias_12m": "patron_compra",
    "ctr_relativo": "rendimiento_campanas",
    "retraso_medio_cobro_12m": "cobro_financiero",
    "propuestas_perdidas_12m": "propuestas_perdidas",
    "recencia_dias": "inactividad",
    "antiguedad_meses": "inactividad",
}
N_FACTORES = 3          # factores que se guardan por cuenta (los que más suben el riesgo)


def contribuciones(modelo, X):
    """DataFrame (id_cliente × variable del modelo) con la contribución de cada variable a la puntuación."""
    imputar, escalar, logistica = modelo[0], modelo[1], modelo[-1]
    Z = escalar.transform(imputar.transform(X[VARIABLES_MODELO]))
    nombres = list(VARIABLES_MODELO) + [f"sin_dato_{VARIABLES_MODELO[i]}" for i in imputar.indicator_.features_]
    c = pd.DataFrame(Z * logistica.coef_[0], columns=nombres, index=X["id_cliente"].astype(str).values)
    return c[list(VARIABLES_MODELO)]


def factores(modelo, X, n=N_FACTORES):
    """Una fila por cuenta: las n variables que más suben su riesgo (solo contribuciones positivas), su motivo y los
    valores de todas las variables del modelo (para escribir las pruebas)."""
    c = contribuciones(modelo, X)
    valores = X.set_index(X["id_cliente"].astype(str))[list(VARIABLES_MODELO)]
    filas = []
    for cid, fila in c.iterrows():
        positivas = fila[fila > 0].sort_values(ascending=False, kind="stable").head(n)
        d = {"id_cliente": cid}
        for k in range(n):
            var = positivas.index[k] if k < len(positivas) else None
            d[f"factor_{k + 1}"] = var
            d[f"contribucion_{k + 1}"] = round(float(positivas.iloc[k]), 4) if var else np.nan
        motivos = []
        for var in positivas.index:
            m = MOTIVO_DE_VARIABLE[var]
            if m not in motivos:
                motivos.append(m)
        d["motivo_modelo"] = motivos[0] if motivos else "desconocido"
        d["motivo_modelo_secundario"] = motivos[1] if len(motivos) > 1 else None
        filas.append(d)
    out = pd.DataFrame(filas).set_index("id_cliente")
    return out.join(valores.add_prefix("var_")).reset_index().sort_values("id_cliente").reset_index(drop=True)


def _eur(x):
    return f"{x:,.0f} €".replace(",", ".")


def texto_evidencia(variable, v):
    """Frase con el dato que el comercial puede comprobar. `v` es el valor de la variable (misma definición que el
    modelo). Devuelve None si el valor no aporta nada que decir."""
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "sin ningún contacto comercial con respuesta registrado" if variable == "dias_sin_contacto" else None
    v = float(v)
    textos = {
        "dias_sin_contacto": f"{v:.0f} días sin contacto comercial con respuesta",
        "cambio_interlocutor_12m": "cambio de interlocutor en los últimos 12 meses" if v > 0 else None,
        "pedidos_firmados_pendientes": "sin ningún pedido firmado pendiente de emitir" if v == 0 else
                                       f"{v:.0f} pedido(s) firmado(s) pendiente(s) de emitir",
        "propuestas_abiertas": "sin propuestas abiertas" if v == 0 else f"{v:.0f} propuesta(s) abierta(s)",
        "valor_mismo_periodo_anio_anterior": f"compró {_eur(v)} en el mismo periodo del año pasado" if v > 0 else None,
        "tendencia": f"inversión de los últimos 6 meses un {abs(v) * 100:.0f} % {'por debajo' if v < 0 else 'por encima'} "
                     "del semestre anterior" if v != 0 else "inversión de los últimos 6 meses igual a la del semestre anterior",
        "valor_12m": f"facturación de los últimos 12 meses {_eur(v)}",
        "frecuencia_12m": f"{v:.0f} campaña(s) en los últimos 12 meses",
        "n_familias_12m": f"{v:.0f} familia(s) de producto en los últimos 12 meses",
        "ctr_relativo": f"sus campañas digitales consiguen el {v * 100:.0f} % de los clics esperados en esos productos",
        "retraso_medio_cobro_12m": f"retraso medio de cobro de {v:.0f} días",
        "propuestas_perdidas_12m": f"{v:.0f} propuesta(s) perdida(s) o sin respuesta en 12 meses" if v > 0 else None,
        "recencia_dias": f"última campaña hace {v:.0f} días",
        "antiguedad_meses": f"cliente desde hace {v:.0f} meses",
    }
    return textos.get(variable)
