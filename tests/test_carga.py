"""W0 · carga semanal: la validación del nodo Code con las tablas reales (como las leería Google Sheets) y su carga en Postgres."""
import csv, json, os, uuid
import pytest
from test_n8n import correr
RAIZ = os.path.join(os.path.dirname(__file__), "..")
TABLAS = ["dim_comercial", "dim_productos", "dim_clientes", "fact_campanas", "fact_facturacion", "fact_interacciones", "oportunidades",
          "contactos"]


def empaquetar(h):
    """Como devuelve la API de Google Sheets (values:batchGet) las pestañas {'Leer t': filas}: cabecera + filas en matriz."""
    vr = []
    for k, filas in h.items():
        cab = list(filas[0].keys()) if filas else []
        vr.append({"range": f"'{k.replace('Leer ', '')}'!A1:Z99999", "values": [cab] + [[f.get(c, "") for c in cab] for f in filas if f]})
    return {"Google Sheets: leer pestañas": [{"valueRanges": vr}]}


def hoja():
    """Cada pestaña como la devuelve el nodo de Google Sheets: una fila = un objeto con las cabeceras."""
    return {f"Leer {t}": list(csv.DictReader(open(os.path.join(RAIZ, "tablas", t + ".csv"), encoding="utf-8"))) for t in TABLAS}


def test_tablas_reales_pasan_completas_y_en_orden():
    out = correr("w0_preparar_tablas.js", {"nodos": empaquetar(hoja())})
    assert not out[0]["abortar"]
    res = {r["tabla"]: r for r in out[0]["resumen"]}
    for t in TABLAS:
        n = sum(1 for _ in open(os.path.join(RAIZ, "tablas", t + ".csv"), encoding="utf-8")) - 1
        assert res[t]["leidas"] == n and res[t]["rechazadas"] == 0, (t, res[t]["ejemplos_rechazo"][:3])
    assert [o["tabla"] for o in out] == sorted([o["tabla"] for o in out], key=TABLAS.index)        # dependencias primero
    assert max(len(o["filas"]) for o in out) <= 1000
    f = next(o for o in out if o["tabla"] == "dim_productos")["filas"][0]
    assert f["es_producto_entrada"] is True and f["tarifa_base_eur"] == 900 and f["meses_disponible"].startswith("1,2,3")


def test_formatos_de_hoja_espanola_y_filas_rechazadas():
    h = hoja()
    c = h["Leer fact_campanas"]
    c[0] = dict(c[0], fecha_emision="05/10/2023", importe_eur="1.234,50")            # formatos de una hoja en español
    c[1] = dict(c[1], fecha_emision="31/02/2024")                                   # fecha imposible
    c[2] = dict(c[2], id_cliente="C9999")                                           # anunciante inexistente
    c.append(dict(c[3]))                                                            # identificador repetido
    out = correr("w0_preparar_tablas.js", {"nodos": empaquetar(h)})
    assert not out[0]["abortar"]
    r = next(x for x in out[0]["resumen"] if x["tabla"] == "fact_campanas")
    assert r["rechazadas"] == 3
    motivos = " | ".join(e["motivo"] for e in r["ejemplos_rechazo"])
    assert "no es una fecha válida" in motivos and "C9999 no existe en dim_clientes" in motivos and "repetido" in motivos
    fila = next(f for o in out if o["tabla"] == "fact_campanas" for f in o["filas"] if f["id_orden"] == c[0]["id_orden"])
    assert fila["fecha_emision"] == "2023-10-05" and fila["importe_eur"] == 1234.5
    # Las facturas de las órdenes rechazadas también se rechazan (no quedan huérfanas)
    rf = next(x for x in out[0]["resumen"] if x["tabla"] == "fact_facturacion")
    assert rf["rechazadas"] >= 1 and all("no existe en fact_campanas" in e["motivo"] for e in rf["ejemplos_rechazo"])


@pytest.mark.parametrize("cambio,mensaje", [
    (lambda h: h.__setitem__("Leer dim_clientes", [{k: v for k, v in f.items() if k != "fecha_alta"} for f in h["Leer dim_clientes"]]),
     "dim_clientes: faltan las columnas fecha_alta"),
    (lambda h: h.__setitem__("Leer oportunidades", [{}]), "oportunidades: la pestaña está vacía"),
    (lambda h: h.pop("Leer contactos"), "contactos: no está la pestaña en la hoja"),
    (lambda h: [f.__setitem__("importe_eur", "mucho") for f in h["Leer fact_facturacion"][:200]], "fact_facturacion: 200 de"),
])
def test_carga_detenida_sin_escribir_nada(cambio, mensaje):
    h = hoja(); cambio(h)
    out = correr("w0_preparar_tablas.js", {"nodos": empaquetar(h)})
    assert len(out) == 1 and out[0]["abortar"] and any(mensaje in f for f in out[0]["fatales"])
    aviso = correr("w0_solo_abortada.js", {"input": out})[0]
    assert "DETENIDA" in aviso["asunto"] and aviso["registro"]["estado"] == "carga_detenida"


