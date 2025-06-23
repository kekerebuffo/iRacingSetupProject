import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from supabase import create_client, Client
import copy

# Configuración de Supabase desde variables de entorno
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

app = FastAPI(
    title="iRacing Setup API",
    version="1.0.0",
    description="API que obtiene setups base y aplica ajustes dinámicos"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class SetupRequest(BaseModel):
    coche: str
    circuito: str
    tipo_conduccion: str
    temperatura: int
    vueltas: int

def obtener_setup_base(coche, circuito, tipo_conduccion):
    response = supabase.table('setup_base')\
        .select('*')\
        .eq('coche', coche)\
        .eq('circuito', circuito)\
        .eq('tipo_conduccion', tipo_conduccion)\
        .execute()
    return response.data[0] if response.data else None

def obtener_ajustes_condiciones(setup_base_id, temperatura, vueltas):
    response = (
        supabase.table('ajuste_condiciones')
        .select('*')
        .eq('setup_base_id', setup_base_id)
        .lte('temp_min', temperatura)   # temp_min <= temperatura
        .gte('temp_max', temperatura)   # temp_max >= temperatura
        .lte('vueltas_min', vueltas)    # vueltas_min <= vueltas
        .gte('vueltas_max', vueltas)    # vueltas_max >= vueltas
        .execute()
    )
    return response.data or []

def aplicar_ajustes(setup_json, ajustes_list):
    setup_final = copy.deepcopy(setup_json)
    for ajuste in ajustes_list:
        ajustes = ajuste['ajustes_json']
        for key, val in ajustes.items():
            if isinstance(val, dict) and isinstance(setup_final.get(key), dict):
                for subkey, subval in val.items():
                    setup_final[key][subkey] = round(setup_final[key].get(subkey, 0) + subval, 2)
            elif isinstance(val, (int, float)):
                setup_final[key] = round(setup_final.get(key, 0) + val, 2)
            else:
                setup_final[key] = val
    return setup_final

@app.post("/setup")
def obtener_setup_final(req: SetupRequest):
    base = obtener_setup_base(req.coche, req.circuito, req.tipo_conduccion)
    if not base:
        raise HTTPException(status_code=404, detail="Setup base no encontrado")
    ajustes = obtener_ajustes_condiciones(base['id'], req.temperatura, req.vueltas)
    setup_final = aplicar_ajustes(base['setup_json'], ajustes)
    return {"setup": setup_final}

@app.get("/opciones")
def obtener_opciones():
    response = supabase.table('setup_base').select('coche,circuito').execute()

    coches = sorted(list({row['coche'] for row in response.data}))
    circuitos = sorted(list({row['circuito'] for row in response.data}))

    return {"coches": coches, "circuitos": circuitos}

@app.get("/")
def index():
    return {"message": "API funcionando correctamente 🎉"}
