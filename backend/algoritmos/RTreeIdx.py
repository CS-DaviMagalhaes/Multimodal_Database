import struct
import os
from rtree import index

"""
Contiene las clases necesarias para el indice RTREE.
IMPORTANTE: para que sirva, la clase debe contener las columnas:
- longitude : entero
- latitude  : entero
Esos son los que usaremos para las queries del RTree
"""

# Metadata class
class RTreeMetadata:
    """
    Resulta que la metadata de rtree no mantiene las coordenadas de cada 
    uno de los elementos. No quedade otra que manejarlo con un archivo de 
    metadata aparte que los que crea la librería.
    
    Archivo de metadata para el RTree. Manejado con un free list, mantiene 
    el id, posicion y coordenadas de cada registro dentro del RTree.
    """
    FORMAT = 'i f f i' # key, pos, lon, lat, free
    SIZE = struct.calcsize(FORMAT)
    HEADER_FORMAT = 'i'
    HEADER_SIZE = struct.calcsize(HEADER_FORMAT)

    def __init__(self, filename):
        self.filename = filename

        if not os.path.exists(self.filename):
            with open(self.filename, 'wb') as file:
                file.write(struct.pack(self.HEADER_FORMAT, -1))
    
    def read_header(self):
        with open(self.filename, 'rb') as file:
            return struct.unpack(self.HEADER_FORMAT, file.read(self.HEADER_SIZE))[0]

    def write_header(self, head):
        with open(self.filename, 'r+b') as file:
            file.seek(0)
            file.write(struct.pack(self.HEADER_FORMAT, head))
    
    def add(self, pos, lon, lat):
        head = self.read_header()
        if head == -1:
            with open(self.filename, 'ab') as file:
                entry = struct.pack(self.FORMAT, pos, lon, lat, -1)
                file.write(entry)
        else:
            with open(self.filename, 'r+b') as file:
                entry_offset = self.HEADER_SIZE + head * self.SIZE
                file.seek(entry_offset)
                _, _, _, _, next_free = struct.unpack(self.FORMAT, file.read(self.SIZE))
                file.seek(entry_offset)
                file.write(struct.pack(self.FORMAT, pos, lon, lat, -1))
                self.write_header(next_free)
    
    def get(self, pos):
        with open(self.filename, 'rb') as file:
            file.seek(self.HEADER_SIZE)
            current_pos = 0
            while True:
                bytes_read = file.read(self.SIZE)
                if not bytes_read or len(bytes_read) < self.SIZE:
                    break
                
                unpacked = struct.unpack(self.FORMAT, bytes_read)
                stored_pos = unpacked[0]
                
                if stored_pos == -1:
                    current_pos += 1
                    continue

                if stored_pos == pos:
                    return {
                        'record_pos': unpacked[0],
                        'longitud': unpacked[1],
                        'latitud': unpacked[2],
                        'offset_in_meta_file': self.HEADER_SIZE + current_pos * self.SIZE
                    }
                current_pos += 1
        return None

    def erase(self, pos):
        entry = self.get(pos)
        if not entry:
            print(f"WARNING: No hay registro en la posicion {pos} dentro del indice RTree.")
            return

        offset = entry['offset']
        free_head = self.read_header()
        with open(self.filename, 'r+b') as file:
            file.seek(offset)
            file.write(struct.pack(self.FORMAT, -1, 0.0, 0.0, free_head))
        self.write_header((offset - self.HEADER_SIZE) // self.SIZE)

# INDEX CLASS
class RTreeIndex:
    """
    Manejo de archivos fisicos usando un índice bajo una estructura RTree.
    La metadata maneja {key : (lon, lat)} para cada registro del archivo.
    La libreria no maneja puntos directamente, sino como boxes de area 0.
    Para manejar puntos (lon, lat), crear box (lon, lat, lon, lat)
    """
    def __init__(self, index_name):            
        p = index.Property()
        p.dimension = 2
        p.overwrite = False

        self.rtree_idx = index.Index(index_name + ".rtree", properties=p)
        self.meta_file = RTreeMetadata(index_name + ".rtree.meta")

    def add(self, lon, lat, pos):
        """
        Insertamos un record al árbol.
        Pasamos las coordenadas (lon, lat) y su pos.
        """
        point = (lon, lat, lon, lat)
        self.rtree_idx.insert(pos, point)
        self.meta_file.add(pos, lon, lat)

    def box_search(self, lower_coords, upper_coords):
        """
        Buscar puntos dentro de un box definido por (lower_coords) y (upper_coords).
        Devuelve unicamente los punteros que debe leer la clase principal
        """
        min_lon, min_lat = lower_coords
        max_lon, max_lat = upper_coords
        query = (min_lon, min_lat, max_lon, max_lat)
        matches = list(self.rtree_idx.intersection(query))
        return matches if matches else None

    def radius_search(self, coords, radius):
        """
        Busca elementos dentro de un radio definido por 
        las coordenadas de un punto] (x,y) y un radio.
        Devuelve todos los keys dentro del círculo
        """    
        cx, cy = coords
        
        min_lon, min_lat = cx - radius, cy - radius
        max_lon, max_lat = cx + radius, cy + radius

        matches = list(self.rtree_idx.intersection((min_lon, min_lat, max_lon, max_lat)))
        results = []

        for pos in matches:
            e = self.meta_file.get(pos)
            if e:
                dx, dy = e['longitud'] - cx, e['latitud'] - cy
                dist = (dx*dx + dy*dy)**0.5
                if dist <= radius:
                    results.append(e['record_pos'])
        
        return results if results else None

    def knn_search(self, coords, k):
        """
        Devuelve los k vecinos más cercanos de cierto
        elemento dentro del árbol.
        """
        cx, cy = coords
        point = (cx, cy, cx, cy)
        neighbours = list(self.rtree_idx.nearest(point, num_results=k))

        vecinitos = []
        for pos in neighbours:
            if self.meta_file.get(pos):
                vecinitos.append(pos)
            if len(vecinitos) == k:
                break

        return vecinitos if vecinitos else None

    def erase(self, pos):
        """
        Eliminacion de un record en específico.
        Pasamos una posicion en especifico
        """
        entry = self.meta_file.get(pos)
        if not entry:
            print(f"WARNING: No hay registro en la posicion {pos} dentro del indice RTree.")
            return

        lon, lat = entry['longitud'], entry['latitud']
        point = (lon, lat, lon, lat)
        self.rtree_idx.delete(pos, point)
        self.meta_file.erase(pos)