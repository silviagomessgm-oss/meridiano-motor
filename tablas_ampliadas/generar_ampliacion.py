"""
Meridiano · Ampliación de los datos sintéticos (ene-2020 → 27-nov-2026)

Añade filas a las tablas originales (tablas/, oct-2023 → sep-2026) SIN MODIFICAR NINGUNA: las filas originales se copian
byte a byte y las nuevas se añaden al final con identificadores que continúan la numeración.

  · Hacia atrás (ene-2020 → sep-2023): la historia previa de los anunciantes actuales dados de alta antes de oct-2023 y
    anunciantes antiguos que abandonaron antes de oct-2023 (no existían en los datos originales).
  · Hacia delante (sep-2026 → 27-nov-2026): la continuación de los anunciantes actuales y algunas altas nuevas.

Método (para no inventar reglas que luego «descubra» el modelo):
  · Cada campaña nueva es una copia de una campaña REAL de un anunciante del mismo tamaño (productos, importes, duración,
    impresiones, clics), desplazada en el tiempo y con un ±5 % de ruido. Los anunciantes actuales siguen su propio ritmo
    anual y su estacionalidad (mezclada con la de su sector).
  · El abandono sigue el mecanismo documentado en el caso: el 70 % de las bajas va precedido de un descenso de la inversión
    y del CTR en los últimos 6 meses; el 30 % desaparece de golpe. El cambio de interlocutor y las reclamaciones se
    calibran para que su relación con el abandono sea la de los datos originales.
  · Interacciones, facturas y oportunidades se generan con las frecuencias y distribuciones medidas en los datos originales.

Uso:  python tablas_ampliadas/generar_ampliacion.py      (semilla fija: el resultado es reproducible)
"""
import os, re, sys, math
import numpy as np, pandas as pd

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ORIG = os.path.join(RAIZ, "tablas")
SAL = os.path.dirname(os.path.abspath(__file__))
INICIO, FIN_ATRAS = pd.Timestamp("2020-01-01"), pd.Timestamp("2023-09-30")
HOY = pd.Timestamp("2026-11-27")
REF_ANTIGUEDAD = pd.Timestamp("2026-09-30")          # la misma referencia que usan los datos originales
rng = np.random.default_rng(2020)

# Anunciantes activos por ejercicio (oct–sep) en la parte añadida. EF2024 real = 135; antes, crecimiento moderado con el
# bache de 2020 (supuesto). Se cubren con la historia de los anunciantes actuales y, el resto, con anunciantes antiguos.
OBJETIVO_ACTIVOS = {2020: 98, 2021: 110, 2022: 122, 2023: 130}
P_GRADUAL = 0.70                                       # bajas precedidas de descenso (Léame del caso)
# Los anunciantes que se dan de baja antes de oct-2023 (antiguos y los 35 sin campañas) tienen su última campaña como muy
# tarde el 30-jun-2023: así no entran en la población (≤ 540 días sin actividad) de los cortes de evaluación originales.
ULT_BAJA = pd.Timestamp(os.environ.get("CAL_UB", "2023-06-30"))
P_EF23 = float(os.environ.get("CAL_EF23", 1.0))  # anunciantes actuales sin compras hasta después de abr-24 que compran por última vez en oct-22–sep-23
# Señales, calibradas para que su relación con el abandono (etiqueta E2) sea la de los datos originales (ver README).
# Se pueden sobrescribir con variables de entorno CAL_* solo para recalibrar; los valores por defecto generan los CSV publicados.
CAL = dict(
    base_interlocutor=float(os.environ.get("CAL_BI", 0.015)),   # cambios de interlocutor al año, a cualquier anunciante
    p_interlocutor=float(os.environ.get("CAL_PI", 0.22)),      # probabilidad de un cambio antes de cada episodio de abandono
    base_reclamacion=0.04,
    p_base_sin_resolver=float(os.environ.get("CAL_PBR", 0.15)),  # de esas, sin resolver (solo anunciantes que no están en los originales)                                     # reclamaciones al año (resueltas), a cualquier anunciante
    p_reclamacion=float(os.environ.get("CAL_PR", 0.20)),       # reclamación sin resolver antes de una pérdida definitiva
    p_ctr=float(os.environ.get("CAL_PC", 0.35)),               # CTR un 40 % más bajo en el año previo a un episodio
    propuestas_mes=0.05,                                       # propuestas de ampliación no ganadas por anunciante y mes
    propuestas_previas=float(os.environ.get("CAL_PP", 0.8)),   # propuestas perdidas de más en los meses previos a un episodio
    ventana_interlocutor=int(os.environ.get("CAL_VI", 60)),    # días antes del corte en que se sitúa el cambio
)

# ---------------------------------------------------------------- lectura de los originales
L = lambda n, fechas=(): pd.read_csv(os.path.join(ORIG, n + ".csv"), parse_dates=list(fechas), keep_default_na=True)
cli = L("dim_clientes", ["fecha_alta"]); camp = L("fact_campanas", ["fecha_orden", "fecha_emision"])
fac = L("fact_facturacion", ["fecha_emision", "fecha_vencimiento", "fecha_cobro"]); inter = L("fact_interacciones", ["fecha"])
opo = L("oportunidades", ["fecha_envio", "fecha_cierre"]); con = L("contactos"); com = L("dim_comercial")
prod = L("dim_productos").set_index("id_producto")
num = lambda s: int(re.sub(r"\D", "", s))
sig = {k: max(map(num, v)) + 1 for k, v in {"C": cli.id_cliente, "O": camp.id_orden, "K": camp.id_campana, "F": fac.id_factura,
                                              "I": inter.id_interaccion, "OP": opo.id_oportunidad,
                                              "L": opo.id_lead.dropna()}.items()}
