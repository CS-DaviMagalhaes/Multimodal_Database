import struct
import os
from rtree_index import RTreeIndex

class Record:
    FORMAT = "i20sdd"
    SIZE = struct.calcsize(FORMAT)

    def __init__(self, id, name, lat, lon):
        self.id = id
        self.name = name
        self.lat = lat
        self.lon = lon
    
    def display(self):
        return f"[{self.id}] {self.name} : ( {self.lat} , {self.lon} )"

    def pack(self):
        return struct.pack(
            Record.FORMAT,
            self.id,
            self.name.encode(),
            self.lat,
            self.lon
        )

    @staticmethod
    def unpack(data):
        unpacked = struct.unpack(Record.FORMAT, data)
        return Record(
            unpacked[0],
            unpacked[1].decode().rstrip('\x00').strip(),
            unpacked[2],
            unpacked[3]
        )

class RecordFile:
    HEADER_SIZE = 4
    def __init__(self, filename):
        """
        Archivo almacén de records. Será la 
        base del índice creado con el RTree.
        Utiliza un header para la free list.
        """
        self.filename = filename
        self.index = RTreeIndex(index_name=f"{filename}_index", main_file=filename, record_size=Record.SIZE)

        if not os.path.exists(self.filename) or os.path.getsize(self.filename) < self.HEADER_SIZE:
            with open(self.filename, 'wb') as file:
                file.write(struct.pack('i'), -1)
    
    def _read_header(self):
        """
        Lee el header del archivo.
        """
        with open(self.filename, 'rb') as file:
            return struct.unpack('i', file.read(self.HEADER_SIZE))[0]
    
    def _write_header(self, value):
        """
        Sobreescribe el header del archivo.
        Util para actualizar la free list.
        """
        with open(self.filename, 'r+b') as file:
            file.write(struct.pack('i', value))
    
    def add(self, record):
        """
        Inserta un nuevo record al archivo.
        No interesa preservar el orden aquí.
        """
        free_pos = self._read_header()
        with open(self.filename, 'r+b') as file:
            if free_pos == -1:
                file.seek(0, os.SEEK_END)
                file.write(record.pack())
            else:
                file.seek(self.HEADER_SIZE + (free_pos * Record.SIZE) + (Record.SIZE - 4) )
                next_free = file.read(4)
                next_free = struct.unpack('i', next_free)[0]
                file.seek(self.HEADER_SIZE + free_pos * Record.SIZE)
                file.write(record.pack())
                self._write_header(next_free)
        
        # Confirmado el insert, pasamos al RTree
        self.index.add(record)

    def search(self, lon, lat):
        """
        Búsqueda dentro del archivo. Se
        apoya en el método del RTree.
        """
        coords = (lon, lat)
        match_idx = self.index.search(coords)[0]
        
        if not match_idx:
            return None

        with open(self.filename, 'rb') as file:
            file.seek(self.HEADER_SIZE + match_idx * Record.SIZE)
            record_bytes = file.read(Record.SIZE)
            if len(record_bytes) == Record.SIZE:
                record = Record.unpack(record_bytes)
                return record

    def range_search(self, min_lon, min_lat, max_lon, max_lat):
        """
        Búsqueda de rango dentro del archivo.
        Se apoya en el método del RTree.
        """
        min_coords = (min_lon, min_lat)
        max_coords = (max_lon, max_lat)
        match_ids = self.index.range_search(min_coords, max_coords)
        
        if not match_ids:
            return None

        found_records = []

        with open(self.filename, 'rb') as file:
            for idx in match_ids:
                file.seek(self.HEADER_SIZE + idx * Record.SIZE)
                record_bytes = file.read(Record.SIZE)
                if len(record_bytes) == Record.SIZE:
                    record = Record.unpack(record_bytes)
                    found_records.append(record)
        
        return found_records

    def remove(self, key):
        """
        Borra elementos usando el método dentro del RTree.
        """

        # Buscamos las coordenadas del record
        coords = (None, None)
        with open(self.filename, 'rb') as file:
            file.seek(self.HEADER_SIZE + key * Record.SIZE)
            record_bytes = file.read(Record.SIZE)
            if len(record_bytes) == Record.SIZE:
                record = Record.unpack(record_bytes)
                coords = (record.lon, record.lat)
        
        # Actualizamos la free list
        free_pos = self._read_header()
        with open(self.filename, 'r+b') as file:
            deleted = Record(0, "", 0.0, 0.0, free_pos)
            file.seek(self.HEADER_SIZE + key * Record.SIZE)
            file.write(deleted.pack())
        self._write_header(key)

        # Eliminamos en el arbol
        self.index.erase(key, coords)