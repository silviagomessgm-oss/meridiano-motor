import json, os, sys
import numpy as np, pandas as pd
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from evaluar_umbral_abandono import (inicios_de_campana, ciclo_mediano, umbral, foto_a_fecha, metricas,
                                     decidir, senales_a_fecha, prediccion, valor_neto)
import btyd
import p_activo
from evaluar_umbral_abandono import anadir_p_activo, SENALES, marcar_topk, variables_logit, VARIABLES_CONTACTO, VARIABLES_L3_SIN_CONTACTO
CFG = json.load(open(os.path.join(os.path.dirname(__file__), "..", "config", "criterio.json"), encoding="utf-8"))


def _fact():
    filas = [("A", "K1", "2024-01-01", 1000), ("A", "K1", "2024-02-01", 1000), ("A", "K1", "2024-03-01", 1000),
             ("A", "K2", "2024-04-10", 500), ("A", "K3", "2024-07-19", 500),
             ("B", "K4", "2024-01-01", 300), ("C", "K5", "2025-06-01", 800)]
    f = pd.DataFrame(filas, columns=["id_cliente", "id_campana", "fecha_emision", "importe_eur"])
    f["fe"] = pd.to_datetime(f.fecha_emision); f["impresiones"] = 0; f["clics"] = 0; f["id_producto"] = "P07"
    return f


def _gt(f):
    gt = pd.DataFrame({"fecha_baja_real": pd.to_datetime(["2025-03-01", None, None])}, index=["A", "B", "C"])
    gt["ultima_orden_total"] = f.groupby("id_cliente").fe.max(); return gt


def test_criterio_iteracion_2_registrado():
    assert CFG["iteracion"] == 5 and CFG["definicion_principal"] == "V3_sin_campana_210d"
    assert CFG["criterio_decision"]["metrica_principal"] == "valor_neto_esperado_eur"


def test_cortes_con_ventana_observable_completa():
    fin = pd.Timestamp(CFG["fecha_fin_datos"])
    assert all(pd.Timestamp(c) + pd.Timedelta(days=CFG["horizonte_objetivo_dias"]) <= fin for c in CFG["cortes"])


def test_ciclo_se_mide_por_inicio_de_campana():
    c = ciclo_mediano(inicios_de_campana(_fact()))
    assert c["A"] == 100.0 and np.isnan(c["B"])


def test_umbrales():
    c = pd.Series([50.0, np.nan, 400.0])
    assert list(umbral(c, "dias", 210)) == [210.0] * 3
    assert list(umbral(c, "factor", 1.5, 210)) == [210.0, 210.0, 600.0]


def test_verdad_observable_mira_solo_los_210_dias_siguientes():
    f = _fact(); ini = inicios_de_campana(f); gt = _gt(f)
    T = pd.Timestamp("2024-12-31")
    s = foto_a_fecha(f, ini, gt.loc[["A", "B"]], T, 365, 210).set_index("id_cliente")
    assert s.loc["A", "V3_sin_campana_210d"] == 1 and s.loc["B", "V3_sin_campana_210d"] == 1
    f2 = pd.concat([f, pd.DataFrame({"id_cliente": ["B"], "id_campana": ["K8"], "fecha_emision": ["2025-05-01"],
                                     "importe_eur": [100], "fe": [pd.Timestamp("2025-05-01")], "impresiones": [0], "clics": [0], "id_producto": ["P07"]})])
    s2 = foto_a_fecha(f2, inicios_de_campana(f2), _gt(f2).loc[["A", "B"]], T, 365, 210).set_index("id_cliente")
    assert s2.loc["B", "V3_sin_campana_210d"] == 0          # campaña a 121 días: dentro del horizonte
    assert s2.loc["B", "recencia"] == s.loc["B", "recencia"]   # las variables no ven el futuro