ANCHO = {"C": 4, "O": 5, "K": 5, "F": 5, "I": 6, "OP": 5, "L": 5}
def nuevo_id(pref):
    v = sig[pref]; sig[pref] += 1
    return f"{pref}{v:0{ANCHO[pref]}d}"

camp = camp.merge(cli[["id_cliente", "tamano", "categoria"]], on="id_cliente", how="left")
# Todo lo que se mide en los datos originales para generar (plantillas, ritmos, frecuencias, calibración) usa solo datos
# hasta el último corte de entrenamiento (jun-2025): los cortes de prueba (sep-2025 y dic-2025) no intervienen.
REF = pd.Timestamp("2025-06-30")
camp_ref = camp[camp.fecha_emision <= REF]
plantillas = {t: [g for _, g in camp_ref[camp_ref.tamano == t].groupby("id_campana")] for t in cli.tamano.unique()}
propias = {c: [g for _, g in g0.groupby("id_campana")] for c, g0 in camp_ref.groupby("id_cliente")}

# Ritmo anual de campañas por anunciante actual (campañas / años entre su primera y última campaña, mínimo 1 año)
def ritmo(g):
    ini = g.groupby("id_campana").fecha_emision.min()
    años = max(1.0, (ini.max() - ini.min()).days / 365.25 + 0.5)
    return len(ini) / años
ritmo_cli = camp_ref.groupby("id_cliente").apply(ritmo, include_groups=False)
ritmos_tam = {t: ritmo_cli[ritmo_cli.index.isin(cli[cli.tamano == t].id_cliente)].values for t in cli.tamano.unique()}
tam_cli = cli.set_index("id_cliente").tamano
ritmo_de = lambda idc: ritmo_cli[idc] if idc in ritmo_cli.index else float(np.median(ritmos_tam[tam_cli[idc]]))
# Estacionalidad: meses de inicio de campaña por sector y por anunciante
mes_inicio = camp_ref.groupby("id_campana").agg(c=("id_cliente", "first"), cat=("categoria", "first"), f=("fecha_emision", "min"))
mes_inicio["m"] = mes_inicio.f.dt.month
est_sector = {k: (g.m.value_counts().reindex(range(1, 13), fill_value=0) + 1).values for k, g in mes_inicio.groupby("cat")}
est_cli = {k: g.m.value_counts().reindex(range(1, 13), fill_value=0).values for k, g in mes_inicio.groupby("c")}

def pesos_mes(id_c, cat):
    s = est_sector.get(cat, np.ones(12)).astype(float); s = s / s.sum()
    p = est_cli.get(id_c)
    if p is not None and p.sum() > 0:
        p = (p + 0.3) / (p + 0.3).sum(); s = 0.5 * s + 0.5 * p
    return s / s.sum()

# ---------------------------------------------------------------- generación de campañas
filas_camp = []

def emitir_campana(id_c, comercial, tam, inicio, propias_c=None, factor_importe=1.0, factor_ctr=1.0, limite=None, minimo=None):
    """Copia una campaña real (del propio anunciante si existe; si no, de uno del mismo tamaño) que empieza en `inicio`.
    `minimo` (fecha de alta): si la primera orden quedara antes, la campaña se retrasa al mes siguiente."""
    fuente = propias_c if propias_c and rng.random() < 0.7 else plantillas[tam]
    plant = fuente[rng.integers(len(fuente))].sort_values("fecha_emision")
    base = plant.fecha_emision.min()
    if minimo is not None:
        adelanto = int((plant.fecha_emision - plant.fecha_orden).dt.days.max())
        while inicio.replace(day=min(base.day, 28)) - pd.Timedelta(days=adelanto) < minimo:
            inicio = inicio + pd.DateOffset(months=1)
    if limite is not None and inicio.replace(day=min(base.day, 28)) > limite: return
    k = nuevo_id("K")
    for _, o in plant.iterrows():
        meses = (o.fecha_emision.year - base.year) * 12 + (o.fecha_emision.month - base.month)
        em = (inicio + pd.DateOffset(months=meses)).replace(day=min(o.fecha_emision.day, 28))
        if limite is not None and em > limite: break
        orden = em - pd.Timedelta(days=int((o.fecha_emision - o.fecha_orden).days))
        ruido = rng.normal(1, 0.05)
        imp = int(round(o.impresiones * rng.normal(1, 0.08))) if o.impresiones else 0
        cl = int(round(o.clics * rng.normal(1, 0.08) * factor_ctr)) if o.clics else 0
        filas_camp.append(dict(id_orden=nuevo_id("O"), id_cliente=id_c, id_producto=o.id_producto, familia=o.familia,
                               fecha_orden=orden, fecha_emision=em, mes_emision=em.strftime("%Y-%m"),
                               tarifa_base_eur=int(o.tarifa_base_eur), descuento_pct=o.descuento_pct,
                               importe_eur=round(o.importe_eur * ruido * factor_importe, 2), impresiones=max(imp, 0),
                               clics=max(min(cl, imp) if imp else cl, 0), leads_entregados=int(o.leads_entregados),
                               comercial=comercial, id_campana=k))

