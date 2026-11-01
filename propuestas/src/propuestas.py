"""
Meridiano · Automatismo de propuestas de retención de anunciantes (FORGEN v2.0, nodos N01-N07).

  N01 foto a fecha de corte (solo datos <= T)   N02 variables por campaña y temporada esperada
  N03 riesgo: scores del modelo externo si existen (data/scores_modelo.csv); si no, respaldo de señales
  N04 motivo + ficha de cuenta                    N05 plan: matriz de acciones, capacidad, control, límites
  N06 materiales (plantilla; LLM opcional con validador de cifras)   N07 exportación para el CRM + log

El sistema PROPONE; el comercial aprueba y envía. Nunca escribe al anunciante.
"""
import argparse, hashlib, json, os, re, uuid
from datetime import datetime
import numpy as np, pandas as pd

TIPOS_CONTACTO = {"Llamada", "Email comercial", "Visita", "Videollamada"}
RES_EFECTIVO = {"Contacto efectivo", "Interesado", "Pospone decision", "Seguimiento de campana"}
NOMBRE_MES = "enero febrero marzo abril mayo junio julio agosto septiembre octubre noviembre diciembre".split()
CONFIRMACION = ["estado_confirmado_comercial", "motivo_confirmado", "diagnostico_correcto", "comentario_comercial"]
OPCIONES_ESTADO = ["Perdido", "Redujo mucho", "Activo", "Pausa: volvió después", "No sé"]
OPCIONES_MOTIVO = ["rendimiento_campanas", "relacion_interlocutor", "perdida_contacto", "servicio_reclamacion",
                   "presupuesto_inversion", "cobro_financiero", "temporada", "otro"]
ORDEN_MOTIVOS = ["relacion_interlocutor", "servicio_reclamacion", "rendimiento_campanas",
                 "perdida_contacto", "presupuesto_inversion", "cobro_financiero", "inactividad"]


def eur(x): return f"{x:,.0f} €".replace(",", ".")
def pct(x): return f"{x*100:.1f} %".replace(".", ",")


# ------------------------------------------------------------------ N01 · foto a fecha de corte
def cargar(datos):
    rd = lambda n, fechas: pd.read_csv(os.path.join(datos, n + ".csv"), parse_dates=fechas)
    t = dict(c=rd("dim_clientes", ["fecha_alta"]), p=rd("dim_productos", []),
             f=rd("fact_campanas", ["fecha_orden", "fecha_emision"]),
             fa=rd("fact_facturacion", ["fecha_emision", "fecha_vencimiento", "fecha_cobro"]),
             it=rd("fact_interacciones", ["fecha"]), o=rd("oportunidades", ["fecha_envio", "fecha_cierre"]),
             dc=rd("dim_comercial", []))
    sp = os.path.join(datos, "scores_modelo.csv")
    t["scores"] = pd.read_csv(sp)[["id_cliente", "prob_abandono"]] if os.path.exists(sp) else None
    return t


def foto(t, T):
    """Filtra cada tabla a lo conocido en T. Un cobro posterior a T se trata como pendiente."""
    fa = t["fa"][t["fa"].fecha_emision <= T].copy()
    fa.loc[fa.fecha_cobro > T, ["fecha_cobro", "dias_retraso"]] = np.nan
    o = t["o"][t["o"].fecha_envio <= T].copy()
    o.loc[o.fecha_cierre > T, "desenlace"] = "Abierta"
    return dict(c=t["c"][t["c"].fecha_alta <= T], p=t["p"], f=t["f"][t["f"].fecha_emision <= T],
                fa=fa, it=t["it"][t["it"].fecha <= T], o=o, dc=t["dc"])


