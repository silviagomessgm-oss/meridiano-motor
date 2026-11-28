"""
Meridiano · SIMULACRO para la presentación (datos ficticios; no usar para evaluar el modelo).

Reproduce el circuito completo con el sistema real, en una copia temporal del repositorio (no toca historico/ ni salidas/):
  1. Ciclos semanales pasados (por defecto, 8 lunes desde el 5-ene-2026) con ciclo_semanal.py: el modelo puntúa, el sistema
     elige 12 cuentas (4 por comercial) y el grupo de control.
  2. Acciones simuladas de los comerciales: cada propuesta se aprueba (acción) o se rechaza, con su fecha.
  3. Ciclo de la semana de la demo: el modelo se reentrena sin las cuentas en las que se actuó y el paso 5 calcula el
     resultado de las acciones a 210 días (lo que pasó en los datos).
  4. ESCENARIO SUPUESTO (rotulado como tal): una parte de las cuentas con acción que abandonaron pasan a «salvada» con
     el resultado «salvada_escenario». Es un supuesto para enseñar el circuito, no un resultado.

Salidas en --salida (por defecto demo/salida/):
  simulacro.xlsx            informe paso a paso para proyectar
  cargar_simulacro.sql      resultados del simulacro para Supabase (el panel los muestra en «Resultado de las acciones»)
  borrar_simulacro.sql      los borra después de la presentación

Uso:
  python demo/simulacro.py                       # valores por defecto
  python demo/simulacro.py --efecto 0.3 --aprobacion 0.75 --fecha-demo 2026-11-23
"""
import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
from modelo_churn.resultado_acciones import efecto, resumen  # noqa: E402

COPIAR = ["ciclo_semanal.py", "modelo_churn", "evaluacion", "propuestas", "tablas"]
RESULTADO_ESCENARIO = "salvada_escenario"
A_CONFIRMACION = {"perdida_total": "Perdido", "contraccion": "Redujo mucho", "activo": "Activo",
                  RESULTADO_ESCENARIO: "Activo", "fuera_de_poblacion_volvio": "Activo",
                  "fuera_de_poblacion_sin_compra": "Perdido"}


def copia_temporal():
    d = Path(tempfile.mkdtemp(prefix="meridiano_simulacro_"))
    ignorar = shutil.ignore_patterns("__pycache__", ".pytest_cache", "salidas", "historico")
    for x in COPIAR:
        o = RAIZ / x
        (shutil.copytree(o, d / x, ignore=ignorar) if o.is_dir() else shutil.copy(o, d / x))
    (d / "historico").mkdir()
    return d