def inicios(id_c, cat, lam, desde, hasta):
    """Fechas de inicio de campaña: Poisson anual con la estacionalidad del anunciante."""
    p = pesos_mes(id_c, cat); out = []
    for año in range(desde.year, hasta.year + 1):
        a, b = max(desde, pd.Timestamp(f"{año}-01-01")), min(hasta, pd.Timestamp(f"{año}-12-31"))
        if a > b: continue
        meses_ok = [m for m in range(1, 13) if pd.Timestamp(f"{año}-{m:02d}-01") <= b and pd.Timestamp(f"{año}-{m:02d}-28") >= a]
        if not meses_ok: continue
        pm = p[[m - 1 for m in meses_ok]]; pm = pm / pm.sum()
        n = rng.poisson(lam * len(meses_ok) / 12 * (p[[m - 1 for m in meses_ok]].sum() * 12 / len(meses_ok)))
        for m in rng.choice(meses_ok, size=n, p=pm):
            d = pd.Timestamp(f"{año}-{m:02d}-{int(rng.integers(1, 29)):02d}")
            if a <= d <= b: out.append(d)
    return sorted(out)

# ---------------------------------------------------------------- 1. historia previa de los anunciantes actuales
perfil = {}         # id_cliente → dict(ventana, baja, gradual) para interacciones, facturas y oportunidades
primera_orig = camp.groupby("id_cliente").fecha_emision.min()
for _, c in cli[(cli.fecha_alta < "2023-10-01") & cli.id_cliente.isin(primera_orig.index)].iterrows():
    desde = max(c.fecha_alta, INICIO); hasta = FIN_ATRAS
    baja = None
    # Quien no compra hasta bien entrado el periodo original se trata como un anunciante que se fue y volvió (reactivación)
    ef23 = False
    if primera_orig[c.id_cliente] > pd.Timestamp("2024-04-30") and desde < pd.Timestamp("2022-10-01") and rng.random() < P_EF23:
        # Compra por última vez entre oct-22 y sep-23 y no vuelve hasta después de abr-24 (calibrado para que el abandono de
        # los cortes de 2023 ronde el 50 %, como en el resto)
        ef23 = True
        baja = pd.Timestamp("2022-11-01") + pd.Timedelta(days=int(rng.integers(0, 334)))
        hasta = baja
    elif primera_orig[c.id_cliente] > pd.Timestamp("2024-03-31") and rng.random() < 0.85 and desde < pd.Timestamp("2023-03-31"):
        baja = desde + pd.Timedelta(days=int(rng.integers(120, max(121, (pd.Timestamp("2023-06-30") - desde).days))))
        hasta = min(baja, FIN_ATRAS)
    lam = ritmo_de(c.id_cliente) * rng.normal(1, 0.1)
    gradual = rng.random() < P_GRADUAL
    for d in inicios(c.id_cliente, c.categoria, lam, desde, hasta):
        if rng.random() < 0.10: continue                                    # pausas puntuales
        decl = baja is not None and gradual and d > baja - pd.Timedelta(days=183)
        if decl and rng.random() < 0.5: continue
        emitir_campana(c.id_cliente, c.comercial_asignado, c.tamano, d, propias.get(c.id_cliente),
                       0.6 if decl else 1.0, 0.7 if decl else 1.0, limite=hasta, minimo=c.fecha_alta)
    if ef23 and not any(f["id_cliente"] == c.id_cliente and f["fecha_emision"] >= pd.Timestamp("2022-10-01") for f in filas_camp[-40:]):
        d = pd.Timestamp("2022-10-01") + pd.Timedelta(days=int(rng.integers(0, max(1, (baja - pd.Timestamp("2022-10-01")).days))))
        emitir_campana(c.id_cliente, c.comercial_asignado, c.tamano, d, propias.get(c.id_cliente), limite=hasta, minimo=c.fecha_alta)
    perfil[c.id_cliente] = dict(desde=desde, hasta=hasta, baja=baja, gradual=gradual, nuevo=False,
                                comercial=c.comercial_asignado, tam=c.tamano, en_originales=True)

