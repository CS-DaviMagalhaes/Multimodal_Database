import os
import json
import re

from registro import Registro

from algoritmos.BPlusIdx import BPlusIndex
from algoritmos.rtreeidx import RTreeIndex
from algoritmos.seqindex import SequentialFile

from funciones import *

class DBManager:
    """
    He desacoplado funciones del parseo de SQL y lo metí aca
    porque la firme me perdía un montón leyéndolo xd.
    """

    def __init__(self):
        os.makedirs("tablas", exist_ok=True)
        os.makedirs("indices", exist_ok=True)
        self.loaded_indices = {}
        self.table_schemas = {}
    
    def _load_table_schema(self, nombre_tabla):
        if nombre_tabla in self.table_schemas:
            return self.table_schemas[nombre_tabla]

        meta_path = os.path.join("tablas", f"{nombre_tabla}.meta")
        try:
            with open(meta_path, "r") as f:
                schema = json.load(f)
                self.table_schemas[nombre_tabla] = schema
                return schema
        except FileNotFoundError:
            return None
        except Exception as e:
            print(f"Error leyendo metadata para tabla '{nombre_tabla}': {str(e)}")
            return None
        
    def _get_index_instance(self, nombre_tabla, nombre_columnas_key, algoritmo, schema):
        idx_key = (nombre_tabla, nombre_columnas_key, algoritmo)

        if idx_key in self.loaded_indices:
            return self.loaded_indices[idx_key]

        idx_instance = None
        try:
            if algoritmo == "BPLUS":
                idx_filename = os.path.join("indices", f"{nombre_tabla}_{nombre_columnas_key}")
                col_info = next((c for c in schema["columnas"] if c["nombre"].lower() == nombre_columnas_key.lower()), None)

                if not col_info:
                    raise ValueError(f"No hay columna '{nombre_columnas_key}' para B+.")
                
                col_tipo = col_info['tipo']
                idx_instance = BPlusIndex(filename=idx_filename + ".idx", m=3, tipo=col_tipo)

            elif algoritmo == "SEQUENTIAL":
                idx_filename = os.path.join("indices", f"{nombre_tabla}_{nombre_columnas_key}")
                col_info = next((c for c in schema["columnas"] if c["nombre"].lower() == nombre_columnas_key.lower()), None)
                
                if not col_info:
                    raise ValueError(f"No hay columna '{nombre_columnas_key}' para el Sequential.")
                
                col_tipo = col_info['tipo']
                idx_instance = SequentialFile(filename=idx_filename, key_attr=nombre_columnas_key, key_type=col_tipo)

            elif algoritmo == "RTREE":
                idx_filename = os.path.join("indices", f"{nombre_tabla}")
                idx_instance = RTreeIndex(index_name=idx_filename)
            else:
                raise ValueError(f"Algoritmo de índice '{algoritmo}' no soportado.")
        except Exception as e:
            print(f"Error inicializando {algoritmo} para {nombre_tabla}.{nombre_columnas_key}: {e}")
            return None

        if idx_instance:
            self.loaded_indices[idx_key] = idx_instance
        return idx_instance
    
    def _get_all_indices_for_table(self, nombre_tabla):
        indices_encontrados = []
        for filename in os.listdir("indices"):
            if filename.startswith(f"{nombre_tabla}_") and filename.endswith(".idx.meta"):
                idx_meta_path = os.path.join("indices", filename)
                try:
                    with open(idx_meta_path, "r") as f:
                        idx_metadata = json.load(f)
                        required_keys = ["tabla", "columnas", "algoritmo"]
                        all_keys_present = all(k in idx_metadata for k in required_keys)
                        if all_keys_present:
                            columnas_key = idx_metadata["columnas"]
                            indices_encontrados.append((
                                idx_metadata["tabla"],
                                columnas_key,
                                idx_metadata["algoritmo"]
                            ))
                except Exception as e:
                    print(f"WARNING: No se pudo leer metadata {filename}: {e}")
        return indices_encontrados

    def create_table(self, raw_query):
        parsed_info = parse_create_table(raw_query)

        if parsed_info is None:
            return {"error": "Error al parsear el CREATE TABLE. Formato incorrecto."}

        nombre_tabla = parsed_info['tabla']
        tabla_meta_path = os.path.join("tablas", f"{nombre_tabla}.meta")
        tabla_data_path = os.path.join("tablas", f"{nombre_tabla}.tbl")

        if os.path.exists(tabla_meta_path):
            return {"error": f"La tabla '{nombre_tabla}' ya existe."}

        try:
            with open(tabla_meta_path, "w") as f:
                json.dump(parsed_info, f, indent=4)
            open(tabla_data_path, "ab").close()
            self.table_schemas[nombre_tabla] = parsed_info
            return {"resultado": f"Tabla '{nombre_tabla}' creada exitosamente.", "estructura": parsed_info}
        except Exception as e:
            return {"error": f"Error al crear la tabla '{nombre_tabla}': {str(e)}"}

    def insert_values(self, raw_query):
        parsed_insert = parse_insert(raw_query)
        if not parsed_insert:
            return {"error": "INSERT mal formado. Verifique la sintaxis."}

        nombre_tabla = parsed_insert["tabla"]
        values_insert = parsed_insert["valores"]

        schema = self._load_table_schema(nombre_tabla)
        if not schema:
            return {"error": f"La tabla '{nombre_tabla}' no existe."}

        try:
            registro_manager = Registro(nombre_tabla, schema["columnas"])
            current_records = len(registro_manager.leer_todos())
            record_pos = current_records
            registro_manager.insertar(values_insert)
            tabla_columnas = schema["columnas"]
            tabla_meta = self._get_all_indices_for_table(nombre_tabla)

            for _, nombre_columnas_key, algoritmo in tabla_meta:
                idx_instance = self._get_index_instance(nombre_tabla, nombre_columnas_key, algoritmo, schema)
                if not idx_instance:
                    print(f"WARNING: No se puede cargar índice {nombre_tabla}.{nombre_columnas_key} ({algoritmo}). Skipeando.")
                    continue

                try:
                    if algoritmo == "BPLUS" or algoritmo == "SEQUENTIAL":
                        col_info = next((c for c in tabla_columnas if c["nombre"].lower() == nombre_columnas_key.lower()), None)
                        if col_info:
                            col_idx = tabla_columnas.index(col_info)
                            key_val = values_insert[col_idx]
                            idx_instance.add(key_val, record_pos)
                            print(f"Actualizado {algoritmo} para '{nombre_columnas_key}' con key '{key_val}' en la posición {record_pos}")
                        else:
                            print(f"WARNING: No se encontró '{nombre_columnas_key}' en el schema para actualizar {algoritmo}.")
                    elif algoritmo == "RTREE":
                        lon_col_info = next((c for c in tabla_columnas if c["nombre"].lower() == "longitud"), None)
                        lat_col_info = next((c for c in tabla_columnas if c["nombre"].lower() == "latitud"), None)
                        
                        if lon_col_info and lat_col_info:
                            lon_idx = tabla_columnas.index(lon_col_info)
                            lat_idx = tabla_columnas.index(lat_col_info)
                            longitud_val = float(values_insert[lon_idx])
                            latitud_val = float(values_insert[lat_idx])
                            idx_instance.add(longitud_val, latitud_val, record_pos)
                            print(f"Actualizado RTREE para 'longitud,latitud' con key ({longitud_val}, {latitud_val}) en la posición {record_pos}")
                        else:
                            print(f"WARNING: No se encontró 'longitud' o 'latitud' en el schema para actualizar RTREE.")
                except Exception as e:
                    print(f"Advertencia: No se pudo actualizar el índice {algoritmo} para la columna(s) '{nombre_columnas_key}': {str(e)}")
            
            return {"resultado": "Registro insertado correctamente."}

        except ValueError as e:
            return {"error": str(e)}
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {"error": f"Error inesperado al insertar registro: {str(e)}"}
        
    def create_index(self, raw_query):
        parsed_idx = parse_create_index(raw_query)

        if not parsed_idx:
            return {"error": "CREATE INDEX mal formado. Verifique la sintaxis."}

        nombre_tabla = parsed_idx["tabla"]
        nombre_columnas_idx = parsed_idx["columna"]
        nombre_idx = parsed_idx["nombre"]
        algoritmo = parsed_idx.get("algoritmo", "BPLUS").upper()

        schema = self._load_table_schema(nombre_tabla)
        if not schema:
            return {"error": f"La tabla '{nombre_tabla}' no existe."}

        tabla_columnas = schema["columnas"]
        col_info_list = []
        idx_columna_filename_part = "" 

        if algoritmo == "RTREE":
            rtree_cols_check = [c.strip().lower() for c in nombre_columnas_idx.split(',')]

            if len(nombre_columnas_idx) != 2 or \
               'longitud' not in [c.lower() for c in rtree_cols_check] or \
               'latitud' not in [c.lower() for c in rtree_cols_check]:
                return {"error": "RTREE requiere columnas 'longitud' y 'latitud'."}
            
            lon_col_info = next((c for c in tabla_columnas if c["nombre"].lower() == "longitud"), None)
            lat_col_info = next((c for c in tabla_columnas if c["nombre"].lower() == "latitud"), None)
            if not lon_col_info or not lat_col_info or \
               lon_col_info['tipo'].lower() != 'int' or lat_col_info['tipo'].lower() != 'int':
                return {"error": "RTREE requiere que 'longitud' y 'latitud' sean INT."}
            
            idx_columna_filename_part = "longitud,latitud"
        else:
            if len(nombre_columnas_idx.split(',')) != 1:
                 return {"error": f"{algoritmo} requiere exactamente una sola columna."}
            
            single_columa_nombre = nombre_columnas_idx.strip()

            col_info = next((c for c in tabla_columnas if c["nombre"].lower() == single_columa_nombre.lower()), None)
            if not col_info:
                return {"error": f"No hay columna '{single_columa_nombre}' para tabla '{nombre_tabla}'."}
            col_info_list.append(col_info)

            idx_columna_filename_part = single_columa_nombre
        
        idx_instance = self._get_index_instance(nombre_tabla, idx_columna_filename_part, algoritmo, schema)
        if not idx_instance:
            return {"error": f"No se pudo inicializar el índice para el algoritmo '{algoritmo}'."}

        registro_manager = Registro(nombre_tabla, tabla_columnas)
        all_records_data_list = registro_manager.leer_todos()

        print(f"Creando índice'{nombre_idx}' para tabla '{nombre_tabla}' en '{nombre_columnas_idx}' usando {algoritmo}...")
        
        for i, record_raw_data in enumerate(all_records_data_list):
            try:
                if algoritmo == "RTREE":
                    lon_col_info = next((c for c in tabla_columnas if c["nombre"].lower() == "longitud"), None)
                    lat_col_info = next((c for c in tabla_columnas if c["nombre"].lower() == "latitud"), None)
                    lon_idx = tabla_columnas.index(lon_col_info)
                    lat_idx = tabla_columnas.index(lat_col_info)

                    longitud_val = float(record_raw_data[lon_idx])
                    latitud_val = float(record_raw_data[lat_idx])

                    idx_instance.add(longitud_val, latitud_val, i)

                elif algoritmo == "SEQUENTIAL":
                    key_col_info = col_info_list[0]
                    key_idx = tabla_columnas.index(key_col_info)
                    key_val = record_raw_data[key_idx]

                    idx_instance.add(key_val, i)

                else:
                    key_col_info = col_info_list[0]
                    key_idx = tabla_columnas.index(key_col_info)
                    key_val = record_raw_data[key_idx]

                    idx_instance.add(key_val, i)

            except Exception as e:
                print(f"WARNING: No se pudo agregar record en la posición {i} al índice {nombre_idx}. Error: {e}")

        idx_meta_path = os.path.join("indices", f"{nombre_tabla}_{idx_columna_filename_part}.idx.meta")
        idx_metadata = {
            "nombre": nombre_idx,
            "tabla": nombre_tabla,
            "columnas": idx_columna_filename_part,
            "algoritmo": algoritmo
        }
        with open(idx_meta_path, "w") as f:
            json.dump(idx_metadata, f, indent=4)

        return {
            "resultado": f"Índice '{nombre_idx}' creado en columna(s) '{nombre_columnas_idx}' de la tabla '{nombre_tabla}' usando {algoritmo}."
        }
    
    # --- QUERIES ---
    def select_query(self, raw_query):
        nombre_tabla = extraer_tabla_from_select(raw_query)
        if not nombre_tabla:
            return {"error": "No se pudo identificar la tabla en la consulta SELECT."}

        schema = self._load_table_schema(nombre_tabla)
        if not schema:
            return {"error": f"La tabla '{nombre_tabla}' no existe."}

        columnas = [col["nombre"] for col in schema["columnas"]]

        # 1. Parsear columnas del SELECT
        query_columnas = []
        try:
            parsed_stmt = sqlparse.parse(raw_query)[0]
            tokens = [t for t in parsed_stmt.tokens if not t.is_whitespace]

            idx_select = -1
            idx_from = -1
            for i, t in enumerate(tokens):
                if t.value.lower() == "select":
                    idx_select = i
                elif t.value.lower() == "from":
                    idx_from = i
                    break

            if idx_select != -1 and idx_from != -1:
                columnas_raw_tokens = tokens[idx_select + 1:idx_from]
                columnas_str = "".join(t.value for t in columnas_raw_tokens).strip()
                query_columnas = [c.strip() for c in columnas_str.split(",")]

                if '*' in query_columnas:
                    query_columnas = columnas
                else:
                    for col in query_columnas:
                        if col not in columnas:
                            return {"error": f"La columna '{col}' no existe en la tabla '{nombre_tabla}'."}
            else:
                query_columnas = columnas
        except Exception as e:
            return {"error": f"Error al analizar las columnas solicitadas: {str(e)}"}

        # 2. Parsear WHERE / tipo de query
        where_col = None
        where_val = None
        range_min = None
        range_max = None
        is_between = False
        
        box_search_coords = None
        radius_search_params = None
        knn_search_params = None

        lower_query = raw_query.lower()
        if "where" in lower_query:
            where_part = lower_query.split("where")[1].strip()

            if "between" in where_part and "and" in where_part:
                parts = where_part.split("between")
                where_col = parts[0].strip()
                range_values_part = parts[1].strip()
                range_parts = range_values_part.split("and")
                range_min = range_parts[0].strip("'\"; ").strip()
                range_max = range_parts[1].strip("'\"; ").strip()
                is_between = True
            elif "box(" in where_part:
                match = re.search(r"box\(\s*\(\s*(\-?\d+\.?\d*)\s*,\s*(\-?\d+\.?\d*)\s*\)\s*,\s*\(\s*(\-?\d+\.?\d*)\s*,\s*(\-?\d+\.?\d*)\s*\)\s*\)", where_part)
                if match:
                    min_lon, min_lat, max_lon, max_lat = map(float, match.groups())
                    box_search_coords = ((min_lon, min_lat), (max_lon, max_lat))
                    where_col = "rtree_box_search"
            elif "radius(" in where_part:
                match = re.search(r"radius\(\s*\(\s*(\-?\d+\.?\d*)\s*,\s*(\-?\d+\.?\d*)\s*\)\s*,\s*(\d+\.?\d*)\s*\)", where_part)
                if match:
                    center_lon, center_lat, radius_val = map(float, match.groups())
                    radius_search_params = ((center_lon, center_lat), radius_val)
                    where_col = "rtree_radius_search"
            elif "knn(" in where_part:
                match = re.search(r"knn\(\s*\(\s*(\-?\d+\.?\d*)\s*,\s*(\-?\d+\.?\d*)\s*\)\s*,\s*(\d+)\s*\)", where_part)
                if match:
                    target_lon, target_lat, k_value = map(float, match.groups())
                    knn_search_params = ((target_lon, target_lat), int(k_value))
                    where_col = "rtree_knn_search"
            elif "=" in where_part:
                parts = [p.strip() for p in where_part.split("=", 1)]
                if len(parts) == 2:
                    where_col = parts[0]
                    where_val = parts[1].strip(" '\";")

        # 3. Para ejecuciones específicas
        result_data = None
        algoritmo_idx = "None"

        if not where_col:
            # SELECT Básico
            result_data = self._execute_basic_select(nombre_tabla, schema, columnas)
        elif where_col.startswith("rtree_"):
            # Query básico para el RTree
            result_data, algoritmo_idx = self._execute_spatial_select(
                nombre_tabla, schema, columnas,
                box_search_coords, radius_search_params, knn_search_params
            )
        else:
            # Basic/Range query (try B+ Tree or Sequential)
            result_data, algoritmo_idx = self._execute_indexed_select(
                nombre_tabla, schema, columnas,
                where_col, where_val, is_between, range_min, range_max
            )
        
        if result_data is None:
            return {"error": "Error al ejecutar la consulta SELECT o no se encontraron registros."}

        # 4. Proyección final
        final_filtered_rows = result_data
        indices = [columnas.index(col) for col in query_columnas]
        
        result_records = [
            {col: row[idx] for col, idx in zip(query_columnas, indices)}
            for row in final_filtered_rows
        ]

        return {
            "resultado": f"Consulta SELECT de tabla '{nombre_tabla}'",
            "columnas": query_columnas,
            "registros": result_records,
            "indice_usado": algoritmo_idx
        }

    def _execute_basic_select(self, nombre_tabla, schema, columnas_disponibles):
        """
        Para un SELECT simple.
        """
        registro_manager = Registro(nombre_tabla, schema["columnas"])
        return registro_manager.leer_todos()

    def _execute_indexed_select(self, nombre_tabla, schema, columnas_disponibles, where_col, where_val, is_between, range_min, range_max):
        """
        Para SELECTs con condiciones WHERE (ideal para
        B+ Tree o un Sequential File por ejemplo)
        """
        posiciones = None
        algoritmo = "None"
        
        actual_col_for_index = next((c for c in columnas_disponibles if c.lower() == where_col.lower()), None)

        if actual_col_for_index:
            col_info = next((c for c in schema["columnas"] if c["nombre"].lower() == actual_col_for_index.lower()), None)
            if col_info:
                col_tipo = col_info['tipo']
                search_val_typed = None
                range_min_typed = None
                range_max_typed = None

                if col_tipo.lower() == 'int':
                    if is_between:
                        range_min_typed = int(range_min)
                        range_max_typed = int(range_max)
                    else:
                        search_val_typed = int(where_val)
                elif col_tipo.lower().startswith('varchar'):
                    if is_between:
                        range_min_typed = range_min
                        range_max_typed = range_max
                    else:
                        search_val_typed = where_val

                # Probando B+
                bplus_idx_info = next((idx for idx in self._get_all_indices_for_table(nombre_tabla)
                                         if idx[1].lower() == actual_col_for_index.lower() and idx[2] == "BPLUS"), None)
                if bplus_idx_info:
                    bplus_instance = self._get_index_instance(nombre_tabla, actual_col_for_index, "BPLUS", schema)
                    if bplus_instance:
                        try:
                            if is_between:
                                posiciones = bplus_instance.rangeSearch(range_min_typed, range_max_typed)
                            else:
                                posiciones = bplus_instance.search(search_val_typed)
                            
                            if posiciones is not None:
                                if not is_between and all(isinstance(x, tuple) for x in posiciones):
                                    posiciones = [x[1] for x in posiciones]
                                algoritmo = "BPLUS"
                                print(f"B+ usando para la query.")
                            else:
                                posiciones = []
                        except Exception as e:
                            print(f"Error usando B+: {e}. Fallbackeando.")
                            posiciones = None # Fallback

                # Probando el Sequential
                if posiciones is None:
                    seq_idx_info = next((idx for idx in self._get_all_indices_for_table(nombre_tabla)
                                           if idx[1].lower() == actual_col_for_index.lower() and idx[2] == "SEQUENTIAL"), None)
                    if seq_idx_info:
                        seq_instance = self._get_index_instance(nombre_tabla, actual_col_for_index, "SEQUENTIAL", schema)
                        if seq_instance:
                            try:
                                if is_between:
                                    posiciones = seq_instance.rangeSearch(range_min_typed, range_max_typed)
                                else:
                                    posiciones = seq_instance.search(search_val_typed)
                                
                                if posiciones is not None:
                                    algoritmo = "SEQUENTIAL"
                                    print(f"SEQUENTIAL usado para la query.")
                                else:
                                    posiciones = []
                            except Exception as e:
                                print(f"Error usando SEQUENTIAL: {e}. Fallbackeando.")
                                posiciones = None # Fallback
        
        # Full scan pipipipipi
        registro_manager = Registro(nombre_tabla, schema["columnas"])
        all_records = registro_manager.leer_todos()

        final_filtered_rows = []
        if posiciones is not None:
            for pos in posiciones:
                if 0 <= pos < len(all_records):
                    final_filtered_rows.append(all_records[pos])
        else:
            # Para filtrado manual
            for row_idx, row_data in enumerate(all_records):
                col_idx = -1
                for idx, col_def in enumerate(schema["columnas"]):
                    if col_def["nombre"].lower() == where_col.lower():
                        col_idx = idx
                        break
                
                if col_idx != -1:
                    val_in_row = row_data[col_idx]
                    col_tipo = schema["columnas"][col_idx]["tipo"].lower()

                    if is_between:
                        compare_val_in_row = int(val_in_row) if col_tipo == 'int' else str(val_in_row)
                        range_min_typed_manual = int(range_min) if col_tipo == 'int' else str(range_min)
                        range_max_typed_manual = int(range_max) if col_tipo == 'int' else str(range_max)
                        
                        if range_min_typed_manual <= compare_val_in_row <= range_max_typed_manual:
                            final_filtered_rows.append(row_data)
                    else: # =
                        compare_val_in_row = int(val_in_row) if col_tipo == 'int' else str(val_in_row)
                        where_val_typed_manual = int(where_val) if col_tipo == 'int' else str(where_val)
                        if compare_val_in_row == where_val_typed_manual:
                            final_filtered_rows.append(row_data)
        
        return final_filtered_rows, algoritmo

    def _execute_spatial_select(self, nombre_tabla, schema, columnas_disponibles, box_coords, radius_params, knn_params):
        """
        RTree, como trata con datos espaciales,
        tiene queries especificas, no compatibles
        con el resto de índices. No hay de otra que
        manejarlas por separado.
        """
        posiciones = None
        algoritmo = "None"

        rtree_columnas_key = "longitud,latitud" # Debe tener esas columnas
        rtree_idx_info = next((idx for idx in self._get_all_indices_for_table(nombre_tabla)
                                 if idx[1].lower() == rtree_columnas_key.lower() and idx[2] == "RTREE"), None)
        
        if rtree_idx_info:
            rtree_instance = self._get_index_instance(nombre_tabla, rtree_columnas_key, "RTREE", schema)
            if rtree_instance:
                try:
                    if box_coords:
                        posiciones = rtree_instance.box_search(box_coords[0], box_coords[1])
                    elif radius_params:
                        posiciones = rtree_instance.radius_search(radius_params[0], radius_params[1])
                    elif knn_params:
                        posiciones = rtree_instance.knn_search(knn_params[0], knn_params[1])
                    
                    if posiciones is not None:
                        algoritmo = "RTREE"
                        print(f"RTREE usado para la query.")
                    else:
                        posiciones = []
                except Exception as e:
                    print(f"Error usando RTREE: {e}.")
                    return [], "None" 

        # Sacando records
        registro_manager = Registro(nombre_tabla, schema["columnas"])
        all_records = registro_manager.leer_todos()
        
        final_filtered_rows = []
        if posiciones is not None:
            for pos in posiciones:
                if 0 <= pos < len(all_records):
                    final_filtered_rows.append(all_records[pos])
        
        return final_filtered_rows, algoritmo
    
    def select_all_from_table(self, nombre_tabla):
        schema = self._load_table_schema(nombre_tabla)
        if not schema:
            return {"error": f"La tabla '{nombre_tabla}' no existe."}

        registro_manager = Registro(nombre_tabla, schema["columnas"])
        all_rows = registro_manager.leer_todos()

        columnas = [col["nombre"] for col in schema["columnas"]]
        result_records = [dict(zip(columnas, row)) for row in all_rows]

        return {
            "tabla": nombre_tabla,
            "columnas": columnas,
            "registros": result_records
        }
