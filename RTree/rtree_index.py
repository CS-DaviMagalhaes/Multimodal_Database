from rtree import index
from metadata import RTreeMetadata

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

    def erase(self, key):
        """
        Eliminacion de un record en específico.
        Pasamos una posicion en especifico
        """
        entry = self.meta_file._get_key(key)
        if not entry:
            raise KeyError(f"Registro {key} no presente en metadata")
        
        lon, lat = entry['lon'], entry['lat']
        point = (lon, lat, lon, lat)
        self.rtree_idx.delete(entry['pos'], point)
        self.meta_file.erase(entry)