# ---------------------------------------------------------------- 1b. los 35 anunciantes de dim_clientes sin campañas
# Están dados de alta (2016–2022) y reciben propuestas de recuperación en el periodo original, pero no compran: son
# anunciantes que abandonaron antes de oct-2023. Se genera su historia desde el alta (o ene-2020) hasta su baja.
sin_camp = cli[~cli.id_cliente.isin(primera_orig.index)]
for _, c in sin_camp.iterrows():
    desde = max(c.fecha_alta, INICIO)
    margen = (ULT_BAJA - desde).days
    baja = desde + pd.Timedelta(days=int(rng.integers(min(180, margen - 1), margen)))
    lam = max(rng.choice(ritmos_tam[c.tamano]) * rng.normal(1, 0.15), 0.8)
    gradual = rng.random() < P_GRADUAL; n0 = len(filas_camp)
    for d in inicios(c.id_cliente, c.categoria, lam, desde, baja):
        decl = gradual and d > baja - pd.Timedelta(days=183)
        if decl and rng.random() < 0.5: continue
        emitir_campana(c.id_cliente, c.comercial_asignado, c.tamano, d, None, 0.6 if decl else 1.0, 0.7 if decl else 1.0,
                       limite=baja, minimo=c.fecha_alta)
    if len(filas_camp) == n0:
        emitir_campana(c.id_cliente, c.comercial_asignado, c.tamano, desde + pd.Timedelta(days=int(rng.integers(10, 60))),
                       limite=baja, minimo=c.fecha_alta)
    perfil[c.id_cliente] = dict(desde=desde, hasta=baja, baja=baja, gradual=gradual, nuevo=False,
                                comercial=c.comercial_asignado, tam=c.tamano, en_originales=False)

# ---------------------------------------------------------------- 2. anunciantes antiguos que abandonaron antes de oct-2023
def activos_por_ejercicio(fc):
    fc = pd.DataFrame(fc)
    if fc.empty: return {}
    ef = fc.fecha_emision.dt.year + (fc.fecha_emision.dt.month >= 10)
    return fc.groupby(ef).id_cliente.nunique().to_dict()

plant_cli = cli.sample(frac=1, random_state=7).reset_index(drop=True)
nuevos_cli = []; i_pl = 0
for _ in range(400):
    act = activos_por_ejercicio(filas_camp)
    falta = {ef: OBJETIVO_ACTIVOS[ef] - act.get(ef, 0) for ef in OBJETIVO_ACTIVOS}
    ef = max(falta, key=falta.get)
    if falta[ef] <= 0: break
    t = plant_cli.iloc[i_pl % len(plant_cli)]; i_pl += 1
    ini_ef = pd.Timestamp(f"{ef - 1}-10-01")
    alta = ini_ef - pd.Timedelta(days=int(rng.integers(0, 1800))) if rng.random() < 0.6 else ini_ef + pd.Timedelta(days=int(rng.integers(0, 300)))
    desde = max(alta, INICIO)
    baja = min(ULT_BAJA, max(desde + pd.Timedelta(days=int(rng.integers(150, 300))),
                              pd.Timestamp(f"{ef}-09-30") - pd.Timedelta(days=int(rng.integers(0, 200)))
                              + pd.Timedelta(days=int(rng.exponential(120)))))
    if baja <= desde + pd.Timedelta(days=90): continue
    idc = nuevo_id("C"); gradual = rng.random() < P_GRADUAL
    lam = rng.choice(ritmos_tam[t.tamano]) * rng.normal(1, 0.15)
    n0 = len(filas_camp)
    for j, d in enumerate(inicios(idc, t.categoria, max(lam, 0.8), desde, baja)):
        decl = gradual and d > baja - pd.Timedelta(days=183)
        if decl and rng.random() < 0.5: continue
        emitir_campana(idc, t.comercial_asignado, t.tamano, d, None, 0.6 if decl else 1.0, 0.7 if decl else 1.0, limite=baja)
    if len(filas_camp) == n0:                                               # todo anunciante tiene al menos una campaña
        emitir_campana(idc, t.comercial_asignado, t.tamano, desde + pd.Timedelta(days=int(rng.integers(10, 60))), limite=baja)
    nuevos_cli.append(dict(id_cliente=idc, plantilla=t.id_cliente, alta=alta, categoria=t.categoria, tamano=t.tamano,
                           comercial=t.comercial_asignado, canal=t.canal_captacion, provincia=t.provincia))
    perfil[idc] = dict(desde=desde, hasta=baja, baja=baja, gradual=gradual, nuevo=True, comercial=t.comercial_asignado, tam=t.tamano,
                       en_originales=False)

# ---------------------------------------------------------------- 3. hacia delante: sep-2026 → hoy
ult = camp.groupby("id_cliente").fecha_emision.max()
inicio_adelante = pd.Timestamp("2026-09-02")
for _, c in cli[cli.id_cliente.isin(ult.index)].iterrows():
    u = ult[c.id_cliente]
    if (pd.Timestamp("2026-09-01") - u).days > 365: continue               # ya no estaba activo
    g = camp[camp.id_cliente == c.id_cliente]
    f6 = g[g.fecha_emision > "2026-03-01"].importe_eur.sum(); f6p = g[(g.fecha_emision > "2025-09-01") & (g.fecha_emision <= "2026-03-01")].importe_eur.sum()
    tend = min(1.5, f6 / f6p) if f6p > 0 else (1.0 if f6 > 0 else 0.4)
    for d in inicios(c.id_cliente, c.categoria, ritmo_de(c.id_cliente) * tend, inicio_adelante, HOY):
        emitir_campana(c.id_cliente, c.comercial_asignado, c.tamano, d, propias.get(c.id_cliente), limite=HOY)
    perfil[c.id_cliente + "+"] = dict(desde=pd.Timestamp("2026-10-01"), hasta=HOY, baja=None, gradual=False, nuevo=False,
                                      comercial=c.comercial_asignado, tam=c.tamano, real=c.id_cliente, en_originales=True)
