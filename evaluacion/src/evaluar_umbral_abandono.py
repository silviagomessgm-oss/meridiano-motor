"""
Meridiano · Evaluación de reglas de detección de abandono de anunciantes (iteración 2).

Compara reglas candidatas con un backtest por cortes trimestrales y las decide por valor neto
esperado (config/criterio.json, fijado antes de ejecutar). Verdad principal observable:
el anunciante no inicia ninguna campaña en los 210 días siguientes al corte.

Uso:
    python src/evaluar_umbral_abandono.py --datos data --config config/criterio.json --salida resultados
"""
import argparse, json, os
import numpy as np
import pandas as pd
import btyd
import p_activo

TIPOS_CONTACTO = {"Llamada", "Email comercial", "Visita", "Videollamada"}


# ----------------------------------------------------------------- funciones puras
def inicios_de_campana(fact):
    return (fact.sort_values("fe").groupby("id_campana")
            .agg(id_cliente=("id_cliente", "first"), fe=("fe", "min")).reset_index())


def ciclo_mediano(inicios):
    return (inicios.sort_values("fe").groupby("id_cliente").fe
            .apply(lambda s: s.diff().dt.days.median()))


def umbral(ciclo, tipo, parametro, minimo=210):
    if tipo in ("dias", "senales"):
        return pd.Series(float(parametro), index=ciclo.index)
    if tipo == "factor":
        return np.maximum(float(minimo), parametro * ciclo.fillna(0.0))
    raise ValueError(f"tipo de regla desconocido: {tipo}")


def senales_a_fecha(fact, inter, fact_fac, T, cfg_s):
    """Señales calculadas solo con datos <= T. Devuelve un DataFrame booleano por anunciante."""
    d = lambda n: T - pd.Timedelta(days=n)
    f = fact[fact.fe <= T]
    f6 = f[f.fe > d(182)].groupby("id_cliente").importe_eur.sum()
    f6p = f[(f.fe > d(365)) & (f.fe <= d(182))].groupby("id_cliente").importe_eur.sum()
    idx = f.id_cliente.unique()
    f6, f6p = f6.reindex(idx).fillna(0), f6p.reindex(idx).fillna(0)
    tend = ((f6 - f6p) / f6p.clip(lower=1)).clip(-1, 1)
    med = f[f.impresiones > 0].assign(ctr=lambda z: z.clics / z.impresiones).groupby("id_producto").ctr.median()
    m = f[(f.fe > d(365)) & (f.impresiones > 0)].assign(ctr=lambda z: z.clics / z.impresiones)
    ctr_rel = (m.ctr / m.id_producto.map(med)).groupby(m.id_cliente).mean().reindex(idx)
    it = inter[inter.fe <= T]
    ult = it[it.tipo.isin(TIPOS_CONTACTO)].groupby("id_cliente").fe.max().reindex(idx)
    ci = it[(it.tipo == "Cambio de interlocutor") & (it.fe > d(cfg_s["cambio_interlocutor_ultimos_dias"]))].id_cliente.unique()
    rec = it[(it.tipo == "Reclamacion") & (it.resultado == "Sin resolver")].id_cliente.unique()
    fa = fact_fac[fact_fac.fecha_emision <= T]
    venc = fa[(fa.fecha_vencimiento <= T) & (fa.fecha_cobro.isna() | (fa.fecha_cobro > T))].id_cliente.unique()
    s = pd.DataFrame(index=idx)
    s["s_tendencia"] = tend < cfg_s["tendencia_6m_menor_que"]
    s["s_ctr"] = ctr_rel < cfg_s["ctr_relativo_menor_que"]          # NaN (sin campañas medibles) -> False
    s["s_interlocutor"] = s.index.isin(ci)
    s["s_sin_contacto"] = ((T - ult).dt.days > cfg_s["dias_sin_contacto_mayor_que"]).fillna(True)
    s["s_reclamacion"] = s.index.isin(rec) if cfg_s["reclamacion_sin_resolver"] else False
    s["s_factura"] = s.index.isin(venc) if cfg_s["factura_vencida_impagada"] else False
    excl = set(cfg_s.get("excluir_del_recuento", []))
    s["n_senales"] = s[[c for c in s.columns if c not in excl]].sum(axis=1)
    # Variables continuas para el modelo a medida (iteración 5), todas con datos <= T
    s["v_tendencia"] = tend
    s["v_ctr_medible"] = ctr_rel.notna().astype(float)
    s["v_ctr_rel"] = ctr_rel.clip(upper=3).fillna(1.0)
    s["v_log_dias_sin_contacto"] = np.log1p((T - ult).dt.days.fillna(730).clip(lower=0))
    f12 = f[f.fe > d(365)]
    s["v_n_familias_12m"] = (f12.groupby("id_cliente").familia.nunique().reindex(idx).fillna(0)
                             if "familia" in f12 else 0.0)
    comp = set(cfg_s.get("productos_compromiso", ["P04", "P07", "P08", "P09"]))
    s["v_compromiso"] = s.index.isin(f[f.id_producto.isin(comp)].id_cliente.unique()).astype(float)
    s["valor_cuenta"] = np.maximum(f[f.fe > d(365)].groupby("id_cliente").importe_eur.sum().reindex(idx).fillna(0),
                                   f[f.fe > d(730)].groupby("id_cliente").importe_eur.sum().reindex(idx).fillna(0) / 2)
    return s