def test_senales_sin_fuga_temporal():
    f = _fact(); T = pd.Timestamp("2024-12-31")
    inter = pd.DataFrame({"id_cliente": ["A", "A"], "tipo": ["Llamada", "Cambio de interlocutor"],
                          "resultado": ["Contacto efectivo", "Nuevo responsable de marketing"],
                          "fe": pd.to_datetime(["2024-12-01", "2025-02-01"])})
    fac = pd.DataFrame({"id_cliente": ["A"], "fecha_emision": pd.to_datetime(["2024-11-01"]),
                        "fecha_vencimiento": pd.to_datetime(["2024-12-01"]), "fecha_cobro": pd.to_datetime(["2025-01-15"])})
    s = senales_a_fecha(f, inter, fac, T, CFG["senales"])
    assert not s.loc["A", "s_interlocutor"]               # el cambio es posterior al corte
    assert not s.loc["A", "s_sin_contacto"]               # contacto hace 30 días
    assert s.loc["A", "s_factura"]                        # cobrada después del corte: en T estaba vencida


def test_regla_con_senales_exige_inactividad_y_senales():
    df = pd.DataFrame({"recencia": [300, 300, 100], "ciclo_dias": [np.nan] * 3, "n_senales": [0, 2, 3]})
    p1, _ = prediccion(df, {"tipo": "senales", "parametro": 210, "min_senales": 1})
    assert list(p1) == [0, 1, 0]


def test_valor_neto_y_decision():
    df = pd.DataFrame({"recencia": [300, 300, 100], "ciclo_dias": [np.nan] * 3, "valor_cuenta": [10000.0, 5000.0, 0.0],
                       "ultima_actividad": pd.to_datetime(["2024-01-01"] * 3),
                       "fecha_baja_real": pd.to_datetime([None] * 3), "V": [1, 0, 1]})
    pred, _ = prediccion(df, {"tipo": "dias", "parametro": 210})
    assert valor_neto(df, pred, "V", {"coste_accion_eur": 100, "tasa_recuperacion": 0.2}) == 10000 * 0.2 - 100 - 100
    esc = CFG["criterio_decision"]["escenarios"]
    t = pd.DataFrame([dict(regla="X", **{f"valor_neto_{k}_eur": 10 for k in esc}),
                      dict(regla="Y", **{f"valor_neto_{k}_eur": 5 for k in esc})])
    g, robusta, _, _ = decidir(t, CFG["criterio_decision"])
    assert g == "X" and robusta


def test_tendencia_no_cuenta_en_reglas_con_senales():
    f = _fact(); T = pd.Timestamp("2024-12-31")    # A: última campaña en julio, 0 € en los últimos 6 meses
    inter = pd.DataFrame({"id_cliente": ["A"], "tipo": ["Llamada"], "resultado": ["Contacto efectivo"],
                          "fe": pd.to_datetime(["2024-12-01"])})
    fac = pd.DataFrame(columns=["id_cliente", "fecha_emision", "fecha_vencimiento", "fecha_cobro"]).astype(
        {"fecha_emision": "datetime64[ns]", "fecha_vencimiento": "datetime64[ns]", "fecha_cobro": "datetime64[ns]"})
    s = senales_a_fecha(f, inter, fac, T, CFG["senales"])
    assert s.loc["A", "s_tendencia"] and s.loc["A", "n_senales"] == 0


def test_btyd_recupera_parametros_conocidos():
    """Valida la implementación del MBG/NBD: datos simulados con parámetros conocidos."""
    x, tx, T = btyd.simular(30000, 0.8, 10.0, 0.6, 3.0, 150, semilla=1)
    par = btyd.ajustar(x, tx, T)
    for k, real in dict(r=0.8, alpha=10.0, a=0.6, b=3.0).items():
        assert abs(par[k] - real) / real < 0.10, (k, par[k])
    assert par["identificado"]


def test_btyd_detecta_cuando_los_datos_no_identifican_el_modelo():
    x, tx, T = btyd.simular(150, 0.8, 10.0, 0.6, 3.0, 150, semilla=3)
    x[:] = 0; tx[:] = 0                                   # nadie repite: no hay información sobre abandono
    assert not btyd.ajustar(x, tx, T)["identificado"]