for _ in range(5):                                                         # altas nuevas en otoño de 2026
    t = plant_cli.iloc[i_pl % len(plant_cli)]; i_pl += 1
    alta = pd.Timestamp("2026-09-05") + pd.Timedelta(days=int(rng.integers(0, 70)))
    idc = nuevo_id("C")
    emitir_campana(idc, t.comercial_asignado, t.tamano, max(alta + pd.Timedelta(days=int(rng.integers(5, 15))), pd.Timestamp("2026-10-01")), limite=HOY)
    nuevos_cli.append(dict(id_cliente=idc, plantilla=t.id_cliente, alta=alta, categoria=t.categoria, tamano=t.tamano,
                           comercial=t.comercial_asignado, canal=t.canal_captacion, provincia=t.provincia))
    perfil[idc] = dict(desde=alta, hasta=HOY, baja=None, gradual=False, nuevo=True, comercial=t.comercial_asignado, tam=t.tamano,
                       en_originales=False)

C = pd.DataFrame(filas_camp)
C = C[(C.fecha_emision <= HOY) & (((C.fecha_emision >= INICIO) & (C.fecha_emision <= FIN_ATRAS)) | (C.fecha_emision >= inicio_adelante))]

# ---------------------------------------------------------------- 4. clientes y contactos nuevos
pal = [r.split() for r in cli.razon_social.str.replace(r" S\.[LA]\.U?\.?$", "", regex=True)]
p1, p2 = sorted({w[0] for w in pal}), sorted({w[-1] for w in pal if len(w) > 1})
usadas = set(cli.razon_social)
nombres = sorted({n.split()[0] for n in con.nombre}); apellidos = sorted({n.split()[-1] for n in con.nombre})
quita = str.maketrans("áéíóúñü", "aeiounu")
filas_cli, filas_con = [], []
primera_orden = C.groupby("id_cliente").fecha_orden.min()
for n in nuevos_cli:                                                       # el alta nunca es posterior a la primera orden
    if n["id_cliente"] in primera_orden.index:
        n["alta"] = min(n["alta"], primera_orden[n["id_cliente"]] - pd.Timedelta(days=int(rng.integers(0, 21))))
    while True:
        rs = f"{rng.choice(p1)} {rng.choice(p2)} {rng.choice(['S.L.', 'S.L.', 'S.A.'])}"
        if rs not in usadas: usadas.add(rs); break
    t = cli[cli.id_cliente == n["plantilla"]].iloc[0]
    meses = max(0, (REF_ANTIGUEDAD.year - n["alta"].year) * 12 + REF_ANTIGUEDAD.month - n["alta"].month - (REF_ANTIGUEDAD.day < n["alta"].day))
    filas_cli.append(dict(id_cliente=n["id_cliente"], razon_social=rs, categoria=n["categoria"], provincia=n["provincia"],
                          tamano=n["tamano"], fecha_alta=n["alta"], antiguedad_meses=meses, canal_captacion=n["canal"],
                          comercial_asignado=n["comercial"], cp_sede=int(rng.integers(1000, 52999)),
                          tiene_web_propia=bool(t.tiene_web_propia),
                          anio_fundacion=int(min(n["alta"].year, n["alta"].year - rng.integers(0, 25)))))
    dominio = re.sub(r"[^a-z0-9]+", "-", rs.lower().translate(quita).replace(" s.l.", "").replace(" s.a.", "")).strip("-") + ".example"
    for k in range(1, 2 + (rng.random() < 0.1)):
        nom, ape = rng.choice(nombres), rng.choice(apellidos)
        filas_con.append(dict(id_contacto=f"CT-{n['id_cliente']}-{k}", id_cliente=n["id_cliente"], nombre=f"{nom} {ape}",
                              cargo=rng.choice(con.cargo.values),
                              email=f"{nom.lower().translate(quita)}.{ape.lower().translate(quita)}@{dominio}",
                              telefono=f"+34 6{rng.integers(10, 99)} {rng.integers(100, 999)} {rng.integers(100, 999)}",
                              principal=(k == 1), ficticio=True))

# ---------------------------------------------------------------- 5. facturas (una por orden)
fac_ref = fac[fac.fecha_emision <= REF]
cond_cli = fac_ref.merge(camp[["id_orden", "id_cliente"]], on="id_orden").groupby("id_cliente_x").condiciones_pago_dias.agg(lambda s: s.mode().iloc[0])
retrasos = fac_ref.dias_retraso.dropna().values
filas_fac = []
for _, o in C.sort_values("fecha_emision").iterrows():
    em = o.fecha_emision + pd.Timedelta(days=int(rng.integers(1, 12)))
    if em > HOY: continue
    cond = int(cond_cli.get(o.id_cliente, rng.choice([30, 30, 60, 90])))
    venc = em + pd.Timedelta(days=cond)
    p = perfil.get(o.id_cliente, {})
    r = float(rng.choice(retrasos)) + (rng.integers(0, 16) if p.get("baja") is not None and o.fecha_emision > p["baja"] - pd.Timedelta(days=183) else 0)
    cobro = venc + pd.Timedelta(days=r)
    pend = cobro > HOY
    filas_fac.append(dict(id_factura=nuevo_id("F"), id_cliente=o.id_cliente, id_orden=o.id_orden, importe_eur=o.importe_eur,
                          fecha_emision=em, condiciones_pago_dias=cond, fecha_vencimiento=venc,
                          fecha_cobro=None if pend else cobro, dias_retraso=None if pend else float(r),
                          estado="Pendiente" if pend else "Cobrada"))