def foto_a_fecha(fact, inicios, verdad, T, excl_dias, horizonte=210, inter=None, fact_fac=None, cfg_s=None):
    fx, sx = fact[fact.fe <= T], inicios[inicios.fe <= T]
    s = pd.DataFrame({
        "ultima_actividad": fx.groupby("id_cliente").fe.max(),
        "primera_compra": sx.groupby("id_cliente").fe.min(),
        "ciclo_dias": ciclo_mediano(sx),
        "n_campanas": sx.groupby("id_cliente").size(),
    })
    s = s[s.index.isin(verdad.index)]
    s["recencia"] = (T - s.ultima_actividad).dt.days
    v = verdad.reindex(s.index)
    s["fecha_baja_real"] = v.fecha_baja_real
    s = s[s.fecha_baja_real.isna() | (s.fecha_baja_real > T - pd.Timedelta(days=excl_dias))]
    v = verdad.reindex(s.index)
    s["V1_baja_registrada"] = (s.fecha_baja_real <= T).astype(int)
    s["V2_ultima_compra_realizada"] = (v.fecha_baja_real.notna() & (v.ultima_orden_total <= T)).astype(int)
    fut = inicios[(inicios.fe > T) & (inicios.fe <= T + pd.Timedelta(days=horizonte))].id_cliente.unique()
    s["V3_sin_campana_210d"] = (~s.index.isin(fut)).astype(int)
    if inter is not None:
        s = s.join(senales_a_fecha(fact, inter, fact_fac, T, cfg_s))
    # BTYD: P(vivo) por anunciante, modelo ajustado en este corte solo con datos <= T
    sem = lambda td: td.dt.days / 7.0
    s["btyd_x"] = s.n_campanas - 1
    s["btyd_tx"] = sem(s.ultima_actividad - s.primera_compra)
    s["btyd_T"] = sem(T - s.primera_compra)
    par = btyd.ajustar(s.btyd_x, s.btyd_tx, s.btyd_T)
    s["p_vivo"] = btyd.p_vivo(par, s.btyd_x, s.btyd_tx, s.btyd_T) if par["identificado"] else np.nan
    for k in ("r", "alpha", "a", "b"):
        s[f"btyd_{k}"] = par[k]
    s["btyd_convergio"] = par["convergio"]; s["btyd_identificado"] = par["identificado"]
    s["segmento"] = np.where(s.n_campanas < 2, "Una campaña",
                             np.where(s.ciclo_dias < 150, "Ciclo < 150", "Ciclo >= 150"))
    s["corte"] = T
    return s.reset_index().rename(columns={"index": "id_cliente"})


