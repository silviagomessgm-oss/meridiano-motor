"""
Meridiano · Motor de cálculo como servicio HTTP (ALTERNATIVA a GitHub Actions, para un servidor propio).

  GET  /salud               · comprobación
  POST /ciclo               · {"fecha_corte": "AAAA-MM-DD"}  bajar de Supabase → ciclo semanal → subir a Supabase
                              Devuelve el resumen y las propuestas de la semana (para que n8n redacte los materiales con la IA)

Seguridad: cabecera X-Motor-Token igual a la variable de entorno MOTOR_TOKEN.
Arranque: uvicorn motor.app:app --host 0.0.0.0 --port 8000
"""
import os, sys
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "motor"))
import sync_supabase as sync
import servicio

app = FastAPI(title="Meridiano · motor de churn", version="1.0")


class Peticion(BaseModel):
    fecha_corte: str


def _auth(token):
    esperado = os.environ.get("MOTOR_TOKEN")
    if esperado and token != esperado:
        raise HTTPException(status_code=401, detail="Token no válido")


@app.get("/salud")
def salud():
    return {"estado": "ok", "modo": "local" if sync.modo_local() else "supabase"}


@app.post("/ciclo")
def ciclo(p: Peticion, x_motor_token: str | None = Header(default=None)):
    _auth(x_motor_token)
    try:
        return servicio.ejecutar(p.fecha_corte)
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