# ------------------------------------------------------------------ N02 · variables
def variables(x, T, cfg):
    f, it, fa, o, p = x["f"], x["it"], x["fa"], x["o"], x["p"]
    d = lambda n: T - pd.Timedelta(days=n)
    ini = f.sort_values("fecha_emision").groupby("id_campana").agg(
        id_cliente=("id_cliente", "first"), fe=("fecha_emision", "min"), id_producto=("id_producto", "first")).reset_index()
    g = pd.DataFrame(index=x["c"].id_cliente)
    g["ultima_actividad"] = f.groupby("id_cliente").fecha_emision.max()
    g = g[g.ultima_actividad.notna()]
    g["recencia_dias"] = (T - g.ultima_actividad).dt.days
    g = g[g.recencia_dias <= cfg["horizonte_actividad_dias"]]
    g["n_campanas_total"] = ini.groupby("id_cliente").size()
    g["n_campanas_12m"] = ini[ini.fe > d(365)].groupby("id_cliente").size()
    g["ciclo_mediano_campanas_dias"] = ini.sort_values("fe").groupby("id_cliente").fe.apply(lambda s: s.diff().dt.days.median())
    fac = lambda a, b: f[(f.fecha_emision > d(a)) & (f.fecha_emision <= d(b))].groupby("id_cliente").importe_eur.sum()
    g["facturacion_12m"] = fac(365, 0); g["facturacion_6m"] = fac(182, 0); g["facturacion_6m_previos"] = fac(365, 182)
    g["facturacion_24m"] = fac(730, 0)
    g = g.fillna({"n_campanas_12m": 0, "facturacion_12m": 0, "facturacion_6m": 0, "facturacion_6m_previos": 0, "facturacion_24m": 0})
    g["tendencia_6m"] = ((g.facturacion_6m - g.facturacion_6m_previos) / g.facturacion_6m_previos.clip(lower=1)).clip(-1, 1)
    g["valor_cuenta"] = np.maximum(g.facturacion_12m, g.facturacion_24m / 2)
    f12 = f[f.fecha_emision > d(365)]
    g["n_familias_12m"] = f12.groupby("id_cliente").familia.nunique()
    comp = set(p[p.es_producto_compromiso].id_producto)
    g["usa_producto_compromiso"] = f[f.id_producto.isin(comp)].groupby("id_cliente").size().reindex(g.index).fillna(0) > 0
    # rendimiento: CTR relativo al mediano del producto, ambos con datos <= T
    med = f[f.impresiones > 0].assign(ctr=lambda z: z.clics / z.impresiones).groupby("id_producto").ctr.median()
    m = f12[f12.impresiones > 0].assign(ctr=lambda z: z.clics / z.impresiones)
    m["rel"] = m.ctr / m.id_producto.map(med)
    g["ctr_relativo_12m"] = m.groupby("id_cliente").rel.mean()
    g["leads_entregados_12m"] = f12.groupby("id_cliente").leads_entregados.sum()
    g["producto_principal_12m"] = f12.groupby("id_cliente").id_producto.agg(lambda s: s.value_counts().index[0])
    # relación
    con = it[it.tipo.isin(TIPOS_CONTACTO)]
    ult = con.groupby("id_cliente").fecha.max()
    g["dias_sin_contacto"] = (T - ult.reindex(g.index)).dt.days
    g["dias_sin_contacto"] = g.dias_sin_contacto.fillna((T - x["c"].set_index("id_cliente").fecha_alta.reindex(g.index)).dt.days)
    g["contactos_efectivos_90d"] = con[(con.fecha > d(90)) & con.resultado.isin(RES_EFECTIVO)].groupby("id_cliente").size()
    ci = it[(it.tipo == "Cambio de interlocutor")]
    g["cambio_interlocutor_12m"] = ci[ci.fecha > d(365)].groupby("id_cliente").size().reindex(g.index).fillna(0) > 0
    g["dias_desde_cambio_interlocutor"] = (T - ci.groupby("id_cliente").fecha.max().reindex(g.index)).dt.days
    g["eventos_asistidos_12m"] = it[it.tipo.str.startswith("Asistencia") & (it.fecha > d(365))].groupby("id_cliente").size()
    rec = it[it.tipo == "Reclamacion"]
    g["reclamaciones_12m"] = rec[rec.fecha > d(365)].groupby("id_cliente").size()
    g["reclamaciones_sin_resolver"] = rec[rec.resultado == "Sin resolver"].groupby("id_cliente").size()
    # cobro
    fa12 = fa[fa.fecha_emision > d(365)]
    g["retraso_cobro_medio_12m"] = fa12[fa12.fecha_cobro.notna()].groupby("id_cliente").dias_retraso.mean()
    g["facturas_vencidas_impagadas"] = fa[(fa.fecha_vencimiento <= T) & fa.fecha_cobro.isna()].groupby("id_cliente").size()
    # comercial
    g["propuestas_abiertas"] = o[o.desenlace == "Abierta"].groupby("id_cliente").size()
    g["propuestas_muertas_12m"] = o[(o.desenlace == "Muerta en silencio") & (o.fecha_cierre > d(365))].groupby("id_cliente").size()
    for k in ["contactos_efectivos_90d", "eventos_asistidos_12m", "reclamaciones_12m", "reclamaciones_sin_resolver",
              "facturas_vencidas_impagadas", "propuestas_abiertas", "propuestas_muertas_12m", "n_familias_12m", "leads_entregados_12m"]:
        g[k] = g[k].fillna(0).astype(int)
    # temporada esperada
    cv = cfg["ventana_estacional"]
    cli = x["c"].set_index("id_cliente")
    ini["mes"] = ini.fe.dt.month; ini["categoria"] = ini.id_cliente.map(cli.categoria)
    meses_cat = ini.groupby("categoria").mes.agg(lambda s: set(s.value_counts().index[:cv["meses_categoria"]]))
    meses_cli = ini.groupby("id_cliente").mes.agg(set)
    def proxima(cid):
        ms = meses_cli.get(cid, set()) if g.at[cid, "n_campanas_total"] >= cv["min_campanas_propias"] else meses_cat.get(cli.at[cid, "categoria"], set())
        if not ms: return np.nan, ""
        best = None
        for k in range(0, 13):
            mm = ((T.month + k - 1) % 12) + 1
            if mm in ms:
                y = T.year + (T.month + k - 1) // 12
                dd = max(0, (pd.Timestamp(y, mm, 1) - T).days); best = (dd, NOMBRE_MES[mm - 1]); break
        return best if best else (np.nan, "")
    pr = {cid: proxima(cid) for cid in g.index}
    g["dias_hasta_proxima_ventana"] = [pr[c][0] for c in g.index]
    g["proxima_ventana_mes"] = [pr[c][1] for c in g.index]
    g = g.join(cli[["razon_social", "categoria", "tamano", "comercial_asignado"]])
    g["fecha_corte"] = T.date()
    return g.reset_index().rename(columns={"index": "id_cliente"})


