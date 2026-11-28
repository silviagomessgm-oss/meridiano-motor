"""Tests de la SDD (Orchestrate) y Golden Dataset (Govern) del automatismo de propuestas."""
import json, os, sys
import numpy as np, pandas as pd, pytest
RAIZ = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(RAIZ, "src"))
import propuestas as P

CFG = json.load(open(os.path.join(RAIZ, "config", "parametros.json"), encoding="utf-8"))
T = pd.Timestamp(CFG["fecha_corte"]); T_TEST = pd.Timestamp("2025-12-31")


@pytest.fixture(scope="module")
def tablas():
    return P.cargar(os.path.join(RAIZ, "data"))


@pytest.fixture(scope="module")
def salida(tablas):
    x = P.foto(tablas, T); g = P.variables(x, T, CFG); g, _ = P.riesgo(g, CFG, None)
    return P.plan(g, CFG, x["p"], x["f"], T), g, x


# ---------------------------------------------------------------- N01/N02 · sin fuga temporal
def test_datos_futuros_no_cambian_las_variables(tablas):
    base = P.variables(P.foto(tablas, T_TEST), T_TEST, CFG).set_index("id_cliente")
    t2 = dict(tablas)                      # los datos reales ya tienen 9 meses posteriores a T_TEST
    corto = {k: v for k, v in tablas.items()}
    corto["f"] = tablas["f"][tablas["f"].fecha_emision <= T_TEST]
    corto["it"] = tablas["it"][tablas["it"].fecha <= T_TEST]
    corto["fa"] = tablas["fa"][tablas["fa"].fecha_emision <= T_TEST]
    corto["o"] = tablas["o"][tablas["o"].fecha_envio <= T_TEST]
    solo_pasado = P.variables(P.foto(corto, T_TEST), T_TEST, CFG).set_index("id_cliente")
    cols = [c for c in base.columns if c not in ("fecha_corte",)]
    pd.testing.assert_frame_equal(base[cols].sort_index(), solo_pasado[cols].sort_index(), check_dtype=False)


def test_cobro_posterior_al_corte_cuenta_como_pendiente(tablas):
    x = P.foto(tablas, T_TEST)
    assert (x["fa"].fecha_cobro.dropna() <= T_TEST).all()
    assert (x["o"].loc[x["o"].desenlace != "Abierta", "fecha_cierre"] <= T_TEST).all()


def test_variables_excluidas_no_entran(salida):
    _, g, _ = salida
    for c in ("cp_sede", "tiene_web_propia", "anio_fundacion"):
        assert c not in g.columns


# ---------------------------------------------------------------- N05 · límites del plan
def test_capacidad_por_comercial(salida):
    pl, _, _ = salida
    cap = CFG["capacidad_semanal_por_comercial"] * CFG["semanas_del_plan"]
    assert pl[pl.estado_plan == "propuesto"].groupby("comercial_asignado").size().max() <= cap


def test_control_solo_banda_media_y_nunca_cuentas_clave(salida):
    pl, _, _ = salida
    c = pl[pl.grupo_experimental == "control"]
    assert (c.banda_riesgo == "media").all() and (~c.cuenta_clave).all()


def test_prioridad_por_facturacion_en_riesgo(salida):
    pl, _, _ = salida
    for _, d in pl[pl.estado_plan == "propuesto"].groupby("comercial_asignado"):
        assert d.sort_values("orden_comercial").facturacion_en_riesgo.is_monotonic_decreasing


def test_una_accion_por_cuenta(salida):
    pl, _, _ = salida
    assert not pl.id_cliente.duplicated().any()


def test_asignacion_de_control_reproducible(salida, tablas):
    pl, _, _ = salida
    x = P.foto(tablas, T); g = P.variables(x, T, CFG); g, _ = P.riesgo(g, CFG, None)
    pl2 = P.plan(g, CFG, x["p"], x["f"], T)
    assert set(pl[pl.grupo_experimental == "control"].id_cliente) == set(pl2[pl2.grupo_experimental == "control"].id_cliente)