def test_btyd_p_vivo_cae_con_la_inactividad_y_sube_con_la_frecuencia():
    par = dict(r=0.8, alpha=10.0, a=0.6, b=3.0)
    assert btyd.p_vivo(par, 3, 100, 150) > btyd.p_vivo(par, 3, 50, 150)       # más reciente, más vivo
    assert btyd.p_vivo(par, 6, 50, 150) < btyd.p_vivo(par, 1, 50, 150)       # mismo silencio, cliente frecuente: más sospechoso
    assert btyd.p_vivo(par, 0, 0, 150) < 1.0                                  # MBG/NBD: una sola compra no es "vivo seguro"


def test_regla_btyd():
    df = pd.DataFrame({"p_vivo": [0.2, 0.6]})
    p, u = prediccion(df, {"tipo": "btyd", "parametro": 0.5})
    assert list(p) == [1, 0] and u is None


def test_p1_ritmo_propio():
    # más silencio -> menos activo; con el mismo silencio, quien compraba a menudo es más sospechoso
    assert p_activo.p1_ritmo_propio(3, 50, 30, 0.02) < p_activo.p1_ritmo_propio(3, 50, 10, 0.02)
    assert p_activo.p1_ritmo_propio(8, 50, 30, 0.02) < p_activo.p1_ritmo_propio(1, 50, 30, 0.02)
    assert 0 < p_activo.p1_ritmo_propio(0, 0, 30, 0.02) < 1        # sin historial: solo el ritmo del sector


def test_logistica_recupera_coeficientes():
    g = np.random.default_rng(0); X = g.normal(size=(20000, 2))
    y = (g.random(20000) < 1 / (1 + np.exp(-(0.5 + 1.5 * X[:, 0] - 1.0 * X[:, 1])))).astype(int)
    m = p_activo.Logistica(lam=0.0).fit(X, y)
    w = m.w[1:] / m.sd                                             # deshacer la estandarización
    assert abs(w[0] - 1.5) < 0.1 and abs(w[1] + 1.0) < 0.1


def _panel_sintetico():
    g = np.random.default_rng(1); filas = []
    for T in pd.to_datetime(["2024-09-30", "2024-12-31", "2025-03-31", "2025-06-30", "2025-12-31"]):
        for i in range(60):
            filas.append(dict(corte=T, id_cliente=f"K{i}", btyd_x=g.integers(0, 5), btyd_tx=g.uniform(0, 80),
                              btyd_T=g.uniform(80, 150), recencia=g.uniform(0, 400), n_campanas=g.integers(1, 6),
                              valor_cuenta=g.uniform(500, 20000), V3_sin_campana_210d=int(g.random() < 0.5),
                              **{s: bool(g.random() < 0.3) for s in SENALES}))
    return pd.DataFrame(filas)


def test_entrenamiento_sin_fuga_temporal(tmp_path):
    pd.DataFrame({"id_cliente": [f"K{i}" for i in range(60)], "categoria": ["X"] * 60}).to_csv(tmp_path / "c.csv", index=False)
    cfg = {**CFG, "cortes_prueba": ["2025-06-30", "2025-12-31"]}
    p = anadir_p_activo(_panel_sintetico(), None, tmp_path / "c.csv", cfg)
    for Tp in cfg["cortes_prueba"]:
        usados = pd.to_datetime(p[p.corte == Tp].cortes_entrenamiento.iloc[0].split(","))
        assert (usados + pd.Timedelta(days=210) <= pd.Timestamp(Tp)).all()   # solo resultados ya conocidos
    assert p[~p.corte.isin(pd.to_datetime(cfg["cortes_prueba"]))].p_sin_campana_L1.isna().all()