def prediccion(df, regla):
    if regla["tipo"] == "btyd":
        return (df.p_vivo < regla["parametro"]).astype(int), None
    if regla["tipo"] == "p1":
        return (df.p1_activo < regla["parametro"]).astype(int), None
    if regla["tipo"] == "topk":
        return df[f"marca_topk_{regla['modelo']}"].fillna(0).astype(int), None
    if regla["tipo"] == "logit":
        return df[f"marca_{regla['modelo']}"].fillna(0).astype(int), None
    u = umbral(df.ciclo_dias, regla["tipo"], regla["parametro"], regla.get("minimo_dias", 210))
    pred = df.recencia > u
    if regla["tipo"] == "senales":
        pred &= df.n_senales >= regla["min_senales"]
    return pred.astype(int), u


def valor_neto(df, pred, col_verdad, esc):
    vp = (pred == 1) & (df[col_verdad] == 1); fp = (pred == 1) & (df[col_verdad] == 0)
    return float((df.valor_cuenta[vp] * esc["tasa_recuperacion"] - esc["coste_accion_eur"]).sum()
                 - fp.sum() * esc["coste_accion_eur"])


def metricas(df, regla, col_verdad, escenarios=None):
    pred, u = prediccion(df, regla); real = df[col_verdad]
    vp = int(((pred == 1) & (real == 1)).sum()); fp = int(((pred == 1) & (real == 0)).sum())
    fn = int(((pred == 0) & (real == 1)).sum()); vn = int(((pred == 0) & (real == 0)).sum())
    prec = vp / (vp + fp) if vp + fp else np.nan
    rec = vp / (vp + fn) if vp + fn else np.nan
    f1 = 2 * prec * rec / (prec + rec) if (vp and prec + rec) else np.nan
    m = (pred == 1) & (real == 1) & df.fecha_baja_real.notna()
    deteccion = df.corte if u is None else df.ultima_actividad + pd.to_timedelta(u, "D")
    retraso = (deteccion[m] - df.fecha_baja_real[m]).dt.days
    out = dict(regla=regla["nombre"], verdad=col_verdad, n=len(df), marcados=int(pred.sum()), VP=vp, FP=fp, FN=fn, VN=vn,
               precision=prec, recall=rec, F1=f1,
               retraso_mediano_dias=float(retraso.median()) if len(retraso) else np.nan)
    for k, esc in (escenarios or {}).items():
        out[f"valor_neto_{k}_eur"] = round(valor_neto(df, pred, col_verdad, esc), 0)
    return out


def decidir(tabla, criterio):
    esc = criterio["escenarios"]; central = criterio["escenario_principal"]
    col = f"valor_neto_{central}_eur"
    g = tabla.sort_values(col, ascending=False).iloc[0]
    mejores = {k: tabla.sort_values(f"valor_neto_{k}_eur", ascending=False).iloc[0].regla for k in esc}
    robusta = all(r == g.regla for r in mejores.values())
    if g[col] <= 0:
        return None, False, mejores, ("Ninguna regla genera valor neto positivo en el escenario central: "
                                      "actuar con estas reglas cuesta más de lo que recupera. Revisar con el equipo.")
    motivo = (f"Mayor valor neto esperado en el escenario {central} ({g[col]:,.0f} €)." +
              (" Es también la mejor en todos los escenarios: decisión ROBUSTA." if robusta else
               " No es la mejor en todos los escenarios: decisión SENSIBLE A LOS SUPUESTOS, revisar con el equipo."))
    return g.regla, robusta, mejores, motivo


# ------------------------------------------------------------- iteración 4 · P(Activo)
SENALES = ["s_tendencia", "s_ctr", "s_interlocutor", "s_sin_contacto", "s_reclamacion", "s_factura"]


VARIABLES_L3_SIN_CONTACTO = ["v_silencio_relativo", "v_tendencia", "v_ctr_rel", "v_ctr_medible", "v_n_familias_12m",
                             "v_compromiso", "v_tamano", "v_en_temporada_60d", "v_log_valor",
                             "s_interlocutor", "s_reclamacion", "s_factura"]