# ---------------------------------------------------------------- Golden Dataset (Govern)
def _caso(g, **cambios):
    r = g.iloc[[0]].copy()
    neutro = dict(tendencia_6m=0.0, ctr_relativo_12m=1.0, cambio_interlocutor_12m=False, reclamaciones_sin_resolver=0,
                  dias_sin_contacto=10, facturas_vencidas_impagadas=0, recencia_dias=30, ciclo_mediano_campanas_dias=120.0,
                  dias_hasta_proxima_ventana=200.0, eventos_asistidos_12m=0, valor_cuenta=5000.0)
    for k, v in {**neutro, **cambios}.items():
        r[k] = v
    return r


def test_golden_cambio_interlocutor_en_cuenta_clave(salida):
    pl, g, x = salida
    otras = g.copy(); otras["valor_cuenta"] = 100.0
    caso = _caso(g, cambio_interlocutor_12m=True, dias_desde_cambio_interlocutor=20, tendencia_6m=-0.5, valor_cuenta=90000.0)
    caso["id_cliente"] = "GOLD1"
    gg, _ = P.riesgo(pd.concat([otras, caso]), CFG, None)
    r = P.plan(gg, CFG, x["p"], x["f"], T).set_index("id_cliente").loc["GOLD1"]
    assert r.accion_id == "reunion_nuevo_interlocutor" and r.grupo_experimental == "tratamiento" and r.requiere_direccion


def test_golden_pausa_estacional_no_se_trata_como_abandono(salida):
    _, g, x = salida
    caso = _caso(g, tendencia_6m=-1.0, dias_sin_contacto=120, recencia_dias=250, dias_hasta_proxima_ventana=30.0)
    caso["id_cliente"] = "GOLD2"
    gg, _ = P.riesgo(pd.concat([g, caso]), CFG, None)
    r = gg.set_index("id_cliente").loc["GOLD2"]
    assert r.pausa_estacional_probable
    pr = P.plan(gg, CFG, x["p"], x["f"], T).set_index("id_cliente").loc["GOLD2"]
    assert pr.accion_id == "reserva_anticipada_temporada"          # no se pierde la cuenta ni se le habla de riesgo


def test_golden_ctr_bajo_es_motivo_de_rendimiento(salida):
    _, g, x = salida
    caso = _caso(g, ctr_relativo_12m=0.6, tendencia_6m=-0.4); caso["id_cliente"] = "GOLD3"
    gg, _ = P.riesgo(pd.concat([g, caso]), CFG, None)
    r = gg.set_index("id_cliente").loc["GOLD3"]
    assert r.motivo_principal == "rendimiento_campanas"
    assert any("CTR" in e for e in P.evidencias(r))


def test_golden_sin_campanas_medibles_no_menciona_ctr(salida):
    _, g, _ = salida
    r = _caso(g, ctr_relativo_12m=np.nan, tendencia_6m=-0.5).iloc[0]
    assert not any("CTR" in e for e in P.evidencias(r))


# ---------------------------------------------------------------- N06 · validador del LLM
def test_validador_rechaza_cifras_inventadas_y_condiciones_economicas():
    ctx = "Datos: inversión 6 meses 2.449 €; última campaña hace 241 días"
    assert P.validar_llm("Su inversión fue de 2.449 € y su última campaña fue hace 241 días.", ctx)[0]
    assert not P.validar_llm("Su CTR fue del 3,2 en su última campaña.", ctx)[0]
    assert not P.validar_llm("Le ofrecemos un descuento especial.", ctx)[0]


def test_materiales_no_contienen_condiciones_economicas(salida):
    pl, _, _ = salida
    m = P.materiales(pl, {**CFG, "llm": {**CFG["llm"], "usar": False}})
    assert not m.material_cuerpo.str.contains(r"\d+\s*%|descuento|rebaja|gratis", case=False, regex=True).any()
    assert not m.material_cuerpo.str.contains("riesgo", case=False).any()


