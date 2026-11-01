"""
Genera la hoja de datos operativos que lee n8n (W0 · Carga semanal) a partir de tablas/*.csv:
  python despliegue/preparar_hoja_datos.py   →   despliegue/Meridiano_Datos_Operativos.xlsx
Se importa en Google Sheets (Archivo → Importar → Subir → "Sustituir hoja de cálculo"). Una pestaña por tabla, con los
mismos nombres de pestaña y de columna que Supabase. Fechas como texto AAAA-MM-DD para que no dependan de la configuración
regional; las fechas que se escriban a mano pueden ir como DD/MM/AAAA (hoja con configuración regional de España).
"""
import os
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SALIDA = os.path.join(RAIZ, "despliegue", "Meridiano_Datos_Operativos.xlsx")
TABLAS = ["dim_comercial", "dim_productos", "dim_clientes", "fact_campanas", "fact_facturacion", "fact_interacciones", "oportunidades",
          "contactos"]
NUMERICAS = {"tarifa_base_eur", "margen", "capacidad_mensual", "capacidad_anual_eur", "antiguedad_meses", "cp_sede", "anio_fundacion",
             "descuento_pct", "importe_eur", "impresiones", "clics", "leads_entregados", "condiciones_pago_dias", "dias_retraso",
             "importe_propuesto_eur", "n_toques_seguimiento", "dias_hasta_cierre"}
LEEME = [
    ("Meridiano · Datos operativos (ficticios, caso de estudio)", ""),
    ("", ""),
    ("Para qué sirve", "Es la fuente de las tablas. Cada lunes a las 21:00, n8n (W0 · Carga semanal) la lee, la valida y la carga en Supabase."),
    ("Cómo se mantiene", "Añadir al final de cada pestaña las órdenes, facturas, interacciones y oportunidades nuevas. Para corregir, editar la fila (sin cambiar su identificador)."),
    ("No hacer", "No cambiar el nombre de las pestañas ni de las columnas. No borrar filas: una fila borrada aquí sigue en Supabase."),
    ("Identificadores", "Primera columna de cada pestaña. Únicos dentro de la pestaña."),
    ("Fechas", "AAAA-MM-DD o DD/MM/AAAA (configuración regional de la hoja: España)."),
    ("Números", "Sin símbolo de moneda. Decimales con coma o punto."),
    ("Sí/no", "TRUE/FALSE, Sí/No o 1/0."),
    ("Contactos", "Personas de contacto de los clientes. FICTICIAS en el caso (dominio .example). Los contactos de leads no van aquí: entran por el formulario web o por el panel."),
    ("Si algo está mal", "La fila no se carga y llega un correo con la pestaña, la fila y el motivo. Si falta una pestaña o columna, o más del 5 % de una tabla tiene errores, no se carga nada esa semana."),
]


def main():
    wb = Workbook(); ws = wb.active; ws.title = "LEEME"
    for r, (a, b) in enumerate(LEEME, 1):
        ws.cell(r, 1, a).font = Font(name="Arial", bold=True, size=12 if r == 1 else 10)
        ws.cell(r, 2, b).font = Font(name="Arial", size=10); ws.cell(r, 2).alignment = Alignment(wrap_text=True, vertical="top")
    ws.column_dimensions["A"].width = 22; ws.column_dimensions["B"].width = 110
    cab = PatternFill("solid", start_color="1F3A5F"); fuente_cab = Font(name="Arial", bold=True, color="FFFFFF"); fuente = Font(name="Arial", size=10)
    for t in TABLAS:
        df = pd.read_csv(os.path.join(RAIZ, "tablas", t + ".csv"), dtype=str, keep_default_na=False)
        h = wb.create_sheet(t)
        for j, col in enumerate(df.columns, 1):
            c = h.cell(1, j, col); c.font = fuente_cab; c.fill = cab
            h.column_dimensions[c.column_letter].width = max(12, min(40, len(col) + 4))
        for i, fila in enumerate(df.itertuples(index=False), 2):
            for j, (col, v) in enumerate(zip(df.columns, fila), 1):
                if v == "": continue
                if col in NUMERICAS:
                    x = float(v); v = int(x) if x.is_integer() and not col.endswith(("eur", "pct", "margen", "retraso")) else x
                c = h.cell(i, j, v); c.font = fuente
                if col not in NUMERICAS: c.number_format = "@"
        h.freeze_panes = "A2"
    wb.save(SALIDA); print(SALIDA)


if __name__ == "__main__":
    main()
