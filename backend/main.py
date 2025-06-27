from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from funciones import *
from registro import *
import json
import uvicorn


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

    ''' PROBAR CREATE INDEX EN POSTMAN:
        {
    "query": "CREATE INDEX idx_nombre ON alumnos(id) USING BPLUS;"
        }
    '''
    if raw_query.lower().startswith("create index"):
        
        parsed_index = parse_create_index(raw_query)
        
        if not parsed_index:
            return {"error": "CREATE INDEX mal formado"}

        tabla = parsed_index["tabla"]
        columna = parsed_index["columna"]
        nombre_idx = parsed_index["nombre"]
        algoritmo = parsed_index.get("algoritmo", "BPLUS")  # por defecto BPLUS

        meta_path = os.path.join("tablas", f"{tabla}.meta")
        if not os.path.exists(meta_path):
            return {"error": f"La tabla '{tabla}' no existe"}

        with open(meta_path, "r") as f:
            estructura = json.load(f)

        columnas = estructura["columnas"]
        col_index = next((i for i, c in enumerate(columnas) if c["nombre"] == columna), None)
        if col_index is None:
            return {"error": f"La columna '{columna}' no existe en la tabla"}

        # Cargar clase de índice según el algoritmo solicitado
        try:
            if algoritmo == "BPLUS":
                from algoritmos.BPlusIdx import BPlusIndex as Index
            elif algoritmo == "SEQUENTIAL":
                from algoritmos.seqindex import SequentialFile as Index
            elif algoritmo == "RTREE":
                from algoritmos.rtreeidx import RTreeFile as Index
            else:
                return {"error": f"Algoritmo de índice '{algoritmo}' no soportado"}
        except ImportError:
            return {"error": f"No se encontró la implementación para el índice {algoritmo}"}

        # Leer registros y crear el índice
        reg = Registro(tabla, columnas)
        registros = reg.leer_todos()

        index_file = f"{tabla}__{columna}.idx"

        os.makedirs("indices", exist_ok=True)
        index_file = os.path.join("indices", f"{tabla}__{columna}.idx")
        index = Index(index_file)

        print("Esto es del Create index")
        for i, fila in enumerate(registros):
            key = fila[col_index]
            index.add(key, i)
            print(key,i)
        print("Fin del create index")

        
        return {
            "resultado": f"Índice '{nombre_idx}' creado en columna '{columna}' de la tabla '{tabla}' usando {algoritmo}"
        }

    parsed = sqlparse.parse(raw_query)
    if not parsed:
        return {"error": "No se pudo parsear"}

    stmt = parsed[0]
    tipo = stmt.get_type()

    if tipo == "CREATE":
        parsed_info = parse_create_table(raw_query)
        
        if parsed_info is None:
            return {"error": "Error al parsear el CREATE TABLE"}

        # Crear carpeta si no existe
        os.makedirs("tablas", exist_ok=True)

        tabla_path = os.path.join("tablas", parsed_info['tabla'])

        with open(f"{tabla_path}.meta", "w") as f:
            json.dump(parsed_info, f)

        open(f"{tabla_path}.tbl", "ab").close()

        return {"resultado": "Simulando CREATE", "estructura": parsed_info}
    
    
    elif tipo == "INSERT":
        parsed_insert = parse_insert(raw_query)
        if not parsed_insert:
            return {"error": "INSERT mal formado"}

        tabla = parsed_insert["tabla"]
        valores = parsed_insert["valores"]

        meta_path = os.path.join("tablas", f"{tabla}.meta")
        if not os.path.exists(meta_path):
            return {"error": f"Tabla {tabla} no existe"}

        with open(meta_path, "r") as f:
            estructura = json.load(f)

        try:
            registro = Registro(tabla, estructura["columnas"])
            registro.insertar(valores)

            # Verificar si hay índices existentes para esta tabla
            columnas = estructura["columnas"]
            registros_existentes = registro.leer_todos()
            pos_nueva = len(registros_existentes) - 1  # Nueva posición después de insertar

            for i, col in enumerate(columnas):
                col_nombre = col["nombre"]
                index_file = os.path.join("indices", f"{tabla}__{col_nombre}.idx")
                if os.path.exists(index_file):
                    try:
                        # Detectar algoritmo por ahora solo con BPLUS
                        if "BPLUS" in index_file.upper():
                            from algoritmos.BPlusIdx import BPlusIndex as Index
                        elif "RTREE" in index_file.upper():
                            from algoritmos.rtreeidx import RTreeFile as Index
                        elif "SEQUENTIAL" in index_file.upper():
                            from algoritmos.seqindex import SequentialFile as Index
                        else:
                            continue  # algoritmo no soportado aún

                        index = Index(index_file)
                        index.add(valores[i], pos_nueva)
                    except Exception as e:
                        print(f"No se pudo actualizar índice {index_file}: {e}")

            return {"resultado": "Registro insertado correctamente"}
        
        
        except ValueError as e:
            return {"error": str(e)}
        
    elif tipo == "SELECT":
        where_col = None
        where_val = None
        range_min = None
        range_max = None
        is_between = False
        knn = False
        box_query = False
        rad_query = False
        # Obtener tabla
        tabla = extraer_tabla_from_select(raw_query)
        if not tabla:
            return {"error": "No se pudo identificar la tabla en el SELECT"}

        # Leer estructura de la tabla
        try:
            with open(os.path.join("tablas", f"{tabla}.meta"), "r") as f:
                estructura = json.load(f)
        except FileNotFoundError:
            return {"error": f"La tabla '{tabla}' no existe"}

        columnas_disponibles = [col["nombre"] for col in estructura["columnas"]]

        # Extraer columnas solicitadas
        columnas_solicitadas = []
        parsed = sqlparse.parse(raw_query)[0]
        tokens = [t for t in parsed.tokens if not t.is_whitespace]

        try:
            idx_select = [i for i, t in enumerate(tokens) if t.value.lower() == "select"][0]
            idx_from = [i for i, t in enumerate(tokens) if t.value.lower() == "from"][0]
            columnas_raw = tokens[idx_select + 1:idx_from]
            columnas_str = "".join(t.value for t in columnas_raw).strip()
            columnas_solicitadas = [c.strip() for c in columnas_str.split(",")]

            if columnas_solicitadas == ['*']:
                columnas_solicitadas = columnas_disponibles
            else:
                # Validar que existan
                for col in columnas_solicitadas:
                    if col not in columnas_disponibles:
                        return {"error": f"La columna '{col}' no existe en la tabla '{tabla}'"}

        except Exception as e:
            return {"error": f"Error al analizar las columnas solicitadas: {str(e)}"}

        # Revisión de condición WHERE
        where_col = None
        where_val = None
        if "where" in raw_query.lower():
            lower_query = raw_query.lower()
            where_part = lower_query.split("where")[1].strip()
            if "between" in where_part and "and" in where_part:
                    # Ejemplo: edad BETWEEN 20 AND 25
                    parts = where_part.split()
                    where_col = parts[0]
                    range_min = parts[2].strip("'\"; ")
                    range_max = parts[4].strip("'\"; ")
                    is_between = True
            elif "=" in where_part:
                # Ejemplo: id = 3
                where_col, where_val = [x.strip() for x in where_part.split("=")]
                where_val = where_val.strip("'\"; ")

        # Intentar usar índice si existe
        index_file = os.path.join("indices", f"{tabla}__{where_col}.idx") if where_col else None
        posiciones_indexadas = None
        if where_col and os.path.exists(index_file):
            try:
                # Detectar algoritmo automáticamente
                # Aqui puedes agregar mas algoritmos segun el sufijo si deseas
                if "BPLUS" in index_file.upper():
                    from algoritmos.BPlusIdx import BPlusIndex as Index
                elif "SEQUENTIAL" in index_file.upper():
                    from algoritmos.seqindex import SequentialFile as Index
                elif "RTREE" in index_file.upper():
                    from algoritmos.rtreeidx import RTreeFile as Index
                else:
                    pass # CORREGIR
                print(f"Intentando abrir índice: {index_file}")

                index = Index(index_file)
                if is_between:
                    posiciones_indexadas = index.rangeSearch(range_min, range_max)
                else:
                    posiciones_indexadas = index.search(where_val)
            
            except Exception as e:
                import traceback
                print("ERROR al abrir o usar el índice:")
                traceback.print_exc()
                return {"error": f"No se pudo usar el índice: {str(e)}"}
        # Leer registros desde archivo
        reg = Registro(tabla, estructura["columnas"])
        todas_filas = reg.leer_todos()

        filas_finales = []

        if posiciones_indexadas is not None:
            for pos in posiciones_indexadas:
                if 0 <= pos < len(todas_filas):
                    filas_finales.append(todas_filas[pos])
        else:
            for fila in todas_filas:
                if not where_col:
                    filas_finales.append(fila)
                elif is_between:
                    val = fila[columnas_disponibles.index(where_col)]
                    if range_min <= str(val) <= range_max:
                        filas_finales.append(fila)
                else:
                    if str(fila[columnas_disponibles.index(where_col)]) == where_val:
                        filas_finales.append(fila)
        # Armar respuesta con columnas solicitadas
        indices_a_mostrar = [columnas_disponibles.index(col) for col in columnas_solicitadas]
        resultado = [
            {col: fila[idx] for col, idx in zip(columnas_solicitadas, indices_a_mostrar)}
            for fila in filas_finales
        ]

        return {
            "resultado": f"Consulta SELECT de tabla '{tabla}'",
            "columnas": columnas_solicitadas,
            "registros": resultado
        }

    '''
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
    '''

    
    return {"resultado": f"Consulta de tipo {tipo} aún no soportada"}

@app.get("/select/{tabla}")
def select_todos(tabla: str):
    meta_path = os.path.join("tablas", f"{tabla}.meta")

    try:
        with open(meta_path, "r") as f:
            estructura = json.load(f)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"La tabla '{tabla}' no existe")

    # Leer los registros secuencialmente desde el archivo binario
    reg = Registro(tabla=estructura["tabla"], columnas=estructura["columnas"])
    filas = reg.leer_todos()

    columnas = [col["nombre"] for col in estructura["columnas"]]
    resultado = [dict(zip(columnas, fila)) for fila in filas]

    return {
        "tabla": tabla,
        "columnas": columnas,
        "registros": resultado
    }

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
    