# ---------------------------------------------------------------- decisión: actuar con L2 × valor
def test_con_modelo_se_actua_por_valor_esperado(salida):
    _, g, x = salida
    sc = pd.DataFrame({"id_cliente": g.id_cliente, "prob_abandono": np.linspace(0.05, 0.95, len(g))})
    gg, _ = P.riesgo(g, CFG, sc)
    ve = CFG["valor_esperado"]
    esperado = sc.set_index("id_cliente").prob_abandono.reindex(gg.id_cliente).values * gg.valor_cuenta * ve["tasa_recuperacion"] > ve["coste_accion_eur"]
    assert ((gg.banda_riesgo != "baja") == esperado).all()
    assert (gg.fuente_riesgo == "modelo").all()
    pl = P.plan(gg, CFG, x["p"], x["f"], T)
    for _, d in pl[pl.estado_plan == "propuesto"].groupby("comercial_asignado"):
        assert d.sort_values("orden_comercial").facturacion_en_riesgo.is_monotonic_decreasing   # prioridad = P × valor


def test_sin_puntuacion_se_usa_el_respaldo(salida):
    _, g, _ = salida
    sc = pd.DataFrame({"id_cliente": g.id_cliente.iloc[:10], "prob_abandono": 0.9})
    gg, _ = P.riesgo(g, CFG, sc)
    assert (gg.fuente_riesgo == "respaldo").sum() == len(g) - 10


# ---------------------------------------------------------------- validación continua de la etiqueta
def test_plan_incluye_confirmacion_del_comercial(tmp_path):
    pl, g = P.ejecutar(os.path.join(RAIZ, "data"), os.path.join(RAIZ, "config", "parametros.json"), str(tmp_path))
    plan = pd.read_excel(tmp_path / "propuestas_retencion.xlsx", sheet_name="Plan_por_comercial")
    for c in P.CONFIRMACION:
        assert c in plan.columns
    assert set(P.CONFIRMACION) <= set(pd.read_csv(tmp_path / "crm_tareas.csv").columns)


def test_resumen_de_confirmaciones():
    import confirmaciones as C
    df = pd.DataFrame({"banda_riesgo": ["alta", "media", "alta"], "estado_confirmado_comercial": ["Perdido", "Pausa: volvió después", None],
                       "diagnostico_correcto": ["Sí", "No", None], "motivo_confirmado": ["perdida_contacto", "temporada", None],
                       "motivo_principal": ["perdida_contacto", "presupuesto_inversion", "x"]})
    r = C.resumen(df)
    assert r["propuestas_confirmadas"] == 2 and r["riesgo_confirmado_por_el_comercial"] == 0.5 and r["pausas_detectadas"] == 1
    assert r["diagnostico_correcto"] == 0.5 and r["motivo_coincide"] == 0.5


def test_tipo_de_riesgo_e2(salida):
    _, g, x = salida
    caso = _caso(g, recencia_dias=40, tendencia_6m=-0.6, ctr_relativo_12m=1.0); caso["id_cliente"] = "GOLD5"
    gg, _ = P.riesgo(pd.concat([g, caso]), CFG, pd.DataFrame({"id_cliente": ["GOLD5"], "prob_abandono": [0.9]}))
    r = P.plan(gg, CFG, x["p"], x["f"], T).set_index("id_cliente").loc["GOLD5"]
    assert r.tipo_riesgo == "contraccion" and r.accion_id == "informe_resultados_y_optimizacion"


# ---------------------------------------------------------------- H9 (auditoría) · valor neto positivo y huecos
def test_solo_se_propone_con_valor_neto_positivo(salida):
    pl, g, _ = salida
    assert (pl[pl.estado_plan == "propuesto"].valor_esperado_accion > 0).all()
    assert (g[g.valor_esperado_accion <= 0].banda_riesgo == "baja").all()          # con modelo o con respaldo


