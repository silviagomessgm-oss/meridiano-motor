"""Las cuatro opciones de modelo y el ajuste de sus hiperparámetros con validación temporal.

Todas exponen la misma interfaz de scikit-learn (fit / predict_proba) y una función `puntuacion` para ordenar:
- Referencias (a) y (b): ordenan por una sola variable. Para poder medir su calibración, el orden se convierte en
  probabilidad con una regresión isotónica creciente ajustada en entrenamiento (no cambia el orden).
- (c) Regresión logística con regularización L2; (d) árbol de decisión de 3 niveles como máximo.
"""
import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.impute import SimpleImputer
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier

from .variables import VARIABLES_MODELO

SEMILLA = 42
N_PLIEGUES = 4   # últimos cortes de entrenamiento usados para elegir hiperparámetros
REJILLA = {
    "c_logistica": {"C": [0.01, 0.03, 0.1, 0.3, 1.0, 3.0]},
    "d_arbol": {"min_samples_leaf": [10, 20, 40, 80]},
}
NOMBRES = {
    "a_valor": "(a) Referencia: valor de la cuenta",
    "b_recencia": "(b) Referencia: días sin campaña",
    "c_logistica": "(c) Regresión logística",
    "d_arbol": "(d) Árbol de decisión (3 niveles)",
}


class ReferenciaUnaVariable(BaseEstimator, ClassifierMixin):
    """Ordena por una variable (mayor = más riesgo) y calibra ese orden con una isotónica creciente."""

    def __init__(self, variable):
        self.variable = variable

    def fit(self, X, y):
        self.iso_ = IsotonicRegression(increasing=True, out_of_bounds="clip").fit(X[self.variable], y)
        self.classes_ = np.array([0, 1])
        return self

    def predict_proba(self, X):
        p = np.clip(self.iso_.predict(X[self.variable]), 0, 1)
        return np.column_stack([1 - p, p])


def construir(nombre, **hiper):
    imputar = lambda: SimpleImputer(strategy="median", add_indicator=True)
    if nombre == "a_valor":
        return ReferenciaUnaVariable("valor_12m")
    if nombre == "b_recencia":
        return ReferenciaUnaVariable("recencia_dias")
    if nombre == "c_logistica":
        return make_pipeline(imputar(), StandardScaler(),
                             LogisticRegression(C=hiper.get("C", 1.0), max_iter=5000, random_state=SEMILLA))
    if nombre == "d_arbol":
        return make_pipeline(imputar(), DecisionTreeClassifier(
            max_depth=3, min_samples_leaf=hiper.get("min_samples_leaf", 20), random_state=SEMILLA))
    raise ValueError(nombre)


def puntuacion(nombre, modelo, X):
    """Lo que se usa para ordenar. En las referencias, la variable cruda (el orden comercial puro)."""
    if nombre == "a_valor":
        return X["valor_12m"].to_numpy(dtype=float)
    if nombre == "b_recencia":
        return X["recencia_dias"].to_numpy(dtype=float)
    return modelo.predict_proba(X[VARIABLES_MODELO])[:, 1]


def ajustar(nombre, entreno, **hiper):
    X = entreno if nombre in ("a_valor", "b_recencia") else entreno[VARIABLES_MODELO]
    return construir(nombre, **hiper).fit(X, entreno["abandono"])


def elegir_hiperparametros(nombre, entreno):
    """Validación temporal dentro de entrenamiento: para cada uno de los últimos N_PLIEGUES cortes, se entrena con los
    cortes anteriores y se mide el AUC en ese corte. Se elige la combinación con mejor AUC medio."""
    if nombre not in REJILLA:
        return {}, None
    clave, valores = next(iter(REJILLA[nombre].items()))
    cortes = sorted(entreno["fecha_corte"].unique())
    pliegues = [V for V in cortes[-N_PLIEGUES:] if (entreno["fecha_corte"] < V).any()]
    filas = []
    for v in valores:
        aucs = []
        for V in pliegues:
            ent, val = entreno[entreno["fecha_corte"] < V], entreno[entreno["fecha_corte"] == V]
            m = ajustar(nombre, ent, **{clave: v})
            aucs.append(roc_auc_score(val["abandono"], puntuacion(nombre, m, val)))
        filas.append({clave: v, "AUC medio": np.mean(aucs), **{f"AUC {pd.Timestamp(V).date()}": a
                                                              for V, a in zip(pliegues, aucs)}})
    tabla = pd.DataFrame(filas)
    mejor = tabla.loc[tabla["AUC medio"].idxmax(), clave]
    return {clave: mejor.item() if hasattr(mejor, "item") else mejor}, tabla