def test_regla_logistica_es_valor_esperado(tmp_path):
    pd.DataFrame({"id_cliente": [f"K{i}" for i in range(60)], "categoria": ["X"] * 60}).to_csv(tmp_path / "c.csv", index=False)
    p = anadir_p_activo(_panel_sintetico(), None, tmp_path / "c.csv", {**CFG, "cortes_prueba": ["2025-12-31"]})
    esc = CFG["criterio_decision"]["escenarios"]["central"]
    t = p[p.corte == "2025-12-31"]
    esperado = (t.p_sin_campana_L2 * t.valor_cuenta * esc["tasa_recuperacion"] > esc["coste_accion_eur"]).astype(int)
    assert (t.marca_L2 == esperado).all()


def test_produccion_no_usa_validacion_ni_resultados_futuros():
    import generar_scores, inspect
    codigo = inspect.getsource(generar_scores)
    assert "aux_ground_truth" not in codigo and "validacion" not in codigo
    prod = json.load(open(os.path.join(os.path.dirname(__file__), "..", "config", "produccion.json"), encoding="utf-8"))
    Tp = pd.Timestamp(prod["fecha_puntuacion"])
    assert all(pd.Timestamp(c) + pd.Timedelta(days=prod["horizonte_objetivo_dias"]) <= Tp for c in prod["cortes_entrenamiento"])
    et = json.load(open(os.path.join(os.path.dirname(__file__), "..", "config", "etiqueta.json"), encoding="utf-8"))
    assert all(pd.Timestamp(c) + pd.Timedelta(days=210) <= Tp for c in et["cortes"]) and prod["etiqueta"] == "E2"


def test_poblacion_observable():
    import generar_scores
    f = _fact(); v = generar_scores.poblacion_observable(f, pd.Timestamp("2024-12-31"), 300)
    assert set(v.index) == {"A"}                         # B lleva más de 300 días; C aún no ha comprado


def test_topk_respeta_capacidad_y_valor_esperado():
    df = pd.DataFrame({"valor_cuenta": [10000.0, 5000.0, 100.0, 8000.0, 9000.0]})
    p = pd.Series([0.5, 0.5, 0.9, 0.0, 0.4])
    m = marcar_topk(df, p, 2, {"tasa_recuperacion": 0.2, "coste_accion_eur": 120})
    assert m.sum() == 2 and m.iloc[0] == 1 and m.iloc[4] == 1          # mayor valor esperado
    assert m.iloc[2] == 0 and m.iloc[3] == 0                            # valor esperado negativo o nulo


def test_l3b_no_usa_variables_de_contacto():
    cols = ["recencia", "n_campanas", "btyd_T"] + VARIABLES_L3_SIN_CONTACTO + VARIABLES_CONTACTO
    df = pd.DataFrame(np.ones((3, len(cols))), columns=cols)
    assert variables_logit(df, "L3a").shape[1] == variables_logit(df, "L3b").shape[1] + len(VARIABLES_CONTACTO)
    assert not set(VARIABLES_CONTACTO) & set(VARIABLES_L3_SIN_CONTACTO)


def test_variables_continuas_sin_fuga_temporal():
    f = _fact(); f["familia"] = "Eventos"; T = pd.Timestamp("2024-12-31")
    inter = pd.DataFrame({"id_cliente": ["A"], "tipo": ["Llamada"], "resultado": ["Contacto efectivo"], "fe": pd.to_datetime(["2024-12-01"])})
    fac = pd.DataFrame(columns=["id_cliente", "fecha_emision", "fecha_vencimiento", "fecha_cobro"]).astype(
        {"fecha_emision": "datetime64[ns]", "fecha_vencimiento": "datetime64[ns]", "fecha_cobro": "datetime64[ns]"})
    s1 = senales_a_fecha(f, inter, fac, T, CFG["senales"])
    f2 = pd.concat([f, f.assign(fecha_emision="2025-03-01", fe=pd.Timestamp("2025-03-01"), id_producto="P09")])
    i2 = pd.concat([inter, inter.assign(fe=pd.Timestamp("2025-02-01"))])
    s2 = senales_a_fecha(f2, i2, fac, T, CFG["senales"])
    cols = [c for c in s1.columns if c.startswith("v_")]
    pd.testing.assert_frame_equal(s1[cols].sort_index(), s2[cols].sort_index())
