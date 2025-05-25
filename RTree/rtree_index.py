from rtree import index
from record import Registro
from metadata import RTreeMetadata

class RTreeIndex:
    """
    Manejo de archivos fisicos usando un índice bajo una estructura RTree.
    La metadata maneja {key : (lon, lat)} para cada registro del archivo.
    La libreria no maneja puntos directamente, sino como boxes de area 0.
    Para manejar puntos (lon, lat), crear box (lon, lat, lon, lat)
    """
    def __init__(self, index_name="rtree_index", main_file="main_records.dat", metadata_file="rtree_metadata.dat"):        
        self.main_file = main_file
    
        p = index.Property()
        p.dimension = 2
        p.overwrite = False

        self.rtree_idx = index.Index(index_name, properties=p)
        self.meta_file = RTreeMetadata(metadata_file)

    def add(self, reg: Registro, reg_pos: int):
        """
        Insertamos un record al árbol. Asumimos que la data
        viene enpaquetada antes de insertar al RTree.
        """
        point = (reg.longitude, reg.latitude, reg.longitude, reg.latitude)
        self.rtree_idx.insert(reg_pos, point)
        self.meta_file.add(reg.id, reg_pos, reg.longitude, reg.latitude)

    def box_search(self, begin_coords, end_coords):
        """
        Buscar puntos dentro de un box definido por (begin_key) y (end_key).
        Devuelve unicamente los punteros que debe leer la clase principal
        """
        min_lon, min_lat = begin_coords
        max_lon, max_lat = end_coords
        query = (min_lon, min_lat, max_lon, max_lat)
        matches = list(self.rtree_idx.intersection(query))

        results = []
        for key in matches:
            entry = self.meta_file.get(key)
            if entry:
                results.append(entry['pos'])
        return results

    def radius_search(self, key, radius):
        """
        Busca elementos dentro de un radio definido por 
        las coordenadas de un elemento dentro del árbol 
        (x,y) y un radius.
        Devuelve todos los keys dentro del círculo
        """
        centro = self.meta_file.get(key)
        if not centro:
            return []
    
        cx, cy = centro['lon'], centro['lat']
        
        min_lon, min_lat = cx - radius, cy - radius
        max_lon, max_lat = cx + radius, cy + radius

        matches = list(self.rtree_idx.intersection((min_lon, min_lat, max_lon, max_lat)))
        results = []

        for key in matches:
            e = self.meta_file.get(key)
            if e:
                dx, dy = e['lon'] - cx, e['lat'] - cy
                dist = (dx*dx + dy*dy)**0.5
                if dist <= radius:
                    results.append(e['pos'])
        
        return results

    def knn_search(self, key, k):
        """
        Devuelve los k vecinos más cercanos de cierto
        elemento dentro del árbol.
        """
        centro = self.meta_file.get(key)
        if not centro:
            return []
    
        cx, cy = centro['lon'], centro['lat']
        point = (cx, cy, cx, cy)
        neighbours = list(self.rtree_idx.nearest(point, num_results=k+1))
        matches = [nid for nid in neighbours if nid != key]

        results = []
        for key in matches:
            entry = self.meta_file.get(key)
            if entry:
                results.append(entry['pos'])
        return results

    def erase(self, key):
        """
        Eliminacion de un record en específico.
        Le pasamos la key y las coordenadas del punto.
        """
        entry = self.meta_file.get(key)
        if not entry:
            raise KeyError(f"Key {key} no presente en metadata")
        
        lon, lat = entry['lon'], entry['lan']
        point = (lon, lat, lon, lat)
        self.rtree_idx.delete(key, point)
        self.meta_file.erase(key)