def test_huecos_cuando_no_hay_cuentas_suficientes():
    pl = pd.DataFrame({"comercial_asignado": ["COM-01"] * 4 + ["COM-02"], "estado_plan": ["propuesto"] * 4 + ["propuesto"]})
    h = P.huecos(pl, ["COM-01", "COM-02", "COM-03"], 4)
    assert h.plazas_sin_cubrir.to_dict() == {"COM-01": 0, "COM-02": 3, "COM-03": 4}


# ---------------------------------------------------------------- motivo, acción y pruebas desde modelo_churn
def _explicacion(ids, factor, motivo, secundario=None, **valores):
    d = {"id_cliente": ids, "factor_1": factor, "contribucion_1": 1.0, "factor_2": None, "contribucion_2": np.nan,
         "factor_3": None, "contribucion_3": np.nan, "motivo_modelo": motivo, "motivo_modelo_secundario": secundario,
         "var_recencia_dias": 30.0, "var_tendencia": 0.0}
    d.update(valores)
    return pd.DataFrame(d)


def test_motivo_y_pruebas_salen_del_modelo(salida):
    _, g, x = salida
    caso = _caso(g, cambio_interlocutor_12m=True, valor_cuenta=500000.0); caso["id_cliente"] = "MOD1"
    gg, _ = P.riesgo(pd.concat([g, caso]), CFG, pd.DataFrame({"id_cliente": ["MOD1"], "prob_abandono": [0.9]}),
                     _explicacion(["MOD1"], "dias_sin_contacto", "perdida_contacto", var_dias_sin_contacto=150.0))
    r = gg.set_index("id_cliente").loc["MOD1"]
    assert r.motivo_principal == "perdida_contacto" and r.fuente_motivo == "modelo"   # no los puntos de señales
    assert "150 días sin contacto comercial con respuesta" in P.evidencias(r)
    assert not any("%" in e for e in P.evidencias(r))         # la probabilidad no entra en los materiales
    assert P.plan(gg, CFG, x["p"], x["f"], T).set_index("id_cliente").loc["MOD1"].accion_id == "llamada_reactivacion"


def test_reclamacion_y_factura_vencida_mandan_sobre_el_modelo(salida):
    _, g, _ = salida
    a = _caso(g, reclamaciones_sin_resolver=1); a["id_cliente"] = "REC"
    b = _caso(g, facturas_vencidas_impagadas=2); b["id_cliente"] = "VEN"
    ex = _explicacion(["REC", "VEN"], "tendencia", "presupuesto_inversion", var_tendencia=-0.5)
    gg, _ = P.riesgo(pd.concat([g, a, b]), CFG, pd.DataFrame({"id_cliente": ["REC", "VEN"], "prob_abandono": [0.9, 0.9]}), ex)
    r = gg.set_index("id_cliente")
    assert r.at["REC", "motivo_principal"] == "servicio_reclamacion" and r.at["REC", "fuente_motivo"] == "regla_negocio"
    assert r.at["VEN", "motivo_principal"] == "cobro_financiero"
    assert r.at["REC", "motivo_secundario"] == "presupuesto_inversion"
    assert any("reclamación" in e for e in P.evidencias(r.loc["REC"]))


def test_cuentas_sin_puntuar_siguen_con_el_respaldo(salida):
    _, g, _ = salida
    ex = _explicacion(list(g.id_cliente.iloc[:5]), "tendencia", "presupuesto_inversion")
    gg, _ = P.riesgo(g, CFG, None, ex)            # sin puntuaciones: nada viene del modelo
    assert (gg.fuente_motivo == "respaldo").all()


def test_todos_los_motivos_del_modelo_tienen_accion_y_motivo_confirmable():
    from modelo_churn.explicar import MOTIVO_DE_VARIABLE
    for m in set(MOTIVO_DE_VARIABLE.values()) | {"desconocido"}:
        assert m in P.ACCION and P.MOTIVO_CONFIRMABLE[m] in P.OPCIONES_MOTIVO