# ------------------------------------------------------------------ N03 · riesgo
def riesgo(g, cfg, scores=None):
    r = cfg["respaldo_senales"]; g = g.copy().reset_index(drop=True)
    pts = pd.DataFrame(index=g.index)
    pts["presupuesto_inversion"] = np.where(g.tendencia_6m < r["tendencia_6m_menor_que"], r["peso_tendencia"], 0)
    pts["rendimiento_campanas"] = np.where(g.ctr_relativo_12m < r["ctr_relativo_menor_que"], r["peso_ctr"], 0)
    pts["relacion_interlocutor"] = np.where(g.cambio_interlocutor_12m, r["peso_cambio_interlocutor_12m"], 0)
    pts["servicio_reclamacion"] = np.where(g.reclamaciones_sin_resolver > 0, r["peso_reclamacion_sin_resolver"], 0)
    pts["perdida_contacto"] = np.where(g.dias_sin_contacto > r["dias_sin_contacto_mayor_que"], r["peso_sin_contacto"], 0)
    pts["cobro_financiero"] = np.where(g.facturas_vencidas_impagadas > 0, r["peso_factura_vencida"], 0)
    umbral_inact = np.maximum(210, r["factor_ciclo_inactividad"] * g.ciclo_mediano_campanas_dias.fillna(0))
    pts["inactividad"] = np.where(g.recencia_dias > umbral_inact, r["peso_inactividad"], 0)
    g["puntos_respaldo"] = pts.sum(axis=1)
    senal_fuerte = (pts.relacion_interlocutor > 0) | (pts.servicio_reclamacion > 0)
    # Pausa estacional: su temporada llega pronto y solo hay señales compatibles con una pausa
    # (caída de inversión, falta de contacto, inactividad). Relación, servicio o rendimiento la descartan.
    g["pausa_estacional_probable"] = ((g.dias_hasta_proxima_ventana <= cfg["ventana_estacional"]["dias_hasta_proxima_ventana_max"])
                                      & ~senal_fuerte & (pts.rendimiento_campanas == 0))
    if scores is not None:
        s = scores.set_index("id_cliente")
        g["prob_abandono"] = g.id_cliente.map(s.prob_abandono)
        g["fuente_riesgo"] = np.where(g.prob_abandono.notna(), "modelo", "respaldo")
    else:
        g["prob_abandono"] = np.nan; g["fuente_riesgo"] = "respaldo"
    alta, media = r["banda_alta_desde"], r["banda_media_desde"]
    banda_resp = np.where(g.puntos_respaldo >= alta, "alta", np.where(g.puntos_respaldo >= media, "media", "baja"))
    # Con modelo (decisión: actuar con L2 × valor): se actúa si el valor esperado de la acción es positivo
    ve = cfg.get("valor_esperado", {"coste_accion_eur": 120, "tasa_recuperacion": 0.2, "banda_alta_prob_desde": 0.6})
    g["valor_esperado_accion"] = g.prob_abandono * g.valor_cuenta * ve["tasa_recuperacion"] - ve["coste_accion_eur"]
    banda_mod = np.where(g.valor_esperado_accion > 0,
                         np.where(g.prob_abandono >= ve["banda_alta_prob_desde"], "alta", "media"), "baja")
    g["banda_riesgo"] = np.where(g.fuente_riesgo == "modelo", banda_mod, banda_resp)
    # La pausa estacional no rebaja la prioridad (podría ser un abandono real): cambia la acción en N05.
    intensidad = np.where(g.fuente_riesgo == "modelo", g.prob_abandono, g.puntos_respaldo / max(1, alta))
    g["facturacion_en_riesgo"] = (g.valor_cuenta * np.clip(intensidad, 0, 1)).round(0)
    # N04 · motivo
    orden = {m: i for i, m in enumerate(ORDEN_MOTIVOS)}
    def motivos(i):
        fila = pts.loc[i]; act = [m for m in fila.index if fila[m] > 0]
        act.sort(key=lambda m: (-fila[m], orden[m]))
        return (act[0] if act else "desconocido"), (act[1] if len(act) > 1 else None)
    mm = [motivos(i) for i in g.index]
    g["motivo_principal"] = [a for a, _ in mm]; g["motivo_secundario"] = [b for _, b in mm]
    return g, pts


