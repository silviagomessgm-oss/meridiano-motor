"""
Modelo BTYD: MBG/NBD (Batislam, Denizel y Filiztekin, 2007), variante del BG/NBD de Fader, Hardie y Lee (2005).

Supuestos del modelo, por anunciante:
  · Mientras está "vivo", inicia campañas según un proceso de Poisson de tasa lambda;
    lambda varía entre anunciantes según una Gamma(r, alpha).
  · Tras cada compra (también la primera) puede abandonar con probabilidad p;
    p varía entre anunciantes según una Beta(a, b).
Se elige MBG/NBD y no BG/NBD porque el BG/NBD da P(vivo) = 1 a quien solo ha comprado una vez,
y ~40 % de las observaciones de Meridiano son anunciantes con una sola campaña.

Entradas por anunciante (en semanas): x = compras repetidas, t_x = momento de la última actividad
desde la primera compra, T = antigüedad desde la primera compra hasta la fecha de corte.
"""
import numpy as np
from scipy.optimize import minimize
from scipy.special import gammaln, betaln


def log_verosimilitud(params, x, tx, T):
    r, alpha, a, b = np.exp(params)
    base = gammaln(r + x) - gammaln(r) + r * np.log(alpha)
    A = betaln(a, b + x + 1) - betaln(a, b) - (r + x) * np.log(alpha + T)
    B = betaln(a + 1, b + x) - betaln(a, b) - (r + x) * np.log(alpha + tx)
    return float(np.sum(base + np.logaddexp(A, B)))


LIMITE_LOG = 6.0        # parámetros acotados a [e^-6, e^6]
MARGEN_LOG = 0.5        # un parámetro a menos de 0,5 (en log) del límite se considera no identificado
INICIOS = [(0.5, 5.0, 0.5, 2.0), (2.0, 20.0, 1.0, 5.0), (1.0, 50.0, 0.3, 1.0), (5.0, 100.0, 2.0, 10.0), (0.2, 2.0, 0.1, 0.5)]


def ajustar(x, tx, T):
    """Máxima verosimilitud con varios puntos de partida y parámetros acotados.
    identificado = False si el óptimo queda en el borde: los datos no determinan los parámetros."""
    x, tx, T = (np.asarray(v, dtype=float) for v in (x, tx, T))
    mejor = None
    for ini in INICIOS:
        res = minimize(lambda p: -log_verosimilitud(p, x, tx, T), np.log(ini), method="L-BFGS-B",
                       bounds=[(-LIMITE_LOG, LIMITE_LOG)] * 4)
        if mejor is None or res.fun < mejor.fun:
            mejor = res
    r, alpha, a, b = np.exp(mejor.x)
    en_borde = bool(np.any(np.abs(mejor.x) > LIMITE_LOG - MARGEN_LOG))
    return dict(r=r, alpha=alpha, a=a, b=b, convergio=bool(mejor.success), loglik=-mejor.fun,
                identificado=bool(mejor.success and not en_borde))


def p_vivo(par, x, tx, T):
    x, tx, T = (np.asarray(v, dtype=float) for v in (x, tx, T))
    r, alpha, a, b = par["r"], par["alpha"], par["a"], par["b"]
    return 1.0 / (1.0 + (a / (b + x)) * ((alpha + T) / (alpha + tx)) ** (r + x))


def simular(n, r, alpha, a, b, T, semilla=0):
    """Genera anunciantes con el propio proceso MBG/NBD (para validar el ajuste)."""
    g = np.random.default_rng(semilla)
    lam = g.gamma(r, 1.0 / alpha, n); p = g.beta(a, b, n)
    x = np.zeros(n); tx = np.zeros(n)
    for i in range(n):
        t = 0.0
        while g.random() >= p[i]:            # sobrevive tras la compra
            t += g.exponential(1.0 / lam[i])
            if t > T: break
            x[i] += 1; tx[i] = t
    return x, tx, np.full(n, float(T))
