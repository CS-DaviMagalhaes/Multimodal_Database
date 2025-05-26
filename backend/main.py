from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from funciones import *
from registro import *
import json

app = FastAPI()

# Habilitar CORS para permitir llamadas desde React
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Ajusta si tu frontend corre en otro puerto
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/query")
async def recibir_query(data: dict):
    raw_query = data.get("query", "").strip()
    if not raw_query:
        return {"error": "Consulta vacía"}

    parsed = sqlparse.parse(raw_query)
    if not parsed:
        return {"error": "No se pudo parsear"}

    stmt = parsed[0]
    tipo = stmt.get_type()

    if tipo == "CREATE":
        parsed_info = parse_create_table(raw_query)
        
        if parsed_info is None:
            return {"error": "Error al parsear el CREATE TABLE"}

        with open(f"{parsed_info['tabla']}.meta", "w") as f:
            json.dump(parsed_info, f)

        # Opcional: crear archivo .tbl vacío desde ya
        open(f"{parsed_info['tabla']}.tbl", "ab").close()

        return {"resultado": "Simulando CREATE", "estructura": parsed_info}
    elif tipo == "INSERT":
        parsed_insert = parse_insert(raw_query)
        if not parsed_insert:
            return {"error": "INSERT mal formado"}

        tabla = parsed_insert["tabla"]
        valores = parsed_insert["valores"]

        meta_path = f"{tabla}.meta"
        if not os.path.exists(meta_path):
            return {"error": f"Tabla {tabla} no existe"}

        with open(meta_path, "r") as f:
            estructura = json.load(f)

        try:
            registro = Registro(tabla, estructura["columnas"])
            registro.insertar(valores)
            return {"resultado": "Registro insertado correctamente"}
        except ValueError as e:
            return {"error": str(e)}
    elif tipo == "SELECT":
        tabla = extraer_tabla_from_select(raw_query)
        if not tabla:
            return {"error": "No se pudo identificar la tabla en el SELECT"}

        try:
            with open(f"{tabla}.meta", "r") as f:
                estructura = json.load(f)
        except FileNotFoundError:
            return {"error": f"La tabla '{tabla}' no existe"}

        reg = Registro(tabla, estructura["columnas"])
        filas = reg.leer_todos()

        columnas = [col["nombre"] for col in estructura["columnas"]]
        resultado = [dict(zip(columnas, fila)) for fila in filas]

        return {
            "resultado": f"Consulta SELECT de tabla '{tabla}'",
            "columnas": columnas,
            "registros": resultado
        }

    return {"resultado": f"Consulta de tipo {tipo} aún no soportada"}

@app.get("/select/{tabla}")
def select_todos(tabla: str):
    try:
        with open(f"{tabla}.meta", "r") as f:
            estructura = json.load(f)
    except FileNotFoundError:
        return {"error": f"La tabla '{tabla}' no existe"}

    reg = Registro(tabla=estructura["tabla"], columnas=estructura["columnas"])
    filas = reg.leer_todos()

    # Armar respuesta con nombres de columnas
    columnas = [col["nombre"] for col in estructura["columnas"]]
    resultado = [dict(zip(columnas, fila)) for fila in filas]

    return {"tabla": tabla, "columnas": columnas, "registros": resultado}