def evidencias(r):
    e = []
    if r.tendencia_6m < -0.3: e.append(f"inversión 6 meses {eur(r.facturacion_6m)} frente a {eur(r.facturacion_6m_previos)} el semestre anterior ({pct(r.tendencia_6m)})")
    if pd.notna(r.ctr_relativo_12m) and r.ctr_relativo_12m < 0.8: e.append(f"CTR de sus campañas al {r.ctr_relativo_12m:.2f} del habitual en esos productos".replace(".", ","))
    if r.cambio_interlocutor_12m: e.append(f"cambio de interlocutor hace {int(r.dias_desde_cambio_interlocutor)} días")
    if r.reclamaciones_sin_resolver > 0: e.append(f"{r.reclamaciones_sin_resolver} reclamación(es) sin resolver")
    if r.dias_sin_contacto > 90: e.append(f"{int(r.dias_sin_contacto)} días sin contacto comercial")
    if r.facturas_vencidas_impagadas > 0: e.append(f"{r.facturas_vencidas_impagadas} factura(s) vencida(s) sin cobrar")
    e.append(f"última campaña hace {int(r.recencia_dias)} días")
    return e


# ------------------------------------------------------------------ N05 · plan de acción
ACCION = {"relacion_interlocutor": "reunion_nuevo_interlocutor", "servicio_reclamacion": "resolucion_reclamacion",
          "rendimiento_campanas": "informe_resultados_y_optimizacion", "perdida_contacto": "llamada_reactivacion",
          "presupuesto_inversion": "reserva_anticipada_temporada", "cobro_financiero": "revision_condiciones_pago",
          "inactividad": "llamada_reactivacion", "desconocido": "llamada_reactivacion"}


