from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from supabase import create_client, Client
import copy

# Configura tus credenciales Supabase aquí
SUPABASE_URL = "https://wbdrvlozlqzpdyfwlvki.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6IndiZHJ2bG96bHF6cGR5ZndsdmtpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTA2MzMzMTMsImV4cCI6MjA2NjIwOTMxM30.U-MRsiXhfwjTRMHGpGWHoxodhd-0k4RqYFR8iBwLsIE"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

app = FastAPI()

# CORS - permite todas las peticiones (solo para desarrollo)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permite cualquier origen
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
    if response.data:
        return response.data[0]
    else:
        return None

def obtener_ajustes_condiciones(setup_base_id, temperatura, vueltas):
    response = supabase.table('ajuste_condiciones')\
        .select('*')\
        .eq('setup_base_id', setup_base_id)\
        .filter('temp_min', '<=', temperatura)\
        .filter('temp_max', '>=', temperatura)\
        .filter('vueltas_min', '<=', vueltas)\
        .filter('vueltas_max', '>=', vueltas)\
        .execute()
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