VARIABLES_CONTACTO = ["s_sin_contacto", "v_log_dias_sin_contacto"]


def variables_logit(df, modelo):
    X = np.c_[np.log1p(df.recencia), np.log1p(df.n_campanas), np.log1p(df.btyd_T)]
    if modelo == "L2":
        X = np.c_[X, df[SENALES].astype(float).values]
    if modelo in ("L3a", "L3b"):
        cols = VARIABLES_L3_SIN_CONTACTO + (VARIABLES_CONTACTO if modelo == "L3a" else [])
        X = np.c_[X, df[cols].astype(float).values]
    return X


TAMANO = {"Micro": 0, "Pequena": 1, "Mediana": 2, "Grande": 3}


def variables_extra(panel, inicios, cli):
    """Categoría, tamaño, silencio relativo al ritmo propio (P1) y temporada próxima, con datos <= cada corte."""
    panel = panel.copy()
    panel["categoria"] = panel.id_cliente.map(cli.categoria)
    panel["v_tamano"] = panel.id_cliente.map(cli.tamano).map(TAMANO).fillna(1).astype(float)
    panel["v_log_valor"] = np.log1p(panel.valor_cuenta)
    for T, d in panel.groupby("corte"):
        rs = (d.groupby("categoria").btyd_x.sum() / d.groupby("categoria").btyd_tx.sum().clip(lower=1)).clip(lower=1e-3)
        panel.loc[d.index, "ritmo_sector"] = d.categoria.map(rs).fillna(rs.median()).values
        sx = inicios[inicios.fe <= T].copy(); sx["mes"] = sx.fe.dt.month; sx["categoria"] = sx.id_cliente.map(cli.categoria)
        meses_cat = sx.groupby("categoria").mes.agg(lambda m: set(m.value_counts().index[:4]))
        meses_cli = sx.groupby("id_cliente").mes.agg(set); n_cli = sx.groupby("id_cliente").size()
        def dias(cid, cat):
            ms = meses_cli.get(cid, set()) if n_cli.get(cid, 0) >= 3 else meses_cat.get(cat, set())
            for k in range(13):
                mm = ((T.month + k - 1) % 12) + 1
                if mm in ms:
                    return max(0, (pd.Timestamp(T.year + (T.month + k - 1) // 12, mm, 1) - T).days)
            return 365
        panel.loc[d.index, "v_dias_hasta_temporada"] = [dias(c, k) for c, k in zip(d.id_cliente, d.categoria)]
    panel["v_en_temporada_60d"] = (panel.v_dias_hasta_temporada <= 60).astype(float)
    panel["p1_activo"] = p_activo.p1_ritmo_propio(panel.btyd_x, panel.btyd_tx, panel.recencia / 7.0, panel.ritmo_sector)
    panel["v_silencio_relativo"] = -np.log(np.clip(panel.p1_activo, 1e-9, 1))
    return panel


def marcar_topk(df, p, k, esc, solo_marcados=None):
    """Las k acciones de mayor valor esperado (y solo si es positivo). Devuelve 0/1."""
    ev = p * df.valor_cuenta * esc["tasa_recuperacion"] - esc["coste_accion_eur"]
    ok = ev > 0
    if solo_marcados is not None:
        ok &= solo_marcados
    orden = ev.where(ok).sort_values(ascending=False).dropna().index[:k]
    return pd.Series(df.index.isin(orden).astype(int), index=df.index)


def anadir_p_activo(panel, inicios, ruta_clientes, cfg):
    cli = pd.read_csv(ruta_clientes).set_index("id_cliente")
    panel = variables_extra(panel, inicios, cli) if inicios is not None else _extra_minimo(panel, cli)
    H = cfg["horizonte_objetivo_dias"]; pa = cfg.get("p_activo", {})
    central = cfg["criterio_decision"]["escenarios"][cfg["criterio_decision"]["escenario_principal"]]
    k = cfg.get("capacidad_acciones_por_corte")
    modelos = ["L1", "L2"] + (["L3a", "L3b"] if "v_silencio_relativo" in panel else [])
    panel["cortes_entrenamiento"] = ""
    coefs = []
    for Tp in pd.to_datetime(cfg.get("cortes_prueba", [])):
        entr = panel[panel.corte + pd.Timedelta(days=H) <= Tp]
        prueba = panel.corte == Tp
        panel.loc[prueba, "cortes_entrenamiento"] = ",".join(sorted(entr.corte.dt.strftime("%Y-%m-%d").unique()))
        y = entr[cfg["definicion_principal"]]
        for m in modelos:
            mod = p_activo.Logistica(pa.get("regularizacion_L2", 1.0)).fit(variables_logit(entr, m), y)
            p = pd.Series(mod.predict_proba(variables_logit(panel[prueba], m)), index=panel.index[prueba])
            panel.loc[prueba, f"p_sin_campana_{m}"] = p
            panel.loc[prueba, f"marca_{m}"] = (p * panel.loc[prueba, "valor_cuenta"] * central["tasa_recuperacion"]
                                               > central["coste_accion_eur"]).astype(int)
            coefs.append(dict(corte_prueba=Tp.date(), modelo=m, **{f"w{i}": w for i, w in enumerate(mod.w)}))
            if k:
                panel.loc[prueba, f"marca_topk_{m}"] = marcar_topk(panel[prueba], p, k, central)
        if k:
            d = panel[prueba]
            base = pd.Series(y.mean(), index=d.index)
            panel.loc[prueba, "marca_topk_VALOR"] = marcar_topk(d, base, k, central)
            panel.loc[prueba, "marca_topk_A"] = marcar_topk(d, pd.Series(1.0, index=d.index), k,
                                                            {"tasa_recuperacion": 1.0, "coste_accion_eur": 0.0}, d.recencia > 210)
    panel.attrs["coeficientes"] = pd.DataFrame(coefs)
    return panel


def _extra_minimo(panel, cli):
    """Para tests con paneles sintéticos sin inicios de campaña."""
    panel = panel.copy(); panel["categoria"] = panel.id_cliente.map(cli.categoria)
    panel["ritmo_sector"] = (panel.btyd_x.sum() / max(panel.btyd_tx.sum(), 1))
    panel["p1_activo"] = p_activo.p1_ritmo_propio(panel.btyd_x, panel.btyd_tx, panel.recencia / 7.0, panel.ritmo_sector)
    return panel


def calidad_probabilidades(panel, col_verdad):
    """Información complementaria (no decide): Brier y AUC de las probabilidades en los cortes de prueba."""
    filas = []
    y = panel[col_verdad].values
    for nombre, p in [("P1 · 1 − P(Activo)", 1 - panel.p1_activo.values),
                      ("L1", panel.get("p_sin_campana_L1", pd.Series(np.nan, index=panel.index)).values),
                      ("L2", panel.get("p_sin_campana_L2", pd.Series(np.nan, index=panel.index)).values),
                      ("L3a", panel.get("p_sin_campana_L3a", pd.Series(np.nan, index=panel.index)).values),
                      ("L3b", panel.get("p_sin_campana_L3b", pd.Series(np.nan, index=panel.index)).values)]:
        ok = ~np.isnan(p)
        if ok.sum() == 0: continue
        pp, yy = p[ok], y[ok]
        orden = np.argsort(pp); rangos = np.empty(len(pp)); rangos[orden] = np.arange(1, len(pp) + 1)
        n1 = yy.sum(); n0 = len(yy) - n1
        auc = (rangos[yy == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0) if n1 and n0 else np.nan
        filas.append(dict(modelo=nombre, n=int(ok.sum()), brier=float(np.mean((pp - yy) ** 2)), auc=float(auc)))
    return pd.DataFrame(filas)


# ----------------------------------------------------------------------- ejecución
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--datos", default="data"); ap.add_argument("--config", default="config/criterio.json")
    ap.add_argument("--salida", default="resultados")
    a = ap.parse_args(); os.makedirs(a.salida, exist_ok=True)
    cfg = json.load(open(a.config, encoding="utf-8"))
    H = cfg["horizonte_objetivo_dias"]; fin = pd.Timestamp(cfg["fecha_fin_datos"])

    fact = pd.read_csv(os.path.join(a.datos, "fact_campanas.csv"), parse_dates=["fecha_emision"]); fact["fe"] = fact.fecha_emision
    inter = pd.read_csv(os.path.join(a.datos, "fact_interacciones.csv"), parse_dates=["fecha"]); inter["fe"] = inter.fecha
    ffac = pd.read_csv(os.path.join(a.datos, "fact_facturacion.csv"), parse_dates=["fecha_emision", "fecha_vencimiento", "fecha_cobro"])
    gt = pd.read_csv(os.path.join(a.datos, "validacion", "aux_ground_truth.csv"), parse_dates=["fecha_baja_real"])
    gt = gt[~gt.inactivo_pre_ventana.astype(bool)].set_index("id_cliente")
    gt["ultima_orden_total"] = fact.groupby("id_cliente").fe.max().reindex(gt.index)
    inicios = inicios_de_campana(fact)

    cortes = pd.to_datetime(cfg["cortes"])
    assert (cortes + pd.Timedelta(days=H) <= fin).all(), "Hay cortes sin ventana observable completa"
    panel = pd.concat([foto_a_fecha(fact, inicios, gt, T, cfg["ventana_exclusion_bajas_antiguas_dias"], H,
                                    inter, ffac, cfg["senales"]) for T in cortes], ignore_index=True)
    verdades = list(cfg["definiciones_de_verdad"]); reglas = cfg["reglas_candidatas"]
    esc = cfg["criterio_decision"]["escenarios"]
    panel = anadir_p_activo(panel, inicios, os.path.join(a.datos, "dim_clientes.csv"), cfg)
    if cfg.get("cortes_prueba"):
        cp = pd.to_datetime(cfg["cortes_prueba"])
        panel_completo = panel
        panel = panel[panel.corte.isin(cp)].copy()
        cortes = cp

    resumen = pd.DataFrame([metricas(panel, r, v, esc) for v in verdades for r in reglas])
    segm = pd.DataFrame([dict(segmento=s, **metricas(panel[panel.segmento == s], r, v, esc))
                         for v in verdades for s in ["Ciclo < 150", "Ciclo >= 150", "Una campaña"] for r in reglas])
    porc = pd.DataFrame([dict(corte=T.date(), **metricas(panel[panel.corte == T], r, v, esc))
                         for v in verdades for T in cortes for r in reglas])
    sens_reglas = ([{"nombre": f"{k} días", "tipo": "dias", "parametro": k} for k in cfg["sensibilidad"]["dias"]] +
                   [{"nombre": f"MAX(210; {k} × ciclo)", "tipo": "factor", "parametro": k, "minimo_dias": 210}
                    for k in cfg["sensibilidad"]["factor"]] +
                   [{"nombre": f"{k} días y ≥ {n} señal(es)", "tipo": "senales", "parametro": k, "min_senales": n}
                    for k in cfg["sensibilidad"]["dias"] for n in (1, 2)] +
                   [{"nombre": f"BTYD P(vivo) < {k}", "tipo": "btyd", "parametro": k} for k in cfg["sensibilidad"].get("btyd", [])] +
                   [{"nombre": f"P1 · P(Activo) < {k}", "tipo": "p1", "parametro": k} for k in cfg["sensibilidad"].get("p1", [])])
    sens = pd.DataFrame([metricas(panel, r, cfg["definicion_principal"], esc) for r in sens_reglas])

    principal = resumen[resumen.verdad == cfg["definicion_principal"]]
    ident = panel.groupby("corte").btyd_identificado.first()
    nota_btyd = ""
    if not ident.all():
        nombres_btyd = [r["nombre"] for r in reglas if r["tipo"] == "btyd"]
        principal = principal[~principal.regla.isin(nombres_btyd)]
        nota_btyd = (f"\n**BTYD excluido de la decisión:** el modelo MBG/NBD solo se identificó en {int(ident.sum())} de "
                     f"{len(ident)} cortes (parámetros en el borde de la búsqueda: los datos no los determinan). "
                     "Detalle en btyd_parametros_por_corte.csv.\n")
    nombres_decide = [r["nombre"] for r in reglas if r.get("decide")]
    if nombres_decide:
        principal = principal[principal.regla.isin(nombres_decide)]
    ganadora, robusta, mejores, motivo = decidir(principal, cfg["criterio_decision"])

    if cfg.get("cortes_prueba"):
        panel_completo.to_csv(os.path.join(a.salida, "panel_completo_entrenamiento.csv"), index=False)
    for nombre, df in [("resumen", resumen), ("por_segmento", segm), ("por_corte", porc),
                       ("sensibilidad", sens), ("panel_backtest", panel)]:
        df.to_csv(os.path.join(a.salida, f"{nombre}.csv"), index=False)
    with pd.ExcelWriter(os.path.join(a.salida, "resultados_evaluacion.xlsx")) as xl:
        for nombre, df in [("resumen", resumen), ("por_segmento", segm), ("por_corte", porc), ("sensibilidad", sens)]:
            df.to_excel(xl, sheet_name=nombre, index=False)
    cols = ["regla", "marcados", "VP", "FP", "FN", "precision", "recall", "F1"] + [f"valor_neto_{k}_eur" for k in esc]
    with open(os.path.join(a.salida, "decision.md"), "w", encoding="utf-8") as fh:
        fh.write(f"# Decisión sobre la regla de abandono · iteración {cfg.get('iteracion', 1)}\n\n")
        if cfg.get("cortes_prueba"):
            fh.write(f"- Cortes de prueba (todas las reglas): {', '.join(cfg['cortes_prueba'])}\n")
        fh.write(f"- Verdad principal: `{cfg['definicion_principal']}`\n- Criterio: valor neto esperado (escenario {cfg['criterio_decision']['escenario_principal']})\n")
        fh.write(f"- Regla ganadora: **{ganadora or 'ninguna'}**\n- Motivo: {motivo}\n")
        fh.write("- Mejor regla por escenario: " + "; ".join(f"{k}: {v}" for k, v in mejores.items()) + "\n" + nota_btyd + "\n")
        fh.write("## Resumen (verdad principal)\n\n" + principal[cols].round(3).to_markdown(index=False) + "\n\n")
        fh.write("## Controles con el archivo de validación\n\n" +
                 resumen[resumen.verdad != cfg["definicion_principal"]][["verdad"] + cols].round(3).to_markdown(index=False) + "\n")
    if "coeficientes" in panel_completo.attrs if cfg.get("cortes_prueba") else False:
        co = panel_completo.attrs["coeficientes"]
        if len(co):
            nombres = {"L1": ["intercepto", "log_recencia", "log_campanas", "log_antiguedad"]}
            nombres["L2"] = nombres["L1"] + SENALES
            nombres["L3b"] = nombres["L1"] + VARIABLES_L3_SIN_CONTACTO
            nombres["L3a"] = nombres["L3b"] + VARIABLES_CONTACTO
            filas = [dict(corte_prueba=r.corte_prueba, modelo=r.modelo, variable=n, coeficiente_estandarizado=getattr(r, f"w{i}"))
                     for r in co.itertuples() for i, n in enumerate(nombres[r.modelo])]
            pd.DataFrame(filas).to_csv(os.path.join(a.salida, "coeficientes_por_corte.csv"), index=False)
    if "p1_activo" in panel:
        calidad_probabilidades(panel, cfg["definicion_principal"]).to_csv(os.path.join(a.salida, "calidad_probabilidades.csv"), index=False)
    (panel.groupby("corte")[["btyd_r", "btyd_alpha", "btyd_a", "btyd_b", "btyd_convergio", "btyd_identificado"]].first()
     .to_csv(os.path.join(a.salida, "btyd_parametros_por_corte.csv")))
    print(open(os.path.join(a.salida, "decision.md"), encoding="utf-8").read())


if __name__ == "__main__":
    main()