def plan(g, cfg, p, f_hasta_T, T):
    g = g[g.banda_riesgo.isin(["alta", "media"])].copy()
    clave = g.valor_cuenta >= g.valor_cuenta.quantile(cfg["percentil_cuentas_clave"]) if len(g) else pd.Series(dtype=bool)
    g["cuenta_clave"] = clave
    g["accion_id"] = g.motivo_principal.map(ACCION)
    # E2: contracción (sigue comprando pero invierte mucho menos) frente a pérdida total
    tr = cfg.get("tipo_riesgo", {"dias_compra_reciente": 120, "tendencia_contraccion_menor_que": -0.3})
    g["tipo_riesgo"] = np.where((g.recencia_dias <= tr["dias_compra_reciente"]) & (g.tendencia_6m < tr["tendencia_contraccion_menor_que"]),
                                "contraccion", "perdida_total")
    prioritarios = {"relacion_interlocutor", "servicio_reclamacion", "cobro_financiero"}
    g.loc[(g.tipo_riesgo == "contraccion") & ~g.motivo_principal.isin(prioritarios), "accion_id"] = "informe_resultados_y_optimizacion"
    g.loc[(g.accion_id == "llamada_reactivacion") & (g.eventos_asistidos_12m > 0), "accion_id"] = "invitacion_evento"
    g.loc[g.pausa_estacional_probable, "accion_id"] = "reserva_anticipada_temporada"
    lejos = (g.accion_id == "reserva_anticipada_temporada") & ~(g.dias_hasta_proxima_ventana <= 90)
    g.loc[lejos, "accion_id"] = "llamada_reactivacion"   # sin temporada cercana ni modelo de venta cruzada
    # producto sugerido (sin modelo de venta cruzada: reglas trazables)
    med = (f_hasta_T[f_hasta_T.impresiones > 0].assign(ctr=lambda z: z.clics / z.impresiones)
           .groupby("id_producto").ctr.median())
    fam = p.set_index("id_producto").familia; nom = p.set_index("id_producto").nombre
    def sugerido(r):
        if r.accion_id == "informe_resultados_y_optimizacion" and pd.notna(r.producto_principal_12m):
            cand = med[med.index.map(fam) == fam.get(r.producto_principal_12m)]
            cand = cand.drop(r.producto_principal_12m, errors="ignore")
            return cand.idxmax() if len(cand) else None
        if r.accion_id == "reserva_anticipada_temporada":
            return r.producto_principal_12m if pd.notna(r.producto_principal_12m) else None
        return None
    g["producto_sugerido"] = g.apply(sugerido, axis=1)
    g["producto_sugerido_nombre"] = g.producto_sugerido.map(nom)
    # grupo de control: 20 % reproducible de la banda media, nunca cuentas clave. El sorteo es estable durante el
    # trimestre (no por fecha de corte): con el ciclo semanal, una cuenta no cambia de grupo de una semana a otra
    trimestre = f"{T.year}-T{(T.month - 1) // 3 + 1}"
    h = g.id_cliente.astype(str).map(lambda s: int(hashlib.sha256(f"{s}|{trimestre}".encode()).hexdigest(), 16) % 100)
    g["grupo_experimental"] = np.where((g.banda_riesgo == "media") & ~g.cuenta_clave &
                                       (h < cfg["porcentaje_control_banda_media"] * 100), "control", "tratamiento")
    g["requiere_direccion"] = g.cuenta_clave
    g["prioridad_valor"] = g.facturacion_en_riesgo
    g = g.sort_values(["grupo_experimental", "prioridad_valor"], ascending=[False, False])
    cap = cfg["capacidad_semanal_por_comercial"] * cfg["semanas_del_plan"]
    g["estado_plan"] = "control"
    tr = g.grupo_experimental == "tratamiento"
    g.loc[tr, "orden_comercial"] = g[tr].groupby("comercial_asignado").cumcount() + 1
    g.loc[tr, "estado_plan"] = np.where(g.loc[tr, "orden_comercial"] <= cap, "propuesto", "aplazado")
    plazos = cfg["plazos_dias"]
    g["fecha_limite"] = [(T + pd.Timedelta(days=plazos.get(a, plazos["por_defecto"]))).date() for a in g.accion_id]
    g["justificacion"] = g.apply(lambda r: f"Motivo {r.motivo_principal.replace('_', ' ')}; banda {r.banda_riesgo}; "
                                           f"facturación en riesgo {eur(r.facturacion_en_riesgo)}" +
                                           ("; cuenta clave: revisa dirección comercial" if r.cuenta_clave else ""), axis=1)
    return g