# ---------------------------------------------------------------- 6. interacciones
inter = inter[inter.fecha <= REF]                                      # solo hasta el último corte de entrenamiento
normales = inter[~inter.tipo.isin(["Cambio de interlocutor", "Reclamacion"])][["tipo", "canal", "resultado"]].values
salientes_sin = inter[(inter.resultado == "Sin respuesta")][["tipo", "canal", "resultado"]].values
interloc = inter[inter.tipo == "Cambio de interlocutor"][["tipo", "canal", "resultado"]].values
reclam = inter[inter.tipo == "Reclamacion"][["canal"]].values
TASA_MES = 1.23 * len(inter) / (inter.id_cliente.nunique() * 21)     # calibrado: ≈ 1,9 interacciones por cliente activo y mes, como en los datos originales
# Episodios de abandono: cortes trimestrales en los que la etiqueta del modelo (modelo_churn/etiqueta.py, copiada en
# etiqueta_modelo_churn.py: población con campaña en los 12 meses anteriores, E2 con W de 210 días) marca abandono y el
# corte anterior no. Se excluyen los anunciantes con menos de un año desde el alta. Se calculan sobre las campañas ya generadas.
sys.path.insert(0, SAL)
from etiqueta_modelo_churn import etiquetar
fact_todo = pd.concat([camp[["id_cliente", "id_campana", "fecha_emision", "importe_eur"]],
                       C[["id_cliente", "id_campana", "fecha_emision", "importe_eur"]]])
alta_de = pd.concat([cli.set_index("id_cliente").fecha_alta, pd.Series({n["id_cliente"]: n["alta"] for n in nuevos_cli})])
clientes_todo = alta_de.rename("fecha_alta").rename_axis("id_cliente").reset_index()
ult_total = fact_todo.groupby("id_cliente").fecha_emision.max()
episodios, previo = {}, {}
for T in pd.date_range("2020-12-31", "2024-09-30", freq="QE-DEC"):
    e = etiquetar(fact_todo, clientes_todo, T)
    e = e[~e.nuevo]
    for idc, tipo, y in zip(e.id_cliente, e.tipo, e.abandono):
        if y and not previo.get(idc, False):
            definitiva = tipo == "perdida_total" and ult_total[idc] <= T       # no vuelve a comprar nunca
            episodios.setdefault(idc, []).append((T, definitiva))
        previo[idc] = bool(y)
    for idc in set(previo) - set(e.id_cliente): previo[idc] = False

# CTR más bajo en el año previo a una parte de los episodios (en los datos originales el CTR bajo acompaña al abandono)
C = C.reset_index(drop=True)
for clave, eps in episodios.items():
    for T, _ in eps:
        if rng.random() < CAL["p_ctr"]:
            m = (C.id_cliente == clave) & (C.fecha_emision > T - pd.Timedelta(days=365)) & (C.fecha_emision <= T)
            C.loc[m, "clics"] = (C.loc[m, "clics"] * rng.uniform(0.45, 0.75)).round().astype(int)
# El CTR relativo se mide frente a la mediana del producto: se reajusta la parte añadida para que esa mediana siga siendo la
# de los datos originales y no cambie la señal en los cortes originales.
ctr = lambda d: (d.clics / d.impresiones)[d.impresiones > 0].groupby(d.id_producto[d.impresiones > 0]).median()
ajuste = (ctr(camp_ref) / ctr(C)).reindex(C.id_producto).fillna(1.0).values
C["clics"] = np.minimum((C.clics * ajuste).round(), C.impresiones).astype(int)

filas_int = []
def interaccion(idc, fecha, terna, comercial):
    filas_int.append(dict(id_interaccion=nuevo_id("I"), id_cliente=idc, fecha=fecha, tipo=terna[0], canal=terna[1],
                          resultado=terna[2], comercial=comercial, previa_al_alta="No"))