def ciclo(d, fecha):
    r = subprocess.run([sys.executable, "ciclo_semanal.py", "--fecha_corte", fecha], cwd=d, capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(f"Falló el ciclo {fecha}:\n{r.stdout[-2000:]}\n{r.stderr[-2000:]}")
    return r.stdout


def acciones_simuladas(d, semanas, p_aprobar, rng):
    """Cada propuesta de cada semana: «aprobada» (acción, 1–5 días después) o «rechazada»."""
    filas = []
    for s in semanas:
        plan = pd.read_excel(d / "salidas" / s / "propuestas_retencion.xlsx", sheet_name="Plan_por_comercial")
        for r in plan.itertuples():
            aprobada = rng.random() < p_aprobar
            filas.append({"fecha_corte": s, "id_cliente": str(r.id_cliente), "razon_social": r.razon_social,
                          "comercial": r.comercial_nombre, "banda_riesgo": r.banda_riesgo, "accion_sugerida": r.accion_id,
                          "decision_comercial": "aprobada" if aprobada else "rechazada",
                          "fecha_accion": (pd.Timestamp(s) + pd.Timedelta(days=int(rng.integers(1, 6)))).date()
                          if aprobada else None})
    acc = pd.DataFrame(filas)
    acc[acc.decision_comercial == "aprobada"].rename(columns={"fecha_accion": "fecha"})[["id_cliente", "fecha"]].to_csv(
        d / "historico" / "intervenciones.csv", index=False)
    return acc


def aplicar_escenario(res, p_efecto, rng):
    """SUPUESTO: la acción evita una parte de los abandonos de las cuentas con acción."""
    res = res.copy()
    res["escenario_supuesto"] = False
    candidatas = res.index[(res.grupo == "accion") & (res.abandono == 1)]
    salvadas = [i for i in candidatas if rng.random() < p_efecto]
    res.loc[salvadas, ["abandono", "salvada", "resultado", "escenario_supuesto"]] = [0, True, RESULTADO_ESCENARIO, True]
    res["estado_confirmado_comercial"] = res["resultado"].map(A_CONFIRMACION)
    return res


def sql_valor(v):
    if v is None or (isinstance(v, float) and np.isnan(v)) or v is pd.NaT:
        return "null"
    if isinstance(v, (bool, np.bool_)):
        return "true" if v else "false"
    return "'" + str(v).replace("'", "''") + "'"


def escribir_sql(res, salida, parametros):
    cab = (f"-- Meridiano · SIMULACRO para la presentación (datos ficticios, escenario supuesto).\n"
           f"-- Generado por demo/simulacro.py con {json.dumps(parametros, ensure_ascii=False)}\n")
    cols = ["fecha_corte", "id_cliente", "grupo", "banda_riesgo", "resultado", "abandono", "salvada",
            "estado_confirmado_comercial", "fecha_resultado"]
    valores = ",\n".join("  (" + ", ".join(sql_valor(bool(r[c]) if c in ("abandono", "salvada") else r[c]) for c in cols) + ")"
                         for _, r in res.iterrows())
    (salida / "cargar_simulacro.sql").write_text(
        cab + "-- Requiere supabase/modelo_churn.sql. Carga solo resultados (no asignaciones): el motor no los recalcula.\n"
        "-- Después de la presentación, ejecutar borrar_simulacro.sql.\n"
        f"insert into resultado_acciones ({', '.join(cols)}) values\n{valores}\n"
        "on conflict (fecha_corte, id_cliente) do update set grupo = excluded.grupo, banda_riesgo = excluded.banda_riesgo,\n"
        "  resultado = excluded.resultado, abandono = excluded.abandono, salvada = excluded.salvada,\n"
        "  estado_confirmado_comercial = excluded.estado_confirmado_comercial, fecha_resultado = excluded.fecha_resultado;\n"
        "select * from resumen_resultado_acciones; select * from efecto_accion;\n", encoding="utf-8")
    claves = ",\n".join(f"  ({sql_valor(r.fecha_corte)}::date, {sql_valor(r.id_cliente)})" for r in res.itertuples())
    (salida / "borrar_simulacro.sql").write_text(
        cab + "-- Borra exactamente las filas que cargó cargar_simulacro.sql.\n"
        f"delete from resultado_acciones where (fecha_corte, id_cliente) in (values\n{claves});\n"
        "select count(*) as filas_restantes from resultado_acciones;\n", encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--desde", default="2026-01-05", help="Primer lunes de los ciclos pasados")
    ap.add_argument("--semanas", type=int, default=8,
                    help="Más semanas agotan las cuentas: una cuenta propuesta no se repite en 90 días")
    ap.add_argument("--fecha-demo", default="2026-11-23", help="Lunes de la semana de la demo (ventanas de 210 días cerradas)")
    ap.add_argument("--aprobacion", type=float, default=0.75, help="Parte de las propuestas que el comercial aprueba")
    ap.add_argument("--efecto", type=float, default=0.30, help="SUPUESTO: parte de los abandonos con acción que se evitan")
    ap.add_argument("--semilla", type=int, default=2026)
    ap.add_argument("--salida", default=str(RAIZ / "demo" / "salida"))
    a = ap.parse_args()
    rng = np.random.default_rng(a.semilla)
    salida = Path(a.salida); salida.mkdir(parents=True, exist_ok=True)
    semanas = [str(d.date()) for d in pd.date_range(a.desde, periods=a.semanas, freq="7D")]
    d = copia_temporal()
    try:
        print(f"1. Ciclos semanales pasados ({semanas[0]} → {semanas[-1]})", flush=True)
        ciclos = []
        for s in semanas:
            ciclo(d, s)
            pl = pd.read_excel(d / "salidas" / s / "propuestas_retencion.xlsx", sheet_name=None)
            ciclos.append({"semana": s, "propuestas": len(pl["Plan_por_comercial"]), "grupo_control": len(pl["Grupo_control"]),
                           "aplazadas": len(pl["Aplazados"])})
            print(f"   {s}: {ciclos[-1]['propuestas']} propuestas, {ciclos[-1]['grupo_control']} en control", flush=True)
        print("2. Acciones simuladas de los comerciales", flush=True)
        acc = acciones_simuladas(d, semanas, a.aprobacion, rng)
        print(f"   {(acc.decision_comercial == 'aprobada').sum()} aprobadas y {(acc.decision_comercial == 'rechazada').sum()} rechazadas")
        print(f"3. Ciclo de la semana de la demo ({a.fecha_demo})", flush=True)
        log = ciclo(d, a.fecha_demo)
        excluidas = next((l.split(":")[1].strip() for l in log.splitlines() if "excluidas_por_intervencion" in l), "0")
        print(f"   el modelo deja fuera del entrenamiento {excluidas} observaciones de cuentas con acción")
        sal = d / "salidas" / a.fecha_demo
        res_datos = pd.read_csv(sal / "resultado_acciones.csv", dtype={"id_cliente": str})
        res_datos = res_datos[res_datos.fecha_corte.isin(semanas)].reset_index(drop=True)
        plan_demo = pd.read_excel(sal / "propuestas_retencion.xlsx", sheet_name=None)
        print("4. Escenario supuesto sobre el resultado de las acciones", flush=True)
        res = aplicar_escenario(res_datos, a.efecto, rng)
        r_datos, r_esc = resumen(res_datos), resumen(res)
        e_datos, e_esc = efecto(res_datos), efecto(res)
        print(r_esc.to_string(index=False)); print("   efecto (banda media):", e_esc)

        nombres = pd.read_csv(RAIZ / "tablas" / "dim_clientes.csv", dtype=str).set_index("id_cliente")["razon_social"]
        parametros = {"desde": a.desde, "semanas": a.semanas, "fecha_demo": a.fecha_demo, "aprobacion": a.aprobacion,
                      "efecto_supuesto": a.efecto, "semilla": a.semilla}
        leeme = pd.DataFrame([
            ("Qué es", "Simulacro del circuito completo para la presentación. Datos ficticios."),
            ("Real (sistema)", "Ciclos semanales, puntuación del modelo, selección de cuentas, grupo de control, exclusión de "
                               "cuentas con acción al reentrenar y cálculo del resultado a 210 días."),
            ("Simulado", f"Decisiones de los comerciales: se aprueba el {a.aprobacion:.0%} de las propuestas."),
            ("ESCENARIO SUPUESTO", f"La acción evita el {a.efecto:.0%} de los abandonos de las cuentas con acción "
                                   f"(resultado «{RESULTADO_ESCENARIO}»). Es un supuesto para enseñar el circuito, no un resultado."),
            ("Efecto según los datos (sin supuesto)", f"{e_datos}. OJO: no es un efecto. Las acciones son simuladas y no cambian "
                                                      "los datos; la diferencia se debe al azar (pocas cuentas en el grupo de control)."),
            ("Efecto en el escenario supuesto", f"{e_esc}"),
            ("Parámetros", json.dumps(parametros, ensure_ascii=False)),
        ], columns=["", "Detalle"])
        with pd.ExcelWriter(salida / "simulacro.xlsx") as xl:
            leeme.to_excel(xl, sheet_name="Léeme", index=False)
            pd.DataFrame(ciclos).to_excel(xl, sheet_name="1 Ciclos semanales", index=False)
            acc.to_excel(xl, sheet_name="2 Acciones comerciales", index=False)
            plan_demo["Plan_por_comercial"].to_excel(xl, sheet_name="3 Plan semana demo", index=False)
            res.assign(razon_social=res.id_cliente.map(nombres)).to_excel(xl, sheet_name="4 Resultado acciones", index=False)
            pd.concat([r_datos.assign(version="datos"), r_esc.assign(version="escenario supuesto")]).to_excel(
                xl, sheet_name="5 Resumen", index=False)
            pd.DataFrame([dict(e_datos, version="datos"), dict(e_esc, version="escenario supuesto")]).to_excel(
                xl, sheet_name="6 Efecto (banda media)", index=False)
        escribir_sql(res, salida, parametros)
        print(f"\nEscrito en {salida}: simulacro.xlsx, cargar_simulacro.sql, borrar_simulacro.sql")
    finally:
        shutil.rmtree(d, ignore_errors=True)


if __name__ == "__main__":
    main()