# ------------------------------------------------------------------ N06 · materiales
def plantilla(r, ev):
    s = f"Estimado/a responsable de marketing de {r.razon_social}:"
    base = {
        "reunion_nuevo_interlocutor": ("Agenda de reunión de presentación",
            f"{s}\n\nNos gustaría presentarnos y repasar con usted lo que su marca ha conseguido con Meridiano en los últimos meses. "
            f"Propuesta de agenda (30 minutos):\n1. Resultados de sus campañas recientes.\n2. Objetivos de su marca para los próximos meses.\n"
            f"3. Calendario de oportunidades del público senior para su sector.\n¿Le encaja alguna fecha en los próximos quince días?"),
        "resolucion_reclamacion": ("Seguimiento de su incidencia",
            f"{s}\n\nQueremos cerrar la incidencia que tiene abierta con nosotros antes de cualquier otra conversación. "
            f"Le propongo una llamada breve esta semana para confirmar la solución y que quede resuelta."),
        "informe_resultados_y_optimizacion": ("Informe de resultados y propuesta de mejora",
            f"{s}\n\nLe adjunto el resumen de sus últimas campañas. Hemos detectado margen de mejora en el rendimiento"
            + (f" y creemos que el formato {r.producto_sugerido_nombre} encaja mejor con sus objetivos" if pd.notna(r.producto_sugerido_nombre) else "")
            + ". ¿Podemos revisarlo juntos en una llamada?"),
        "llamada_reactivacion": ("Guion de llamada",
            "1. Interesarse por los objetivos actuales de la marca.\n2. Repasar resultados de su última campaña.\n"
            "3. Presentar el calendario de próximos meses de su sector.\n4. Acordar un siguiente paso con fecha."),
        "invitacion_evento": ("Invitación a la próxima jornada",
            f"{s}\n\nEsta temporada celebramos nuevas jornadas con profesionales y público senior de su sector. "
            f"Nos encantaría contar con usted como invitado y comentar en persona cómo encaja su marca."),
        "reserva_anticipada_temporada": ("Reserva anticipada para su temporada",
            f"{s}\n\nSe acerca {r.proxima_ventana_mes or 'su temporada'}, uno de sus momentos habituales de campaña. "
            f"Le propongo reservar con antelación"
            + (f" su {r.producto_sugerido_nombre}" if pd.notna(r.producto_sugerido_nombre) else " su espacio")
            + " para asegurar disponibilidad. ¿Lo vemos esta semana?"),
        "revision_condiciones_pago": ("Revisión de facturación",
            f"{s}\n\nQuería revisar con usted el estado de la facturación pendiente y encontrar la fórmula que mejor le encaje, antes de planificar nuevas campañas."),
    }
    titulo, cuerpo = base[r.accion_id]
    return titulo, cuerpo, "Notas internas (no enviar): " + "; ".join(ev)


def numeros(texto): return set(re.findall(r"\d+(?:[.,]\d+)?", texto))


def validar_llm(texto, contexto):
    """Sensor computacional de Govern: toda cifra del borrador debe estar en el input; sin condiciones económicas."""
    inventadas = numeros(texto) - numeros(contexto)
    economico = re.search(r"\d+\s*%|descuento|rebaja|gratis", texto, re.I)
    return (len(inventadas) == 0 and not economico), sorted(inventadas)


