import struct
import os
from registro import Registro
from rtree import index

"""
Contiene las clases necesarias para el indice RTREE.
Para usarlo, importar la clase RTreeFile.
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
    FORMAT = 'i i f f i' # key, pos, lon, lat, free
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
    
    def add(self, key, pos, lon, lat):
        head = self.read_header()
        if head == -1:
            with open(self.filename, 'ab') as file:
                entry = struct.pack(self.FORMAT, key, pos, lon, lat, -1)
                file.write(entry)
        else:
            with open(self.filename, 'r+b') as file:
                entry_offset = self.HEADER_SIZE + head * self.SIZE
                file.seek(entry_offset)
                _, _, _, _, next_free = struct.unpack(self.FORMAT, file.read(self.SIZE))
                file.seek(entry_offset)
                file.write(struct.pack(self.FORMAT, key, pos, lon, lat, -1))
                self.write_header(next_free)
    
    def get(self, pos):
        offset = self.HEADER_SIZE + pos * self.SIZE 
        with open(self.filename, 'rb') as file:
            file.seek(offset)
            bytes_read = file.read(self.SIZE)

            if not bytes_read or len(bytes_read) < self.SIZE:
                return None
            
            unpacked = struct.unpack(self.FORMAT, bytes_read)
            if unpacked[0] == -1:
                return None

            return {
                'key': unpacked[0],
                'pos': unpacked[1],
                'lon': unpacked[2],
                'lat': unpacked[3],
                'offset': offset
            }

    def erase(self, entry):
        offset = entry['offset']
        free_head = self.read_header()
        with open(self.filename, 'r+b') as file:
            file.seek(offset)
            file.write(struct.pack(self.FORMAT, -1, -1, 0.0, 0.0, free_head))
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

        self.rtree_idx = index.Index(index_name, properties=p)
        self.meta_file = RTreeMetadata(index_name + ".meta.dat")

    def add(self, reg, reg_pos: int):
        """
        Insertamos un record al árbol. Asumimos que la data
        viene enpaquetada antes de insertar al RTree.
        """
        point = (reg.longitude, reg.latitude, reg.longitude, reg.latitude)
        self.rtree_idx.insert(reg_pos, point)
        self.meta_file.add(reg.id, reg_pos, reg.longitude, reg.latitude)

    def box_search(self, lower_coords, upper_coords):
        """
        Buscar puntos dentro de un box definido por (lower_coords) y (upper_coords).
        Devuelve unicamente los punteros que debe leer la clase principal
        """
        min_lon, min_lat = lower_coords
        max_lon, max_lat = upper_coords
        query = (min_lon, min_lat, max_lon, max_lat)
        matches = list(self.rtree_idx.intersection(query))
        return matches

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
                dx, dy = e['lon'] - cx, e['lat'] - cy
                dist = (dx*dx + dy*dy)**0.5
                if dist <= radius:
                    results.append(e['pos'])
        
        return results

    def knn_search(self, coords, k):
        """
        Devuelve los k vecinos más cercanos de cierto
        elemento dentro del árbol.
        """
        cx, cy = coords
        point = (cx, cy, cx, cy)
        neighbours = list(self.rtree_idx.nearest(point, num_results=k))
        return neighbours[:k]

    def erase(self, pos):
        """
        Eliminacion de un record en específico.
        Pasamos una posicion en especifico
        """
        entry = self.meta_file.get(pos)
        lon, lat = entry['lon'], entry['lat']
        point = (lon, lat, lon, lat)
        self.rtree_idx.delete(pos, point)
        self.meta_file.erase(entry)

# Manejar borrados
class FreeList:
    FORMAT = 'i'
    SIZE = struct.calcsize(FORMAT)

    def __init__(self, filename):
        self.filename = filename
        if not os.path.exists(self.filename):
            with open(self.filename, 'wb'):
                pass
    
    def get_all(self):
        with open(self.filename, 'rb') as f:
            data = f.read()
            return [pos[0] for pos in struct.iter_unpack(self.FORMAT, data)]
    
    def add(self, pos):
        with open(self.filename, 'ab') as f:
            f.write(struct.pack(self.FORMAT, pos))
    
    def pop(self):
        positions = self.get_all()
        if not positions: 
            return None
        pos = positions.pop(0)
        
        with open(self.filename, 'wb') as f:
            for p in positions:
                f.write(struct.pack(self.FORMAT, p))
            
        return pos

# MAIN CLASS
class RTreeFile:
    REG_FORMAT = Registro.get_format()
    REG_SIZE = struct.calcsize(REG_FORMAT)

    def __init__(self, filename):
        self.filename = filename + ".dat"
        self.free_list = FreeList(filename + ".free.dat")
        self.index = RTreeIndex(index_name=filename + ".rtree")

        if not os.path.exists(self.filename):
            with open(self.filename, 'wb') as file:
                pass

    def load(self):
        free_positions = set(self.free_list.get_all())
        registros = []
        with open(self.filename, 'rb') as file:
            pos = 0
            while True:
                data = file.read(self.REG_SIZE)
                if not data or len(data) < self.REG_SIZE:
                    break
                if pos not in free_positions:
                    registros.append((pos, Registro.from_bytes(data)))
                pos += 1

        return registros

    def add(self, registro, dumm):
        pos = self.free_list.pop()
        with open(self.filename, 'r+b') as file:
            if pos is not None:
                file.seek(pos * self.REG_SIZE)
            else:
                file.seek(0, os.SEEK_END)
                pos = file.tell() // self.REG_SIZE
            file.write(registro.pack())
        
        self.index.add(registro, pos)    
        return pos

    def read(self, pos):
        if pos in self.free_list.get_all():
            return None
        with open(self.filename, 'rb') as file:
            file.seek(pos * self.REG_SIZE)
            data = file.read(self.REG_SIZE)
            if not data or len(data) < self.REG_SIZE:
                return None
            return Registro.from_bytes(data)

    def box_search(self, lower_coords, upper_coords):
        matches = self.index.box_search(lower_coords, upper_coords)

        if not matches:
            return None

        registros = [self.read(match) for match in matches]            
        return registros

    def radius_search(self, coords, radius):
        matches = self.index.radius_search(coords, radius)

        if not matches:
            return None

        registros = [self.read(match) for match in matches]
        return registros

    def knn_search(self, coords, k):
        matches = self.index.knn_search(coords, k)

        if not matches:
            return None

        registros = [self.read(match) for match in matches]
        return registros

    def remove(self, pos):
        self.index.erase(pos)
        self.free_list.add(pos)