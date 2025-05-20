from rtree import index
from record import Record

class RTreeIndex:
    """
    Manejo de archivos fisicos usando un índice bajo una estructura RTree.
    La metadata maneja {key : (lon, lat)} para cada registro del archivo.
    La libreria no maneja puntos directamente, sino como boxes de area 0.
    Para manejar puntos (lon, lat), crear box (lon, lat, lon, lat)
    """
    def __init__(self, index_name="rtree_index", main_file="main_records.dat", record_size=None):        
        self.main_file = main_file
        self.record_size = record_size
    
        p = index.Property()
        p.dimension = 2
        p.overwrite = False

        self.rtree_idx = index.Index(index_name, properties=p)

    def add(self, data):
        """
        Insertamos un record al árbol. Asumimos que la data
        viene enpaquetada antes de insertar al RTree.
        """
        rec = Record.unpack(data)
        idx = rec.id
        point = (rec.lon, rec.lat, rec.lon, rec.lat)

        self.rtree_idx.insert(idx, point)

    def search(self, key):
        """
        TODO: interpretar search() adecuado para RTree.
        Por mientras, aplicar spatial query sobre un rectangulo pequeño.
        Devuelve unicamente el id del record (normalmente 1).
        """
        lon, lat = key
        eps = 1e-7
        query = (lon-eps, lat-eps, lon+eps, lat+eps)
        match_ids = list(self.rtree_idx.intersection(query))
        return match_ids

    def range_search(self, begin_key, end_key):
        """
        Buscar puntos dentro de un box definido por (begin_key) y (end_key).
        Devuelve unicamente los indices que debe leer la clase principal
        """
        min_lon, min_lat = begin_key
        max_lon, max_lat = end_key
        query = (min_lon, min_lat, max_lon, max_lat)
        match_ids = list(self.rtree_idx.intersection(query))
        return match_ids

    def erase(self, key, coords):
        """
        Eliminacion de un record en específico.
        Le pasamos la key y las coordenadas del punto.
        """
        lon, lat = coords
        point = (lon, lat, lon, lat)
        self.rtree_idx.delete(key, point)