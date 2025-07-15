from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from dbms import DBManager
import os

app = FastAPI()

# Habilitar CORS para permitir llamadas desde React
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Ajusta si tu frontend corre en otro puerto
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

db_manager = DBManager()

@app.post("/query")
async def recibir_query(data: dict):
    raw_query = data.get("query", "").strip()
    if not raw_query:
        return {"error": "Consulta vacía"}

    lower_raw_query = raw_query.lower()

    if lower_raw_query.startswith("create table"):
        response = db_manager.create_table(raw_query)
    elif lower_raw_query.startswith("insert into"):
        response = db_manager.insert_values(raw_query)
    elif lower_raw_query.startswith("create index"):
        response = db_manager.create_index(raw_query)
    elif lower_raw_query.startswith("select"):
        response = db_manager.select_query(raw_query)
    else:
        response = {"error": "Tipo de consulta no soportado."}
    
    return response

@app.get("/select/{tabla}")
def select_todos(tabla: str):
    response = db_manager.select_all_from_table(tabla)
    
    if "error" in response:
        raise HTTPException(status_code=404, detail=response["error"])
    
    return response

if __name__ == "__main__":
    os.makedirs("tablas", exist_ok=True)
    os.makedirs("indices", exist_ok=True)
    
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)