for clave, p in perfil.items():
    idc = p.get("real", clave)
    desde, hasta = p["desde"], min(p["hasta"], HOY)
    if desde > hasta: continue
    for mes in pd.date_range(desde.replace(day=1), hasta, freq="MS"):
        cerca = p["baja"] is not None and p["gradual"] and mes > p["baja"] - pd.Timedelta(days=92)
        for _ in range(rng.poisson(TASA_MES * (0.6 if cerca else 1.0))):
            d = mes + pd.Timedelta(days=int(rng.integers(0, 28)))
            if desde <= d <= hasta and not (FIN_ATRAS < d < pd.Timestamp("2026-10-01")):
                interaccion(idc, d, normales[rng.integers(len(normales))] if not cerca or rng.random() > 0.3
                            else salientes_sin[rng.integers(len(salientes_sin))], p["comercial"])
    años = max(0.1, (hasta - desde).days / 365.25)
    eventos = [("interlocutor", None)] * rng.poisson(CAL["base_interlocutor"] * años)
    for _ in range(rng.poisson(CAL["base_reclamacion"] * años)):            # una parte queda sin resolver (no en los originales)
        eventos.append(("reclamacion_sin_resolver" if not p["en_originales"] and rng.random() < CAL["p_base_sin_resolver"] else "reclamacion", None))
    for T, definitiva in episodios.get(clave, []):                          # antes de cada episodio de abandono (E2)
        if rng.random() < CAL["p_interlocutor"]:
            eventos.append(("interlocutor", T - pd.Timedelta(days=int(rng.integers(0, CAL["ventana_interlocutor"])))))
        # Una reclamación sin resolver cuenta en todos los cortes posteriores: solo en pérdidas definitivas de anunciantes
        # que no aparecen en los datos originales, para no alterar las señales de los cortes originales.
        if definitiva and not p["en_originales"] and rng.random() < CAL["p_reclamacion"]:
            eventos.append(("reclamacion_sin_resolver", T - pd.Timedelta(days=int(rng.integers(10, 150)))))
    for e, d in eventos:
        if d is None: d = desde + pd.Timedelta(days=int(rng.integers(0, max(1, (hasta - desde).days))))
        if not (desde <= d <= min(hasta if e == "reclamacion" else FIN_ATRAS, HOY)) or (FIN_ATRAS < d < pd.Timestamp("2026-10-01")): continue
        if e == "interlocutor":
            interaccion(idc, d, interloc[rng.integers(len(interloc))], p["comercial"])
        else:
            interaccion(idc, d, ("Reclamacion", reclam[rng.integers(len(reclam))][0],
                                 "Sin resolver" if e == "reclamacion_sin_resolver" else "Resuelta"), p["comercial"])
    if p["baja"] is not None:                                               # intentos de contacto tras la baja
        for k in range(rng.poisson(1.5)):
            d = p["baja"] + pd.Timedelta(days=int(rng.integers(15, 120)))
            if d <= FIN_ATRAS: interaccion(idc, d, salientes_sin[rng.integers(len(salientes_sin))], p["comercial"])

# ---------------------------------------------------------------- 7. oportunidades
opo_ref = opo[opo.fecha_envio <= REF]
bolsa = {k: g[["importe_propuesto_eur", "n_toques_seguimiento", "dias_hasta_cierre"]].values for k, g in opo_ref.groupby(["origen", "desenlace"])}
no_gan_ampl = opo_ref[(opo_ref.origen == "Ampliacion de cartera") & (opo.desenlace != "Ganada")].desenlace.values
no_gan_lead = opo_ref[(opo_ref.origen == "Lead nuevo") & (opo.desenlace != "Ganada")].desenlace.values
P_GANADA = float(os.environ.get("CAL_PG", 0.84))   # campañas con propuesta ganada (originales: 0,87 en EF2024, 0,73 en EF2025)
prods = prod.index.values; coms = com.id_comercial.values
_g = opo_ref[opo_ref.desenlace == "Ganada"].merge(camp[["id_orden", "fecha_orden"]], on="id_orden")
desfase_ganadas = (_g.fecha_cierre - _g.fecha_orden).dt.days.values
filas_op = []
def oportunidad(idc, id_lead, origen, desenlace, envio, id_orden, comercial, producto, fila=None):
    imp, toques, dias = fila if fila is not None else bolsa[(origen, desenlace)][rng.integers(len(bolsa[(origen, desenlace)]))]
    cierre = envio + pd.Timedelta(days=int(dias))
    if cierre > HOY or envio < INICIO - pd.Timedelta(days=90): return
    if FIN_ATRAS < envio < pd.Timestamp("2026-09-23"): return
    filas_op.append(dict(id_oportunidad=nuevo_id("OP"), id_cliente=idc, id_lead=id_lead, origen=origen, id_producto_propuesto=producto,
                         importe_propuesto_eur=round(float(imp) * rng.normal(1, 0.05), 2), fecha_envio=envio, fecha_cierre=cierre,
                         desenlace=desenlace, id_orden=id_orden, n_toques_seguimiento=int(toques), dias_hasta_cierre=int(dias),
                         comercial=comercial, correccion="—"))
primera_total = pd.concat([camp[["id_cliente", "fecha_emision"]], C[["id_cliente", "fecha_emision"]]]).groupby("id_cliente").fecha_emision.min()
for k, g in C.groupby("id_campana"):
    o = g.sort_values("fecha_emision").iloc[0]
    if rng.random() > P_GANADA: continue
    es_primera = o.fecha_emision == primera_total[o.id_cliente]
    origen = "Lead nuevo" if es_primera else "Ampliacion de cartera"
    fila = bolsa[(origen, "Ganada")][rng.integers(len(bolsa[(origen, "Ganada")]))]
    cierre = o.fecha_orden + pd.Timedelta(days=int(rng.choice(desfase_ganadas)))   # cierre − orden, como en los originales
    oportunidad(o.id_cliente, nuevo_id("L") if es_primera else None, origen, "Ganada", cierre - pd.Timedelta(days=int(fila[2])),
                o.id_orden, o.comercial, o.id_producto, fila)
    if origen == "Lead nuevo":                                              # leads que no llegaron a ser clientes
        for _ in range(rng.poisson(8.06)):
            env = o.fecha_orden - pd.Timedelta(days=int(rng.integers(-200, 200)))
            oportunidad(None, nuevo_id("L"), "Lead nuevo", rng.choice(no_gan_lead), env, None, rng.choice(coms), rng.choice(prods))