def material_llm(r, ev, cfg):
    import anthropic  # solo si se activa el LLM
    contexto = (f"Anunciante: {r.razon_social} ({r.categoria}). Acción: {r.accion_id}. Motivo: {r.motivo_principal}. "
                f"Producto sugerido: {r.producto_sugerido_nombre}. Próxima temporada: {r.proxima_ventana_mes}. Datos: " + "; ".join(ev))
    sistema = ("Preparas materiales para un comercial de Meridiano, medio para el público senior que vive de anunciantes. "
               "Reglas: usa solo cifras del contexto, tal cual; nunca menciones que el cliente está en riesgo; "
               "no incluyas ninguna condición económica ni porcentaje; tono profesional y cercano, de usted; máximo 200 palabras. "
               "Devuelve solo el texto del material.")
    cli = anthropic.Anthropic()
    msg = cli.messages.create(model=cfg["llm"]["modelo"], max_tokens=cfg["llm"]["max_tokens"], system=sistema,
                              messages=[{"role": "user", "content": contexto}])
    texto = msg.content[0].text
    ok, inv = validar_llm(texto, contexto)
    return texto, ok, inv


def materiales(g, cfg):
    out = []
    for _, r in g.iterrows():
        ev = evidencias(r); titulo, cuerpo, notas = plantilla(r, ev); fuente = "plantilla"
        if cfg["llm"]["usar"] and r.estado_plan == "propuesto":
            try:
                texto, ok, inv = material_llm(r, ev, cfg)
                if ok: cuerpo, fuente = texto, "llm"
                else: fuente = f"plantilla (LLM descartado: cifras no trazables {inv})"
            except Exception as e:
                fuente = f"plantilla (LLM no disponible: {type(e).__name__})"
        out.append(dict(material_titulo=titulo, material_cuerpo=cuerpo, notas_internas=notas,
                        evidencias="; ".join(ev), fuente_material=fuente))
    return pd.concat([g.reset_index(drop=True), pd.DataFrame(out)], axis=1)


# ------------------------------------------------------------------ N07 · exportación y log
def ficha(r):
    return (f"{r.razon_social} · {r.categoria} · {r.tamano}. Valor de cuenta {eur(r.valor_cuenta)}; riesgo {r.banda_riesgo} "
            f"({r.fuente_riesgo}). Motivo: {r.motivo_principal.replace('_', ' ')}. Señales: {r.evidencias}.")


def anadir_desplegables(ruta, hoja, columnas):
    """Listas cerradas para que la confirmación del comercial sea comparable con la etiqueta."""
    from openpyxl import load_workbook
    from openpyxl.worksheet.datavalidation import DataValidation
    from openpyxl.utils import get_column_letter as L
    wb = load_workbook(ruta); ws = wb[hoja]; n = max(ws.max_row, 2)
    for col, opciones in [("estado_confirmado_comercial", OPCIONES_ESTADO), ("motivo_confirmado", OPCIONES_MOTIVO),
                          ("diagnostico_correcto", ["Sí", "No"])]:
        dv = DataValidation(type="list", formula1='"' + ",".join(opciones) + '"', allow_blank=True)
        c = L(columnas.index(col) + 1); dv.add(f"{c}2:{c}{n}"); ws.add_data_validation(dv)
    wb.save(ruta)


