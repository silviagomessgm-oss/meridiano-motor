"""
Meridiano · Modelos de P(Activo) para la iteración 4.

P1 · ritmo propio (Gamma-Poisson empírico):
    El ritmo de campañas de cada anunciante se estima con su historial, completado con el ritmo
    de su sector con un peso equivalente a 1 compra. P(Activo) = probabilidad de observar un
    silencio de R semanas si siguiera activo a ese ritmo: (beta / (beta + R)) ** alpha.

L1 / L2 · regresión logística con regularización L2, implementada con scipy (sin dependencias nuevas).
"""
import numpy as np
from scipy.optimize import minimize


def p1_ritmo_propio(x, tx, R, ritmo_sector, peso_sector=1.0):
    """x: compras repetidas; tx: semanas entre primera y última actividad; R: semanas sin actividad;
    ritmo_sector: compras por semana de su sector (datos <= corte)."""
    x, tx, R, rs = (np.asarray(v, dtype=float) for v in (x, tx, R, ritmo_sector))
    alpha = x + peso_sector
    beta = tx + peso_sector / np.clip(rs, 1e-6, None)
    return (beta / (beta + R)) ** alpha


class Logistica:
    def __init__(self, lam=1.0):
        self.lam = lam

    def fit(self, X, y):
        X = np.asarray(X, float); y = np.asarray(y, float)
        self.mu, self.sd = X.mean(0), X.std(0); self.sd[self.sd == 0] = 1.0
        Z = np.c_[np.ones(len(X)), (X - self.mu) / self.sd]
        def nll(w):
            z = Z @ w
            return np.sum(np.logaddexp(0, z) - y * z) + 0.5 * self.lam * np.sum(w[1:] ** 2)
        def grad(w):
            p = 1 / (1 + np.exp(-(Z @ w)))
            g = Z.T @ (p - y); g[1:] += self.lam * w[1:]; return g
        self.w = minimize(nll, np.zeros(Z.shape[1]), jac=grad, method="L-BFGS-B").x
        return self

    def predict_proba(self, X):
        Z = np.c_[np.ones(len(X)), (np.asarray(X, float) - self.mu) / self.sd]
        return 1 / (1 + np.exp(-(Z @ self.w)))
