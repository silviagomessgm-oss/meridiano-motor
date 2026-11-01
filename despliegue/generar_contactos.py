"""
Genera contactos FICTICIOS para los clientes del caso (tablas/contactos.csv), reproducibles.
Correos con dominio .example (reservado: no existe ni puede recibir correo). En la demo, n8n desvía todos los envíos
al buzón de pruebas configurado, así que ningún mensaje sale a direcciones reales.
"""
import os, random, re, unicodedata
import pandas as pd

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NOMBRES = ["Laura", "Javier", "Carmen", "Andrés", "Lucía", "Miguel", "Elena", "Pablo", "Marta", "Sergio", "Isabel", "Raúl",
           "Teresa", "Alberto", "Pilar", "Diego", "Rosa", "Fernando", "Beatriz", "Óscar", "Nuria", "Héctor", "Silvia", "Ignacio"]
APELLIDOS = ["García", "Martín", "López", "Sánchez", "Romero", "Navarro", "Torres", "Domínguez", "Vázquez", "Ramos", "Gil",
             "Serrano", "Molina", "Ortega", "Delgado", "Castro", "Ortiz", "Rubio", "Marín", "Sanz", "Iglesias", "Medina"]
CARGOS = {"Grande": ["Directora de marketing", "Responsable de medios", "Brand manager"],
          "Mediana": ["Responsable de marketing", "Gerente", "Responsable de comunicación"],
          "Pequena": ["Gerente", "Propietario", "Responsable comercial"]}


def ascii_(t): return unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode().lower()


def dominio(razon):
    base = re.sub(r"\b(s\.?l\.?u?|s\.?a\.?|s\.?coop\.?|sociedad limitada)\b", "", ascii_(razon))
    return re.sub(r"[^a-z0-9]+", "-", base).strip("-")[:40] + ".example"


def main():
    cl = pd.read_csv(os.path.join(RAIZ, "tablas", "dim_clientes.csv"))
    rnd = random.Random(20261101); filas = []
    for r in cl.itertuples():
        n = 2 if r.tamano == "Grande" else 1
        for k in range(1, n + 1):
            nom, ape = rnd.choice(NOMBRES), rnd.choice(APELLIDOS)
            filas.append(dict(id_contacto=f"CT-{r.id_cliente}-{k}", id_cliente=r.id_cliente, nombre=f"{nom} {ape}",
                              cargo=rnd.choice(CARGOS.get(r.tamano, CARGOS["Mediana"])),
                              email=f"{ascii_(nom)}.{ascii_(ape)}@{dominio(r.razon_social)}",
                              telefono=f"+34 6{rnd.randint(10, 99)} {rnd.randint(100, 999)} {rnd.randint(100, 999)}",
                              principal=(k == 1), ficticio=True))
    out = os.path.join(RAIZ, "tablas", "contactos.csv")
    pd.DataFrame(filas).to_csv(out, index=False); print(out, len(filas))


if __name__ == "__main__":
    main()