def test_resumen_de_la_carga():
    out = correr("w0_preparar_tablas.js", {"nodos": empaquetar(hoja())})
    resp = [{"statusCode": 201}] * len(out)
    r = correr("w0_resumen.js", {"input": resp, "nodos": {"Solo cargables": out}})[0]
    assert r["registro"]["estado"] == "carga_ok" and not r["avisar"]
    resp[-1] = {"statusCode": 409, "body": {"message": "duplicate key"}}
    r = correr("w0_resumen.js", {"input": resp, "nodos": {"Solo cargables": out}})[0]
    assert r["registro"]["estado"] == "carga_con_errores" and r["avisar"] and "duplicate key" in r["texto"]


psycopg2 = pytest.importorskip("psycopg2")
DSN = os.environ.get("MERIDIANO_PG_TEST")


@pytest.mark.skipif(not DSN, reason="define MERIDIANO_PG_TEST con un Postgres local de pruebas")
def test_lotes_se_cargan_en_el_esquema_y_la_recarga_actualiza():
    """Imita lo que hace PostgREST con cada lote (insert … on conflict do update) contra supabase/schema.sql."""
    nombre = "t_" + uuid.uuid4().hex[:8]
    adm = psycopg2.connect(DSN + " dbname=postgres"); adm.autocommit = True; adm.cursor().execute(f"create database {nombre}")
    try:
        c = psycopg2.connect(DSN + f" dbname={nombre}"); c.autocommit = True; cur = c.cursor()
        cur.execute(open(os.path.join(RAIZ, "tests", "supabase_stub.sql")).read())
        cur.execute(open(os.path.join(RAIZ, "supabase", "schema.sql")).read())

        def cargar(lotes):
            for o in lotes:
                cols = list(o["filas"][0])
                cur.execute(f"""insert into {o['tabla']} ({','.join(cols)})
                                select {','.join(cols)} from json_populate_recordset(null::{o['tabla']}, %s)
                                on conflict ({o['pk']}) do update set {','.join(f'{k}=excluded.{k}' for k in cols if k != o['pk'])}""",
                            (json.dumps(o["filas"]),))
        cargar(correr("w0_preparar_tablas.js", {"nodos": empaquetar(hoja())}))
        for t in TABLAS:
            cur.execute(f"select count(*) from {t}")
            assert cur.fetchone()[0] == sum(1 for _ in open(os.path.join(RAIZ, "tablas", t + ".csv"), encoding="utf-8")) - 1
        h = hoja(); h["Leer dim_clientes"][0]["razon_social"] = "Nombre corregido S.L."             # corrección en la hoja
        cargar(correr("w0_preparar_tablas.js", {"nodos": empaquetar(h)}))
        cur.execute("select razon_social from dim_clientes where id_cliente=%s", (h["Leer dim_clientes"][0]["id_cliente"],))
        assert cur.fetchone()[0] == "Nombre corregido S.L."
        cur.execute("select count(*) from dim_clientes"); assert cur.fetchone()[0] == len(h["Leer dim_clientes"])
        c.close()
    finally:
        adm.cursor().execute(f"drop database {nombre} with (force)"); adm.close()


def test_hoja_generada_para_google_sheets_carga_sin_rechazos(tmp_path):
    """La hoja que se importa en Google Sheets, leída celda a celda (números como números, texto como texto), pasa entera."""
    import sys
    from openpyxl import load_workbook
    sys.path.insert(0, os.path.join(RAIZ, "despliegue"))
    import preparar_hoja_datos as p
    p.SALIDA = str(tmp_path / "hoja.xlsx"); p.main()
    wb = load_workbook(p.SALIDA, read_only=True)
    nodos = {}
    for t in TABLAS:
        filas = list(wb[t].iter_rows(values_only=True))
        nodos[f"Leer {t}"] = [{k: ("" if v is None else v) for k, v in zip(filas[0], f)} for f in filas[1:]]
    out = correr("w0_preparar_tablas.js", {"nodos": empaquetar(nodos)})
    assert not out[0]["abortar"] and all(r["rechazadas"] == 0 for r in out[0]["resumen"])