def ejecutar(datos, config, salida):
    cfg = json.load(open(config, encoding="utf-8")); os.makedirs(salida, exist_ok=True)
    T = pd.Timestamp(cfg["fecha_corte"]); t0 = datetime.now()
    t = cargar(datos); x = foto(t, T)
    g = variables(x, T, cfg)
    g, _ = riesgo(g, cfg, t["scores"])
    # Ciclo semanal: fuera del plan las cuentas propuestas o en control en los últimos dias_enfriamiento días
    rec_ruta = os.path.join(datos, "propuestas_recientes.csv")
    en_seguimiento = 0
    if os.path.exists(rec_ruta):
        rec = pd.read_csv(rec_ruta, dtype={"id_cliente": str})
        excl = g.id_cliente.astype(str).isin(set(rec.id_cliente))
        en_seguimiento = int(excl.sum()); g = g[~excl].copy()
    pl = materiales(plan(g, cfg, x["p"], x["f"], T), cfg)
    pl["ficha_cuenta"] = pl.apply(ficha, axis=1)
    com = x["dc"].set_index("id_comercial")
    pl["comercial_nombre"] = pl.comercial_asignado.map(com.nombre)
    cols = ["comercial_asignado", "comercial_nombre", "orden_comercial", "estado_plan", "id_cliente", "razon_social", "categoria",
            "tipo_riesgo", "banda_riesgo", "fuente_riesgo", "prob_abandono", "valor_esperado_accion", "pausa_estacional_probable", "facturacion_en_riesgo", "valor_cuenta", "cuenta_clave", "requiere_direccion",
            "motivo_principal", "motivo_secundario", "accion_id", "producto_sugerido", "producto_sugerido_nombre", "fecha_limite",
            "grupo_experimental", "justificacion", "ficha_cuenta", "material_titulo", "material_cuerpo", "notas_internas",
            "fuente_material", "fecha_corte"]
    prop = pl[pl.estado_plan == "propuesto"][cols].sort_values(["comercial_asignado", "orden_comercial"]).copy()
    # Validación continua de la etiqueta: el comercial confirma al cerrar cada propuesta (columnas a rellenar)
    for c in CONFIRMACION:
        prop[c] = None
    apl = pl[pl.estado_plan == "aplazado"][cols]; ctl = pl[pl.estado_plan == "control"][cols]
    resumen = (pl.groupby(["comercial_asignado", "estado_plan"]).size().unstack(fill_value=0)
               .join(pl[pl.estado_plan == "propuesto"].groupby("comercial_asignado").facturacion_en_riesgo.sum().rename("facturacion_en_riesgo_propuesta")))
    with pd.ExcelWriter(os.path.join(salida, "propuestas_retencion.xlsx")) as xl:
        prop.to_excel(xl, sheet_name="Plan_por_comercial", index=False); apl.to_excel(xl, sheet_name="Aplazados", index=False)
        ctl.to_excel(xl, sheet_name="Grupo_control", index=False); resumen.to_excel(xl, sheet_name="Resumen")
        g.to_excel(xl, sheet_name="Riesgo_todos", index=False)
    crm = prop.assign(tipo_tarea=prop.accion_id, estado="Pendiente de aprobación")[
        ["id_cliente", "comercial_asignado", "tipo_tarea", "fecha_limite", "estado", "justificacion", "material_titulo", "material_cuerpo"] + CONFIRMACION]
    crm.to_csv(os.path.join(salida, "crm_tareas.csv"), index=False)
    anadir_desplegables(os.path.join(salida, "propuestas_retencion.xlsx"), "Plan_por_comercial", list(prop.columns))
    g.to_csv(os.path.join(salida, "exec_n02_n03_riesgo.csv"), index=False)
    log = dict(execution_id=str(uuid.uuid4()), timestamp=t0.isoformat(), node_version="propuestas-1.0",
               fecha_corte=str(T.date()), fuente_riesgo="modelo" if t["scores"] is not None else "respaldo",
               anunciantes_evaluados=int(len(g)), en_seguimiento=en_seguimiento, propuestos=int(len(prop)), aplazados=int(len(apl)), control=int(len(ctl)),
               latency_ms=int((datetime.now() - t0).total_seconds() * 1000), status="success", parametros=cfg)
    json.dump(log, open(os.path.join(salida, "log_ejecucion.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    print(resumen.to_string()); print(f"\nEvaluados {len(g)} · en seguimiento (enfriamiento) {en_seguimiento} · propuestos {len(prop)} · aplazados {len(apl)} · control {len(ctl)} · riesgo: {log['fuente_riesgo']}")
    return pl, g


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--datos", default="data"); ap.add_argument("--config", default="config/parametros.json")
    ap.add_argument("--salida", default="resultados"); a = ap.parse_args()
    ejecutar(a.datos, a.config, a.salida)