# Propuestas de ampliación no ganadas: se envían a un ritmo constante a cada anunciante desde su primera campaña, siga
# comprando o no (en los datos originales: 0,070 por mes a los activos y 0,066 a los que llevan más de un año sin comprar).
# El envío no depende de si el anunciante va a abandonar; que ese anunciante deje de ganar propuestas es lo que hace que
# acumule perdidas, como en los datos originales.
prim_nueva = C.groupby("id_cliente").fecha_emision.min()
for clave, p in perfil.items():
    idc = p.get("real", clave)
    if "real" in p: a, b = pd.Timestamp("2026-09-23"), HOY
    elif idc in prim_nueva.index: a, b = prim_nueva[idc], (HOY if p["desde"] > FIN_ATRAS else FIN_ATRAS)
    else: continue
    for mes in pd.date_range(a.replace(day=1), b, freq="MS"):
        for _ in range(rng.poisson(CAL["propuestas_mes"])):
            env = mes + pd.Timedelta(days=int(rng.integers(0, 28)))
            if a <= env <= b:
                oportunidad(idc, None, "Ampliacion de cartera", rng.choice(no_gan_ampl), env, None, p["comercial"], rng.choice(prods))

for clave, eps in episodios.items():                                       # propuestas que no salen antes de un episodio
    p = perfil.get(clave)
    if p is None: continue
    for T, _ in eps:
        for _ in range(rng.poisson(CAL["propuestas_previas"])):
            env = T - pd.Timedelta(days=int(rng.integers(20, 240)))
            if env <= FIN_ATRAS:
                oportunidad(clave, None, "Ampliacion de cartera", rng.choice(no_gan_ampl), env, None, p["comercial"], rng.choice(prods))

# ---------------------------------------------------------------- 8. escritura: originales byte a byte + filas nuevas al final
def fmt(df, cols, fechas):
    df = df[cols].copy()
    for c in fechas: df[c] = pd.to_datetime(df[c]).dt.strftime("%Y-%m-%d")
    return df
salidas = {
    "dim_clientes": (pd.DataFrame(filas_cli), ["fecha_alta"]),
    "contactos": (pd.DataFrame(filas_con), []),
    "fact_campanas": (C.drop(columns=[c for c in ("tamano", "categoria") if c in C]), ["fecha_orden", "fecha_emision"]),
    "fact_facturacion": (pd.DataFrame(filas_fac), ["fecha_emision", "fecha_vencimiento", "fecha_cobro"]),
    "fact_interacciones": (pd.DataFrame(filas_int).sort_values("fecha"), ["fecha"]),
    "oportunidades": (pd.DataFrame(filas_op), ["fecha_envio", "fecha_cierre"]),
}
os.makedirs(SAL, exist_ok=True)
for nombre in sorted(os.listdir(ORIG)):
    if not nombre.endswith(".csv"): continue
    t = nombre[:-4]
    original = open(os.path.join(ORIG, nombre), encoding="utf-8").read()
    cabecera = original.splitlines()[0].split(",")
    nuevas = ""
    if t in salidas:
        df, fechas = salidas[t]
        if len(df):
            df = fmt(df, cabecera, fechas)
            nuevas = df.to_csv(index=False, header=False, lineterminator="\n", float_format=None)
    with open(os.path.join(SAL, nombre), "w", encoding="utf-8", newline="") as fh:
        fh.write(original if original.endswith("\n") else original + "\n"); fh.write(nuevas)
    print(f"{t:20s} originales {original.count(chr(10)) - 1 + (not original.endswith(chr(10))):5d} · nuevas {nuevas.count(chr(10)):6d}")

# ---------------------------------------------------------------- 9. facturas originales pendientes a 30-sep-2026
# Las 61 facturas originales «Pendiente» reflejan el estado a 30-sep-2026 y no se modifican. Su situación a 27-nov-2026 va
# en una tabla aparte (cobros_posteriores.csv), con el mismo retraso de cobro que el resto de facturas del anunciante.
pend = fac[fac.estado == "Pendiente"].copy()
filas_cob = []
for _, f in pend.iterrows():
    r = float(rng.choice(retrasos)); cobro = f.fecha_vencimiento + pd.Timedelta(days=r)
    cobro = max(cobro, pd.Timestamp("2026-10-01"))                       # a 30-sep seguía sin cobrar
    ok = cobro <= HOY
    filas_cob.append(dict(id_factura=f.id_factura, id_cliente=f.id_cliente, fecha_vencimiento=f.fecha_vencimiento.strftime("%Y-%m-%d"),
                          fecha_cobro=cobro.strftime("%Y-%m-%d") if ok else "",
                          dias_retraso=(cobro - f.fecha_vencimiento).days if ok else "",
                          estado_27nov2026="Cobrada" if ok else "Pendiente"))
pd.DataFrame(filas_cob).to_csv(os.path.join(SAL, "cobros_posteriores.csv"), index=False, lineterminator="\n")
print(f"cobros_posteriores   {len(filas_cob)} facturas originales pendientes a 30-sep-2026 · "
      f"{sum(f['estado_27nov2026'] == 'Cobrada' for f in filas_cob)} cobradas a 27-nov-2026")

